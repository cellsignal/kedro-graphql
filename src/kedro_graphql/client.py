from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

import backoff
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError
from gql.transport.websockets import WebsocketsTransport
import logging

from kedro_graphql.config import KedroGraphQLConfig, load_config
from kedro_graphql.models import (
    DataSetInput,
    DataSetPartitions,
    Pipeline,
    PipelineEvent,
    PipelineInput,
    PipelineLogMessage,
    Pipelines,
    SignedUrl,
    SignedUrls,
)

logger = logging.getLogger("kedro-graphql")
PIPELINE_GQL = """{
                    id
                    parent
                    name
                    describe
                    createdAt
                    projectVersion
                    pipelineVersion
                    kedroGraphqlVersion
                    hooks
                    dataCatalog {
                      name
                      config
                      tags {
                        key
                        value
                      }
                    }
                    nodes {
                      name
                      inputs
                      outputs
                      tags
                    }
                    parameters {
                      name
                      value
                      type
                    }
                    status {
                      session
                      state
                      runner
                      startedAt
                      finishedAt
                      taskId
                      taskName
                      taskArgs
                      taskKwargs
                      taskRequest
                      taskException
                      taskTraceback
                      taskEinfo
                      taskResult
                    }
                    tags {
                      key
                      value
                    }
                  }"""


