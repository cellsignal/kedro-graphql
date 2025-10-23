from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport
from kedro_graphql.models import PipelineInput, Pipeline, Pipelines, PipelineEvent, PipelineLogMessage, DataSetInput
from kedro_graphql.config import load_config
import backoff
from gql.transport.exceptions import TransportQueryError
from typing import Optional, List
import logging

logger = logging.getLogger("kedro-graphql")
CONFIG = load_config()
logger.debug("configuration loaded by {s}".format(s=__name__))

PIPELINE_GQL = """{
                    id
                    parent
                    name
                    describe
                    createdAt
                    projectVersion
                    pipelineVersion
                    kedroGraphqlVersion
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


class KedroGraphqlClient():

    def __init__(self, uri_graphql=None, uri_ws=None, pipeline_gql=None, headers={}, cookies=None):
        """
        Kwargs:
            uri_graphql (str): uri to api [default: http://localhost:5000/graphql]
            uri_ws (str): uri to websocket [default: ws://localhost:5000/graphql]
            pipeline_gql (str): pipeline graphql query [default: kedro_graphql.client.PIPELINE_GQL]

        """
        self.uri_graphql = uri_graphql or CONFIG["KEDRO_GRAPHQL_CLIENT_URI_GRAPHQL"]
        self.uri_ws = uri_ws or CONFIG["KEDRO_GRAPHQL_CLIENT_URI_WS"]
        if cookies:
            self._cookies = "; ".join(
                [f"{key}={value}" for key, value in cookies.items()])
            self._cookies = {"Cookie": self._cookies}
        else:
            self._cookies = {}

        self._headers = headers
        self._headers.update(self._cookies)

        self._aio_transport = AIOHTTPTransport(
            url=self.uri_graphql, headers=headers)

        self._aio_client = Client(transport=self._aio_transport)
        self._aio_session = None
        self.pipeline_gql = pipeline_gql or PIPELINE_GQL

    async def _get_aio_session(self):
        """Get or create an aio session.
        """
        if not self._aio_session:
            logger.info("connecting aio session")
            self._aio_session = await self._aio_client.connect_async(reconnecting=True)
            return self._aio_session
        else:
            return self._aio_session

    async def close_sessions(self):
        """Close any open aio and web sessions.
        """
        if self._aio_session:
            logger.info("closing aio session")
            await self._aio_client.close_async()

    async def execute_query(self, query: str, variable_values: Optional[dict] = None):
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

    async def create_pipeline(self, pipeline_input: PipelineInput = None, unique_paths: List[str] = None):
        """Create a pipeline

        Kwargs:
            pipeline (PipelineInput): pipeline input object

        Returns:
            Pipeline: pipeline object
        """
        query = """
            mutation createPipeline($pipeline: PipelineInput!, $uniquePaths: [String!]) {
              createPipeline(pipeline: $pipeline, uniquePaths: $uniquePaths) """ + self.pipeline_gql + """
            }
        """

        result = await self.execute_query(query, variable_values={"pipeline": pipeline_input.encode(encoder="graphql"), "uniquePaths": unique_paths})
        return Pipeline.decode(result["createPipeline"], decoder="graphql")

    async def read_pipeline(self, id: str = None):
        """Read a pipeline.
        Kwargs:
            id (str): pipeline id

        Returns:
            Pipeline: pipeline object
        """
        query = """
            query readPipeline($id: String!) {
              readPipeline(id: $id) """ + self.pipeline_gql + """
            }
        """

        result = await self.execute_query(query, variable_values={"id": str(id)})
        return Pipeline.decode(result["readPipeline"], decoder="graphql")

    async def read_pipelines(self, limit: int = 10, cursor: str = None, filter: str = "", sort: str = ""):
        """Read pipelines.

        Kwargs:
            limit (int): limit
            cursor (str): cursor
            filter (str): a valid MongoDb document query filter https://www.mongodb.com/docs/manual/core/document/#std-label-document-query-filter.

        Returns:
            Pipelines (list): an list of pipeline objects
        """
        query = """
            query readPipelines($limit: Int!, $cursor: String, $filter: String, $sort: String) {
              readPipelines(limit: $limit, cursor: $cursor, filter: $filter, sort: $sort) { 
                pageMeta {
                  nextCursor
                }
                pipelines """ + self.pipeline_gql + """
              }
            }
        """

        result = await self.execute_query(query, variable_values={"limit": limit, "cursor": cursor, "filter": filter, "sort": sort})
        return Pipelines.decode(result, decoder="graphql")

    async def update_pipeline(self, id: str = None, pipeline_input: PipelineInput = None, unique_paths: List[str] = None):
        """Update a pipeline

        Kwargs:
            id (str): pipeline id
            pipeline_input (PipelineInput): pipeline input object

        Returns:
            Pipeline: pipeline object
        """
        query = """
            mutation updatePipeline($id: String!, $pipeline: PipelineInput!, $uniquePaths: [String!]) {
              updatePipeline(id: $id, pipeline: $pipeline, uniquePaths: $uniquePaths) """ + self.pipeline_gql + """
            }
        """

        result = await self.execute_query(query, variable_values={"id": str(id), "pipeline": pipeline_input.encode(encoder="graphql"), "uniquePaths": unique_paths})
        return Pipeline.decode(result["updatePipeline"], decoder="graphql")

    async def delete_pipeline(self, id: str = None):
        """Delete a pipeline.

        Kwargs:
            id (str): pipeline id

        Returns:
            Pipeline: pipeline object that was deleted.
        """
        query = """
            mutation deletePipeline($id: String!) {
              deletePipeline(id: $id) """ + self.pipeline_gql + """ 
            }
        """

        result = await self.execute_query(query, variable_values={"id": str(id)})
        return Pipeline.decode(result["deletePipeline"], decoder="graphql")

    async def read_datasets(self, id: str = None, datasets: list[DataSetInput] = None, expires_in_sec: int = 43200):
        """Read a dataset.
        Kwargs:
            id (str): pipeline id
            datasets (list[DataSetInput]): dataset inputs for which to get signed URLs. In order to read specific partitions of a PartitionedDataset, pass a DataSetInput with the dataset name and list of partitions e.g. DataSetInput(name="dataset_name", partitions=["partition1", "partition2"]).
            expires_in_sec (int): number of seconds the signed URL should be valid for

        Returns:
            str: signed URL for reading the dataset
        """
        query = """
            query readDatasets($id: String!, $datasets: [DataSetInput!]!, $expires_in_sec: Int!) {
              readDatasets(id: $id, datasets: $datasets, expiresInSec: $expires_in_sec) 
            }
        """

        result = await self.execute_query(query, variable_values={"id": str(id), "datasets": [d.encode(encoder="graphql") for d in datasets], "expires_in_sec": expires_in_sec})
        return result["readDatasets"]

    async def create_datasets(self, id: str = None, datasets: list[DataSetInput] = None, expires_in_sec: int = 43200):
        """create a dataset.
        Kwargs:
            id (str): pipeline id
            datasets (list[DataSetInput]): List of datasets for which to create signed URLs. In order to create specific partitions of a PartitionedDataset, pass a DataSetInput with the dataset name and list of partitions e.g. DataSetInput(name="dataset_name", partitions=["partition1", "partition2"]).
            expires_in_sec (int): number of seconds the signed URL should be valid for

        Returns:
            [str]: array of signed URLs for creating the datasets
        """
        query = """
            mutation createDatasets($id: String!, $datasets: [DataSetInput!]!, $expires_in_sec: Int!) {
              createDatasets(id: $id, datasets: $datasets, expiresInSec: $expires_in_sec)
            }
        """

        result = await self.execute_query(query, variable_values={"id": str(id), "datasets": [d.encode(encoder="graphql") for d in datasets], "expires_in_sec": expires_in_sec})
        return result["createDatasets"]

    @backoff.on_exception(backoff.expo, Exception, max_time=60, giveup=lambda e: isinstance(e, TransportQueryError))
    async def pipeline_events(self, id: str = None):
        """Subscribe to pipeline events.

        Kwargs:
            id (str): pipeline id

        Returns:
            PipelineEvent (generator): a generator of PipelineEvent objects
        """
        async with Client(
            transport=WebsocketsTransport(url=self.uri_ws, headers=self._headers),
        ) as session:
            query = gql(
                """
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
            """
            )
            logger.info("started pipeline events subscription")
            async for result in session.subscribe(query, variable_values={"id": str(id)}):
                yield PipelineEvent.decode(result, decoder="graphql")

    @backoff.on_exception(backoff.expo, Exception, max_time=60, giveup=lambda e: isinstance(e, TransportQueryError))
    async def pipeline_logs(self, id: str = None):
        """Subscribe to pipeline logs.

        Kwargs:
            id (str): pipeline id

        Returns:
            PipelineLogMessage (generator): a generator of PipelineLogMessage objects
        """
        async with Client(
            transport=WebsocketsTransport(url=self.uri_ws, headers=self._headers),
        ) as session:

            query = gql(
                """
                subscription pipelineLogs($id: String!) {
                  pipelineLogs(id: $id) {
                    id
                    message
                    messageId
                    taskId
                    time
                  }
                }
            """
            )
            logger.info("started pipeline logs subscription")
            async for result in session.subscribe(query, variable_values={"id": str(id)}):
                yield PipelineLogMessage.decode(result, decoder="graphql")
