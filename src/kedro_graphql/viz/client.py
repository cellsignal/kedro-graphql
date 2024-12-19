from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport
from kedro_graphql.models import PipelineInput, Pipeline, Pipelines, PageMeta, PipelineEvent, PipelineLogMessage
from fastapi.encoders import jsonable_encoder
from strawberry.utils.str_converters import to_camel_case, to_snake_case
from kedro_graphql.config import config

class KedroGraphqlClient():

    def __init__(self, url = None, ws = None ):
        """
        Kwargs:
            url (str): Url to api [default: http://localhost:5000/graphql]
        
        """
        ##self.url = url or "http://localhost:5000/graphql" config["KEDRO_GRAPHQL_VIZ_API_ENDPOINT"]
        ##self.ws = ws or "ws://localhost:5000/graphql" config["KEDRO_GRAPHQL_VIZ_WS_ENDPOINT"]
        self.url = url or config["KEDRO_GRAPHQL_VIZ_API_ENDPOINT"]
        self.ws = ws or config["KEDRO_GRAPHQL_VIZ_WS_ENDPOINT"]
        self._aio_transport = AIOHTTPTransport(url=self.url) 
        self._web_transport = WebsocketsTransport(url=self.ws) 
        self._aio_client = Client(transport=self._aio_transport)
        self._aio_session = None
        self._web_client = Client(transport=self._web_transport)
        self._web_session = None

    async def connect_aio(self):
        if not self._aio_session:
            self._aio_session = await self._aio_client.connect_async(reconnecting=True)

    async def connect_web(self):
        if not self._web_session:
            self._web_session = await self._web_client.connect_async(reconnecting=True)

    async def createPipeline(self, pipeline: PipelineInput):
    
        # Using `async with` on the client will start a connection on the transport
        # and provide a `session` variable to execute queries on this connection
        async with Client(
            transport=self._aio_transport,
        ) as gql_session:

    
            # Execute mutation
            query = gql(
                """
                mutation createPipeline($pipeline: PipelineInput!) {
                  pipeline(pipeline: $pipeline) {
                    id
                    name
                    describe
                    dataCatalog {
                      name
                      config
                    }
                    inputs {
                      name
                      config
                    }
                    nodes {
                      name
                      inputs
                      outputs
                      tags
                    }
                    outputs {
                      name
                      config
                    }
                    parameters {
                      name
                      value
                    }
                    status
                    tags {
                      key
                      value
                    }
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
                }
            """
            )
            ## convert from object to json compatible dict
            pipeline = jsonable_encoder(pipeline)

            ## need to convert to camelCase
            pipeline = {to_camel_case(k):v for k,v in pipeline.items()}
                        
            result = await gql_session.execute(query, variable_values={"pipeline":pipeline})
            #result = await gql_session.execute(query, variable_values={"pipeline":pipeline})
            return Pipeline.from_dict(result["pipeline"])

    async def readPipeline(self, pipeline: str):
    
        # Using `async with` on the client will start a connection on the transport
        # and provide a `session` variable to execute queries on this connection
        async with Client(
            transport=self._aio_transport,
        ) as gql_session:
    
            # Execute query
            query = gql(
                """
                query readPipeline($pipeline: String!) {
                  pipeline(id: $pipeline) {
                    id
                    name
                    describe
                    dataCatalog {
                      name
                      config
                    }
                    inputs {
                      name
                      config
                    }
                    nodes {
                      name
                      inputs
                      outputs
                      tags
                    }
                    outputs {
                      name
                      config
                    }
                    parameters {
                      name
                      value
                    }
                    status
                    tags {
                      key
                      value
                    }
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
                }
            """
            )
            result = await gql_session.execute(query, variable_values={"pipeline":pipeline})
            result = {to_snake_case(k):v for k,v in result["pipeline"].items()}
            return Pipeline.from_dict(result)

    async def readPipelines(self, limit: int, cursor: str = None, filter: str = None):
    
        # Using `async with` on the client will start a connection on the transport
        # and provide a `session` variable to execute queries on this connection
        async with Client(
            transport=self._aio_transport,
        ) as gql_session: 
            # Execute query
            query = gql(
                """
                query readPipelines($limit: Int!, $cursor: String, $filter: String!) {
                  pipelines(limit: $limit, cursor: $cursor, filter: $filter) { 
                    pageMeta {
                      nextCursor
                    }
                    pipelines {
                      id
                      parent
                      name
                      dataCatalog {
                        name
                        config
                      }
                      inputs {
                        name
                        config
                      }
                      outputs {
                        name
                        config
                      }
                      parameters {
                        name
                        value
                      }
                      status
                      tags {
                        key
                        value
                      }
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
                  }
                }
            """
            )
            result = await gql_session.execute(query, variable_values={"limit":limit, "cursor":cursor, "filter":filter})
            meta = {to_snake_case(k):v for k,v in result["pipelines"]["pageMeta"].items()}
            pipelines = [{to_snake_case(k):v for k,v in p.items()} for p in result["pipelines"]["pipelines"]]
            return Pipelines(page_meta = PageMeta(**meta),
                             pipelines = [Pipeline.from_dict(p) for p in pipelines])

    async def pipelineEvents(self, pipeline: str):
    
        # Using `async with` on the client will start a connection on the transport
        # and provide a `session` variable to execute queries on this connection
        async with Client(
            transport=self._web_transport,
        ) as gql_session:
    
            # Execute
            query = gql(
                """
                subscription pipelineEvents($pipeline: String!) {
                  pipeline(id: $pipeline) {
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

            async for result in gql_session.subscribe(query, variable_values={"pipeline":pipeline}):
                result = {to_snake_case(k):v for k,v in result["pipeline"].items()}
                yield PipelineEvent(**result)

    async def pipelineLogs(self, pipeline: str):
    
        # Using `async with` on the client will start a connection on the transport
        # and provide a `session` variable to execute queries on this connection
        async with Client(
            transport=self._web_transport,
        ) as gql_session:
    
            # Execute
            query = gql(
                """
                subscription pipelineLogs($pipeline: String!) {
                  pipelineLogs(id: $pipeline) {
                    id
                    message
                    messageId
                    taskId
                    time
                  }
                }
            """
            )
            async for result in gql_session.subscribe(query, variable_values={"pipeline":pipeline}):
                result = {to_snake_case(k):v for k,v in result["pipelineLogs"].items()}
                ## need to figure out which fields can be optional
                yield PipelineLogMessage(id = result["id"], 
                                         message = result.get("message", ""),
                                         message_id = result.get("message_id", ""),
                                         task_id = result.get("task_id", ""),
                                         time = result.get("time", ""))
