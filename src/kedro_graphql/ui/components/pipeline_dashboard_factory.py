import panel as pn
import param
from kedro_graphql.ui.decorators import UI_PLUGINS
from kedro_graphql.ui.components.pipeline_detail import PipelineDetail
from kedro_graphql.ui.components.pipeline_monitor import PipelineMonitor
from kedro_graphql.ui.components.pipeline_viz import PipelineViz
from kedro_graphql.client import KedroGraphqlClient


class PipelineDashboardFactory(pn.viewable.Viewer):
    viz_static = param.String(default="")
    id = param.String(default="")
    pipeline = param.String(default="")
    client = param.ClassSelector(class_=KedroGraphqlClient)

    @param.depends("pipeline", "client")
    async def build_data(self):

        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        p = await self.client.read_pipeline(id=self.id)

        monitor = PipelineMonitor(client=self.client, pipeline=p)
        detail = PipelineDetail(pipeline=p)
        viz = PipelineViz(pipeline=p.name, viz_static=self.viz_static)
        tabs = pn.Tabs(dynamic=False)
        tabs.append(("Monitor", monitor))
        tabs.append(("Detail", detail))
        tabs.append(("Viz", viz))
        if UI_PLUGINS["DATA"].get(self.pipeline, None):
            for d in UI_PLUGINS["DATA"][self.pipeline]:
                d.pipeline = p
                d.client = self.param.client
                tabs.append((d.title, d))
        yield tabs

    def __panel__(self):
        pn.state.location.sync(self, {"id": "id", "pipeline": "pipeline"})

        return self.build_data
