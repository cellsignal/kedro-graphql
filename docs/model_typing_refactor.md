# Model typing refactor

## Purpose

The model layer previously mixed several responsibilities behind generic `encode` and `decode` methods. A model could contain either raw dictionaries or model instances, enum fields sometimes became strings, and collection fields could be either a list or `None`. Callers consequently needed defensive `isinstance`, `None`, and string-conversion checks even after data had crossed a validated application boundary.

This refactor makes each model's in-memory shape predictable and gives every application boundary an explicit conversion method. The result is a smaller interface with fewer valid states.

## Design principles

The refactored models follow four rules:

1. Model fields have one stable Python type after construction.
2. Collection fields are lists, never `None`.
3. Enums remain enum members inside Python code.
4. Conversion methods name the boundary they serve.

The model layer does not attempt to provide a configurable serialization framework. Each supported conversion is implemented directly because the GraphQL API, document backend, Kedro runtime, and Python client require different shapes.

## Explicit conversion boundaries

The configurable `encode(encoder=...)` and `decode(..., decoder=...)` interface has been removed. Developers should use the method corresponding to the actual boundary:

| Method | Direction | Intended use |
| --- | --- | --- |
| `from_dict()` | Mapping to model | Backend documents and other internal mappings |
| `from_graphql()` | GraphQL response to model | Python client response decoding |
| `to_graphql()` | Input model to mapping | GraphQL variables sent by the Python client |
| `to_input()` | Output model to input model | Cloning or resubmitting a pipeline |
| `to_kedro()` | Pipeline model to mapping | Kedro pipeline execution |
| `to_dict()` | Model to mapping | Document persistence and general model output |

For example:

```python
pipeline = Pipeline.from_dict(document)
pipeline_input = pipeline.to_input()
graphql_variables = pipeline_input.to_graphql()
kedro_payload = pipeline.to_kedro()
```

This replaces callback-based calls whose result type depended on the supplied encoder or decoder.

## Stable collection fields

Collection fields now use non-null list types and independent empty-list defaults. This applies to fields such as:

- pipeline parameters, datasets, nodes, statuses, tags, and hooks;
- pipeline-input parameters, datasets, tags, slices, and hooks;
- dataset tags and requested partitions;
- status filtered nodes; and
- signed URL fields and grouped URLs.

Code can now iterate over these fields directly:

```python
for tag in pipeline.tags:
    process(tag)
```

Checks such as `if pipeline.tags is not None` are no longer necessary. Incoming mappings containing `null` for a collection are normalized to an empty list at the decoding boundary. In the GraphQL schema, these fields are exposed as non-null lists; input collections default to `[]` where appropriate.

## Enum consistency

Parameter types, pipeline states, input states, and pipeline-slice types now remain enum members within Python models. They are converted to GraphQL wire values only by `to_graphql()` and decoded from strings by the relevant constructor.

For example:

```python
parameter.type is ParameterType.INTEGER
status.state is State.SUCCESS
```

Developers should no longer compare these fields to string names or pass `parameter.type.name` between internal models. Pass the enum member itself.

Parameter type inference also distinguishes booleans from integers. This matters because `bool` is a subclass of `int` in Python: `True` now reliably becomes `ParameterType.BOOLEAN`, not `ParameterType.INTEGER`.

## Dataset configuration remains JSON text

`DataSet.config` deliberately remains a JSON string. This refactor does not change the stored or GraphQL representation of dataset configuration.

The output `DataSet` model requires the string because a persisted or returned dataset must have a concrete configuration. `DataSetInput.config` remains optional because some operations, such as partition discovery or signed URL requests, identify an existing dataset by name.

Use `DataSet.parse_config()` when a dictionary is required. It validates that the string contains a JSON object and raises `DataSetConfigError` for invalid JSON or a non-object value.

```python
dataset = DataSet(name="events", config='{"type": "json.JSONDataset"}')
config = dataset.parse_config()
```

## Typed partition results

`KedroGraphQLClient.read_datasets()` no longer returns an unstructured dictionary for partition-discovery results. Its return type is now:

```python
list[SignedUrl | SignedUrls | DataSetPartitions]
```

Developers should handle `DataSetPartitions` explicitly:

```python
results = await client.read_datasets(
    pipeline_id,
    [DataSetInput(name="events", list_partitions=True)],
)

partition_result = results[0]
if isinstance(partition_result, DataSetPartitions):
    for partition in partition_result.partitions:
        process(partition)
```

The client also constructs `Pipeline`, `Pipelines`, `PipelineEvent`, `PipelineLogMessage`, `SignedUrl`, and `SignedUrls` through their explicit GraphQL response constructors. It no longer mutates response dictionaries while determining union result types.

## Removed model interfaces

The unused credential input models and the model-layer `DataCatalogInput` wrapper were removed. Catalog mappings are converted directly with `dataset_inputs_from_mapping()` or `PipelineInput.create()`.

There is no transitional wrapper for the removed generic `encode` and `decode` methods. Consumers must select the explicit conversion method matching their boundary.

## Application integration changes

The schema, document backend, task execution layer, example pipelines, and UI components now share the same conversion vocabulary:

- MongoDB persistence uses `Pipeline.from_dict()` and `Pipeline.to_dict()`.
- GraphQL resolvers decode pipeline input with `Pipeline.from_dict()` and prepare execution with `Pipeline.to_kedro()`.
- Celery tasks consume `Pipeline.to_kedro()` output.
- UI cloning and retry flows use `Pipeline.to_input()` and preserve enum members.
- The Python client uses `to_graphql()` for request variables and `from_graphql()` for responses.

This organization keeps transport-specific shapes at the edge instead of allowing them to leak through the application.

## Strawberry request context correction

During validation, WebSocket subscriptions exposed a related context-construction issue. Strawberry requires a custom context to inherit from `BaseContext` or be a dictionary. `GraphQLContext` already inherits from `BaseContext`; its request field now accepts either an HTTP `Request`, a `WebSocket`, or `None`.

The FastAPI context getter creates an empty `GraphQLContext`, allowing Strawberry to inject the active HTTP request or WebSocket. This preserves one context type for queries, mutations, and subscriptions without manually binding an HTTP-only request during application setup.

## Developer migration checklist

- Replace generic model `encode` and `decode` calls with the explicit boundary method.
- Treat model collections as lists and remove `None` branches around them.
- Compare and pass enum members rather than enum names or raw strings.
- Handle partition discovery as `DataSetPartitions`, not `dict`.
- Continue passing dataset configuration as JSON text; call `parse_config()` to obtain a mapping.
- Replace removed credential or catalog wrappers with concrete input models and helper functions.

## Validation

The refactor was validated against the complete `src/tests` suite, including client, schema, signed URL, application, and WebSocket subscription behavior. The generated API reference was rebuilt, Python sources were compiled, and the documentation site was built in strict mode.
