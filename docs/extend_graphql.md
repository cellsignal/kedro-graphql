The GraphQL API can be extended using decorators.

This example adds a query, mutation, and subscription types.

```python
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

```bash
kedro gql --imports "kedro_graphql.plugins.plugins"
```

Multiple import paths can be specified using comma separated values.

```bash
kedro gql --imports "kedro_graphql.plugins.plugins,example_pkg.example.my_types"
```

## Capture custom logs in `pipelineLogs`

`pipelineLogs` streams logs from the active pipeline task using a task-scoped Redis stream.
To ensure your custom logs are included consistently:

1. Use Python logging (avoid `print()` for pipeline runtime messages).
2. Log from any module logger (for example `logging.getLogger(__name__)`).
3. Keep logger propagation enabled (default behavior) so records reach the root logger.

### Example: custom node logs

```python
import logging

node_logger = logging.getLogger(__name__)


def enrich_features(df):
    node_logger.info("starting feature enrichment")
    # ... node logic ...
    node_logger.info("feature enrichment completed")
    return df
```

### Example: subscribe to pipeline logs

```graphql
subscription MyPipelineLogs {
    pipelineLogs(id: "67b795d44f0f5729b9b5730e") {
        id
        taskId
        messageId
        time
        message
    }
}
```

### Notes

- `pipelineLogs` is per task run; it starts streaming once a `taskId` exists.
- The subscription requires the `subscribe_to_logs` permission action.
- For consistent output, prefer a single logging style (`logger.info`, `logger.warning`, `logger.error`) across custom code.
