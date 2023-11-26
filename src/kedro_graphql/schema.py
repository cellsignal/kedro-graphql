#from .config import PIPELINES, TYPE_PLUGINS
from .events import PipelineEventMonitor
import strawberry
from strawberry.tools import merge_types
from strawberry.types import Info
from typing import AsyncGenerator, Optional
from .tasks import run_pipeline
from .models import Pipeline, Pipelines, PipelineInput, PipelineEvent, PipelineLogMessage, PipelineTemplate, PipelineTemplates, PageMeta
from .logs.logger import logger, PipelineLogStream
from fastapi.encoders import jsonable_encoder
from base64 import b64encode, b64decode
from bson.objectid import ObjectId


def encode_cursor(id: int) -> str:
    """
    Encodes the given id into a cursor.

    :param id: The ID to encode.

    :return: The encoded cursor.
    """
    return b64encode(f"cursor:{id}".encode("ascii")).decode("ascii")


def decode_cursor(cursor: str) -> int:
    """
    Decodes the ID from the given cursor.

    :param cursor: The cursor to decode.

    :return: The decoded user ID.
    """
    cursor_data = b64decode(cursor.encode("ascii")).decode("ascii")
    return cursor_data.split(":")[1]


@strawberry.type
class Query:

    @strawberry.field(description="Get a pipeline template.")
    def pipeline_template(self, info: Info, id: str) -> PipelineTemplate:
        for p in info.context["request"].app.kedro_pipelines_index:
            print(p.id, type(p.id))
            if p.id == id:
                return p

    @strawberry.field(description="Get a list of pipeline templates.")
    def pipeline_templates(self, info: Info, limit: int, cursor: Optional[str] = None) -> PipelineTemplates:
        if cursor is not None:
            # decode the user ID from the given cursor.
            pipe_id = ObjectId(decode_cursor(cursor=cursor))
        else:
            pipe_id = ObjectId("100000000000000000000000") ## unix epoch Jan 1, 1970 as objectId

        # filter the pipeline template data, going through the next set of results.
        filtered_data = [pipe for pipe in info.context["request"].app.kedro_pipelines_index if pipe.id.generation_time >= pipe_id.generation_time]

        # slice the relevant pipeline template data (Here, we also slice an
        # additional pipe instance, to prepare the next cursor).
        sliced_pipes = filtered_data[: limit + 1]

        if len(sliced_pipes) > limit:
            # calculate the client's next cursor.
            last_pipe = sliced_pipes.pop(-1)
            next_cursor = encode_cursor(id=last_pipe.id)
        else:
            # We have reached the last page, and
            # don't have the next cursor.
            next_cursor = None

        return PipelineTemplates(
            pipeline_templates=sliced_pipes, page_meta=PageMeta(next_cursor=next_cursor)
        )

    @strawberry.field(description = "Get a pipeline instance.")
    def pipeline(self, id: str, info: Info) -> Pipeline:
        p = info.context["request"].app.backend.load(id)
        p.kedro_pipelines_index = info.context["request"].app.kedro_pipelines_index
        return p

    @strawberry.field(description = "Get a list of pipeline instances.")
    def pipelines(self, info: Info, limit: int, cursor: Optional[str] = None, filter: Optional[str] = "") -> Pipelines:
        if cursor is not None:
            # decode the user ID from the given cursor.
            pipe_id = decode_cursor(cursor=cursor)
        else:
            pipe_id = "000000000000000000000000" ## unix epoch Jan 1, 1970 as objectId

        results = info.context["request"].app.backend.list(cursor = pipe_id, limit = limit + 1, filter = filter)

        if len(results) > limit:
            # calculate the client's next cursor.
            last_pipe = results.pop(-1)
            next_cursor = encode_cursor(id=last_pipe.id)
        else:
            # We have reached the last page, and
            # don't have the next cursor.
            next_cursor = None

        return Pipelines(
            pipelines=results, page_meta=PageMeta(next_cursor=next_cursor)
        )

