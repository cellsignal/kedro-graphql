from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport
from kedro_graphql.models import PipelineInput, Pipeline, Pipelines, PipelineEvent, PipelineLogMessage
from kedro_graphql.config import config
import backoff
from gql.transport.exceptions import TransportQueryError
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

    def __init__(self, uri=None, ws=None, pipeline_gql=None):
        """
        Kwargs:
            uri (str): uri to api [default: http://localhost:5000/graphql]
            ws (str): uri to websocket [default: ws://localhost:5000/graphql]
            pipeline_gql (str): pipeline graphql query [default: kedro_graphql.client.PIPELINE_GQL]

        """
        self.url = uri or config["KEDRO_GRAPHQL_UI_API_ENDPOINT"]
        self.ws = ws or config["KEDRO_GRAPHQL_UI_WS_ENDPOINT"]
        self._aio_transport = AIOHTTPTransport(url=self.url)
        self._web_transport = WebsocketsTransport(url=self.ws)
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

    async def _get_web_session(self):
        """Get or create a web session.
        """
        if not self._web_session:
            logger.info("connecting web session")
            self._web_session = await self._web_client.connect_async(reconnecting=True)
            return self._web_session
        else:
            return self._web_session

    async def close_sessions(self):
        """
        """
        if self._aio_session:
            logger.info("closing aio session")
            await self._aio_client.close_async()
        if self._web_session:
            logger.info("closing web session")
            await self._web_client.close_async()

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

        session = await self._get_aio_session()
        result = await session.execute(query, variable_values={"pipeline": pipeline_input.encode(encoder="graphql")})
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

        session = await self._get_aio_session()
        result = await session.execute(query, variable_values={"id": str(id)})
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
        session = await self._get_aio_session()
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

        result = await session.execute(query, variable_values={"limit": limit, "cursor": cursor, "filter": filter, "sort": sort})
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

        session = await self._get_aio_session()
        result = await session.execute(query, variable_values={"id": str(id), "pipeline": pipeline_input.encode(encoder="graphql")})
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

        session = await self._get_aio_session()
        result = await session.execute(query, variable_values={"id": str(id)})
        return Pipeline.decode(result["deletePipeline"], decoder="graphql")

    @backoff.on_exception(backoff.expo, Exception, max_time=60, giveup=lambda e: isinstance(e, TransportQueryError))
    async def pipeline_events(self, id: str = None):
        """Subscribe to pipeline events.

        Kwargs:
            id (str): pipeline id

        Returns:
            PipelineEvent (generator): a generator of PipelineEvent objects
        """
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

        session = await self._get_web_session()
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

        session = await self._get_web_session()
        async for result in session.subscribe(query, variable_values={"id": str(id)}):
            yield PipelineLogMessage.decode(result, decoder="graphql")
