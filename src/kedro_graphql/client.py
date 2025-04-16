from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport
from kedro_graphql.models import PipelineInput, Pipeline, Pipelines, PipelineEvent, PipelineLogMessage
from kedro_graphql.config import config
import backoff
from gql.transport.exceptions import TransportQueryError
from typing import Optional
import logging

logger = logging.getLogger("kedro-graphql")

PIPELINE_GQL = """{
                    id
                    parent
                    name
                    describe
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

    def __init__(self, uri_graphql=None, uri_ws=None, pipeline_gql=None):
        """
        Kwargs:
            uri_graphql (str): uri to api [default: http://localhost:5000/graphql]
            uri_ws (str): uri to websocket [default: ws://localhost:5000/graphql]
            pipeline_gql (str): pipeline graphql query [default: kedro_graphql.client.PIPELINE_GQL]

        """
        self.uri_graphql = uri_graphql or config["KEDRO_GRAPHQL_CLIENT_URI_GRAPHQL"]
        self.uri_ws = uri_ws or config["KEDRO_GRAPHQL_CLIENT_URI_WS"]
        self._aio_transport = AIOHTTPTransport(url=self.uri_graphql)
        self._web_transport = WebsocketsTransport(url=self.uri_ws)
        self._aio_client = Client(transport=self._aio_transport)
        self._aio_session = None
        self._web_client = Client(transport=self._web_transport)
        self._web_session = None
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
        """
        """
        if self._aio_session:
            logger.info("closing aio session")
            await self._aio_client.close_async()
        if self._web_session:
            logger.info("closing web session")
            await self._web_client.close_async()


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

    async def create_pipeline(self, pipeline_input: PipelineInput = None):
        """Create a pipeline

        Kwargs:
            pipeline (PipelineInput): pipeline input object

        Returns:
            Pipeline: pipeline object
        """
        query = gql(
            """
            mutation createPipeline($pipeline: PipelineInput!) {
              createPipeline(pipeline: $pipeline) """ + self.pipeline_gql + """
            }
        """
        )

        result = await self.execute_query(query, variable_values={"pipeline": pipeline_input.encode(encoder="graphql")})
        return Pipeline.decode(result["createPipeline"], decoder="graphql")

    async def read_pipeline(self, id: str = None):
        """Read a pipeline.
        Kwargs:
            id (str): pipeline id

        Returns:
            Pipeline: pipeline object
        """
        query = gql(
            """
            query readPipeline($id: String!) {
              readPipeline(id: $id) """ + self.pipeline_gql + """
            }
        """
        )

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
        query = gql(
            """
            query readPipelines($limit: Int!, $cursor: String, $filter: String, $sort: String) {
              readPipelines(limit: $limit, cursor: $cursor, filter: $filter, sort: $sort) { 
                pageMeta {
                  nextCursor
                }
                pipelines """ + self.pipeline_gql + """
              }
            }
        """
        )

        result = await self.execute_query(query, variable_values={"limit": limit, "cursor": cursor, "filter": filter, "sort": sort})
        return Pipelines.decode(result, decoder="graphql")

    async def update_pipeline(self, id: str = None, pipeline_input: PipelineInput = None):
        """Update a pipeline

        Kwargs:
            id (str): pipeline id
            pipeline_input (PipelineInput): pipeline input object

        Returns:
            Pipeline: pipeline object
        """
        query = gql(
            """
            mutation updatePipeline($id: String!, $pipeline: PipelineInput!) {
              updatePipeline(id: $id, pipeline: $pipeline) """ + self.pipeline_gql + """
            }
        """
        )

        result = await self.execute_query(query, variable_values={"id": str(id), "pipeline": pipeline_input.encode(encoder="graphql")})
        return Pipeline.decode(result["updatePipeline"], decoder="graphql")

    async def delete_pipeline(self, id: str = None):
        """Delete a pipeline.

        Kwargs:
            id (str): pipeline id

        Returns:
            Pipeline: pipeline object that was deleted.
        """
        query = gql(
            """
            mutation deletePipeline($id: String!) {
              deletePipeline(id: $id) """ + self.pipeline_gql + """ 
            }
        """
        )

        result = await self.execute_query(query, variable_values={"id": str(id)})
        return Pipeline.decode(result["deletePipeline"], decoder="graphql")

    @backoff.on_exception(backoff.expo, Exception, max_time=60, giveup=lambda e: isinstance(e, TransportQueryError))
    async def pipeline_events(self, id: str = None):
        """Subscribe to pipeline events.

        Kwargs:
            id (str): pipeline id

        Returns:
            PipelineEvent (generator): a generator of PipelineEvent objects
        """
        async with Client(
            transport=WebsocketsTransport(url=self.uri_ws),
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
            transport=WebsocketsTransport(url=self.uri_ws),
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
