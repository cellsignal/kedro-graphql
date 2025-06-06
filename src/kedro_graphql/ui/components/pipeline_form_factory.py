import panel as pn
import param
from kedro_graphql.ui.decorators import UI_PLUGINS


class PipelineFormFactory(pn.viewable.Viewer):
    """A factory for building forms for Kedro pipelines using registered @ui_form plugins.
    This component allows users to select a form for a specific pipeline and build the form dynamically.

    Attributes:
        form (str): The name of the form to build.
        pipeline (str): The name of the pipeline for which the form is built.
        options (list): A list of available forms for the selected pipeline.
        spec (dict): The specification for the UI, including configuration and pages."""

    form = param.String(default=None)
    pipeline = param.String(default=None)
    options = param.List(default=[])
    spec = param.Dict(default={})

    def __init__(self, **params):
        super().__init__(**params)

    @param.depends("pipeline")
    async def build_options(self):
        """Builds the options for the form selection based on the registered @ui_form plugins for the selected pipeline."""

        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        self.options = []
        if UI_PLUGINS["FORMS"].get(self.pipeline, None):
            for f in UI_PLUGINS["FORMS"][self.pipeline]:
                self.options = [f.__name__ for f in UI_PLUGINS["FORMS"][self.pipeline]]

        if not self.form or self.form not in self.options:
            self.form = self.options[0] if self.options else None

        yield pn.widgets.Select.from_param(self.param.form,
                                           name='Select a form', options=self.options, value=self.param.form)

    @param.depends("form", "pipeline", "spec")
    async def build_form(self):
        """Builds the form based on the selected form and pipeline, using the registered @ui_form plugins."""

        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        form = None
        for f in UI_PLUGINS["FORMS"][self.pipeline]:
            if f.__name__ == self.form:
                form = f
        f = pn.bind(form, spec=self.param.spec)
        yield f

    def __panel__(self):
        pn.state.location.sync(
            self, {"pipeline": "pipeline", "form": "form"})

        return pn.Column(
            pn.Row(self.build_options),
            pn.Row(self.build_form)
        )
