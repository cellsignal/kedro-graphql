import asyncio
from typing import AsyncGenerator

import strawberry

from kedro_graphql.decorators import (
    gql_mutation,
    gql_query,
    gql_subscription,
)


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
