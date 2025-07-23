# Table of Contents

* [\_\_init\_\_](#__init__)
* [\_\_main\_\_](#__main__)
* [decorators](#decorators)
  * [NameConflictError](#decorators.NameConflictError)
* [pipeline\_registry](#pipeline_registry)
  * [register\_pipelines](#pipeline_registry.register_pipelines)
* [settings](#settings)
* [celeryapp](#celeryapp)
* [client](#client)
  * [KedroGraphqlClient](#client.KedroGraphqlClient)
    * [\_\_init\_\_](#client.KedroGraphqlClient.__init__)
    * [\_get\_aio\_session](#client.KedroGraphqlClient._get_aio_session)
    * [close\_sessions](#client.KedroGraphqlClient.close_sessions)
    * [execute\_query](#client.KedroGraphqlClient.execute_query)
    * [create\_pipeline](#client.KedroGraphqlClient.create_pipeline)
    * [read\_pipeline](#client.KedroGraphqlClient.read_pipeline)
    * [read\_pipelines](#client.KedroGraphqlClient.read_pipelines)
    * [update\_pipeline](#client.KedroGraphqlClient.update_pipeline)
    * [delete\_pipeline](#client.KedroGraphqlClient.delete_pipeline)
    * [read\_dataset](#client.KedroGraphqlClient.read_dataset)
    * [create\_dataset](#client.KedroGraphqlClient.create_dataset)
    * [pipeline\_events](#client.KedroGraphqlClient.pipeline_events)
    * [pipeline\_logs](#client.KedroGraphqlClient.pipeline_logs)
* [commands](#commands)
  * [gql](#commands.gql)
* [hooks](#hooks)
  * [InvalidPipeline](#hooks.InvalidPipeline)
  * [DataValidationHooks](#hooks.DataValidationHooks)
    * [before\_pipeline\_run](#hooks.DataValidationHooks.before_pipeline_run)
  * [DataLoggingHooks](#hooks.DataLoggingHooks)
* [permissions](#permissions)
  * [IsAuthenticatedAction](#permissions.IsAuthenticatedAction)
    * [\_\_init\_\_](#permissions.IsAuthenticatedAction.__init__)
    * [get\_user\_info](#permissions.IsAuthenticatedAction.get_user_info)
    * [has\_permission](#permissions.IsAuthenticatedAction.has_permission)
  * [IsAuthenticatedAlways](#permissions.IsAuthenticatedAlways)
    * [get\_user\_info](#permissions.IsAuthenticatedAlways.get_user_info)
    * [has\_permission](#permissions.IsAuthenticatedAlways.has_permission)
  * [IsAuthenticatedXForwardedEmail](#permissions.IsAuthenticatedXForwardedEmail)
    * [has\_permission](#permissions.IsAuthenticatedXForwardedEmail.has_permission)
  * [IsAuthenticatedXForwardedRBAC](#permissions.IsAuthenticatedXForwardedRBAC)
    * [has\_permission](#permissions.IsAuthenticatedXForwardedRBAC.has_permission)
* [pipeline\_event\_monitor](#pipeline_event_monitor)
  * [PipelineEventMonitor](#pipeline_event_monitor.PipelineEventMonitor)
    * [\_\_init\_\_](#pipeline_event_monitor.PipelineEventMonitor.__init__)
    * [\_task\_event\_receiver](#pipeline_event_monitor.PipelineEventMonitor._task_event_receiver)
    * [\_start\_task\_event\_receiver\_thread](#pipeline_event_monitor.PipelineEventMonitor._start_task_event_receiver_thread)
    * [start](#pipeline_event_monitor.PipelineEventMonitor.start)
* [schema](#schema)
  * [encode\_cursor](#schema.encode_cursor)
  * [decode\_cursor](#schema.decode_cursor)
  * [Query](#schema.Query)
    * [create\_dataset](#schema.Query.create_dataset)
    * [read\_dataset](#schema.Query.read_dataset)
  * [Mutation](#schema.Mutation)
    * [create\_pipeline](#schema.Mutation.create_pipeline)
  * [Subscription](#schema.Subscription)
    * [pipeline](#schema.Subscription.pipeline)
    * [pipeline\_logs](#schema.Subscription.pipeline_logs)
* [tasks](#tasks)
  * [KedroGraphqlTask](#tasks.KedroGraphqlTask)
    * [before\_start](#tasks.KedroGraphqlTask.before_start)
    * [on\_success](#tasks.KedroGraphqlTask.on_success)
    * [on\_retry](#tasks.KedroGraphqlTask.on_retry)
    * [on\_failure](#tasks.KedroGraphqlTask.on_failure)
    * [after\_return](#tasks.KedroGraphqlTask.after_return)
  * [create\_pipeline\_input](#tasks.create_pipeline_input)
  * [handle\_event](#tasks.handle_event)
* [asgi](#asgi)
* [config](#config)
  * [load\_api\_spec](#config.load_api_spec)
  * [load\_config](#config.load_config)
* [models](#models)
  * [Parameter](#models.Parameter)
    * [decode](#models.Parameter.decode)
    * [serialize](#models.Parameter.serialize)
  * [CredentialSetInput](#models.CredentialSetInput)
    * [serialize](#models.CredentialSetInput.serialize)
  * [CredentialInput](#models.CredentialInput)
    * [serialize](#models.CredentialInput.serialize)
  * [CredentialNestedInput](#models.CredentialNestedInput)
    * [serialize](#models.CredentialNestedInput.serialize)
  * [DataSet](#models.DataSet)
    * [serialize](#models.DataSet.serialize)
    * [decode](#models.DataSet.decode)
  * [DataCatalogInput](#models.DataCatalogInput)
    * [create](#models.DataCatalogInput.create)
  * [PipelineTemplates](#models.PipelineTemplates)
    * [\_build\_pipeline\_index](#models.PipelineTemplates._build_pipeline_index)
  * [PipelineSlice](#models.PipelineSlice)
    * [args](#models.PipelineSlice.args)
  * [PipelineInput](#models.PipelineInput)
    * [create](#models.PipelineInput.create)
  * [Pipeline](#models.Pipeline)
    * [decode](#models.Pipeline.decode)
    * [decode\_pipeline\_input](#models.Pipeline.decode_pipeline_input)
  * [Pipelines](#models.Pipelines)
    * [decode](#models.Pipelines.decode)
  * [PipelineEvent](#models.PipelineEvent)
    * [decode](#models.PipelineEvent.decode)
  * [PipelineLogMessage](#models.PipelineLogMessage)
    * [decode](#models.PipelineLogMessage.decode)
* [utils](#utils)
  * [merge](#utils.merge)
  * [parse\_s3\_filepath](#utils.parse_s3_filepath)
* [backends](#backends)
* [backends.base](#backends.base)
  * [BaseBackend](#backends.base.BaseBackend)
    * [startup](#backends.base.BaseBackend.startup)
    * [shutdown](#backends.base.BaseBackend.shutdown)
    * [read](#backends.base.BaseBackend.read)
    * [list](#backends.base.BaseBackend.list)
    * [create](#backends.base.BaseBackend.create)
    * [update](#backends.base.BaseBackend.update)
    * [delete](#backends.base.BaseBackend.delete)
* [backends.mongodb](#backends.mongodb)
  * [MongoBackend](#backends.mongodb.MongoBackend)
    * [startup](#backends.mongodb.MongoBackend.startup)
    * [shutdown](#backends.mongodb.MongoBackend.shutdown)
    * [read](#backends.mongodb.MongoBackend.read)
    * [create](#backends.mongodb.MongoBackend.create)
    * [update](#backends.mongodb.MongoBackend.update)
    * [delete](#backends.mongodb.MongoBackend.delete)
* [example](#example)
* [example.app](#example.app)
* [logs](#logs)
* [logs.json\_log\_formatter](#logs.json_log_formatter)
  * [JSONFormatter](#logs.json_log_formatter.JSONFormatter)
    * [to\_json](#logs.json_log_formatter.JSONFormatter.to_json)
    * [extra\_from\_record](#logs.json_log_formatter.JSONFormatter.extra_from_record)
    * [json\_record](#logs.json_log_formatter.JSONFormatter.json_record)
    * [mutate\_json\_record](#logs.json_log_formatter.JSONFormatter.mutate_json_record)
  * [VerboseJSONFormatter](#logs.json_log_formatter.VerboseJSONFormatter)
* [logs.logger](#logs.logger)
  * [RedisLogStreamSubscriber](#logs.logger.RedisLogStreamSubscriber)
    * [create](#logs.logger.RedisLogStreamSubscriber.create)
  * [PipelineLogStream](#logs.logger.PipelineLogStream)
    * [create](#logs.logger.PipelineLogStream.create)
* [pipelines](#pipelines)
* [pipelines.example00](#pipelines.example00)
* [pipelines.example00.nodes](#pipelines.example00.nodes)
* [pipelines.example00.pipeline](#pipelines.example00.pipeline)
* [pipelines.example01](#pipelines.example01)
* [pipelines.example01.nodes](#pipelines.example01.nodes)
  * [uppercase](#pipelines.example01.nodes.uppercase)
  * [reverse](#pipelines.example01.nodes.reverse)
  * [append\_timestamp](#pipelines.example01.nodes.append_timestamp)
* [pipelines.example01.pipeline](#pipelines.example01.pipeline)
* [pipelines.event00](#pipelines.event00)
* [pipelines.event00.nodes](#pipelines.event00.nodes)
  * [create\_pipeline\_input](#pipelines.event00.nodes.create_pipeline_input)
  * [run\_example00\_via\_api](#pipelines.event00.nodes.run_example00_via_api)
* [pipelines.event00.pipeline](#pipelines.event00.pipeline)
* [plugins](#plugins)
* [plugins.plugins](#plugins.plugins)
* [runners](#runners)
* [runners.argo](#runners.argo)
* [runners.argo.argo](#runners.argo.argo)
  * [ArgoWorkflowsRunner](#runners.argo.argo.ArgoWorkflowsRunner)
    * [create\_default\_data\_set](#runners.argo.argo.ArgoWorkflowsRunner.create_default_data_set)
    * [\_run](#runners.argo.argo.ArgoWorkflowsRunner._run)
    * [create\_workflow](#runners.argo.argo.ArgoWorkflowsRunner.create_workflow)
    * [get\_workflow](#runners.argo.argo.ArgoWorkflowsRunner.get_workflow)
    * [workflow\_logs](#runners.argo.argo.ArgoWorkflowsRunner.workflow_logs)
* [ui](#ui)
* [ui.app](#ui.app)
  * [template\_factory](#ui.app.template_factory)
  * [start\_ui](#ui.app.start_ui)
* [ui.auth](#ui.auth)
  * [PKCELoginHandler](#ui.auth.PKCELoginHandler)
    * [\_fetch\_access\_token](#ui.auth.PKCELoginHandler._fetch_access_token)
    * [get](#ui.auth.PKCELoginHandler.get)
* [ui.components](#ui.components)
* [ui.components.pipeline\_cards](#ui.components.pipeline_cards)
  * [PipelineCards](#ui.components.pipeline_cards.PipelineCards)
    * [navigate](#ui.components.pipeline_cards.PipelineCards.navigate)
    * [build\_component](#ui.components.pipeline_cards.PipelineCards.build_component)
* [ui.components.pipeline\_cloning](#ui.components.pipeline_cloning)
  * [PipelineCloning](#ui.components.pipeline_cloning.PipelineCloning)
    * [\_create\_datasets\_section](#ui.components.pipeline_cloning.PipelineCloning._create_datasets_section)
    * [\_dataset\_edit\_modal](#ui.components.pipeline_cloning.PipelineCloning._dataset_edit_modal)
    * [\_delete\_dataset\_tag\_modal](#ui.components.pipeline_cloning.PipelineCloning._delete_dataset_tag_modal)
    * [\_add\_dataset\_tag\_modal](#ui.components.pipeline_cloning.PipelineCloning._add_dataset_tag_modal)
    * [\_create\_parameters\_section](#ui.components.pipeline_cloning.PipelineCloning._create_parameters_section)
    * [\_param\_edit\_modal](#ui.components.pipeline_cloning.PipelineCloning._param_edit_modal)
    * [\_create\_tags\_section](#ui.components.pipeline_cloning.PipelineCloning._create_tags_section)
    * [\_add\_tag\_modal](#ui.components.pipeline_cloning.PipelineCloning._add_tag_modal)
    * [\_tag\_edit\_modal](#ui.components.pipeline_cloning.PipelineCloning._tag_edit_modal)
    * [clone\_pipeline](#ui.components.pipeline_cloning.PipelineCloning.clone_pipeline)
* [ui.components.pipeline\_detail](#ui.components.pipeline_detail)
  * [PipelineDetail](#ui.components.pipeline_detail.PipelineDetail)
    * [build\_detail](#ui.components.pipeline_detail.PipelineDetail.build_detail)
* [ui.components.pipeline\_form\_factory](#ui.components.pipeline_form_factory)
  * [PipelineFormFactory](#ui.components.pipeline_form_factory.PipelineFormFactory)
    * [build\_options](#ui.components.pipeline_form_factory.PipelineFormFactory.build_options)
    * [build\_form](#ui.components.pipeline_form_factory.PipelineFormFactory.build_form)
* [ui.components.pipeline\_monitor](#ui.components.pipeline_monitor)
  * [PipelineMonitor](#ui.components.pipeline_monitor.PipelineMonitor)
    * [build\_table](#ui.components.pipeline_monitor.PipelineMonitor.build_table)
    * [build\_terminal](#ui.components.pipeline_monitor.PipelineMonitor.build_terminal)
* [ui.components.pipeline\_retry](#ui.components.pipeline_retry)
  * [PipelineRetry](#ui.components.pipeline_retry.PipelineRetry)
    * [build\_card](#ui.components.pipeline_retry.PipelineRetry.build_card)
    * [pipeline\_run](#ui.components.pipeline_retry.PipelineRetry.pipeline_run)
* [ui.components.pipeline\_search](#ui.components.pipeline_search)
  * [PipelineSearch](#ui.components.pipeline_search.PipelineSearch)
    * [navigate](#ui.components.pipeline_search.PipelineSearch.navigate)
    * [build\_filter](#ui.components.pipeline_search.PipelineSearch.build_filter)
    * [build\_table](#ui.components.pipeline_search.PipelineSearch.build_table)
* [ui.components.pipeline\_viz](#ui.components.pipeline_viz)
  * [PipelineViz](#ui.components.pipeline_viz.PipelineViz)
    * [load\_viz\_json](#ui.components.pipeline_viz.PipelineViz.load_viz_json)
    * [build\_viz](#ui.components.pipeline_viz.PipelineViz.build_viz)
* [ui.components.template](#ui.components.template)
  * [NavigationSidebarButton](#ui.components.template.NavigationSidebarButton)
    * [navigate](#ui.components.template.NavigationSidebarButton.navigate)
    * [build\_button](#ui.components.template.NavigationSidebarButton.build_button)
  * [TemplateMainFactory](#ui.components.template.TemplateMainFactory)
    * [build\_page](#ui.components.template.TemplateMainFactory.build_page)
  * [KedroGraphqlMaterialTemplate](#ui.components.template.KedroGraphqlMaterialTemplate)
    * [user\_menu\_action](#ui.components.template.KedroGraphqlMaterialTemplate.user_menu_action)
    * [build\_user\_menu](#ui.components.template.KedroGraphqlMaterialTemplate.build_user_menu)
    * [init\_client](#ui.components.template.KedroGraphqlMaterialTemplate.init_client)
    * [\_\_init\_\_](#ui.components.template.KedroGraphqlMaterialTemplate.__init__)
* [ui.components.data\_catalog\_explorer](#ui.components.data_catalog_explorer)
  * [DataCatalogExplorer](#ui.components.data_catalog_explorer.DataCatalogExplorer)
* [ui.components.dataset\_perspective](#ui.components.dataset_perspective)
  * [DatasetPerspective](#ui.components.dataset_perspective.DatasetPerspective)
* [ui.components.pipeline\_dashboard\_factory](#ui.components.pipeline_dashboard_factory)
  * [PipelineDashboardFactory](#ui.components.pipeline_dashboard_factory.PipelineDashboardFactory)
    * [build\_default\_dashboard](#ui.components.pipeline_dashboard_factory.PipelineDashboardFactory.build_default_dashboard)
    * [build\_custom\_dashboard](#ui.components.pipeline_dashboard_factory.PipelineDashboardFactory.build_custom_dashboard)
    * [build\_dashboard](#ui.components.pipeline_dashboard_factory.PipelineDashboardFactory.build_dashboard)
* [ui.decorators](#ui.decorators)
  * [discover\_plugins](#ui.decorators.discover_plugins)
  * [ui\_form](#ui.decorators.ui_form)
  * [ui\_data](#ui.decorators.ui_data)
  * [ui\_dashboard](#ui.decorators.ui_dashboard)
* [ui.plugins](#ui.plugins)
  * [BaseExample00Form](#ui.plugins.BaseExample00Form)
    * [navigate](#ui.plugins.BaseExample00Form.navigate)
    * [upload](#ui.plugins.BaseExample00Form.upload)
    * [pipeline\_input](#ui.plugins.BaseExample00Form.pipeline_input)
    * [run](#ui.plugins.BaseExample00Form.run)
  * [Example00PipelineFormV1](#ui.plugins.Example00PipelineFormV1)
    * [\_\_panel\_\_](#ui.plugins.Example00PipelineFormV1.__panel__)
  * [Example00PipelineFormV2](#ui.plugins.Example00PipelineFormV2)
    * [\_\_panel\_\_](#ui.plugins.Example00PipelineFormV2.__panel__)
  * [Example00Data00](#ui.plugins.Example00Data00)
    * [\_\_panel\_\_](#ui.plugins.Example00Data00.__panel__)
  * [Example00Data01](#ui.plugins.Example00Data01)
    * [build\_plot](#ui.plugins.Example00Data01.build_plot)
  * [BaseExample01Form](#ui.plugins.BaseExample01Form)
    * [navigate](#ui.plugins.BaseExample01Form.navigate)
    * [upload](#ui.plugins.BaseExample01Form.upload)
    * [pipeline\_input](#ui.plugins.BaseExample01Form.pipeline_input)
    * [run](#ui.plugins.BaseExample01Form.run)
  * [Example01PipelineFormV1](#ui.plugins.Example01PipelineFormV1)
  * [Example01PipelineUIV1](#ui.plugins.Example01PipelineUIV1)
* [signed\_url](#signed_url)
* [signed\_url.base](#signed_url.base)
  * [SignedUrlProvider](#signed_url.base.SignedUrlProvider)
    * [read](#signed_url.base.SignedUrlProvider.read)
    * [create](#signed_url.base.SignedUrlProvider.create)
* [signed\_url.local\_file\_provider](#signed_url.local_file_provider)
  * [LocalFileProvider](#signed_url.local_file_provider.LocalFileProvider)
    * [read](#signed_url.local_file_provider.LocalFileProvider.read)
    * [create](#signed_url.local_file_provider.LocalFileProvider.create)
* [signed\_url.s3\_provider](#signed_url.s3_provider)
  * [S3Provider](#signed_url.s3_provider.S3Provider)
    * [read](#signed_url.s3_provider.S3Provider.read)
    * [create](#signed_url.s3_provider.S3Provider.create)

<a id="__init__"></a>

# Module \_\_init\_\_

kedro-graphql

<a id="__main__"></a>

# Module \_\_main\_\_

kedro-graphql file for ensuring the package is executable
as `kedro-graphql` and `python -m kedro_graphql`

<a id="decorators"></a>

# Module decorators

<a id="decorators.NameConflictError"></a>

## NameConflictError Objects

```python
class NameConflictError(BaseException)
```

Raise for errors in adding plugins do to the same name.

<a id="pipeline_registry"></a>

# Module pipeline\_registry

Project pipelines.

<a id="pipeline_registry.register_pipelines"></a>

#### register\_pipelines

```python
def register_pipelines() -> Dict[str, Pipeline]
```

Register the project's pipelines.

**Returns**:

  A mapping from pipeline names to ``Pipeline`` objects.

<a id="settings"></a>

# Module settings

Project settings. There is no need to edit this file unless you want to change values
from the Kedro defaults. For further information, including these default values, see
https://kedro.readthedocs.io/en/stable/kedro_project_setup/settings.html.

<a id="celeryapp"></a>

# Module celeryapp

<a id="client"></a>

# Module client

<a id="client.KedroGraphqlClient"></a>

## KedroGraphqlClient Objects

```python
class KedroGraphqlClient()
```

<a id="client.KedroGraphqlClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__(uri_graphql=None,
             uri_ws=None,
             pipeline_gql=None,
             headers={},
             cookies=None)
```

Kwargs:
uri_graphql (str): uri to api [default: http://localhost:5000/graphql]
uri_ws (str): uri to websocket [default: ws://localhost:5000/graphql]
pipeline_gql (str): pipeline graphql query [default: kedro_graphql.client.PIPELINE_GQL]

<a id="client.KedroGraphqlClient._get_aio_session"></a>

#### \_get\_aio\_session

```python
async def _get_aio_session()
```

Get or create an aio session.

<a id="client.KedroGraphqlClient.close_sessions"></a>

#### close\_sessions

```python
async def close_sessions()
```

Close any open aio and web sessions.

<a id="client.KedroGraphqlClient.execute_query"></a>

#### execute\_query

```python
async def execute_query(query: str, variable_values: Optional[dict] = None)
```

Make a query to the GraphQL API.

Kwargs:
query (str): GraphQL query
variables (dict): GraphQL variables

**Returns**:

- `dict` - response

<a id="client.KedroGraphqlClient.create_pipeline"></a>

#### create\_pipeline

```python
async def create_pipeline(pipeline_input: PipelineInput = None)
```

Create a pipeline

Kwargs:
pipeline (PipelineInput): pipeline input object

**Returns**:

- `Pipeline` - pipeline object

<a id="client.KedroGraphqlClient.read_pipeline"></a>

#### read\_pipeline

```python
async def read_pipeline(id: str = None)
```

Read a pipeline.
Kwargs:
id (str): pipeline id

**Returns**:

- `Pipeline` - pipeline object

<a id="client.KedroGraphqlClient.read_pipelines"></a>

#### read\_pipelines

```python
async def read_pipelines(limit: int = 10,
                         cursor: str = None,
                         filter: str = "",
                         sort: str = "")
```

Read pipelines.

Kwargs:
limit (int): limit
cursor (str): cursor
filter (str): a valid MongoDb document query filter https://www.mongodb.com/docs/manual/core/document/#std-label-document-query-filter.

**Returns**:

- `Pipelines` _list_ - an list of pipeline objects

<a id="client.KedroGraphqlClient.update_pipeline"></a>

#### update\_pipeline

```python
async def update_pipeline(id: str = None,
                          pipeline_input: PipelineInput = None)
```

Update a pipeline

Kwargs:
id (str): pipeline id
pipeline_input (PipelineInput): pipeline input object

**Returns**:

- `Pipeline` - pipeline object

<a id="client.KedroGraphqlClient.delete_pipeline"></a>

#### delete\_pipeline

```python
async def delete_pipeline(id: str = None)
```

Delete a pipeline.

Kwargs:
id (str): pipeline id

**Returns**:

- `Pipeline` - pipeline object that was deleted.

<a id="client.KedroGraphqlClient.read_dataset"></a>

#### read\_dataset

```python
async def read_dataset(id: str = None,
                       name: str = None,
                       expires_in_sec: int = 43200)
```

Read a dataset.
Kwargs:
id (str): pipeline id
name (str): dataset name
expires_in_sec (int): number of seconds the signed URL should be valid for

**Returns**:

- `str` - signed URL for reading the dataset

<a id="client.KedroGraphqlClient.create_dataset"></a>

#### create\_dataset

```python
async def create_dataset(id: str = None,
                         name: str = None,
                         expires_in_sec: int = 43200)
```

create a dataset.
Kwargs:
id (str): pipeline id
name (str): dataset name
expires_in_sec (int): number of seconds the signed URL should be valid for

**Returns**:

- `str` - signed URL for creating the dataset

<a id="client.KedroGraphqlClient.pipeline_events"></a>

#### pipeline\_events

```python
@backoff.on_exception(backoff.expo,
                      Exception,
                      max_time=60,
                      giveup=lambda e: isinstance(e, TransportQueryError))
async def pipeline_events(id: str = None)
```

Subscribe to pipeline events.

Kwargs:
id (str): pipeline id

**Returns**:

- `PipelineEvent` _generator_ - a generator of PipelineEvent objects

<a id="client.KedroGraphqlClient.pipeline_logs"></a>

#### pipeline\_logs

```python
@backoff.on_exception(backoff.expo,
                      Exception,
                      max_time=60,
                      giveup=lambda e: isinstance(e, TransportQueryError))
async def pipeline_logs(id: str = None)
```

Subscribe to pipeline logs.

Kwargs:
id (str): pipeline id

**Returns**:

- `PipelineLogMessage` _generator_ - a generator of PipelineLogMessage objects

<a id="commands"></a>

# Module commands

<a id="commands.gql"></a>

#### gql

```python
@commands.command()
@click.pass_obj
@click.option("--app",
              "-a",
              default=defaults["KEDRO_GRAPHQL_APP"],
              help="Application import path")
@click.option(
    "--backend",
    default=defaults["KEDRO_GRAPHQL_BACKEND"],
    help=
    "The only supported value for this option is 'kedro_graphql.backends.mongodb.MongoBackend'"
)
@click.option("--broker",
              default=defaults["KEDRO_GRAPHQL_BROKER"],
              help="URI to broker e.g. 'redis://localhost'")
@click.option(
    "--celery-result-backend",
    default=defaults["KEDRO_GRAPHQL_CELERY_RESULT_BACKEND"],
    help="URI to backend for celery results e.g. 'redis://localhost'")
@click.option(
    "--conf-source",
    default=defaults["KEDRO_GRAPHQL_CONF_SOURCE"],
    help="Path of a directory where project configuration is stored.")
@click.option(
    "--env",
    "-e",
    default=defaults["KEDRO_GRAPHQL_ENV"],
    help="Kedro configuration environment name. Defaults to `local`.")
@click.option("--imports",
              "-i",
              default=defaults["KEDRO_GRAPHQL_IMPORTS"],
              help="Additional import paths")
@click.option(
    "--mongo-uri",
    default=defaults["KEDRO_GRAPHQL_MONGO_URI"],
    help="URI to mongodb e.g. 'mongodb://root:example@localhost:27017/'")
@click.option("--mongo-db-name",
              default=defaults["KEDRO_GRAPHQL_MONGO_DB_NAME"],
              help="Name to use for collection in mongo e.g. 'pipelines'")
@click.option(
    "--runner",
    default=defaults["KEDRO_GRAPHQL_RUNNER"],
    help=
    "Execution mechanism to run pipelines e.g. 'kedro.runner.SequentialRunner'"
)
@click.option("--log-tmp-dir",
              default=defaults["KEDRO_GRAPHQL_LOG_TMP_DIR"],
              help="Temporary directory for logs")
@click.option("--log-path-prefix",
              default=defaults["KEDRO_GRAPHQL_LOG_PATH_PREFIX"],
              help="Prefix of path to save logs")
@click.option("--reload",
              "-r",
              is_flag=True,
              default=False,
              help="Enable auto-reload.")
@click.option(
    "--reload-path",
    default=None,
    type=click.Path(exists=True, resolve_path=True, path_type=pathlib.Path),
    help="Path to watch for file changes, defaults to <project path>/src")
@click.option(
    "--api-spec",
    default=None,
    type=click.Path(exists=True, resolve_path=True, path_type=pathlib.Path),
    help="Path to watch for file changes, defaults to <project path>/src")
@click.option("--ui",
              "-u",
              is_flag=True,
              default=False,
              help="Start a viz app.")
@click.option("--ui-spec", default="", help="UI YAML specification file")
@click.option("--worker",
              "-w",
              is_flag=True,
              default=False,
              help="Start a celery worker.")
def gql(metadata, app, backend, broker, celery_result_backend, conf_source,
        env, imports, mongo_uri, mongo_db_name, runner, log_tmp_dir,
        log_path_prefix, reload, reload_path, api_spec, ui, ui_spec, worker)
```

Commands for working with kedro-graphql.

<a id="hooks"></a>

# Module hooks

<a id="hooks.InvalidPipeline"></a>

## InvalidPipeline Objects

```python
class InvalidPipeline(Exception)
```

Custom exception for invalid pipeline.

<a id="hooks.DataValidationHooks"></a>

## DataValidationHooks Objects

```python
class DataValidationHooks()
```

A Kedro hook class to validate the existence of input datasets before running a pipeline.

<a id="hooks.DataValidationHooks.before_pipeline_run"></a>

#### before\_pipeline\_run

```python
@hook_impl
def before_pipeline_run(run_params: dict[str, Any], pipeline: Pipeline,
                        catalog: CatalogProtocol) -> None
```

Hook to be invoked before a pipeline runs.

**Arguments**:

- `run_params` - The params used to run the pipeline.
- `pipeline` - The ``Pipeline`` that will be run.
- `catalog` - An implemented instance of ``CatalogProtocol`` to be used during the run.

<a id="hooks.DataLoggingHooks"></a>

## DataLoggingHooks Objects

```python
class DataLoggingHooks()
```

A Kedro hook class to save pipeline logs to S3 bucket.

<a id="permissions"></a>

# Module permissions

<a id="permissions.IsAuthenticatedAction"></a>

## IsAuthenticatedAction Objects

```python
class IsAuthenticatedAction(BasePermission)
```

Base class for authentication permissions using actions.

<a id="permissions.IsAuthenticatedAction.__init__"></a>

#### \_\_init\_\_

```python
def __init__(action)
```

Initialize the permission with a specific action.

<a id="permissions.IsAuthenticatedAction.get_user_info"></a>

#### get\_user\_info

```python
@staticmethod
def get_user_info(info: strawberry.Info) -> typing.Optional[typing.Any]
```

Get user information from the request context.
This method should be overridden in subclasses if needed.

**Arguments**:

- `info` - Strawberry Info object containing the request context.
  

**Returns**:

- `Optional[Any]` - User information, or None if not available.

<a id="permissions.IsAuthenticatedAction.has_permission"></a>

#### has\_permission

```python
def has_permission(source: typing.Any, info: strawberry.Info,
                   **kwargs) -> bool
```

Check if the user has permission for the specified action.
This method should be overridden in subclasses.

Kwargs:
source: The source of the request, typically the fields of the GraphQL query.
info: Strawberry Info object containing the request context.
**kwargs: Additional keyword arguments that may be used in the future.

**Returns**:

- `bool` - True if the user has permission, False otherwise.

<a id="permissions.IsAuthenticatedAlways"></a>

## IsAuthenticatedAlways Objects

```python
class IsAuthenticatedAlways(IsAuthenticatedAction)
```

Permission class that always grants access.

<a id="permissions.IsAuthenticatedAlways.get_user_info"></a>

#### get\_user\_info

```python
@staticmethod
def get_user_info(info: strawberry.Info) -> typing.Optional[typing.Any]
```

Get user information from the request context.
This method returns None since this permission always grants access.

**Arguments**:

- `info` - Strawberry Info object containing the request context.
  

**Returns**:

- `Optional[Any]` - Always returns None.

<a id="permissions.IsAuthenticatedAlways.has_permission"></a>

#### has\_permission

```python
def has_permission(source: typing.Any, info: strawberry.Info,
                   **kwargs) -> bool
```

Always grants permission regardless of user authentication.

Kwargs:
source: The source of the request, typically the fields of the GraphQL query.
info: Strawberry Info object containing the request context.
**kwargs: Additional keyword arguments that may be used in the future.

**Returns**:

- `bool` - Always returns True, granting permission.

<a id="permissions.IsAuthenticatedXForwardedEmail"></a>

## IsAuthenticatedXForwardedEmail Objects

```python
class IsAuthenticatedXForwardedEmail(IsAuthenticatedAction)
```

Permission class that checks for X-Forwarded-Email header.

<a id="permissions.IsAuthenticatedXForwardedEmail.has_permission"></a>

#### has\_permission

```python
def has_permission(source: typing.Any, info: strawberry.Info,
                   **kwargs) -> bool
```

Check if the user has permission based on X-Forwarded-Email header.
If the header is present, permission is granted.
If the header is not present, permission is denied.

Kwargs:
source: The source of the request, typically the fields of the GraphQL query.
info: Strawberry Info object containing the request context.
**kwargs: Additional keyword arguments that may be used in the future.

**Returns**:

- `bool` - True if the user has permission, False otherwise.

<a id="permissions.IsAuthenticatedXForwardedRBAC"></a>

## IsAuthenticatedXForwardedRBAC Objects

```python
class IsAuthenticatedXForwardedRBAC(IsAuthenticatedAction)
```

Permission class that checks for X-Forwarded-Groups header and RBAC mapping.

<a id="permissions.IsAuthenticatedXForwardedRBAC.has_permission"></a>

#### has\_permission

```python
def has_permission(source: typing.Any, info: strawberry.Info,
                   **kwargs) -> bool
```

Check if the user has permission based on X-Forwarded-Groups header and RBAC mapping.
If the header is present and the user belongs to a group that has the required role for
the specified action, permission is granted.
If the header is not present or the user does not belong to a group with the required
role for the specified action, permission is denied.

Kwargs:
source: The source of the request, typically the fields of the GraphQL query.
info: Strawberry Info object containing the request context.
**kwargs: Additional keyword arguments that may be used in the future.

**Returns**:

- `bool` - True if the user has permission, False otherwise.

<a id="pipeline_event_monitor"></a>

# Module pipeline\_event\_monitor

<a id="pipeline_event_monitor.PipelineEventMonitor"></a>

## PipelineEventMonitor Objects

```python
class PipelineEventMonitor()
```

<a id="pipeline_event_monitor.PipelineEventMonitor.__init__"></a>

#### \_\_init\_\_

```python
def __init__(app=None, task_id=None, timeout=1)
```

Kwargs:
app (Celery): celery application instance.
uuid (str): a celery task id.
timeout (float): See https://docs.python.org/3/library/queue.html#queue.Queue.get

<a id="pipeline_event_monitor.PipelineEventMonitor._task_event_receiver"></a>

#### \_task\_event\_receiver

```python
@staticmethod
def _task_event_receiver(app, queue, task_id)
```

Recieves task events from backend broker and puts them in a
Queue.  Incoming tasks are filtered and only tasks with a
root_id or uuid matching the provided id are put in the Queue.

Example event payloads:

{'hostname': 'gen36975@alligator', 'utcoffset': 5, 'pid': 36975, 'clock': 7864, 'uuid': 'd8253d45-ce28-4719-b2ba-8e266dfdaf04', 'root_id': 'd8253d45-ce28-4719-b2ba-8e266dfdaf04', 'parent_id': None, 'name': 'kedro_graphql.tasks.run_pipeline', 'args': '()', 'kwargs': "{'name': 'example00', 'inputs': {'text_in': {'type': 'text.TextDataSet', 'filepath': './data/01_raw/text_in.txt'}}, 'outputs': {'text_out': {'type': 'text.TextDataSet', 'filepath': './data/02_intermediate/text_out.txt'}}}", 'retries': 0, 'eta': None, 'expires': None, 'queue': 'celery', 'exchange': '', 'routing_key': 'celery', 'timestamp': 1672860581.1371481, 'type': 'task-sent', 'local_received': 1672860581.138474}
{'hostname': 'celery@alligator', 'utcoffset': 5, 'pid': 37029, 'clock': 7867, 'uuid': 'd8253d45-ce28-4719-b2ba-8e266dfdaf04', 'timestamp': 1672860581.1411166, 'type': 'task-started', 'local_received': 1672860581.144976}
{'hostname': 'celery@alligator', 'utcoffset': 5, 'pid': 37029, 'clock': 7870, 'uuid': 'd8253d45-ce28-4719-b2ba-8e266dfdaf04', 'result': "'success'", 'runtime': 2.013245126003312, 'timestamp': 1672860583.1549191, 'type': 'task-succeeded', 'local_received': 1672860583.158338}

**Arguments**:

- `app` _Celery_ - celery application instance.
- `queue` _Queue_ - a python queue.Queue.
- `task_id` _str_ - celery task id.

<a id="pipeline_event_monitor.PipelineEventMonitor._start_task_event_receiver_thread"></a>

#### \_start\_task\_event\_receiver\_thread

```python
def _start_task_event_receiver_thread(queue)
```

Start the task event receiver in a thread.

**Arguments**:

- `queue` _Queue_ - a python queue.Queue.
  

**Returns**:

- `worker` _threading.Thread_ - a python thread object.

<a id="pipeline_event_monitor.PipelineEventMonitor.start"></a>

#### start

```python
async def start(interval=0.5) -> AsyncGenerator[dict, None]
```

A simplified but fully async version of the PipelineEventMonitor().consume() method.

The PipelineEventMonitor.consume() method relies on celery's native
real time event processing approach which is syncronous and blocking.
https://docs.celeryq.dev/en/stable/userguide/monitoring.html#real-time-processing

<a id="schema"></a>

# Module schema

<a id="schema.encode_cursor"></a>

#### encode\_cursor

```python
def encode_cursor(id: int) -> str
```

Encodes the given id into a cursor.

:param id: The ID to encode.

:return: The encoded cursor.

<a id="schema.decode_cursor"></a>

#### decode\_cursor

```python
def decode_cursor(cursor: str) -> int
```

Decodes the ID from the given cursor.

:param cursor: The cursor to decode.

:return: The decoded user ID.

<a id="schema.Query"></a>

## Query Objects

```python
@strawberry.type
class Query()
```

<a id="schema.Query.create_dataset"></a>

#### create\_dataset

```python
@strawberry.field(
    description="Create a dataset with a signed URL",
    extensions=[
        PermissionExtension(
            permissions=[PERMISSIONS_CLASS(action="create_dataset")])
    ])
def create_dataset(
    id: str,
    info: Info,
    name: str,
    expires_in_sec: int = CONFIG["KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC"]
) -> JSON | None
```

Get a signed URL for uploading a dataset.

**Arguments**:

- `id` _str_ - The ID of the pipeline.
- `info` _Info_ - The GraphQL execution context.
- `name` _str_ - The name of the dataset.
- `expires_in_sec` _int_ - The number of seconds the signed URL should be valid for.
  

**Returns**:

  JSON | None: A signed URL for uploading the dataset or None if not applicable.
  

**Raises**:

- `ValueError` - If the dataset configuration is invalid, cannot be parsed, or greater than max expires_in_sec

<a id="schema.Query.read_dataset"></a>

#### read\_dataset

```python
@strawberry.field(
    description="Read a dataset with a signed URL",
    extensions=[
        PermissionExtension(
            permissions=[PERMISSIONS_CLASS(action="read_dataset")])
    ])
def read_dataset(
    id: str,
    info: Info,
    name: str,
    expires_in_sec: int = CONFIG["KEDRO_GRAPHQL_SIGNED_URL_MAX_EXPIRES_IN_SEC"]
) -> str | None
```

Get a signed URL for downloading a dataset.

**Arguments**:

- `id` _str_ - The ID of the pipeline.
- `info` _Info_ - The GraphQL execution context.
- `name` _str_ - The name of the dataset.
- `expires_in_sec` _int_ - The number of seconds the signed URL should be valid for.

**Returns**:

  str | None: A signed URL for downloading the dataset or None if not applicable.
  

**Raises**:

- `ValueError` - If the dataset configuration is invalid, cannot be parsed or greater than max expires_in_sec

<a id="schema.Mutation"></a>

## Mutation Objects

```python
@strawberry.type
class Mutation()
```

<a id="schema.Mutation.create_pipeline"></a>

#### create\_pipeline

```python
@strawberry.mutation(
    description="Execute a pipeline.",
    extensions=[
        PermissionExtension(
            permissions=[PERMISSIONS_CLASS(action="create_pipeline")])
    ])
def create_pipeline(pipeline: PipelineInput, info: Info) -> Pipeline
```

- is validation against template needed, e.g. check DataSet type or at least check dataset names

<a id="schema.Subscription"></a>

## Subscription Objects

```python
@strawberry.type
class Subscription()
```

<a id="schema.Subscription.pipeline"></a>

#### pipeline

```python
@strawberry.subscription(
    description="Subscribe to pipeline events.",
    extensions=[
        PermissionExtension(
            permissions=[PERMISSIONS_CLASS(action="subscribe_to_events")])
    ])
async def pipeline(
        id: str,
        info: Info,
        interval: float = 0.5) -> AsyncGenerator[PipelineEvent, None]
```

Subscribe to pipeline events.

<a id="schema.Subscription.pipeline_logs"></a>

#### pipeline\_logs

```python
@strawberry.subscription(
    description="Subscribe to pipeline logs.",
    extensions=[
        PermissionExtension(
            permissions=[PERMISSIONS_CLASS(action="subscribe_to_logs")])
    ])
async def pipeline_logs(
        id: str, info: Info) -> AsyncGenerator[PipelineLogMessage, None]
```

Subscribe to pipeline logs.

<a id="tasks"></a>

# Module tasks

<a id="tasks.KedroGraphqlTask"></a>

## KedroGraphqlTask Objects

```python
class KedroGraphqlTask(Task)
```

<a id="tasks.KedroGraphqlTask.before_start"></a>

#### before\_start

```python
def before_start(task_id, args, kwargs)
```

Handler called before the task starts.

.. versionadded:: 5.2

**Arguments**:

- `task_id` _str_ - Unique id of the task to execute.
- `args` _Tuple_ - Original arguments for the task to execute.
- `kwargs` _Dict_ - Original keyword arguments for the task to execute.
  

**Returns**:

- `None` - The return value of this handler is ignored.

<a id="tasks.KedroGraphqlTask.on_success"></a>

#### on\_success

```python
def on_success(retval, task_id, args, kwargs)
```

Success handler.

Run by the worker if the task executes successfully.

**Arguments**:

- `retval` _Any_ - The return value of the task.
- `task_id` _str_ - Unique id of the executed task.
- `args` _Tuple_ - Original arguments for the executed task.
- `kwargs` _Dict_ - Original keyword arguments for the executed task.
  

**Returns**:

- `None` - The return value of this handler is ignored.

<a id="tasks.KedroGraphqlTask.on_retry"></a>

#### on\_retry

```python
def on_retry(exc, task_id, args, kwargs, einfo)
```

Retry handler.

This is run by the worker when the task is to be retried.

**Arguments**:

- `exc` _Exception_ - The exception sent to :meth:`retry`.
- `task_id` _str_ - Unique id of the retried task.
- `args` _Tuple_ - Original arguments for the retried task.
- `kwargs` _Dict_ - Original keyword arguments for the retried task.
- `einfo` _~billiard.einfo.ExceptionInfo_ - Exception information.
  

**Returns**:

- `None` - The return value of this handler is ignored.

<a id="tasks.KedroGraphqlTask.on_failure"></a>

#### on\_failure

```python
def on_failure(exc, task_id, args, kwargs, einfo)
```

Error handler.

This is run by the worker when the task fails.

**Arguments**:

- `exc` _Exception_ - The exception raised by the task.
- `task_id` _str_ - Unique id of the failed task.
- `args` _Tuple_ - Original arguments for the task that failed.
- `kwargs` _Dict_ - Original keyword arguments for the task that failed.
- `einfo` _~billiard.einfo.ExceptionInfo_ - Exception information.
  

**Returns**:

- `None` - The return value of this handler is ignored.

<a id="tasks.KedroGraphqlTask.after_return"></a>

#### after\_return

```python
def after_return(status, retval, task_id, args, kwargs, einfo)
```

Handler called after the task returns.

**Arguments**:

- `status` _str_ - Current task state.
- `retval` _Any_ - Task return value/exception.
- `task_id` _str_ - Unique id of the task.
- `args` _Tuple_ - Original arguments for the task.
- `kwargs` _Dict_ - Original keyword arguments for the task.
- `einfo` _~billiard.einfo.ExceptionInfo_ - Exception information.
  

**Returns**:

- `None` - The return value of this handler is ignored.

<a id="tasks.create_pipeline_input"></a>

#### create\_pipeline\_input

```python
def create_pipeline_input(name: str, event: CloudEvent) -> PipelineInput
```

Create a PipelineInput object based on the event data.

**Arguments**:

- `name` _str_ - The name of the pipeline.
- `event` _CloudEvent_ - The CloudEvent object containing event data.
  

**Returns**:

- `PipelineInput` - A PipelineInput object with the event data.

<a id="tasks.handle_event"></a>

#### handle\_event

```python
@shared_task(bind=True, base=KedroGraphqlEventTask)
def handle_event(self, event: str, config: dict)
```

This function checks the event source and type against a configuration dictionary
and triggers the corresponding pipeline if a match is found.
It uses the KedroGraphqlClient to create a pipeline based on the event data.

**Arguments**:

- `event` _str_ - The CloudEvent to handle as a JSON string.
- `config` _dict_ - A dictionary mapping pipeline names to their configurations.
  
  config = {"example00_from_event": {
- `"source"` - "example.com", "type": "com.example.event"}}

**Returns**:

- `pipelines` _[dict]_ - Array of created pipeline objects encoded as dictionaries.

<a id="asgi"></a>

# Module asgi

<a id="config"></a>

# Module config

<a id="config.load_api_spec"></a>

#### load\_api\_spec

```python
def load_api_spec()
```

Load API configuration from yaml file.

<a id="config.load_config"></a>

#### load\_config

```python
def load_config()
```

Load configuration from the environment variables and API spec.

<a id="models"></a>

# Module models

<a id="models.Parameter"></a>

## Parameter Objects

```python
@strawberry.type
class Parameter()
```

<a id="models.Parameter.decode"></a>

#### decode

```python
@staticmethod
def decode(input_dict) -> dict
```

Returns a Parameter object from a dictionary.

<a id="models.Parameter.serialize"></a>

#### serialize

```python
def serialize() -> dict
```

Returns serializable dict in format compatible with kedro.

<a id="models.CredentialSetInput"></a>

## CredentialSetInput Objects

```python
@strawberry.input
class CredentialSetInput()
```

<a id="models.CredentialSetInput.serialize"></a>

#### serialize

```python
def serialize() -> dict
```

Returns serializable dict in format compatible with kedro.

<a id="models.CredentialInput"></a>

## CredentialInput Objects

```python
@strawberry.input
class CredentialInput()
```

<a id="models.CredentialInput.serialize"></a>

#### serialize

```python
def serialize() -> dict
```

Returns serializable dict in format compatible with kedro.

<a id="models.CredentialNestedInput"></a>

## CredentialNestedInput Objects

```python
@strawberry.input
class CredentialNestedInput()
```

<a id="models.CredentialNestedInput.serialize"></a>

#### serialize

```python
def serialize() -> dict
```

Returns serializable dict in format compatible with kedro.

<a id="models.DataSet"></a>

## DataSet Objects

```python
@strawberry.type
class DataSet()
```

<a id="models.DataSet.serialize"></a>

#### serialize

```python
def serialize() -> dict
```

Returns serializable dict in format compatible with kedro.

<a id="models.DataSet.decode"></a>

#### decode

```python
@staticmethod
def decode(payload)
```

Return a new DataSet from a dictionary.

**Arguments**:

- `payload` _dict_ - dict representing DataSet e.g.
  
  {
- `"name"` - "text_in",
- `"config"` - '{"filepath": "./data/01_raw/text_in.txt", "type": "text.TextDataSet", "save_args": [{"name": "say", "value": "hello"}], "load_args": [{"name": "say", "value": "hello"}]}',
- `"tags":[{"key"` - "owner name", "value": "harinlee0803"},{"key": "owner email", "value": "test@example.com"}]
  }

<a id="models.DataCatalogInput"></a>

## DataCatalogInput Objects

```python
@strawberry.input
class DataCatalogInput()
```

<a id="models.DataCatalogInput.create"></a>

#### create

```python
@staticmethod
def create(config)
```

context.config_loader["catalog"]

{'text_in': {'type': 'text.TextDataSet',
'filepath': './data/01_raw/text_in.txt'},
'text_out': {'type': 'text.TextDataSet',
'filepath': './data/02_intermediate/text_out.txt'}}

Example usage:

from kedro_graphql.models import DataCatalogInput

catalog = DataCatalogInput.create(context.config_loader["catalog"])

print(catalog)

[DataSetInput(name='text_in', config='{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}', type=None, filepath=None, save_args=None, load_args=None, credentials=None),
DataSetInput(name='text_out', config='{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}', type=None, filepath=None, save_args=None, load_args=None, credentials=None)]

<a id="models.PipelineTemplates"></a>

## PipelineTemplates Objects

```python
@strawberry.type
class PipelineTemplates()
```

<a id="models.PipelineTemplates._build_pipeline_index"></a>

#### \_build\_pipeline\_index

```python
@staticmethod
def _build_pipeline_index(kedro_pipelines, kedro_catalog, kedro_parameters)
```



<a id="models.PipelineSlice"></a>

## PipelineSlice Objects

```python
@strawberry.input(description="Slice a pipeline.")
class PipelineSlice()
```

<a id="models.PipelineSlice.args"></a>

#### args: `List[str]`

e.g. ["node1", "node2"]

<a id="models.PipelineInput"></a>

## PipelineInput Objects

```python
@strawberry.input(description="PipelineInput")
class PipelineInput()
```

<a id="models.PipelineInput.create"></a>

#### create

```python
@staticmethod
def create(name=None, data_catalog=None, parameters=None, tags=None)
```

Example usage:

from kedro_graphql.models import PipelineInput
from fastapi.encoders import jsonable_encoder

p = PipelineInput(name = "example00",
data_catalog = context.config_loader["catalog"],
parameters = context.config_loader["parameters"],
tags = [{""owner":"person"}])

print(p)

PipelineInput(name='example00',
parameters=[
ParameterInput(name='example',
value='hello',
type=<ParameterType.STRING: 'string'>),
ParameterInput(name='duration', value='1', type=<ParameterType.STRING: 'string'>)
],
data_catalog=[
DataSetInput(name='text_in', config='{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}'),
DataSetInput(name='text_out', config='{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}')
],
tags=[TagInput(key='owner', value='sean')])

print(jsonable_encoder(p))

## this can be used as the PipelineInput parameter when calleing the pipeline mutation via the API
{'name': 'example00',
'parameters': [{'name': 'example', 'value': 'hello', 'type': 'string'},
{'name': 'duration', 'value': '1', 'type': 'string'}],
'data_catalog': [{'name': 'text_in',
'config': '{"type": "text.TextDataSet", "filepath": "./data/01_raw/text_in.txt"}'},
{'name': 'text_out',
'config': '{"type": "text.TextDataSet", "filepath": "./data/02_intermediate/text_out.txt"}'}],
'tags': [{'key': 'owner', 'value': 'sean'}],
'credentials': None,
'credentials_nested': None}

<a id="models.Pipeline"></a>

## Pipeline Objects

```python
@strawberry.type
class Pipeline()
```

<a id="models.Pipeline.decode"></a>

#### decode

```python
@classmethod
def decode(cls, payload, decoder=None)
```

Factory method to create a new Pipeline from a dictionary or graphql api response.

<a id="models.Pipeline.decode_pipeline_input"></a>

#### decode\_pipeline\_input

```python
@classmethod
def decode_pipeline_input(cls, payload)
```

Factory method to create a new Pipeline from a PipelineInput object.

<a id="models.Pipelines"></a>

## Pipelines Objects

```python
@strawberry.type
class Pipelines()
```

<a id="models.Pipelines.decode"></a>

#### decode

```python
@classmethod
def decode(cls, payload, decoder=None)
```

Factory method to create a new Pipelines from a graphql api response.

<a id="models.PipelineEvent"></a>

## PipelineEvent Objects

```python
@strawberry.type
class PipelineEvent()
```

<a id="models.PipelineEvent.decode"></a>

#### decode

```python
@classmethod
def decode(cls, payload, decoder=None)
```

Factory method to create a new PipelineEvent from a graphql api response.

<a id="models.PipelineLogMessage"></a>

## PipelineLogMessage Objects

```python
@strawberry.type
class PipelineLogMessage()
```

<a id="models.PipelineLogMessage.decode"></a>

#### decode

```python
@classmethod
def decode(cls, payload, decoder=None)
```

Factory method to create a new PipelineLogMessage from a graphql api response.

<a id="utils"></a>

# Module utils

<a id="utils.merge"></a>

#### merge

```python
def merge(a, b, path=None)
```

Merges nested dictionaries recursively.  Merges b into a.

<a id="utils.parse_s3_filepath"></a>

#### parse\_s3\_filepath

```python
def parse_s3_filepath(filepath: str) -> tuple[str, str]
```

Parse the s3 bucket name and key from DataSet filepath field.

**Arguments**:

- `filepath` _str_ - The S3 file path in the format s3://bucket-name/key
  

**Returns**:

- `tuple` - A tuple containing the bucket name and the S3 key (object path).
  

**Raises**:

- `ValueError` - If the filepath does not start with "s3://" or if the bucket name or S3 key is missing.

<a id="backends"></a>

# Module backends

<a id="backends.base"></a>

# Module backends.base

<a id="backends.base.BaseBackend"></a>

## BaseBackend Objects

```python
class BaseBackend(metaclass=abc.ABCMeta)
```

<a id="backends.base.BaseBackend.startup"></a>

#### startup

```python
@abc.abstractmethod
def startup(**kwargs)
```

Startup hook.

<a id="backends.base.BaseBackend.shutdown"></a>

#### shutdown

```python
@abc.abstractmethod
def shutdown(**kwargs)
```

Shutdown hook.

<a id="backends.base.BaseBackend.read"></a>

#### read

```python
@abc.abstractmethod
def read(id: uuid.UUID = None, task_id: str = None)
```

Load a pipeline by id

<a id="backends.base.BaseBackend.list"></a>

#### list

```python
@abc.abstractmethod
def list(cursor: uuid.UUID = None,
         limit: int = None,
         filter: str = None,
         sort: str = None)
```

List pipelines using cursor pagination

<a id="backends.base.BaseBackend.create"></a>

#### create

```python
@abc.abstractmethod
def create(pipeline: Pipeline)
```

Save a pipeline

<a id="backends.base.BaseBackend.update"></a>

#### update

```python
@abc.abstractmethod
def update(pipeline: Pipeline)
```

Update a pipeline

<a id="backends.base.BaseBackend.delete"></a>

#### delete

```python
@abc.abstractmethod
def delete(id: uuid.UUID = None)
```

Delete a pipeline

<a id="backends.mongodb"></a>

# Module backends.mongodb

<a id="backends.mongodb.MongoBackend"></a>

## MongoBackend Objects

```python
class MongoBackend(BaseBackend)
```

<a id="backends.mongodb.MongoBackend.startup"></a>

#### startup

```python
def startup(**kwargs)
```

Startup hook.

<a id="backends.mongodb.MongoBackend.shutdown"></a>

#### shutdown

```python
def shutdown(**kwargs)
```

Shutdown hook.

<a id="backends.mongodb.MongoBackend.read"></a>

#### read

```python
def read(id: uuid.UUID = None, task_id: str = None)
```

Load a pipeline by id or task_id

<a id="backends.mongodb.MongoBackend.create"></a>

#### create

```python
def create(pipeline: Pipeline)
```

Save a pipeline

<a id="backends.mongodb.MongoBackend.update"></a>

#### update

```python
def update(pipeline: Pipeline = None)
```

Update a pipeline

<a id="backends.mongodb.MongoBackend.delete"></a>

#### delete

```python
def delete(id: uuid.UUID = None)
```

Delete a pipeline using id

<a id="example"></a>

# Module example

<a id="example.app"></a>

# Module example.app

<a id="logs"></a>

# Module logs

<a id="logs.json_log_formatter"></a>

# Module logs.json\_log\_formatter

<a id="logs.json_log_formatter.JSONFormatter"></a>

## JSONFormatter Objects

```python
class JSONFormatter(logging.Formatter)
```

JSON log formatter.

Usage example::

import logging

import json_log_formatter

json_handler = logging.FileHandler(filename='/var/log/my-log.json')
json_handler.setFormatter(json_log_formatter.JSONFormatter())

logger = logging.getLogger('my_json')
logger.addHandler(json_handler)

logger.info('Sign up', extra={'referral_code': '52d6ce'})

The log file will contain the following log record (inline)::

{
"message": "Sign up",
"time": "2015-09-01T06:06:26.524448",
"referral_code": "52d6ce"
}

<a id="logs.json_log_formatter.JSONFormatter.to_json"></a>

#### to\_json

```python
def to_json(record)
```

Converts record dict to a JSON string.

It makes best effort to serialize a record (represents an object as a string)
instead of raising TypeError if json library supports default argument.
Note, ujson doesn't support it.
ValueError and OverflowError are also caught to avoid crashing an app,
e.g., due to circular reference.

Override this method to change the way dict is converted to JSON.

<a id="logs.json_log_formatter.JSONFormatter.extra_from_record"></a>

#### extra\_from\_record

```python
def extra_from_record(record)
```

Returns `extra` dict you passed to logger.

The `extra` keyword argument is used to populate the `__dict__` of
the `LogRecord`.

<a id="logs.json_log_formatter.JSONFormatter.json_record"></a>

#### json\_record

```python
def json_record(message, extra, record)
```

Prepares a JSON payload which will be logged.

Override this method to change JSON log format.

:param message: Log message, e.g., `logger.info(msg='Sign up')`.
:param extra: Dictionary that was passed as `extra` param
`logger.info('Sign up', extra={'referral_code': '52d6ce'})`.
:param record: `LogRecord` we got from `JSONFormatter.format()`.
:return: Dictionary which will be passed to JSON lib.

<a id="logs.json_log_formatter.JSONFormatter.mutate_json_record"></a>

#### mutate\_json\_record

```python
def mutate_json_record(json_record)
```

Override it to convert fields of `json_record` to needed types.

Default implementation converts `datetime` to string in ISO8601 format.

<a id="logs.json_log_formatter.VerboseJSONFormatter"></a>

## VerboseJSONFormatter Objects

```python
class VerboseJSONFormatter(JSONFormatter)
```

JSON log formatter with built-in log record attributes such as log level.

Usage example::

import logging

import json_log_formatter

json_handler = logging.FileHandler(filename='/var/log/my-log.json')
json_handler.setFormatter(json_log_formatter.VerboseJSONFormatter())

logger = logging.getLogger('my_verbose_json')
logger.addHandler(json_handler)

logger.error('An error has occured')

The log file will contain the following log record (inline)::

{
"filename": "tests.py",
"funcName": "test_file_name_is_testspy",
"levelname": "ERROR",
"lineno": 276,
"module": "tests",
"name": "my_verbose_json",
"pathname": "/Users/bob/json-log-formatter/tests.py",
"process": 3081,
"processName": "MainProcess",
"stack_info": null,
"thread": 4664270272,
"threadName": "MainThread",
"message": "An error has occured",
"time": "2021-07-04T21:05:42.767726"
}

Read more about the built-in log record attributes
https://docs.python.org/3/library/logging.html#logrecord-attributes.

<a id="logs.logger"></a>

# Module logs.logger

<a id="logs.logger.RedisLogStreamSubscriber"></a>

## RedisLogStreamSubscriber Objects

```python
class RedisLogStreamSubscriber(object)
```

<a id="logs.logger.RedisLogStreamSubscriber.create"></a>

#### create

```python
@classmethod
async def create(cls, topic, broker_url=None)
```

Factory method for async instantiation RedisLogStreamSubscriber objects.

<a id="logs.logger.PipelineLogStream"></a>

## PipelineLogStream Objects

```python
class PipelineLogStream()
```

<a id="logs.logger.PipelineLogStream.create"></a>

#### create

```python
@classmethod
async def create(cls, task_id, broker_url=None)
```

Factory method for async instantiation PipelineLogStream objects.

<a id="pipelines"></a>

# Module pipelines

<a id="pipelines.example00"></a>

# Module pipelines.example00

This is a boilerplate pipeline 'example00'
generated using Kedro 0.18.4

<a id="pipelines.example00.nodes"></a>

# Module pipelines.example00.nodes

This is a boilerplate pipeline 'example00'
generated using Kedro 0.18.4

<a id="pipelines.example00.pipeline"></a>

# Module pipelines.example00.pipeline

This is a boilerplate pipeline 'example00'
generated using Kedro 0.18.4

<a id="pipelines.example01"></a>

# Module pipelines.example01

This is a boilerplate pipeline 'example01'
generated using Kedro 0.19.11

<a id="pipelines.example01.nodes"></a>

# Module pipelines.example01.nodes

This is a boilerplate pipeline 'example01'
generated using Kedro 0.19.11

<a id="pipelines.example01.nodes.uppercase"></a>

#### uppercase

```python
def uppercase(text: str) -> str
```

Converts text to uppercase.

<a id="pipelines.example01.nodes.reverse"></a>

#### reverse

```python
def reverse(text: str) -> str
```

Reverses the given text.

<a id="pipelines.example01.nodes.append_timestamp"></a>

#### append\_timestamp

```python
def append_timestamp(text: str) -> str
```

Appends a timestamp to the text.

<a id="pipelines.example01.pipeline"></a>

# Module pipelines.example01.pipeline

This is a boilerplate pipeline 'example01'
generated using Kedro 0.19.11

<a id="pipelines.event00"></a>

# Module pipelines.event00

This is a boilerplate pipeline 'event00'
generated using Kedro 0.19.11

<a id="pipelines.event00.nodes"></a>

# Module pipelines.event00.nodes

This is a boilerplate pipeline 'event00'
generated using Kedro 0.19.11

<a id="pipelines.event00.nodes.create_pipeline_input"></a>

#### create\_pipeline\_input

```python
def create_pipeline_input(id: str, event: CloudEvent) -> PipelineInput
```

Create a PipelineInput object based on the provided ID and CloudEvent.

**Arguments**:

- `id` _str_ - The ID of the pipeline to which this node belongs.
- `event` _CloudEvent_ - A CloudEvent object containing event data.
  

**Returns**:

- `PipelineInput` - A PipelineInput object ready for use in the pipeline.

<a id="pipelines.event00.nodes.run_example00_via_api"></a>

#### run\_example00\_via\_api

```python
def run_example00_via_api(id: str, event: DictConfig) -> dict
```

Example node that parse a cloudevent passed as json
and triggers the example00 pipeline via the GraphQL API.

**Arguments**:

- `id` _str_ - The ID of the pipeline to which this node belongs.
- `event` _str_ - A JSON string representing a CloudEvent.
  

**Returns**:

- `dict` - A dictionary representation of the created pipeline.

<a id="pipelines.event00.pipeline"></a>

# Module pipelines.event00.pipeline

This is a boilerplate pipeline 'event00'
generated using Kedro 0.19.11

<a id="plugins"></a>

# Module plugins

<a id="plugins.plugins"></a>

# Module plugins.plugins

<a id="runners"></a>

# Module runners

<a id="runners.argo"></a>

# Module runners.argo

<a id="runners.argo.argo"></a>

# Module runners.argo.argo

<a id="runners.argo.argo.ArgoWorkflowsRunner"></a>

## ArgoWorkflowsRunner Objects

```python
class ArgoWorkflowsRunner(AbstractRunner)
```

``ArgoWorkflowsRunner`` is an ``AbstractRunner`` implementation. It can be used
to run pipelines on [argo workflows](https://argoproj.github.io/argo-workflows/).

<a id="runners.argo.argo.ArgoWorkflowsRunner.create_default_data_set"></a>

#### create\_default\_data\_set

```python
def create_default_data_set(ds_name: str) -> AbstractDataSet
```

Factory method for creating the default data set for the runner.

NOTE THIS SHOULD BE CHANGED TO SOMETHING S3 COMPATIBLE.

**Arguments**:

- `ds_name` - Name of the missing data set

**Returns**:

  An instance of an implementation of AbstractDataSet to be used
  for all unregistered data sets.

<a id="runners.argo.argo.ArgoWorkflowsRunner._run"></a>

#### \_run

```python
def _run(pipeline: Pipeline,
         catalog: DataCatalog,
         hook_manager: PluginManager = None,
         session_id: str = None) -> None
```

The method implementing argo workflows pipeline running.
Example logs output using this implementation:



**Arguments**:

- `pipeline` - The ``Pipeline`` to run.
- `catalog` - The ``DataCatalog`` from which to fetch data.
- `session_id` - The id of the session.

<a id="runners.argo.argo.ArgoWorkflowsRunner.create_workflow"></a>

#### create\_workflow

```python
def create_workflow(manifest)
```



<a id="runners.argo.argo.ArgoWorkflowsRunner.get_workflow"></a>

#### get\_workflow

```python
def get_workflow(name)
```



<a id="runners.argo.argo.ArgoWorkflowsRunner.workflow_logs"></a>

#### workflow\_logs

```python
def workflow_logs(name)
```

Inspired by https://github.com/argoproj/argo-workflows/issues/4017

<a id="ui"></a>

# Module ui

<a id="ui.app"></a>

# Module ui.app

A python panel app for visualizing Kedro pipelines.

<a id="ui.app.template_factory"></a>

#### template\_factory

```python
def template_factory(spec={})
```

Factory function to create a Kedro GraphQL UI template.

**Arguments**:

- `spec` _dict_ - The specification for the UI, containing configuration and pages.

**Returns**:

- `dict` - A dictionary mapping the base URL to a function that builds the template.

<a id="ui.app.start_ui"></a>

#### start\_ui

```python
def start_ui(config={}, spec="")
```

Start the Kedro GraphQL UI application.

**Arguments**:

- `config` _dict_ - Configuration dictionary.
- `spec` _str_ - Path to the YAML specification file for the UI.

<a id="ui.auth"></a>

# Module ui.auth

<a id="ui.auth.PKCELoginHandler"></a>

## PKCELoginHandler Objects

```python
class PKCELoginHandler(GenericLoginHandler)
```

Handles the PKCE login flow for Panel.

<a id="ui.auth.PKCELoginHandler._fetch_access_token"></a>

#### \_fetch\_access\_token

```python
async def _fetch_access_token(client_id,
                              redirect_uri=None,
                              client_secret=None,
                              code=None,
                              refresh_token=None,
                              username=None,
                              password=None)
```

Overrides the panel.auth.OAuthLoginHandler._fetch_access_token method to implement the PKCE flow.
See https://github.com/holoviz/panel/issues/7979.

Fetches the access token.

Parameters
----------
client_id:
The client ID
redirect_uri:
The redirect URI
code:
The response code from the server
client_secret:
The client secret
refresh_token:
A token used for refreshing the access_token
username:
A username
password:
A password

<a id="ui.auth.PKCELoginHandler.get"></a>

#### get

```python
async def get()
```

Handles the GET request for the PKCE login flow.

Copied and modified from panel.auth.CodeChallengeLoginHandler
See https://github.com/holoviz/panel/issues/7979

<a id="ui.components"></a>

# Module ui.components

<a id="ui.components.pipeline_cards"></a>

# Module ui.components.pipeline\_cards

<a id="ui.components.pipeline_cards.PipelineCards"></a>

## PipelineCards Objects

```python
class PipelineCards(pn.viewable.Viewer)
```

A component that displays cards for each pipeline with registered @ui_form plugins.
This component allows users to navigate to a form for running a pipeline or exploring it.

**Attributes**:

- `spec` _dict_ - The specification for the UI, including configuration and pages.
- `explore_page` _str_ - The page to navigate to when a pipeline is explored.
- `form_page` _str_ - The page to navigate to when a form is selected.

<a id="ui.components.pipeline_cards.PipelineCards.navigate"></a>

#### navigate

```python
def navigate(button_click, event=None, pipeline=None, form=None)
```

Navigate to the specified page with the given pipeline and form.

**Arguments**:

- `button_click` _pn.widgets.Button_ - The button that was clicked.
- `event` _str_ - The event that triggered the navigation, either "run" or "explore".
- `pipeline` _str_ - The name of the pipeline to navigate to.
- `form` _panel.viewable.Viewer_ - The form to navigate to.

<a id="ui.components.pipeline_cards.PipelineCards.build_component"></a>

#### build\_component

```python
@param.depends("explore_page", "form_page")
async def build_component()
```

Builds the pipeline cards component, displaying all pipelines that have a @ui_form plugin registered.

**Yields**:

- `pn.FlexBox` - A flexible box containing cards for each pipeline.

<a id="ui.components.pipeline_cloning"></a>

# Module ui.components.pipeline\_cloning

<a id="ui.components.pipeline_cloning.PipelineCloning"></a>

## PipelineCloning Objects

```python
class PipelineCloning(pn.viewable.Viewer)
```

A component that clones a Kedro pipeline

**Attributes**:

- `pipeline` _Pipeline_ - The Kedro pipeline to retry.
- `client` _KedroGraphqlClient_ - The client used to interact with the Kedro GraphQL API.

<a id="ui.components.pipeline_cloning.PipelineCloning._create_datasets_section"></a>

#### \_create\_datasets\_section

```python
def _create_datasets_section()
```

Creates a section for editing datasets in the pipeline.

<a id="ui.components.pipeline_cloning.PipelineCloning._dataset_edit_modal"></a>

#### \_dataset\_edit\_modal

```python
def _dataset_edit_modal(dataset, trigger)
```

Return modal for editing dataset configurations

<a id="ui.components.pipeline_cloning.PipelineCloning._delete_dataset_tag_modal"></a>

#### \_delete\_dataset\_tag\_modal

```python
def _delete_dataset_tag_modal(dataset, tag, trigger)
```

Return modal for deleting a dataset tag

<a id="ui.components.pipeline_cloning.PipelineCloning._add_dataset_tag_modal"></a>

#### \_add\_dataset\_tag\_modal

```python
def _add_dataset_tag_modal(dataset, trigger)
```

Return modal for adding a new tag to a dataset

<a id="ui.components.pipeline_cloning.PipelineCloning._create_parameters_section"></a>

#### \_create\_parameters\_section

```python
def _create_parameters_section()
```

Creates a section for editing/deleting parameters in the pipeline.

<a id="ui.components.pipeline_cloning.PipelineCloning._param_edit_modal"></a>

#### \_param\_edit\_modal

```python
def _param_edit_modal(parameter, trigger)
```

Return modal for editing a parameter's value and type

<a id="ui.components.pipeline_cloning.PipelineCloning._create_tags_section"></a>

#### \_create\_tags\_section

```python
def _create_tags_section()
```

Creates a section for editing/deleting tags in the pipeline.

<a id="ui.components.pipeline_cloning.PipelineCloning._add_tag_modal"></a>

#### \_add\_tag\_modal

```python
def _add_tag_modal(trigger)
```

Return modal for adding a new tag to the pipeline

<a id="ui.components.pipeline_cloning.PipelineCloning._tag_edit_modal"></a>

#### \_tag\_edit\_modal

```python
def _tag_edit_modal(tag, trigger)
```

Return modal for editing a tag's key and value

<a id="ui.components.pipeline_cloning.PipelineCloning.clone_pipeline"></a>

#### clone\_pipeline

```python
async def clone_pipeline(type="staged")
```

Clones the pipeline and stages or runs it based on the operation type.

**Arguments**:

- `type` _str_ - The type of post-cloning operation, either "staged" or "ready".

<a id="ui.components.pipeline_detail"></a>

# Module ui.components.pipeline\_detail

<a id="ui.components.pipeline_detail.PipelineDetail"></a>

## PipelineDetail Objects

```python
class PipelineDetail(pn.viewable.Viewer)
```

<a id="ui.components.pipeline_detail.PipelineDetail.build_detail"></a>

#### build\_detail

```python
async def build_detail(raw)
```

Builds the detail view for the pipeline, showing its parameters, tags, data catalog, and status.

TO DO:
- Implement a more user-friendly way to view and interact with the pipeline's data catalog.
- Support for "batch" view. View child pipelines or parent pipelines if applicable.

**Arguments**:

- `raw` _pn.widgets.CheckButtonGroup_ - A widget to toggle between raw JSON view and structured view.

**Yields**:

- `pn.Row` - A row containing the detail view of the pipeline.

<a id="ui.components.pipeline_form_factory"></a>

# Module ui.components.pipeline\_form\_factory

<a id="ui.components.pipeline_form_factory.PipelineFormFactory"></a>

## PipelineFormFactory Objects

```python
class PipelineFormFactory(pn.viewable.Viewer)
```

A factory for building forms for Kedro pipelines using registered @ui_form plugins.
This component allows users to select a form for a specific pipeline and build the form dynamically.

**Attributes**:

- `form` _str_ - The name of the form to build.
- `pipeline` _str_ - The name of the pipeline for which the form is built.
- `options` _list_ - A list of available forms for the selected pipeline.
- `spec` _dict_ - The specification for the UI, including configuration and pages.

<a id="ui.components.pipeline_form_factory.PipelineFormFactory.build_options"></a>

#### build\_options

```python
@param.depends("pipeline")
async def build_options()
```

Builds the options for the form selection based on the registered @ui_form plugins for the selected pipeline.

<a id="ui.components.pipeline_form_factory.PipelineFormFactory.build_form"></a>

#### build\_form

```python
@param.depends("form", "pipeline", "spec")
async def build_form()
```

Builds the form based on the selected form and pipeline, using the registered @ui_form plugins.

<a id="ui.components.pipeline_monitor"></a>

# Module ui.components.pipeline\_monitor

<a id="ui.components.pipeline_monitor.PipelineMonitor"></a>

## PipelineMonitor Objects

```python
class PipelineMonitor(pn.viewable.Viewer)
```

A component that monitors the state of a Kedro pipeline and displays its status and logs.
This component allows users to view the current status of a pipeline and its logs in real-time.

**Attributes**:

- `pipeline` _Pipeline_ - The Kedro pipeline to monitor.
- `client` _KedroGraphqlClient_ - The client used to interact with the Kedro GraphQL API.

<a id="ui.components.pipeline_monitor.PipelineMonitor.build_table"></a>

#### build\_table

```python
@param.depends('pipeline', 'client')
async def build_table()
```

Builds a table displaying the current status of the pipeline.
This method fetches the pipeline status from the client and updates the table in real-time as events occur.

**Yields**:

- `pn.widgets.Tabulator` - A table displaying the pipeline status.

<a id="ui.components.pipeline_monitor.PipelineMonitor.build_terminal"></a>

#### build\_terminal

```python
@param.depends('pipeline', 'client')
async def build_terminal()
```

Builds a terminal that displays the logs of the pipeline in real-time.
This method connects to the pipeline logs and updates the terminal as new log messages are received.

**Yields**:

- `pn.widgets.Terminal` - A terminal displaying the pipeline logs.

<a id="ui.components.pipeline_retry"></a>

# Module ui.components.pipeline\_retry

<a id="ui.components.pipeline_retry.PipelineRetry"></a>

## PipelineRetry Objects

```python
class PipelineRetry(pn.viewable.Viewer)
```

A component that retries execution of a Kedro pipeline or a slice of it.

**Attributes**:

- `pipeline` _Pipeline_ - The Kedro pipeline to retry.
- `client` _KedroGraphqlClient_ - The client used to interact with the Kedro GraphQL API.

<a id="ui.components.pipeline_retry.PipelineRetry.build_card"></a>

#### build\_card

```python
async def build_card(strategy)
```

Builds a card for retrying the pipeline or a slice of it based on the selected strategy.

**Arguments**:

- `strategy` _str_ - The retry strategy selected by the user, either 'Whole' or 'Slice'.
  

**Yields**:

- `pn.Card` - A card containing the retry options and a button to trigger the retry.

<a id="ui.components.pipeline_retry.PipelineRetry.pipeline_run"></a>

#### pipeline\_run

```python
async def pipeline_run()
```

Run the pipeline based on the selected retry strategy.

<a id="ui.components.pipeline_search"></a>

# Module ui.components.pipeline\_search

<a id="ui.components.pipeline_search.PipelineSearch"></a>

## PipelineSearch Objects

```python
class PipelineSearch(pn.viewable.Viewer)
```

A component that allows users to search for pipelines in the Kedro GraphQL UI.
This component provides a search bar, results per page selection, and buttons to load more or previous results.
It displays the results in a table format with clickable rows to navigate to the pipeline details.

**Attributes**:

- `spec` _dict_ - The specification for the UI, including configuration and client.
- `limit` _int_ - The number of results to display per page.
- `cursor` _str_ - The cursor for pagination.
- `filter` _str_ - The filter string for searching pipelines.
- `prev_cursor` _str_ - The cursor for the previous page.
- `next_cursor` _str_ - The cursor for the next page.
- `more_clicks` _int_ - The number of clicks on the "Load More" button.
- `prev_clicks` _int_ - The number of clicks on the "Load Previous" button.
- `cursors` _list_ - A list of cursors for pagination.
- `cursor_index` _int_ - The index of the current cursor in the cursors list.
- `dashboard_page` _str_ - The page to navigate to when a pipeline is clicked.

<a id="ui.components.pipeline_search.PipelineSearch.navigate"></a>

#### navigate

```python
def navigate(event, df)
```

Navigate to the pipeline details page when a row is clicked.

**Arguments**:

- `event` _pn.widgets.Tabulator.ClickEvent_ - The event triggered by clicking a row.
- `df` _pd.DataFrame_ - The DataFrame containing pipeline data.

<a id="ui.components.pipeline_search.PipelineSearch.build_filter"></a>

#### build\_filter

```python
def build_filter(raw)
```

Build a filter string from  a raw string.

**Arguments**:

- `raw` _str_ - Text input by user.
  

**Returns**:

- `str` - A filter string in JSON format e.g. "{"tags.key": "unique", "tags.value": "unique"}"

<a id="ui.components.pipeline_search.PipelineSearch.build_table"></a>

#### build\_table

```python
async def build_table(limit, filter, load_more, load_prev, show_lineage)
```

Builds a table of pipelines based on the provided filter and pagination parameters.

**Arguments**:

- `limit` _int_ - The number of results to display per page.
- `filter` _str_ - The filter string for searching pipelines.
- `load_more` _int_ - The number of clicks on the "Load More" button.
- `load_prev` _int_ - The number of clicks on the "Load Previous" button.
- `show_lineage` _list_ - A list indicating whether to show lineage in the table.

**Yields**:

- `pn.widgets.Tabulator` - A table displaying the pipelines with clickable rows.

<a id="ui.components.pipeline_viz"></a>

# Module ui.components.pipeline\_viz

<a id="ui.components.pipeline_viz.PipelineViz"></a>

## PipelineViz Objects

```python
class PipelineViz(pn.viewable.Viewer)
```

<a id="ui.components.pipeline_viz.PipelineViz.load_viz_json"></a>

#### load\_viz\_json

```python
def load_viz_json()
```

Not currently used, but can be used to load a static viz JSON file.
This will be useful to programmtically hightlight nodes in the visualization,
however, the kedro-graphql api does not currently support emitting events that
indicate which nodes are currently being processed.

**Returns**:

- `dict` - The JSON data for the visualization.

<a id="ui.components.pipeline_viz.PipelineViz.build_viz"></a>

#### build\_viz

```python
@param.depends("pipeline")
async def build_viz()
```

Builds the visualization iframe for the specified pipeline.

**Returns**:

- `pn.pane.HTML` - The HTML pane containing the iframe for the pipeline visualization.

<a id="ui.components.template"></a>

# Module ui.components.template

A python panel app for visualizing Kedro pipelines.

<a id="ui.components.template.NavigationSidebarButton"></a>

## NavigationSidebarButton Objects

```python
class NavigationSidebarButton(pn.viewable.Viewer)
```

A button for navigating the sidebar in the Kedro GraphQL UI.
This button is used to navigate to different pages in the UI, such as pipelines, nodes, or data catalog.
It updates the URL to reflect the current page and changes its appearance based on whether it is the active page.

**Attributes**:

- `page` _str_ - The name of the page this button navigates to.
- `name` _str_ - The display name of the button.
- `spec` _dict_ - The specification for the UI, including configuration and pages.

<a id="ui.components.template.NavigationSidebarButton.navigate"></a>

#### navigate

```python
def navigate(event)
```

Navigate to the specified page.

<a id="ui.components.template.NavigationSidebarButton.build_button"></a>

#### build\_button

```python
async def build_button()
```

Builds the navigation button for the sidebar.
This button will change its appearance based on whether it is the current page.

**Returns**:

- `pn.widgets.Button` - A button that navigates to the specified page.

<a id="ui.components.template.TemplateMainFactory"></a>

## TemplateMainFactory Objects

```python
class TemplateMainFactory(pn.viewable.Viewer)
```

A factory for building the main content of the Kedro GraphQL UI template.
This component dynamically builds the main content based on the current page specified in the URL.
It uses the `spec` dictionary to determine which module to load for each page.

**Attributes**:

- `page` _str_ - The current page to display in the main content.
- `spec` _dict_ - The specification for the UI, including configuration and pages.

<a id="ui.components.template.TemplateMainFactory.build_page"></a>

#### build\_page

```python
@param.depends("page", "spec")
async def build_page()
```

Builds the main content of the template based on the current page.

<a id="ui.components.template.KedroGraphqlMaterialTemplate"></a>

## KedroGraphqlMaterialTemplate Objects

```python
class KedroGraphqlMaterialTemplate(pn.template.MaterialTemplate)
```

A Material Design template for the Kedro GraphQL UI.
This template includes a sidebar for navigation and a main content area that
displays different pages based on the current URL.
It uses the `spec` dictionary to configure the sidebar and main content.

**Attributes**:

- `title` _str_ - The title of the template.
- `sidebar_width` _int_ - The width of the sidebar in pixels.
- `page` _str_ - The current page to display in the main content.
- `spec` _dict_ - The specification for the UI, including configuration and pages.

<a id="ui.components.template.KedroGraphqlMaterialTemplate.user_menu_action"></a>

#### user\_menu\_action

```python
def user_menu_action(event, user_info_modal, login_link, logout_link)
```

Handles user menu actions such as showing user information, logging in, or logging out.

**Arguments**:

- `event` _str_ - The action triggered by the user menu.
- `user_info_modal` _pn.Modal_ - The modal to display user information.
- `login_link` _str_ - The URL for the login endpoint.
- `logout_link` _str_ - The URL for the logout endpoint.

<a id="ui.components.template.KedroGraphqlMaterialTemplate.build_user_menu"></a>

#### build\_user\_menu

```python
async def build_user_menu()
```

Asynchronously retrieves the user context for the template.
This method can be overridden to provide custom user context data.

<a id="ui.components.template.KedroGraphqlMaterialTemplate.init_client"></a>

#### init\_client

```python
def init_client(spec)
```

Initializes the Kedro GraphQL client with the provided specification.
This method sets up the client to connect to the GraphQL API and WebSocket.

**Arguments**:

- `spec` _dict_ - The specification for the UI, including configuration and pages.

<a id="ui.components.template.KedroGraphqlMaterialTemplate.__init__"></a>

#### \_\_init\_\_

```python
def __init__(title="kedro-graphql", spec=None)
```

Initializes the KedroGraphqlMaterialTemplate with a title and specification.

**Arguments**:

- `title` _str_ - The title of the template.
- `spec` _dict_ - The specification for the UI, including configuration and pages.

<a id="ui.components.data_catalog_explorer"></a>

# Module ui.components.data\_catalog\_explorer

<a id="ui.components.data_catalog_explorer.DataCatalogExplorer"></a>

## DataCatalogExplorer Objects

```python
class DataCatalogExplorer(pn.viewable.Viewer)
```

A component that displays the data catalog of a Kedro pipeline, allowing users to filter, view,
and download datasets using their pre-signed URL implementation of choice.

<a id="ui.components.dataset_perspective"></a>

# Module ui.components.dataset\_perspective

<a id="ui.components.dataset_perspective.DatasetPerspective"></a>

## DatasetPerspective Objects

```python
class DatasetPerspective(pn.viewable.Viewer)
```

A Kedro Dataframe viewer that loads a dataset from a presigned URL and displays it using panel Perspective.

<a id="ui.components.pipeline_dashboard_factory"></a>

# Module ui.components.pipeline\_dashboard\_factory

<a id="ui.components.pipeline_dashboard_factory.PipelineDashboardFactory"></a>

## PipelineDashboardFactory Objects

```python
class PipelineDashboardFactory(pn.viewable.Viewer)
```

A factory for building dashboards for Kedro pipelines using registered @ui_dashboard plugins.
This component allows users to select a dashboard for a specific pipeline and build the dashboard dynamically.

**Attributes**:

- `id` _str_ - The ID of the pipeline to build the dashboard for.
- `pipeline` _str_ - The name of the pipeline for which the dashboard is built.
- `options` _list_ - A list of available dashboards for the selected pipeline.
- `spec` _dict_ - The specification for the UI, including configuration and pages.
- `dashboard_name` _str_ - The name of the selected dashboard.

<a id="ui.components.pipeline_dashboard_factory.PipelineDashboardFactory.build_default_dashboard"></a>

#### build\_default\_dashboard

```python
def build_default_dashboard(p)
```

Builds the default dashboard for a Kedro pipeline, including monitoring, detail, and visualization components
registered to the pipeline using the @ui_data plugin.

**Arguments**:

- `p` _Pipeline_ - The Kedro pipeline for which the dashboard is built.

**Returns**:

- `pn.Tabs` - A panel containing tabs for monitoring, detail, and visualization of the pipeline.

<a id="ui.components.pipeline_dashboard_factory.PipelineDashboardFactory.build_custom_dashboard"></a>

#### build\_custom\_dashboard

```python
def build_custom_dashboard(p)
```

Builds a custom dashboard for a Kedro pipeline using a registered @ui_dashboard plugin.

**Arguments**:

- `p` _Pipeline_ - The Kedro pipeline for which the dashboard is built.

**Returns**:

- `panel.viewable.Viewer` - An instance of the custom dashboard class.

<a id="ui.components.pipeline_dashboard_factory.PipelineDashboardFactory.build_dashboard"></a>

#### build\_dashboard

```python
@param.depends("spec", "dashboard_name", "id", "pipeline")
async def build_dashboard()
```

Builds the dashboard for the selected pipeline and dashboard name.
This method checks if a custom dashboard is registered for the pipeline and builds it accordingly.
If no custom dashboard is registered, it builds the default dashboard with monitoring, detail, and visualization components.

**Yields**:

  pn.Tabs or panel.viewable.Viewer: The built dashboard, either custom or default.

<a id="ui.decorators"></a>

# Module ui.decorators

<a id="ui.decorators.discover_plugins"></a>

#### discover\_plugins

```python
def discover_plugins(config)
```

Discover and import plugins based on the configuration.

**Arguments**:

- `config` _dict_ - Configuration dictionary containing the imports.

<a id="ui.decorators.ui_form"></a>

#### ui\_form

```python
def ui_form(pipeline)
```

Register a UI form plugin for a specific pipeline.

**Arguments**:

- `pipeline` _str_ - Name of the pipeline for which the form is registered.

<a id="ui.decorators.ui_data"></a>

#### ui\_data

```python
def ui_data(pipeline)
```

Register a UI data plugin for a specific pipeline.

**Arguments**:

- `pipeline` _str_ - Name of the pipeline for which the data plugin is registered.

<a id="ui.decorators.ui_dashboard"></a>

#### ui\_dashboard

```python
def ui_dashboard(pipeline)
```

Register a UI dashboard plugin for a specific pipeline.

**Arguments**:

- `pipeline` _str_ - Name of the pipeline for which the dashboard plugin is registered.

<a id="ui.plugins"></a>

# Module ui.plugins

<a id="ui.plugins.BaseExample00Form"></a>

## BaseExample00Form Objects

```python
class BaseExample00Form(pn.viewable.Viewer)
```

Base class for example00 pipeline forms.
This class provides the basic functionality for uploading files, running the pipeline,
and navigating to the pipeline dashboard.

**Attributes**:

- `spec` _dict_ - The specification for the UI, including configuration and pages.
- `text_in` __TemporaryFileWrapper_ - A temporary file wrapper for the input text file.
- `text_out` __TemporaryFileWrapper_ - A temporary file wrapper for the output text file.
- `duration` _int_ - The duration parameter for the pipeline.
- `example` _str_ - An example string parameter for the pipeline.
- `button_disabled` _bool_ - A flag to disable the run button until a file is uploaded.
  

**Methods**:

- `navigate(pipeline_id` - str): Navigate to the pipeline dashboard with the given ID.
- `upload(file_dropper)` - Write the contents of the uploaded file to a temporary file.
- `pipeline_input()` - Create a PipelineInput object with the current parameters.
- `run(event)` - Run the pipeline with the current input and parameters.
- `__panel__()` - Return a Panel component for the form.
  
  This class should be subclassed to implement specific forms for the example00 pipeline.

<a id="ui.plugins.BaseExample00Form.navigate"></a>

#### navigate

```python
def navigate(pipeline_id: str)
```

Navigate to the pipeline dashboard with the given ID.

<a id="ui.plugins.BaseExample00Form.upload"></a>

#### upload

```python
async def upload(file_dropper)
```

write a files contents to a temporary file

<a id="ui.plugins.BaseExample00Form.pipeline_input"></a>

#### pipeline\_input

```python
@param.depends("text_in", "text_out", 'duration', 'example')
async def pipeline_input()
```

Create a PipelineInput object with the current parameters.

<a id="ui.plugins.BaseExample00Form.run"></a>

#### run

```python
async def run(event)
```

Run the pipeline with the current input and parameters.

<a id="ui.plugins.Example00PipelineFormV1"></a>

## Example00PipelineFormV1 Objects

```python
@ui_form(pipeline="example00")
class Example00PipelineFormV1(BaseExample00Form)
```

Form for the example00 pipeline.
This form allows users to upload a file, run the pipeline, and navigate to the pipeline dashboard.
It inherits from BaseExample00Form and implements the __panel__ method to create the form layout.

<a id="ui.plugins.Example00PipelineFormV1.__panel__"></a>

#### \_\_panel\_\_

```python
def __panel__()
```

Create the Panel component for the example00 pipeline form.

<a id="ui.plugins.Example00PipelineFormV2"></a>

## Example00PipelineFormV2 Objects

```python
@ui_form(pipeline="example00")
class Example00PipelineFormV2(BaseExample00Form)
```

Another example form for the example00 pipeline.
This form allows users to enter additional parameters and upload a file.
It inherits from BaseExample00Form and implements the __panel__ method to create the form layout.

<a id="ui.plugins.Example00PipelineFormV2.__panel__"></a>

#### \_\_panel\_\_

```python
def __panel__()
```

Create the Panel component for the example00 pipeline form with additional parameters.

<a id="ui.plugins.Example00Data00"></a>

## Example00Data00 Objects

```python
@ui_data(pipeline="example00")
class Example00Data00(pn.viewable.Viewer)
```

Data viewer for the example00 pipeline.
It inherits from pn.viewable.Viewer and implements the __panel__ method to create the data view.

**Attributes**:

- `spec` _dict_ - The specification for the UI, including configuration and pages.
- `id` _str_ - The ID of the data viewer.
- `pipeline` _Pipeline_ - The Kedro pipeline associated with this data viewer.
- `title` _str_ - The title of the data viewer.

<a id="ui.plugins.Example00Data00.__panel__"></a>

#### \_\_panel\_\_

```python
def __panel__()
```

Create the Panel component for the example00 data viewer.

<a id="ui.plugins.Example00Data01"></a>

## Example00Data01 Objects

```python
@ui_data(pipeline="example00")
class Example00Data01(pn.viewable.Viewer)
```

Another data viewer for the example00 pipeline.
This viewer displays a sample plot using Bokeh figures.
It inherits from pn.viewable.Viewer and implements the __panel__ method to create the plot view.

**Attributes**:

- `spec` _dict_ - The specification for the UI, including configuration and pages.
- `id` _str_ - The ID of the data viewer.
- `pipeline` _Pipeline_ - The Kedro pipeline associated with this data viewer.
- `title` _str_ - The title of the data viewer.

<a id="ui.plugins.Example00Data01.build_plot"></a>

#### build\_plot

```python
async def build_plot()
```

Create a sample gauge plot using Panel and ECharts.

<a id="ui.plugins.BaseExample01Form"></a>

## BaseExample01Form Objects

```python
class BaseExample01Form(pn.viewable.Viewer)
```

Base class for example01 pipeline forms.
This class provides the basic functionality for uploading files, running the pipeline,
and navigating to the pipeline dashboard.

**Attributes**:

- `spec` _dict_ - The specification for the UI, including configuration and pages.
- `text_in` __TemporaryFileWrapper_ - A temporary file wrapper for the input text file.
- `uppercase` __TemporaryFileWrapper_ - A temporary file wrapper for the uppercase output file.
- `reversed` __TemporaryFileWrapper_ - A temporary file wrapper for the reversed output file.
- `timestamped` __TemporaryFileWrapper_ - A temporary file wrapper for the timestamped output file.
- `duration` _int_ - The duration parameter for the pipeline.
- `example` _str_ - An example string parameter for the pipeline.
  

**Methods**:

- `navigate(pipeline_id` - str): Navigate to the pipeline dashboard with the given ID.
- `upload(file_dropper)` - Write the contents of the uploaded file to temporary files.
- `pipeline_input()` - Create a PipelineInput object with the current parameters.
- `run(event)` - Run the pipeline with the current input and parameters.
- `__panel__()` - Return a Panel component for the form.
  
  This class should be subclassed to implement specific forms for the example01 pipeline.

<a id="ui.plugins.BaseExample01Form.navigate"></a>

#### navigate

```python
def navigate(pipeline_id: str)
```

Navigate to the pipeline dashboard with the given ID.

<a id="ui.plugins.BaseExample01Form.upload"></a>

#### upload

```python
async def upload(file_dropper)
```

write a files contents to a temporary file

<a id="ui.plugins.BaseExample01Form.pipeline_input"></a>

#### pipeline\_input

```python
@param.depends("text_in", "uppercase", 'reversed', 'timestamped')
async def pipeline_input()
```

Create a PipelineInput object with the current parameters.

<a id="ui.plugins.BaseExample01Form.run"></a>

#### run

```python
async def run(event)
```

Run the pipeline with the current input and parameters.

<a id="ui.plugins.Example01PipelineFormV1"></a>

## Example01PipelineFormV1 Objects

```python
@ui_form(pipeline="example01")
class Example01PipelineFormV1(BaseExample01Form)
```

Form for the example01 pipeline.
This form allows users to upload a file, run the pipeline, and navigate to the pipeline dashboard.
It inherits from BaseExample01Form and implements the __panel__ method to create the form layout.

<a id="ui.plugins.Example01PipelineUIV1"></a>

## Example01PipelineUIV1 Objects

```python
@ui_dashboard(pipeline="example01")
class Example01PipelineUIV1(pn.viewable.Viewer)
```

Dashboard for the example01 pipeline.
This dashboard displays the pipeline stages and allows users to monitor the pipeline's progress.
It inherits from pn.viewable.Viewer and implements the __panel__ method to create the dashboard layout.

**Attributes**:

- `spec` _dict_ - The specification for the UI, including configuration and pages.
- `id` _str_ - The ID of the pipeline.
- `pipeline` _Pipeline_ - The Kedro pipeline associated with this dashboard.

<a id="signed_url"></a>

# Module signed\_url

<a id="signed_url.base"></a>

# Module signed\_url.base

<a id="signed_url.base.SignedUrlProvider"></a>

## SignedUrlProvider Objects

```python
class SignedUrlProvider(metaclass=abc.ABCMeta)
```

Abstract base class for providing signed URLs for reading and creating kedro datasets

<a id="signed_url.base.SignedUrlProvider.read"></a>

#### read

```python
@abc.abstractmethod
def read(filepath: str, expires_in_sec: int) -> str | None
```

Abstract method to get a signed URL for downloading a dataset.

**Arguments**:

- `filepath` _str_ - The file path of the dataset.
- `expires_in_sec` _int_ - The number of seconds the presigned URL should be valid for.
  

**Returns**:

  str | None: A signed URL for downloading the dataset.

<a id="signed_url.base.SignedUrlProvider.create"></a>

#### create

```python
@abc.abstractmethod
def create(filepath: str, expires_in_sec: int) -> dict | None
```

Abstract method to get a signed URL for uploading a dataset.

**Arguments**:

- `filepath` _str_ - The file path of the dataset.
- `expires_in_sec` _int_ - The number of seconds the signed URL should be valid for.
  

**Returns**:

  dict | None: A dictionary with the URL to post to and form fields and values to submit with the POST.

<a id="signed_url.local_file_provider"></a>

# Module signed\_url.local\_file\_provider

<a id="signed_url.local_file_provider.LocalFileProvider"></a>

## LocalFileProvider Objects

```python
class LocalFileProvider(SignedUrlProvider)
```

Implementation of SignedUrlProvider for a local file system.

<a id="signed_url.local_file_provider.LocalFileProvider.read"></a>

#### read

```python
def read(filepath: str, expires_in_sec: int) -> str | None
```

Get a signed URL for reading a dataset.

**Returns**:

- `str` - A signed URL for reading the dataset.

<a id="signed_url.local_file_provider.LocalFileProvider.create"></a>

#### create

```python
def create(filepath: str, expires_in_sec: int) -> dict | None
```

Get a signed URL for creating a dataset.

**Returns**:

- `dict` - A signed URL for creating the dataset.

<a id="signed_url.s3_provider"></a>

# Module signed\_url.s3\_provider

<a id="signed_url.s3_provider.S3Provider"></a>

## S3Provider Objects

```python
class S3Provider(SignedUrlProvider)
```

Implementation of SignedUrlProvider for AWS S3.

<a id="signed_url.s3_provider.S3Provider.read"></a>

#### read

```python
@staticmethod
def read(filepath: str, expires_in_sec: int) -> str | None
```

Generate a signed URL S3 to download a file.

**Arguments**:

- `filepath` _str_ - The S3 file path in the format s3://bucket-name/key
- `expires_in_sec` _int_ - The number of seconds the signed URL should be valid for.
  

**Returns**:

- `Optional[str]` - download url with query parameters
  
- `Example` - https://your-bucket-name.s3.amazonaws.com/your-object-key?AWSAccessKeyId=your-access-key-id&Signature=your-signature&x-amz-security-token=your-security-token&Expires=expiration-time

<a id="signed_url.s3_provider.S3Provider.create"></a>

#### create

```python
@staticmethod
def create(filepath: str, expires_in_sec: int) -> dict | None
```

Generate a signed URL S3 to upload a file.

**Arguments**:

- `filepath` _str_ - The S3 file path in the format s3://bucket-name/key
- `expires_in_sec` _int_ - The number of seconds the signed URL should be valid for.
  

**Returns**:

- `Optional[JSON]` - Dictionary with the URL to post to and form fields and values to submit with the POST. If an error occurs, returns None.
  

**Example**:

  {
- `"url"` - "https://your-bucket-name.s3.amazonaws.com/",
- `"fields"` - {
- `"key"` - "your-object-key",
- `"AWSAccessKeyId"` - "your-access-key-id",
- `"x-amz-security-token"` - "your-security-token",
- `"policy"` - "your-policy",
- `"signature"` - "your-signature"
  }
  }