@strawberry.type
class Mutation:
    @strawberry.mutation(description = "Execute a pipeline.")
    def pipeline(self, pipeline: PipelineInput, info: Info) -> Pipeline:
        """
        - is validation against template needed, e.g. check DataSet type or at least check dataset names
        """
        d = jsonable_encoder(pipeline)
        p = Pipeline.from_dict(d)
        p.task_name = str(run_pipeline)

        serial = p.serialize()
        ## credentials not supported yet
        ## merge any credentials with inputs and outputs
        ## credentials are intentionally not persisted
        ## NOTE celery result may persist creds in task result?
        ##for k,v in serial["inputs"].items():
        ##    if v.get("credentials", None):
        ##        v["credentials"] = creds[v["credentials"]]

        ##for k,v in serial["outputs"].items():
        ##    if v.get("credentials", None):
        ##        v["credentials"] = creds[v["credentials"]]

        result = run_pipeline.delay(
            name = serial["name"], 
            inputs = serial["inputs"], 
            outputs = serial["outputs"], 
            data_catalog = serial["data_catalog"],
            parameters = serial["parameters"],
            runner = info.context["request"].app.config["KEDRO_GRAPHQL_RUNNER"]
        )  

        p.task_id = result.id
        p.status = result.status

        ## TO DO - remove credentials from inputs and outputs so they are not persisted to backend
        ## replace with original string
        p.task_kwargs = str(
                {"name": serial["name"], 
                "inputs": serial["inputs"], 
                "outputs": serial["outputs"], 
                "data_catalog": serial["data_catalog"],
                "parameters": serial["parameters"],
                "runner": info.context["request"].app.config["KEDRO_GRAPHQL_RUNNER"]}
        )
        
        ## PLACE HOLDER for future reolver plugins
        ## testing plugin_resolvers, 
        #RESOLVER_PLUGINS["text_in"].__input__("called text_in resolver")

        logger.info(f'Starting {p.name} pipeline with task_id: ' + str(p.task_id))

        p = info.context["request"].app.backend.create(p)
        ## add private fields to enable resovling of computed fields e.g. "describe" and "template"
        p.kedro_pipelines_index = info.context["request"].app.kedro_pipelines_index
        #p.kedro_pipelines = info.context["request"].app.kedro_pipelines
        #p.kedro_catalog = info.context["request"].app.kedro_catalog
        #p.kedro_parameters = info.context["request"].app.kedro_parameters
        return p


@strawberry.type
class Subscription:
    @strawberry.subscription(description = "Subscribe to pipeline events.")
    async def pipeline(self, id: str, info: Info, interval: float = 0.5) -> AsyncGenerator[PipelineEvent, None]:
        """Subscribe to pipeline events.
        """
        p  = info.context["request"].app.backend.load(id=id)
        if p:
            async for e in PipelineEventMonitor(app = info.context["request"].app.celery_app, task_id = p.task_id).start(interval=interval):
                e["id"] = id
                yield PipelineEvent(**e)

    @strawberry.subscription(description = "Subscribe to pipeline logs.")
    async def pipeline_logs(self, id: str, info: Info) -> AsyncGenerator[PipelineLogMessage, None]:
        p  = info.context["request"].app.backend.load(id=id)
        if p:
            stream = await PipelineLogStream().create(task_id = p.task_id, broker_url = info.context["request"].app.config["KEDRO_GRAPHQL_BROKER"] )
            async for e in stream.consume():
                e["id"] = id
                yield PipelineLogMessage(**e)

def build_schema(type_plugins):
    ComboQuery = merge_types("Query", tuple([Query] + type_plugins["query"]))
    ComboMutation = merge_types("Mutation", tuple([Mutation] + type_plugins["mutation"]))
    ComboSubscription = merge_types("Subscription", tuple([Subscription] + type_plugins["subscription"]))
    
    return strawberry.Schema(query=ComboQuery, mutation=ComboMutation, subscription=ComboSubscription)

