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
    options = param.List(default=[])
    client = param.ClassSelector(class_=KedroGraphqlClient)
    dashboard_name = param.String(default=None)

    def __init__(self, **params):
        super().__init__(**params)

        if not UI_PLUGINS["DASHBOARD"].get(self.pipeline, None):
            self.options = []
        else:
            for f in UI_PLUGINS["DASHBOARD"][self.pipeline]:
                self.options.append(f.__name__)
            self.dashboard_name = self.options[0]

    def build_default_dashboard(self, p):
        monitor = PipelineMonitor(client=self.client, pipeline=p)
        detail = PipelineDetail(pipeline=p)
        viz = PipelineViz(pipeline=p.name, viz_static=self.viz_static)
        tabs = pn.Tabs(dynamic=False)
        tabs.append(("Monitor", monitor))
        tabs.append(("Detail", detail))
        tabs.append(("Viz", viz))
        if UI_PLUGINS["DATA"].get(self.pipeline, None):
            for d in UI_PLUGINS["DATA"][self.pipeline]:
                data = d(id=self.id, client=self.client,
                         pipeline=p, viz_static=self.viz_static)
                tabs.append((data.title, data))
        return tabs

    def build_custom_dashboard(self, p):
        dash = None
        for d in UI_PLUGINS["DASHBOARD"][self.pipeline]:
            if d.__name__ == self.dashboard_name:
                dash = d
        dash = dash(id=self.id, pipeline=p, client=self.client,
                    viz_static=self.viz_static)
        print("DASHBOARD", dash.__dict__)
        return dash

    @param.depends("client", "dashboard_name", "id", "pipeline", "viz_static")
    async def build_dashboard(self):
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        p = await self.client.read_pipeline(id=self.id)

        if UI_PLUGINS["DASHBOARD"].get(self.pipeline, None):
            yield self.build_custom_dashboard(p)
        else:
            yield self.build_default_dashboard(p)

    # yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

    # p = await self.client.read_pipeline(id=self.id)

    # if UI_PLUGINS["DASHBOARD"].get(self.pipeline, None):
    # dash = None
    # for d in UI_PLUGINS["DASHBOARD"][self.pipeline]:
    # if d.__name__ == self.dashboard_name:
    # dash = d
    # dash.pipeline = p
    # dash.client = self.param.client
    # dash.viz_static = self.param.viz_static
    # dash.id = self.id
    # print("DASHBOARD", dash.client)
    # yield dash

    # else:
    # yield self.build_default_dashboard(p)

    def __panel__(self):
        pn.state.location.sync(
            self, {"id": "id", "pipeline": "pipeline", "dashboard_name": "dashboard_name"})
        select = pn.widgets.Select.from_param(self.param.dashboard_name,
                                              name='Select a dashboard', options=self.options, value=self.param.dashboard_name)

        if len(self.options) > 1:
            return pn.Column(
                pn.Row(select),
                pn.Row(self.build_dashboard)
            )
        else:
            return pn.Row(self.build_dashboard)
