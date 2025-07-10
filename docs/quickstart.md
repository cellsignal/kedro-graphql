
Install kedro-graphql into your kedro project environnment.

```bash
pip install kedro_graphql
```

Start the redis and mongo services using this [docker-compose.yaml](https://github.com/opensean/kedro-graphql/blob/main/docker-compose.yaml).

```bash
docker-compose up -d
```

Start the api server.

```bash
kedro gql
```

Start a worker (in another terminal).

```bash
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

```bash
git clone https://github.com/cellsignal/kedro-graphql.git
```

Create a virtualenv and activate it.

```bash
cd kedro-graphql
python3.10 -m venv venv
source venv/bin/activate
```

Install dependencies.

```bash
pip install -r src/requirements.txt
```

Create a text file.

```bash
echo "Hello" > ./data/01_raw/text_in.txt
```

Start the redis and mongo services.

```bash
docker-compose up -d
```

Start the api server.

```bash
kedro gql
```

Start a worker (in another terminal).

```bash
kedro gql -w
```

### Start a pipeline

Navigate to <http://127.0.0.1:5000/graphql> to access the graphql interface
and execute the following mutation:

```graphql
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

```json
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

```graphql
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

```graphql
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

```graphql
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

```json
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

```graphql
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

```graphql
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

```graphql
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

```graphql
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