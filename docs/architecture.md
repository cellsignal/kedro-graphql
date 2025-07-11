Kedro GraphQL leverages
[Strawberry](https://strawberry.rocks/), [FastAPI](https://fastapi.tiangolo.com/),
and [Celery](https://docs.celeryq.dev/en/stable/index.html) to turn any
 [Kedro](https://docs.kedro.org/en/stable/) project into a GraphqlQL API
 with features such as:

- a distributed task queue

```mermaid
flowchart TD
  client[Client]
  api[GraphQL API<br/><i>FastAPI + Strawberry</i>]
  redis[(Redis <br>Task Queue & Results)]

  client -- "GraphQL Request" --> api
  api -- "Publish Task" --> redis
  redis -- "Consume Task" --> worker00[worker]
  redis -- "Consume Task" --> worker01[worker]
  redis -- "Consume Task" --> worker02[etc...]

  worker00 -- "run_pipeline" --> runner00
  worker01 -- "run_pipeline" --> runner01
  worker02 -- "run_pipeline" --> runner02

  subgraph Celery Workers
    worker00
    worker01
    worker02
  end

  subgraph Kedro Runners
    runner00[SequentialRunner]
    runner01[ArgoWorkflowsRunner]
    runner02[etc...]
  end

classDef worker fill:#f9f,stroke:#333,stroke-width:2px;
```

  - Persist and track all pipeline executions, parameters, and results

```mermaid
flowchart TD
  client[Client]
  api[GraphQL API<br/><i>FastAPI + Strawberry</i>]
  mongodb[(MongoDB<br/>pipelines collection)]

  client -- "GraphQL Request" --> api
  api -- "create_pipeline" --> mongodb
  mongodb -- "read_pipeline" --> api
  api -- "GraphQL Response" --> client
```
  

- streaming pipeline logs via GraphQL subscriptions

```mermaid
flowchart TD
  client[Client]
  api[GraphQL API<br/><i>FastAPI + Strawberry</i>]
  redis[(Redis Stream<br/>Pipeline Logs)]
  worker[Celery Worker<br/><i>Kedro Pipeline</i>]

  worker -- "Publish Logs" --> redis
  redis -- "Stream Logs" --> api
  api -- "GraphQL Subscription<br/>Pipeline Logs" --> client
```

- querying and mutating pipeline data in MongoDB

