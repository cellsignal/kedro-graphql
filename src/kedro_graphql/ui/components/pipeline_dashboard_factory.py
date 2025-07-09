import panel as pn
import param
from kedro_graphql.ui.decorators import UI_PLUGINS
from kedro_graphql.ui.components.pipeline_detail import PipelineDetail
from kedro_graphql.ui.components.pipeline_monitor import PipelineMonitor
from kedro_graphql.ui.components.pipeline_viz import PipelineViz
from kedro_graphql.ui.components.pipeline_retry import PipelineRetry
from kedro_graphql.ui.components.pipeline_cloning import PipelineCloning
from kedro_graphql.ui.components.data_catalog_explorer import DataCatalogExplorer


class PipelineDashboardFactory(pn.viewable.Viewer):
    """A factory for building dashboards for Kedro pipelines using registered @ui_dashboard plugins.
    This component allows users to select a dashboard for a specific pipeline and build the dashboard dynamically.

    Attributes:
        id (str): The ID of the pipeline to build the dashboard for.
        pipeline (str): The name of the pipeline for which the dashboard is built.
        options (list): A list of available dashboards for the selected pipeline.
        spec (dict): The specification for the UI, including configuration and pages.
        dashboard_name (str): The name of the selected dashboard.
    """
    id = param.String(default="")
    pipeline = param.String(default="")
    options = param.List(default=[])
    spec = param.Dict(default={})
    dashboard_name = param.String(default=None)
    dataset_map = param.Dict(default={})

    def __init__(self, **params):
        super().__init__(**params)

    def build_default_dashboard(self, p):
        """Builds the default dashboard for a Kedro pipeline, including monitoring, detail, and visualization components
        registered to the pipeline using the @ui_data plugin.

        Args:
            p (Pipeline): The Kedro pipeline for which the dashboard is built.
        Returns:
            pn.Tabs: A panel containing tabs for monitoring, detail, and visualization of the pipeline.
        """
        monitor = PipelineMonitor(client=self.spec["config"]["client"], pipeline=p)
        detail = PipelineDetail(pipeline=p)
        viz = PipelineViz(pipeline=p.name, spec=self.spec)
        retry = PipelineRetry(client=self.spec["config"]["client"], pipeline=p)
        cloning = PipelineCloning(client=self.spec["config"]["client"], pipeline=p)
        explorer = DataCatalogExplorer(spec=self.spec, pipeline=p, dataset_map=self.dataset_map)
        tabs = pn.Tabs(dynamic=False)
        tabs.append(("Explorer", explorer))
        tabs.append(("Monitor", monitor))
        tabs.append(("Detail", detail))
        tabs.append(("Viz", viz))
        tabs.append(("Retry", retry))
        tabs.append(("Cloning", cloning))
        if UI_PLUGINS["DATA"].get(self.pipeline, None):
            for d in UI_PLUGINS["DATA"][self.pipeline]:
                data = d(id=self.id, spec=self.spec,
                         pipeline=p)
                tabs.append((data.title, data))
        return tabs

    def build_custom_dashboard(self, p):
        """Builds a custom dashboard for a Kedro pipeline using a registered @ui_dashboard plugin.
        Args:
            p (Pipeline): The Kedro pipeline for which the dashboard is built.
        Returns:
            panel.viewable.Viewer: An instance of the custom dashboard class.
        """
        dash = None
        for d in UI_PLUGINS["DASHBOARD"][self.pipeline]:
            if d.__name__ == self.dashboard_name:
                dash = d
        dash = dash(id=self.id, pipeline=p, spec=self.spec)
        return dash

    @param.depends("spec", "dashboard_name", "id", "pipeline")
    async def build_dashboard(self):
        """Builds the dashboard for the selected pipeline and dashboard name.
        This method checks if a custom dashboard is registered for the pipeline and builds it accordingly.
        If no custom dashboard is registered, it builds the default dashboard with monitoring, detail, and visualization components.

        Yields:
            pn.Tabs or panel.viewable.Viewer: The built dashboard, either custom or default.
        """
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        p = await self.spec["config"]["client"].read_pipeline(id=self.id)

        if UI_PLUGINS["DASHBOARD"].get(self.pipeline, None):
            yield self.build_custom_dashboard(p)
        else:
            yield self.build_default_dashboard(p)

    def __panel__(self):
        pn.state.location.sync(
            self, {"id": "id", "pipeline": "pipeline", "dashboard_name": "dashboard_name"})
        if not UI_PLUGINS["DASHBOARD"].get(self.pipeline, None):
            self.options = []
        else:
            for f in UI_PLUGINS["DASHBOARD"][self.pipeline]:
                self.options.append(f.__name__)
            self.dashboard_name = self.options[0]

        select = pn.widgets.Select.from_param(self.param.dashboard_name,
                                              name='Select a dashboard', options=self.options, value=self.param.dashboard_name)

        if len(self.options) > 1:
            return pn.Column(
                pn.Row(select),
                pn.Row(self.build_dashboard)
            )
        else:
            return pn.Row(self.build_dashboard)