class KedroGraphqlClient:

    def __init__(
        self,
        uri_graphql: str | None = None,
        uri_ws: str | None = None,
        pipeline_gql: str | None = None,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, str] | None = None,
        config: KedroGraphQLConfig | None = None,
    ) -> None:
        """
        Kwargs:
            uri_graphql (str): uri to api [default: http://localhost:5000/graphql]
            uri_ws (str): uri to websocket [default: ws://localhost:5000/graphql]
            pipeline_gql (str): pipeline graphql query [default: kedro_graphql.client.PIPELINE_GQL]

        """
        config = config or load_config()
        request_headers = dict(headers or {})
        self.uri_graphql = uri_graphql or config.client_uri_graphql
        self.uri_ws = uri_ws or config.client_uri_ws
        if cookies:
            cookie_header = "; ".join(
                f"{key}={value}" for key, value in cookies.items()
            )
            self._cookies = {"Cookie": cookie_header}
        else:
            self._cookies = {}

        self._headers = request_headers
        self._headers.update(self._cookies)

        self._aio_transport = AIOHTTPTransport(
            url=self.uri_graphql, headers=self._headers
        )

        self._aio_client = Client(transport=self._aio_transport)
        self._aio_session: Any | None = None
        self.pipeline_gql = pipeline_gql or PIPELINE_GQL

    async def _get_aio_session(self) -> Any:
        """Get or create an aio session."""
        if not self._aio_session:
            logger.info("connecting aio session")
            self._aio_session = await self._aio_client.connect_async(reconnecting=True)
            return self._aio_session
        else:
            return self._aio_session

    async def close_sessions(self) -> None:
        """Close any open aio and web sessions."""
        if self._aio_session:
            logger.info("closing aio session")
            await self._aio_client.close_async()

    async def execute_query(
        self,
        query: str,
        variable_values: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a query to the GraphQL API.

        Kwargs:
            query (str): GraphQL query
            variables (dict): GraphQL variables

        Returns:
            dict: response
        """
        variable_values = variable_values or {}
        session = await self._get_aio_session()
        result = await session.execute(gql(query), variable_values=variable_values)
        return result

    async def create_pipeline(
        self,
        pipeline_input: PipelineInput,
        unique_paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> Pipeline:
        """Create a pipeline

        Kwargs:
            pipeline (PipelineInput): pipeline input object
            dry_run (bool): validate and return the projected pipeline without saving or submitting it

        Returns:
            Pipeline: pipeline object
        """
        query = (
            """
            mutation createPipeline($pipeline: PipelineInput!, $uniquePaths: [String!], $dryRun: Boolean!) {
              createPipeline(pipeline: $pipeline, uniquePaths: $uniquePaths, dryRun: $dryRun) """
            + self.pipeline_gql
            + """
            }
        """
        )

        result = await self.execute_query(
            query,
            variable_values={
                "pipeline": pipeline_input.to_graphql(),
                "uniquePaths": unique_paths,
                "dryRun": dry_run,
            },
        )
        return Pipeline.from_dict(result["createPipeline"])

    async def read_pipeline(self, id: str) -> Pipeline:
        """Read a pipeline.
        Kwargs:
            id (str): pipeline id

        Returns:
            Pipeline: pipeline object
        """
        query = (
            """
            query readPipeline($id: String!) {
              readPipeline(id: $id) """
            + self.pipeline_gql
            + """
            }
        """
        )

        result = await self.execute_query(query, variable_values={"id": str(id)})
        return Pipeline.from_dict(result["readPipeline"])

    async def read_pipelines(
        self,
        limit: int = 10,
        cursor: str | None = None,
        filter: str = "",
        sort: str = "",
    ) -> Pipelines:
        """Read pipelines.

        Kwargs:
            limit (int): limit
            cursor (str): cursor
            filter (str): a valid MongoDb document query filter https://www.mongodb.com/docs/manual/core/document/#std-label-document-query-filter.

        Returns:
            Pipelines (list): an list of pipeline objects
        """
        query = (
            """
            query readPipelines($limit: Int!, $cursor: String, $filter: String, $sort: String) {
              readPipelines(limit: $limit, cursor: $cursor, filter: $filter, sort: $sort) { 
                pageMeta {
                  nextCursor
                }
                pipelines """
            + self.pipeline_gql
            + """
              }
            }
        """
        )

        result = await self.execute_query(
            query,
            variable_values={
                "limit": limit,
                "cursor": cursor,
                "filter": filter,
                "sort": sort,
            },
        )
        return Pipelines.from_graphql(result)

    async def update_pipeline(
        self,
        id: str,
        pipeline_input: PipelineInput,
        unique_paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> Pipeline:
        """Update a pipeline

        Kwargs:
            id (str): pipeline id
            pipeline_input (PipelineInput): pipeline input object
            dry_run (bool): validate and return the projected pipeline without saving or submitting it

        Returns:
            Pipeline: pipeline object
        """
        query = (
            """
            mutation updatePipeline($id: String!, $pipeline: PipelineInput!, $uniquePaths: [String!], $dryRun: Boolean!) {
              updatePipeline(id: $id, pipeline: $pipeline, uniquePaths: $uniquePaths, dryRun: $dryRun) """
            + self.pipeline_gql
            + """
            }
        """
        )

        result = await self.execute_query(
            query,
            variable_values={
                "id": str(id),
                "pipeline": pipeline_input.to_graphql(),
                "uniquePaths": unique_paths,
                "dryRun": dry_run,
            },
        )
        return Pipeline.from_dict(result["updatePipeline"])

    async def delete_pipeline(self, id: str) -> Pipeline:
        """Delete a pipeline.

        Kwargs:
            id (str): pipeline id

        Returns:
            Pipeline: pipeline object that was deleted.
        """
        query = (
            """
            mutation deletePipeline($id: String!) {
              deletePipeline(id: $id) """
            + self.pipeline_gql
            + """
            }
        """
        )

        result = await self.execute_query(query, variable_values={"id": str(id)})
        return Pipeline.from_dict(result["deletePipeline"])

    async def read_datasets(
        self,
        id: str,
        datasets: Sequence[DataSetInput],
        expires_in_sec: int = 43200,
    ) -> list[SignedUrl | SignedUrls | DataSetPartitions]:
        """Read a dataset.
        Kwargs:
            id (str): pipeline id
            datasets (list[DataSetInput]): dataset inputs for which to get signed URLs. In order to read specific partitions of a PartitionedDataset, pass a DataSetInput with the dataset name and list of partitions e.g. DataSetInput(name="dataset_name", partitions=["partition1", "partition2"]). To list available partitions, pass DataSetInput(name="dataset_name", list_partitions=True).
            expires_in_sec (int): number of seconds the signed URL should be valid for

        Returns:
            Signed URL objects, or typed partition results when list_partitions is requested.
        """
        query = """
            query readDatasets($id: String!, $datasets: [DataSetInput!]!, $expires_in_sec: Int!) {
              readDatasets(id: $id, datasets: $datasets, expiresInSec: $expires_in_sec){
                __typename
                ... on SignedUrl {
                  url
                  file
                  fields {
                    name
                    value
                  }
                }
                ... on SignedUrls {
                  urls {
                    url
                    file
                    fields {
                      name
                      value
                    }
                  }
                }
                ... on DataSet {
                  name
                  config
                  tags {
                    key
                    value
                  }
                  partitions
                }
              }
            }
        """

        result = await self.execute_query(
            query,
            variable_values={
                "id": str(id),
                "datasets": [dataset.to_graphql() for dataset in datasets],
                "expires_in_sec": expires_in_sec,
            },
        )
        values: list[SignedUrl | SignedUrls | DataSetPartitions] = []
        for item in result["readDatasets"]:
            typename = item["__typename"]
            payload = {key: value for key, value in item.items() if key != "__typename"}
            if typename == "SignedUrl":
                values.append(SignedUrl.from_graphql(payload))
            elif typename == "SignedUrls":
                values.append(SignedUrls.from_graphql(payload))
            elif typename == "DataSet":
                values.append(DataSetPartitions.from_graphql(payload))
            else:
                raise TypeError(
                    f"Unexpected type {typename} returned from readDatasets"
                )

        return values

    async def create_datasets(
        self,
        id: str,
        datasets: Sequence[DataSetInput],
        expires_in_sec: int = 43200,
    ) -> list[SignedUrl | SignedUrls]:
        """create a dataset.
        Kwargs:
            id (str): pipeline id
            datasets (list[DataSetInput]): List of datasets for which to create signed URLs. In order to create specific partitions of a PartitionedDataset, pass a DataSetInput with the dataset name and list of partitions e.g. DataSetInput(name="dataset_name", partitions=["partition1", "partition2"]).
            expires_in_sec (int): number of seconds the signed URL should be valid for

        Returns:
            Signed URL objects for creating the datasets.
        """
        query = """
            mutation createDatasets($id: String!, $datasets: [DataSetInput!]!, $expires_in_sec: Int!) {
              createDatasets(id: $id, datasets: $datasets, expiresInSec: $expires_in_sec){
                __typename
                ... on SignedUrl {
                  url
                  file
                  fields {
                    name
                    value
                  }
                }
                ... on SignedUrls {
                  urls {
                    url
                    file
                    fields {
                      name
                      value
                    }
                  }
                }
              }
            }
        """

        result = await self.execute_query(
            query,
            variable_values={
                "id": str(id),
                "datasets": [dataset.to_graphql() for dataset in datasets],
                "expires_in_sec": expires_in_sec,
            },
        )
        urls: list[SignedUrl | SignedUrls] = []
        for item in result["createDatasets"]:
            typename = item["__typename"]
            payload = {key: value for key, value in item.items() if key != "__typename"}
            if typename == "SignedUrl":
                urls.append(SignedUrl.from_graphql(payload))
            elif typename == "SignedUrls":
                urls.append(SignedUrls.from_graphql(payload))
            else:
                raise TypeError(
                    f"Unexpected type {typename} returned from createDatasets"
                )

        return urls

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_time=60,
        giveup=lambda e: isinstance(e, TransportQueryError),
    )
    async def pipeline_events(self, id: str) -> AsyncIterator[PipelineEvent]:
        """Subscribe to pipeline events.

        Kwargs:
            id (str): pipeline id

        Returns:
            PipelineEvent (generator): a generator of PipelineEvent objects
        """
        async with Client(
            transport=WebsocketsTransport(url=self.uri_ws, headers=self._headers),
        ) as session:
            query = gql("""
                subscription pipelineEvents($id: String!) {
                  pipeline(id: $id) {
                    id
                    taskId
                    status
                    result
                    timestamp
                    traceback
                  }
                }
            """)
            logger.info("started pipeline events subscription")
            async for result in session.subscribe(
                query, variable_values={"id": str(id)}
            ):
                yield PipelineEvent.from_graphql(result)

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_time=60,
        giveup=lambda e: isinstance(e, TransportQueryError),
    )
    async def pipeline_logs(self, id: str) -> AsyncIterator[PipelineLogMessage]:
        """Subscribe to pipeline logs.

        Kwargs:
            id (str): pipeline id

        Returns:
            PipelineLogMessage (generator): a generator of PipelineLogMessage objects
        """
        async with Client(
            transport=WebsocketsTransport(url=self.uri_ws, headers=self._headers),
        ) as session:

            query = gql("""
                subscription pipelineLogs($id: String!) {
                  pipelineLogs(id: $id) {
                    id
                    message
                    messageId
                    taskId
                    time
                  }
                }
            """)
            logger.info("started pipeline logs subscription")
            async for result in session.subscribe(
                query, variable_values={"id": str(id)}
            ):
                yield PipelineLogMessage.from_graphql(result)
