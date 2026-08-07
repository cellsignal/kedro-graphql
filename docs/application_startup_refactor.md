# Application startup architecture refactor

## Purpose

This change makes application startup a composition step rather than a hidden
Kedro runtime. The web process now loads validated configuration, reads an
immutable snapshot of project metadata, builds a FastAPI application, and
starts only the backend resource owned by that application. A `KedroSession`
is created only when a worker executes a pipeline.

The refactor removes shared module state and makes the web and worker startup
paths explicit. This document describes the resulting architecture and the
reason for each change so the full pull request can be reviewed as one design.

## Why the previous initialization was changed

Application construction previously mixed several distinct responsibilities:

- configuration was passed through untyped dictionaries and module globals;
- importing modules could load configuration or discover plugins;
- the FastAPI subclass owned Kedro session and context objects even though it
  did not execute pipelines;
- metadata used by the GraphQL schema was obtained through that session;
- workers initialized the web application even though they only need the
  backend, Celery, and Kedro's project registry;
- permissions, signed URL providers, hooks, and schema resolvers reached into
  global configuration or dynamic application attributes.

This obscured resource ownership and made initialization order significant.
It also gave the long-lived web process a Kedro execution resource for a
metadata-reading concern.

## Resulting process boundaries

### Web process

```text
`kedro-graphql gql` command options
    -> validated configuration
    -> Kedro project bootstrap
    -> project metadata snapshot
    -> FastAPI application factory
    -> backend startup during ASGI lifespan
```

The web process performs the minimum work needed to expose the API. The first
step refers to options supplied to the `kedro-graphql gql` command, for
example `--env`, `--backend`, `--app`, or `--mongo-uri`; options may be omitted
when the same values come from `.env`, environment variables, or YAML.

The startup sequence is:

1. Resolve configuration from defaults, `.env`, environment variables, CLI
   options, and an optional YAML file.
2. Bootstrap the Kedro project so its settings and pipeline registry are
   available.
3. Load the catalog, parameters, templates, and registered pipelines into a
   `ProjectMetadata` snapshot.
4. Compose the schema, permissions, providers, backend, Celery client, hooks,
   routes, and GraphQL router once in `create_app()`.
5. Start and stop the configured backend with the FastAPI lifespan.

No pipeline is executed and no `KedroSession` is created in this path.

### Worker process

```text
`kedro-graphql gql --worker` command options
    -> validated configuration
    -> Kedro project bootstrap
    -> backend and Celery worker
    -> task invocation
    -> one KedroSession for that pipeline execution
```

The worker no longer constructs routes, a GraphQL schema, project metadata, or
a FastAPI application. Project bootstrap remains necessary because Kedro uses
the project registry to resolve pipelines and settings. The task boundary in
`tasks.py` creates and closes one session for each pipeline run, which aligns
the session lifetime with the work it represents.

## Typed configuration

`KedroGraphQLConfig` in `src/kedro_graphql/config.py` is now the single
configuration representation. It is a Pydantic model with typed Python field
names and aliases for the public `KEDRO_GRAPHQL_*` names.

Configuration precedence remains:

```text
defaults < .env < environment < CLI < YAML
```

The important organizational change is that precedence is resolved once and
the result is passed explicitly. Structured fields are parsed and validated at
the boundary, while unsupported YAML fields and malformed values fail during
startup. Downstream code therefore uses typed attributes instead of repeating
dictionary lookups, conversions, and defensive type branches.

The configured `app` value now points to an application factory. The default
is `kedro_graphql.asgi.create_app`, and custom factories receive the resolved
configuration and project metadata.

## Project metadata without a session

`src/kedro_graphql/project.py` introduces the frozen `ProjectMetadata`
dataclass and `load_project_metadata()`.

The loader reads Kedro's configured `CONFIG_LOADER_CLASS` and
`CONFIG_LOADER_ARGS` directly, then gathers:

- the registered pipeline mapping;
- catalog configuration;
- project parameters;
- pipeline templates.

This data is configuration and registry metadata, not execution state. Reading
it directly avoids creating a `KedroSession`, a `KedroContext`, or mutating a
private hook manager merely to initialize the API schema.

The snapshot is intentionally process-scoped. Changes to project configuration
or registered pipelines take effect when the web process restarts, matching
the lifetime of the schema and routes built from that data.

