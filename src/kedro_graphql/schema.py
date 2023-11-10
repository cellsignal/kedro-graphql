#from .config import PIPELINES, TYPE_PLUGINS
from .events import PipelineEventMonitor
import strawberry
from strawberry.tools import merge_types
from strawberry.types import Info
from typing import AsyncGenerator, List
#from .celeryapp import app as APP_CELERY
from .tasks import run_pipeline
from .models import Parameter, DataSet, Pipeline, PipelineInput, PipelineEvent, PipelineLogMessage, PipelineTemplate, Tag
from .logs.logger import logger, PipelineLogStream
from .utils import merge_dicts
from fastapi.encoders import jsonable_encoder

@strawberry.type
class Query:
    @strawberry.field
    def pipeline_templates(self, info: Info) -> List[PipelineTemplate]:
        pipes = []
        for k,v in info.context["request"].app.kedro_pipelines.items():
            pipes.append(PipelineTemplate(name = k, 
                                          kedro_pipelines = info.context["request"].app.kedro_pipelines,
                                          kedro_catalog = info.context["request"].app.kedro_catalog,
                                          kedro_parameters = info.context["request"].app.kedro_parameters))
        return pipes

    @strawberry.field
    def pipeline(self, id: str, info: Info) -> Pipeline:
        p = info.context["request"].app.backend.load(id)
        p.kedro_pipelines = info.context["request"].app.kedro_pipelines
        p.kedro_catalog = info.context["request"].app.kedro_catalog
        p.kedro_parameters = info.context["request"].app.kedro_parameters
        return p


@strawberry.type
class Mutation:
    @strawberry.mutation
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
        p.kedro_pipelines = info.context["request"].app.kedro_pipelines
        p.kedro_catalog = info.context["request"].app.kedro_catalog
        p.kedro_parameters = info.context["request"].app.kedro_parameters
        return p


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def pipeline(self, id: str, info: Info, interval: float = 0.5) -> AsyncGenerator[PipelineEvent, None]:
        """Subscribe to pipeline events.
        """
        p  = info.context["request"].app.backend.load(id=id)
        if p:
            async for e in PipelineEventMonitor(app = info.context["request"].app.celery_app, task_id = p.task_id).start(interval=interval):
                e["id"] = id
                yield PipelineEvent(**e)

    @strawberry.subscription
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

