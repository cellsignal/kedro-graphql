<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/light-logo.png">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/dark-logo.png">
    <img src="https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/light-logo.png" alt="KedroGraphQL Light Logo">
  </picture>
</p>

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/cellsignal/kedro-graphql)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Latest Release](https://img.shields.io/pypi/v/kedro-graphql.svg)](https://pypi.org/project/kedro-graphql/)

## Overview

Kedro-graphql is a [kedro-plugin](https://docs.kedro.org/en/stable/extend_kedro/plugins.html)
for serving kedro projects as a graphql api.  It leverages
[Strawberry](https://strawberry.rocks/), [FastAPI](https://fastapi.tiangolo.com/),
and [Celery](https://docs.celeryq.dev/en/stable/index.html) to turn any
 [Kedro](https://docs.kedro.org/en/stable/) project into a GraphqlQL api
 with features such as:

- a distributed task queue
- subscribe to pipline events and logs via GraphQL subscriptions
- storage
  - persist and track all pipelines executed via the API
- [additional features](#features)

```mermaid
flowchart  TB
  api[GraphQL API<br/><i>strawberry + FastAPI</i>]
  mongodb[(db: 'pipelines'<br/>collection: 'pipelines'<br/><i>mongoDB</i>)]
  redis[(task queue<br/><i>redis</i>)]
  worker[worker<br/><i>celery</i>]

  api<-->mongodb
  api<-->redis
  worker<-->mongodb
  worker<-->redis

```

Figure 1. Architecture

## Quickstart

Install kedro-graphql into your kedro project environnment.

```
pip install kedro_graphql
```

Start the redis and mongo services using this [docker-compose.yaml](https://github.com/opensean/kedro-graphql/blob/main/docker-compose.yaml).

```
docker-compose up -d
```

Start the api server.

```
kedro gql
```

Start a worker (in another terminal).

```
kedro gql -w
```

Navigate to <http://127.0.0.1:5000/graphql> to access the graphql interface.

![strawberry-ui](https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/strawberry-ui.png)

The [docker-compose.yaml](./docker-compose.yaml) includes
[mongo-express](https://github.com/mongo-express/mongo-express) and
[redis-commander](https://github.com/joeferner/redis-commander) services
to provide easy acess to MongoDB and redis.

Navigate to <http://127.0.0.1:8082> to access mongo-express interface.

![mongo-express-ui](https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/mongo-express-ui.png)

Navigate to <http://127.0.0.1:8081> to access the redis-commander interface.
One can access the task queues created and managed by
[Celery](https://docs.celeryq.dev/en/stable/index.html).

![redis-commander-ui](https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/redis-commander-ui.png)

## Example

The kedro-graphl package contains an very simple example
pipeline called "example00".

### Setup

Clone the kedro-graphql repository.

```
git clone https://github.com/cellsignal/kedro-graphql.git
```

Create a virtualenv and activate it.

```
cd kedro-graphql
python3.10 -m venv venv
source venv/bin/activate
```

Install dependencies.

```
pip install -r src/requirements.txt
```

Create a text file.

```
echo "Hello" > ./data/01_raw/text_in.txt
```

Start the redis and mongo services.

```
docker-compose up -d
```

Start the api server.

```
kedro gql
```

Start a worker (in another terminal).

```
kedro gql -w
```

### Start a pipeline

Navigate to <http://127.0.0.1:5000/graphql> to access the graphql interface
and execute the following mutation:

```
mutation MyMutation {
  createPipeline(
    pipeline: {
      name: "example00",
      parameters: [
        {name: "example", value: "hello"},
        {name: "duration", value: "10"}
      ],
      dataCatalog: [
        {name: "text_in", config: "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/01_raw/text_in.txt\"}"},
        {name: "text_out", config: "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/02_intermediate/text_out.txt\"}"}
      ],
      state: READY}
  ) {
    id
    name
  }
}
```

Expected response:

```
{
  "data": {
    "createPipeline": {
      "id": "67b795d44f0f5729b9b5730e",
      "name": "example00"
    }
  }
}
```

### Subscribe to pipeline events

Now execute the following subscription to track the progress:

```
subscription MySubscription {
  pipeline(id: "67b795d44f0f5729b9b5730e") {
    id
    result
    status
    taskId
    timestamp
    traceback
  }
}
```

![subscription](https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/subscription.gif)

### Susbscribe to pipeline logs

Execute the following subscription to recieve log messages:

```
subscription MySubscriptionLogs {
  pipelineLogs(id: "67b795d44f0f5729b9b5730e") {
    id
    message
    messageId
    taskId
    time
  }
}
```

![logs subscription](https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/logs-subscription.gif)

### Get the pipeline result

Fetch the pipeline result with the following query:

```
query MyQuery {
  readPipeline(id: "67b795d44f0f5729b9b5730e") {
    describe
    id
    name
    parameters {
      name
      value
    }
    status {
      filteredNodes
      finishedAt
      runner
      session
      startedAt
      state
      taskArgs
      taskEinfo
      taskException
      taskTraceback
      taskResult
      taskRequest
      taskName
      taskKwargs
      taskId
    }
    dataCatalog {
      config
      name
    }
  }
}
```

Expected result:

```
{
  "data": {
    "readPipeline": {
      "describe": "#### Pipeline execution order ####\nInputs: parameters, params:example, text_in\n\necho_node\n\nOutputs: text_out\n##################################",
      "id": "67b795d44f0f5729b9b5730e",
      "name": "example00",
      "parameters": [
        {
          "name": "example",
          "value": "hello"
        },
        {
          "name": "duration",
          "value": "10"
        }
      ],
      "status": [
        {
          "filteredNodes": [
            "echo_node"
          ],
          "finishedAt": "2025-02-20T15:51:51.045044",
          "runner": "kedro.runner.SequentialRunner",
          "session": "2025-02-20T20.51.47.821Z",
          "startedAt": "2025-02-20T15:51:32.916990",
          "state": "SUCCESS",
          "taskArgs": "[]",
          "taskEinfo": null,
          "taskException": null,
          "taskTraceback": null,
          "taskResult": "success",
          "taskRequest": null,
          "taskName": "<@task: kedro_graphql.tasks.run_pipeline of __main__ at 0x107eaff50>",
          "taskKwargs": "{\"id\": \"67b795d44f0f5729b9b5730e\", \"name\": \"example00\", \"parameters\": {\"example\": \"hello\", \"duration\": \"3\"}, \"data_catalog\": {\"text_in\": {\"type\": \"text.TextDataset\", \"filepath\": \"./data/01_raw/text_in.txt\"}, \"text_out\": {\"type\": \"text.TextDataset\", \"filepath\": \"./data/02_intermediate/text_out.txt\"}}, \"runner\": \"kedro.runner.SequentialRunner\", \"slices\": null, \"only_missing\": false}",
          "taskId": "febc1c7d-d4ac-43f5-9ce4-8806d3d4773a"
        }
      ],
      "dataCatalog": [
        {
          "config": "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/01_raw/text_in.txt\"}",
          "name": "text_in"
        },
        {
          "config": "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/02_intermediate/text_out.txt\"}",
          "name": "text_out"
        }
      ]
    }
  }
}
```

One can explore how the pipeline is persisted using the mongo-express
interface located here <http://127.0.0.1:8082>.  Pipelines are persisted in the
"pipelines" collection of the "pipelines" database.

![mongo-express-pipeline](https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/mongo-express-pipeline.png)

![mongo-express-pipeline-doc](https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/mongo-express-pipeline-doc.png)

### Staging and updating a pipeline

Execute the following mutation to stage a pipeline:

```
mutation MyMutation {
  createPipeline(
    pipeline: {name: "example00", state: STAGED}
  ) {
    id
    name
  }
}
```

Execute the following mutation to update the staged pipeline with a data catalog, tags, and a `READY` state which will run the pipeline:

```
mutation MyMutation {
  updatePipeline(
    id: "67b8b41535ac10b558916cba"
    pipeline: {
      name: "example00",
      parameters: [
        {name: "example", value: "hello"},
        {name: "duration", value: "10"}
      ],
      tags: [{key: "owner", value: "harinlee83"}],
      dataCatalog: [
        {name: "text_in", config: "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/01_raw/text_in.txt\"}"},
        {name: "text_out", config: "{\"type\": \"text.TextDataset\",\"filepath\": \"./data/02_intermediate/text_out.txt\"}"}
      ],
      state: READY}
  ) {
    id
    name
  }
}
```

### Slice a pipeline

You can slice a pipeline by providing **inputs/outputs**, specifying **start/final/tagged nodes** or **node namespaces**, following [Kedro's pipeline slicing pattern](https://docs.kedro.org/en/stable/nodes_and_pipelines/slice_a_pipeline.html). For example, executing the following mutation will only run `"uppercase_node"` and `"reversed_node"` in the `"example01"` pipeline, skipping the `"timestamp_node"`:

```
mutation MyMutation {
  createPipeline(
    pipeline: {
      name: "example01",
      parameters: [
        {name: "example", value: "hello"},
        {name: "duration", value: "10"}
      ],
      tags: [{key: "owner", value: "harinlee83"}],
      dataCatalog: [
        {name: "text_in", config: "{\"type\": \"text.TextDataset\", \"filepath\": \"./data/01_raw/text_in.txt\"}"},
        {name: "uppercased", config: "{\"type\": \"text.TextDataset\", \"filepath\": \"./data/02_intermediate/uppercased.txt\"}"},
        {name: "reversed", config: "{\"type\": \"text.TextDataset\", \"filepath\": \"./data/02_intermediate/reversed.txt\"}"},
        {name: "timestamped", config: "{\"type\": \"text.TextDataset\", \"filepath\": \"./data/02_intermediate/timestamped.txt\"}"}
      ],
      slices: {slice: NODE_NAMES, args: ["uppercase_node", "reverse_node"]},
      state: READY}
  ) {
    id
    name
  }
}
```

### Search for a pipeline

Search for a pipeline using the [MongoDB document query filter](https://www.mongodb.com/docs/manual/core/document/#std-label-document-query-filter), [MongoDB cursor sort sytnax](https://www.mongodb.com/docs/manual/reference/method/cursor.sort/#syntax), and the [MongoDB cursor limit](https://www.mongodb.com/docs/manual/reference/method/cursor.limit/#cursor.limit--) in the `readPipelines` query. Executing the following query below will return up to **10 pipelines** that have a tag key of `"owner"` with a tag value of `"harinlee83"`, sorted chronologically in **descending order**.

```
query QueryForOwner {
  readPipelines(
    filter: "{\"tags.key\":\"owner\",\"tags.value\":\"harinlee83\"}"
    sort: "[(\"created_at\", -1)]"
    limit: 10
  ) {
    pipelines {
      tags {
        key
        value
      }
      name
      id
      createdAt
    }
  }
}
```

## Features

### Extensible API

The api generated by this tool can be extended using decorators.

This example adds a query, mutation, and subscription types.

```
## kedro_graphql.plugins.plugins
import asyncio
from kedro_graphql.decorators import gql_query, gql_mutation, gql_subscription
import strawberry
from typing import AsyncGenerator

@gql_query()
@strawberry.type
class ExampleQueryTypePlugin():
    @strawberry.field
    def hello_world(self) -> str:
        return "Hello World"

@gql_mutation()
@strawberry.type
class ExampleMutationTypePlugin():
    @strawberry.mutation
    def hello_world(self, message: str = "World") -> str:
        return "Hello " + message

@gql_subscription()
@strawberry.type
class ExampleSubscriptionTypePlugin():
    @strawberry.subscription
    async def hello_world(self, message: str = "World", target: int = 11) -> AsyncGenerator[str, None]:
        for i in range(target):
            yield str(i) + " Hello " + message
            await asyncio.sleep(0.5)
```

When starting the api server specify the import path using the
```--imports``` flag.

```
kedro gql --imports "kedro_graphql.plugins.plugins"
```

Multiple import paths can be specified using comma seperated values.

```
kedro gql --imports "kedro_graphql.plugins.plugins,example_pkg.example.my_types"
```

Alternatively, use a ```.env``` file as described in the [General Configuration](#general-configuration) section.

### Configurable Application

The base application is strawberry + FastAPI instance.  One can leverage the
additional features FastAPI offers by defining a custom application class.

This example adds a [CORSMiddleware](https://fastapi.tiangolo.com/tutorial/cors/#use-corsmiddleware).

```
## src/kedro_graphql/example/app.py
from fastapi.middleware.cors import CORSMiddleware
from kedro_graphql.asgi import KedroGraphQL



class MyApp(KedroGraphQL):

    def __init__(self): 
        super(MyApp, self).__init__()

        origins = [
            "http://localhost",
            "http://localhost:8080",
        ]
        
        self.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        print("added CORSMiddleware")

```

When starting the api server specify the import path using the
```--app``` flag.

```
kedro gql --app "my_kedro_project.app.MyApp"
## example output
added CORSMiddleware
INFO:     Started server process [7032]
INFO:     Waiting for application startup.
Connected to the MongoDB database!
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:5000 (Press CTRL+C to quit)
```

Alternatively, use a ```.env``` file as described in the [General Configuration](#general-configuration) section.

### Auto-reload

The cli interface supports "auto-reloading" in order to make development easier.
When starting the api server and worker specify the `-r` or `--reload` option
to turn on auto-reloading.  Any changes to the "src" directory of your kedro
project will trigger a reload.

Start the api server with auto-reload enabled.

```
kedro gql --reload
```

Start a worker (in another terminal) with auto-reload enabled.

```
kedro gql -w --reload
```

The path to watch can be further refined using the `--reload-path` option.
In the following examples a reload will be triggered when changes are
made to files in the `src/kedro_graphql/src/runners` directory.
Start the api server with auto-reload enabled.

```
kedro gql --reload --reload-path ./src/kedro_graphql/runners
```

Start a worker (in another terminal) with auto-reload enabled.

```
kedro gql -w --reload --reload-path ./src/kedro_graphql/runners
`````

## General Configuration

Configuration can be supplied via environment variables or a ```.env``` file.

```
## example .env file
MONGO_URI=mongodb://root:example@localhost:27017/
MONGO_DB_NAME=pipelines
KEDRO_GRAPHQL_IMPORTS=kedro_graphql.plugins.plugins
KEDRO_GRAPHQL_APP=kedro_graphql.asgi.KedroGraphQL
KEDRO_GRAPHQL_BACKEND=kedro_graphql.backends.mongodb.MongoBackend
KEDRO_GRAPHQL_BROKER=redis://localhost
KEDRO_GRAPHQL_CELERY_RESULT_BACKEND=redis://localhost
KEDRO_GRAPHQL_RUNNER=kedro.runner.SequentialRunner
KEDRO_GRAPHQL_ENV=local
KEDRO_GRAPHQL_CONF_SOURCE=None
KEDRO_GRAPHQL_LOG_TMP_DIR=my_tmp_dir/
KEDRO_GRAPHQL_LOG_PATH_PREFIX=s3://my-bucket/
```

The configuration can also be provided at startup through the cli interface.
Configuration values can be mapped to the the appropriate cli option by
removing the "KEDRO_GRAPHQL" prefix and using a lower case, hyphen format
for the remaining string.  For example:

| configuration variable | cli option | example   |
|------------------------|------------|-----------|
|MONGO_URI |   --mongo-uri    | mongodb://root:example@localhost:27017/ |
|MONGO_DB_NAME |   --mongo-db-name    | pipelines |
|KEDRO_GRAPHQL_IMPORTS |   --imports    | kedro_graphql.plugins.plugins |
|KEDRO_GRAPHQL_APP |   --app    | kedro_graphql.asgi.KedroGraphQL |
|KEDRO_GRAPHQL_BACKEND |   --backend    | kedro_graphql.backends.mongodb.MongoBackend |
|KEDRO_GRAPHQL_BROKER |    --broker   | redis://localhost |
|KEDRO_GRAPHQL_CELERY_RESULT_BACKEND |  --celery-result-backend    | redis://localhost |
|KEDRO_GRAPHQL_RUNNER |    --runner   | kedro.runner.SequentialRunner |
|KEDRO_GRAPHQL_ENV |    --env   | local |
|KEDRO_GRAPHQL_CONF_SOURCE |   --conf-source    | $HOME/myproject/conf |
|KEDRO_GRAPHQL_LOG_TMP_DIR |   --log-tmp-dir    | my_tmp_dir/ |
|KEDRO_GRAPHQL_LOG_PATH_PREFIX |   --log-path-prefix    | s3://my-bucket/ |

## How to install dependencies

To install them, run:

```
pip install -r src/requirements.txt
```

## How to test

```
pytest src/tests
```

To configure the coverage threshold, go to the `.coveragerc` file.

## Project dependencies

To generate or update the dependency requirements for your project:

```
kedro build-reqs
```

This will `pip-compile` the contents of `src/requirements.txt` into a new file `src/requirements.lock`. You can see the output of the resolution by opening `src/requirements.lock`.

After this, if you'd like to update your project requirements, please update `src/requirements.txt` and re-run `kedro build-reqs`.

[Further information about project dependencies](https://kedro.readthedocs.io/en/stable/kedro_project_setup/dependencies.html#project-specific-dependencies)

### TO DO

- support custom runners e.g. Argo Workflows, AWS Batch, etc...
- support passing credentials via api

## Changelog

### [1.0.1] - 2025-02-24

Fixed

- Critical bug caused by an unused import in `__init__.py` that prevented KedroGraphQL app from starting
- `on_pipline_error` kedro hook typo. changed to `on_pipeline_error`

Changed

- Changed README.md img src to absolute URLs for PyPi's project description renderer
- Moved `after_catalog_created` kedro hook call after `record_data` is loaded into memory in `tasks.py` because it's needed in the `on_pipeline_error` kedro hook call
- KedroGraphQL configurable application import to `from kedro_graphql.asgi import KedroGraphQL`

### [1.0.0] - 2025-02-21

Added

- `sort` argument to pipelines Query so users could sort through mongodb document fields lexicographically (ascending/descending)
- Support for presigned S3 urls for upload and download of `DataSet`
- `tags` and `exists` fields to `DataSet` type
- `parent`, `runner`, `created_at` fields to `Pipeline` type
- `updatePipeline` and `deletePipeline` mutations
- Universal logs handling with `gql_meta` and `gql_logs` DataSets, `KEDRO_GRAPHQL_LOG_TMP_DIR` and `KEDRO_GRAPHQL_LOG_PATH_PREFIX` env variables, and `DataLoggingHooks`
- Support for `Pipeline` slicing with `PipelineSlice` and `PipelineSliceType` types and `slices` and `only_missing` fields
- Nested parameters using dot-list notation in the `Parameter.name`
- Kedro hook calls in `run_pipeline` task:
  - `after_catalog_created`
  - `before_pipeline_run`
  - `after_pipeline_run`
  - `on_pipeline_error`
- `project_version`, `pipeline_version`, and `kedro_graphql_version` fields to `Pipeline` type

Changed

- `Pipeline` status field refactored with `PipelineStatus`
- Renamed schema fields to follow CRUD naming conventions (`createPipeline`, `readPipelines`, `readPipeline`)
- Back-end interface refactored to improve `Pipeline` object updates and prevent race conditions

Removed

- The following fields of the `Pipeline` and `PipelineInput` types:
  - `filepath`
  - `load_args`
  - `save_args`
  - `type`
  - `credentials`
- The following fields of the `Pipeline` and `PipelineInput` types:
  - `inputs`
  - `outputs`

### [0.5.0] - 2024-07-17

- support python3.11
- support kedro ~=0.19.6

#### DataSet and DataSetInput types

The following fields of the `DataSet` and `DataSetInput` types are marked for
deprecation and will be removed in a future release:

- `filepath`
- `load_args`
- `save_args`
- `type`

```
@strawberry.type
class DataSet:
    name: str
    config: Optional[str] = None
    type: Optional[str] = mark_deprecated(default = None)
    filepath: Optional[str] = mark_deprecated(default = None)
    save_args: Optional[List[Parameter]] = mark_deprecated(default = None)
    load_args: Optional[List[Parameter]] = mark_deprecated(default = None)
    credentials: Optional[str] = None
```

```
@strawberry.input
class DataSetInput:
    name: str
    config: Optional[str] = None
    type: Optional[str] = mark_deprecated(default = None)
    filepath: Optional[str] = mark_deprecated(default = None)
    save_args: Optional[List[ParameterInput]] = mark_deprecated(default = None)
    load_args: Optional[List[ParameterInput]] = mark_deprecated(default = None)
    credentials: Optional[str] = None
```

The `config` field should be used instead to specify a dataset configuration as a JSON
string.  The `config` field approach supports all dataset implementations.

#### Pipeline and PipelineInput types

The following fields of the `Pipeline` and `PipelineInput` types are marked for
deprecation and will be removed in a future release:

- `inputs`
- `outputs`

```
@strawberry.type
class Pipeline:
    kedro_pipelines: strawberry.Private[Optional[dict]] = None
    kedro_catalog: strawberry.Private[Optional[dict]] = None
    kedro_parameters: strawberry.Private[Optional[dict]] = None

    id: Optional[uuid.UUID] = None
    inputs: Optional[List[DataSet]] = mark_deprecated(default= None)
    name: str
    outputs: Optional[List[DataSet]] = mark_deprecated(default= None)
    data_catalog: Optional[List[DataSet]] = None
    parameters: List[Parameter]
    status: Optional[str] = None
    tags: Optional[List[Tag]] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    task_args: Optional[str] = None
    task_kwargs: Optional[str] = None
    task_request: Optional[str] = None
    task_exception: Optional[str] = None
    task_traceback: Optional[str] = None
    task_einfo: Optional[str] = None
    task_result: Optional[str] = None
```

```
@strawberry.input(description = "PipelineInput")
class PipelineInput:
    name: str
    parameters: Optional[List[ParameterInput]] = None
    inputs: Optional[List[DataSetInput]] = mark_deprecated(default = None)
    outputs: Optional[List[DataSetInput]] = mark_deprecated(default = None)
    data_catalog: Optional[List[DataSetInput]] = None
    tags: Optional[List[TagInput]] = None
```

The `data_catalog` field should be used instead.
