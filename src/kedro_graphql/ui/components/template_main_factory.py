import panel as pn
import param
from kedro_graphql.ui.components.pipeline_cards import PipelineCards
from kedro_graphql.ui.components.pipeline_search import PipelineSearch
from kedro_graphql.ui.components.pipeline_form_factory import PipelineFormFactory
from kedro_graphql.ui.components.pipeline_dashboard_factory import PipelineDashboardFactory
from kedro_graphql.ui.components.pipeline_viz import PipelineViz
from kedro_graphql.client import KedroGraphqlClient


class TemplateMainFactory(pn.viewable.Viewer):
    component = param.String(default="pipelines")
    id = param.String(default=None)
    pipeline = param.String(default=None)
    client = param.ClassSelector(class_=KedroGraphqlClient)
    viz_static = param.String(default="")

    async def build_component(self):

        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        if self.component == "pipelines":
            yield PipelineCards()
        elif self.component == "search":
            yield PipelineSearch(client=self.client)
        elif self.component == "form":
            yield PipelineFormFactory(client=self.client, pipeline=self.pipeline)
        elif self.component == "dashboard":
            yield PipelineDashboardFactory(client=self.client, pipeline=self.pipeline, viz_static=self.viz_static)
        elif self.component == "explore":
            yield PipelineViz(viz_static=self.viz_static)

    def __panel__(self):
        pn.state.location.sync(
            self, {"component": "component", "id": "id", "pipeline": "pipeline"})

        return self.build_component
