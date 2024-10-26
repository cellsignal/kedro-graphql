"""A python panel app for visualizing Kedro pipelines."""
import panel as pn
import param



class KedroGraphqlMaterialTemplate(pn.viewable.Viewer):
    config = param.Dict()
    form_pathname = param.String(default = "/pipelines/forms")
    pipelines_pathname = param.String(default = "/pipelines/cards")
    search_pathname = param.String(default = "/pipelines/search")
    monitor_pathname = param.String(default = "/pipelines/monitor")


    def navigate(self, event, name = None):
        if name == "pipelines":
            pn.state.location.pathname = self.pipelines_pathname
            pn.state.location.reload = True
        if name == "search":
            pn.state.location.pathname = self.search_pathname
            pn.state.location.reload = True
        if name == "forms":
            pn.state.location.pathname = self.form_pathname
            self.pipeline_name = name
            self.gql_form = ""
            pn.state.location.reload = True
        if name == "monitor":
            pn.state.location.pathname = self.monitor_pathname
            pn.state.location.reload = True







    def __panel__(self):

        pipelines_button = pn.widgets.Button(name='Pipelines', button_type='primary', sizing_mode="stretch_width")
        search_button = pn.widgets.Button(name='Search', button_type='primary', sizing_mode="stretch_width")
        monitor_button = pn.widgets.Button(name='Monitor', button_type='primary', sizing_mode="stretch_width")
        pn.bind(self.navigate, pipelines_button, name = "pipelines", watch=True),
        pn.bind(self.navigate, search_button, name = "search", watch=True),
        pn.bind(self.navigate, monitor_button, name = "monitor", watch=True),
        sidebar = [
          pipelines_button,
          search_button,
          monitor_button
        ]
        
        template = pn.template.MaterialTemplate(
            title='kedro-graphql',
            sidebar=sidebar
        )
        return template