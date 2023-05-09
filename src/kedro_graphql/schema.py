from .config import PIPELINES
from .events import PipelineEventMonitor
import strawberry
from strawberry.types import Info
from typing import AsyncGenerator, List
from .celeryapp import app as APP_CELERY
from .tasks import run_pipeline
from .models import Parameter, ParameterInput, DataSet, DataSetInput, Pipeline, PipelineInput, PipelineEvent, PipelineTemplate

@strawberry.type
class Query:
    @strawberry.field
    def pipeline_templates(self) -> List[PipelineTemplate]:
        pipes = []
        for k,v in PIPELINES.items():
            pipes.append(PipelineTemplate(name = k))
        return pipes

    @strawberry.field
    def pipeline(self, id: str, info: Info) -> Pipeline:
        return info.context["request"].app.backend.load(id)


@strawberry.type
class Mutation:
    @strawberry.mutation
    def pipeline(self, pipeline: PipelineInput, info: Info) -> Pipeline:
        """
        - fill in missing values from default catalog?
        - is validation against template needed, e.g. check DataSet type?
        """
        p = Pipeline(
            name = pipeline.name,
            inputs = [DataSet(**vars(i)) for i in pipeline.inputs],
            outputs = [DataSet(**vars(o)) for o in pipeline.outputs],
            parameters = [Parameter(**vars(p)) for p in pipeline.parameters],
            task_name = str(run_pipeline),
        )

        serial = p.serialize()

        result = run_pipeline.delay(
            name = serial["name"], 
            inputs = serial["inputs"], 
            outputs = serial["outputs"], 
            parameters = serial["parameters"]
        )  

        p.task_id = result.id
        p.status = result.status
        p.task_kwargs = str(
                {"name": serial["name"], 
                "inputs": serial["inputs"], 
                "outputs": serial["outputs"], 
                "parameters": serial["parameters"]}
        )
        
        ## PLACE HOLDER for future reolver plugins
        ## testing plugin_resolvers, 
        ##info.context["request"].app.resolver_plugins["text_in"].__input__("called text_in resolver")

        print(f'Starting {p.name} pipeline with task_id: ' + str(p.task_id))
        p = info.context["request"].app.backend.create(p)
        print(p.id)

        return p


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def pipeline(self, id: str, info: Info) -> AsyncGenerator[PipelineEvent, None]:
        async for e in PipelineEventMonitor(app = APP_CELERY, task_id = info.context["request"].app.backend.load(id=id).task_id ).consume():
            e["id"] = id
            yield PipelineEvent(**e)

schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
