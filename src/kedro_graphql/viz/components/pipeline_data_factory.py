## some code commented out because it has not been implemented
import panel as pn
import param
from kedro_graphql.viz.decorators import VIZ_PLUGINS
from kedro_graphql.viz.components.pipeline_detail import PipelineDetail
from kedro_graphql.viz.client import KedroGraphqlClient

class PipelineDataFactory(pn.viewable.Viewer):
  
    id = param.String(default = "")
    pipeline = param.String(default = "")

    async def build_data(self):

        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)


        if not VIZ_PLUGINS["DATA"].get(self.pipeline, None):
            yield pn.pane.Alert('No data components found', alert_type = "warning")
        else:

            client = KedroGraphqlClient()
            p = await client.readPipeline(self.id)

            catalog = PipelineDetail(pipeline = p)
            tabs = pn.Tabs(dynamic=False)
            tabs.append(("Detail", catalog))
            for d in VIZ_PLUGINS["DATA"][self.pipeline]:
                d.pipeline = p
                tabs.append((d.title, d))
            yield tabs

    def __panel__(self):
        pn.state.location.sync(self, {"id": "id", "pipeline": "pipeline"})


        return self.build_data

 