## Application factory and runtime services

`src/kedro_graphql/asgi.py` now exposes `create_app(config, metadata) ->
FastAPI`. The custom `KedroGraphQL` FastAPI subclass was removed because the
application does not need a separate type or constructor protocol.

Composition results are collected in the frozen `AppServices` dataclass and
stored at `app.state.services`. It contains the typed configuration, project
metadata, backend, Celery application, GraphQL schema, configured permission
class, signed URL provider, and available hooks.

This gives request-time code one explicit, typed dependency root. REST route
handlers close over these services, and GraphQL receives a small
`GraphQLContext` containing the current `Request` or `WebSocket`. Resolvers,
permissions, and providers obtain process services through that request rather
than importing configuration globals or relying on attributes added to the
application dynamically.

## Resource ownership and lifetimes

| Resource | Created by | Lifetime |
| --- | --- | --- |
| Validated configuration | CLI startup | Process |
| Project metadata | Web startup | Web process |
| GraphQL schema and routes | Application factory | Web process |
| Backend connection | Web lifespan or worker startup | Owning process |
| Celery client/worker application | Web or worker composition | Owning process |
| Kedro session | Pipeline task | One pipeline execution |

FastAPI's lifespan now owns only backend startup and shutdown. This keeps
resource cleanup next to the component that opens the resource and prevents
application construction from having execution-related side effects.

## Schema, permissions, providers, and hooks

Schema construction now consumes `ProjectMetadata` instead of the global Kedro
pipeline registry or application-specific attributes. Pipeline queries,
templates, and READY-event validation therefore use the same startup snapshot.

The configured schema permission class and signed URL provider are resolved
once during application composition. `AppPermission` delegates checks to the
permission class stored in runtime services, and signed URL resolvers use the
provider stored alongside it. The local provider receives typed configuration
at construction rather than loading it independently.

Logging settings are included in the pipeline run parameters passed to the
worker. Hooks can remain stateless and no longer need application-global
configuration to determine execution logging behavior.

Unused resolver registration machinery was removed because schema extensions
already provide the supported extension point.

## Pipeline validation and execution

This refactor does not execute or validate pipelines during application
startup. Startup establishes the pipeline metadata used by the API. Validation
that depends on a requested pipeline and supplied inputs still occurs when the
READY event is handled, using the same metadata snapshot exposed by GraphQL.

Actual execution remains asynchronous through Celery. The production
`KedroSession.create()` call now exists only in the task execution path, so
each run receives an isolated session and closes it when execution finishes.

## Removed initialization contracts

The new design replaces the previous initialization model rather than keeping
two modes. In particular, this change removes:

- construction of a `KedroGraphQL` FastAPI subclass;
- application-owned `kedro_session` and Kedro context state;
- the custom application lifespan handler;
- module-level `CONFIG` and permission globals;
- global mutable CLI configuration;
- worker startup through web application construction;
- Celery's dependency on or attachment to the GraphQL schema;
- dictionary-style configuration access in the core runtime path.

Custom applications must now expose a factory accepting the typed
configuration and `ProjectMetadata`. This is a deliberate API replacement:
there is one startup contract and one place where application dependencies are
assembled.

## Test and documentation changes

Test fixtures now construct `ProjectMetadata` and call the application factory
directly. New application tests verify that metadata uses the configured Kedro
loader without opening a session and that worker initialization does not
compose the web application. Configuration tests cover typed parsing,
precedence, coercion, and startup failures.

The application extension guide, configuration reference, README, generated
API reference, example application, and changelog were updated to describe the
factory-based contract and the new ownership boundaries.

The implemented change set was validated with:

```bash
conda run -n abd pytest -q src/tests
conda run -n abd mkdocs build --strict
```

## Review guide

The central invariants reviewers should be able to trace through the diff are:

1. Configuration is validated once and passed explicitly.
2. Web startup reads metadata without creating a Kedro session.
3. The application factory is the sole composition root for web dependencies.
4. Workers initialize only worker dependencies.
5. A Kedro session exists only for the duration of one pipeline execution.
6. Request-time code obtains configured services from typed application state.
7. The replaced initialization path is removed rather than retained beside the
   new one.
