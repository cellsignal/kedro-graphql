# kedro-graphql

## Overview

Kedro-graphql is a [kedro-plugin](https://docs.kedro.org/en/stable/extend_kedro/plugins.html) 
for serving kedro projects as a graphql api.  It leverages 
[Strawberry](https://strawberry.rocks/), [FastAPI](https://fastapi.tiangolo.com/), 
and [Celery](https://docs.celeryq.dev/en/stable/index.html) to turn any 
 [Kedro](https://docs.kedro.org/en/stable/) project into a GraphqlQL api 
 with features such as:
 
 - a distributed task queue
 - events
   - subscribe to pipeline events (status updates) via GraphQL subscriptions 
 - storage
   - persist and track all pipelines executed via the API
 - [additional features](#features)

```mermaid
flowchart  TB
  api[GraphQL API\n<i>strawberry + FastAPI</i>]
  mongodb[(db: 'pipelines'\ncollection: 'pipelines'\n<i>mongdob</i>)]
  redis[(task queue\n<i>redis</i>)]
  worker[worker\n<i>celery</i>]

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

Navigate to http://127.0.0.1:5000/graphql to access the graphql interface.

![strawberry-ui](docs/strawberry-ui.png)

The [docker-compose.yaml](./docker-compose.yaml) includes 
[mongo-express](https://github.com/mongo-express/mongo-express) and 
[redis-commander](https://github.com/joeferner/redis-commander) services 
to provide easy acess to MongoDB and redis.


Navigate to http://127.0.0.1:8082 to access mongo-express interface.

![mongo-express-ui](docs/mongo-express-ui.png)

Navigate to http://127.0.0.1:8081 to access the redis-commander interface.
One can access the task queues created and managed by 
[Celery](https://docs.celeryq.dev/en/stable/index.html).

![redis-commander-ui](docs/redis-commander-ui.png)

## Example

The kedro-graphl package contains an very simple example 
pipeline called "example00".

### Setup

Clone the kedro-graphql repository.

```
git clone git@github.com:opensean/kedro-graphql.git
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
Navigate to http://127.0.0.1:5000/graphql to access the graphql interface 
and execute the following mutation:

```
mutation MyMutation {
  pipeline(
    pipeline: {name: "example00", parameters: [{name: "example", value: "hello"}, {name: "duration", value: "10"}], inputs: {name: "text_in", type: "text.TextDataSet", filepath: "./data/01_raw/text_in.txt"}, outputs: {name: "text_out", type: "text.TextDataSet", filepath: "./data/02_intermediate/text_out.txt"}}
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
    "pipeline": {
      "id": "6463991db98d7f8564ab15a0",
      "name": "example00"
    }
  }
}
```

Now execute the following subscription to track the progress:

```
subscription MySubscription {
  pipeline(id: "6463991db98d7f8564ab15a0") {
    id
    result
    status
    taskId
    timestamp
    traceback
  }
}
```

![subscription](docs/subscription.gif)

Fetch the pipeline result with the following query:

```
query MyQuery {
  pipeline(id: "6463991db98d7f8564ab15a0") {
    describe
    id
    name
    outputs {
      filepath
      name
      type
    }
    inputs {
      filepath
      name
      type
    }
    parameters {
      name
      value
    }
    status
    taskEinfo
    taskException
    taskId
    taskKwargs
    taskRequest
    taskName
    taskResult
    taskTraceback
  }
}
```

Expected result:

```
{
  "data": {
    "pipeline": {
      "describe": "#### Pipeline execution order ####\nInputs: parameters, params:example, text_in\n\necho_node\n\nOutputs: text_out\n##################################",
      "id": "6463991db98d7f8564ab15a0",
      "name": "example00",
      "outputs": [
        {
          "filepath": "./data/02_intermediate/text_out.txt",
          "name": "text_out",
          "type": "text.TextDataSet"
        }using 
      ],
      "inputs": [
        {
          "filepath": "./data/01_raw/text_in.txt",
          "name": "text_in",
          "type": "text.TextDataSet"
        }
      ],
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
      "status": "SUCCESS",
      "taskEinfo": "None",
      "taskException": null,
      "taskId": "129b4441-6150-4c0b-90df-185c1ec692ea",
      "taskKwargs": "{'name': 'example00', 'inputs': {'text_in': {'type': 'text.TextDataSet', 'filepath': './data/01_raw/text_in.txt'}}, 'outputs': {'text_out': {'type': 'text.TextDataSet', 'filepath': './data/02_intermediate/text_out.txt'}}, 'parameters': {'example': 'hello', 'duration': '10'}}",
      "taskRequest": null,
      "taskName": "<@task: kedro_graphql.tasks.run_pipeline of kedro_graphql at 0x7f29e3e9e500>",
      "taskResult": null,
      "taskTraceback": null
    }
  }
}
```
One can explore how the pipeline is persisted using the mongo-express 
interface located here http://127.0.0.1:8082.  Pipelines are persisted in the
"pipelines" collection of the "pipelines" database.

![mongo-express-pipeline](./docs/mongo-express-pipeline.png)

![mongo-express-pipeline-doc](./docs/mongo-express-pipeline-doc.png)
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
from kedro_graphql import KedroGraphql



class MyApp(KedroGraphql):

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

## General Configuration

Configuration can be supplied via environment variables or a ```.env``` file.

```
## example .env file
MONGO_URI = 'mongodb://root:example@localhost:27017/'
MONGO_DB_NAME = 'pipelines'
KEDRO_GRAPHQL_IMPORTS = "kedro_graphql.plugins.plugins"
KEDRO_GRAPHQL_APP = "kedro_graphql.asgi.KedroGraphql"
```

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

- include EXCEPTION_STATES in kedro_graphql.events.PipelineEventMonitor to exit when task fails
- support custom runners e.g. Argo Workflows, AWS Batch, etc...
- document plan for supporting custom IOResolverPlugins 
- extensible data model to capture additional metadata along with pipeline instance

