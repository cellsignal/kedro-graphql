## some code commented out because it has not been implemented
import panel as pn
import param
from kedro_graphql.viz.decorators import VIZ_PLUGINS
from kedro_graphql.config import config

class PipelineFormFactory(pn.viewable.Viewer):
  
    form = param.String(default = "")
    pipeline = param.String(default = "")

    async def build_form(self):

        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        if not VIZ_PLUGINS["FORMS"].get(self.pipeline, None):
            yield pn.pane.Alert('No forms found', alert_type = "warning")
        else:
            for f in VIZ_PLUGINS["FORMS"][self.pipeline]:
                if f.__name__ == self.form:
                    f.pathname_monitor = config["KEDRO_GRAPHQL_VIZ_BASEPATH"] + "/monitor"
                    yield f

    def __panel__(self):
        pn.state.location.sync(self, {"pipeline": "pipeline", "form": "form"})
        return self.build_form

 