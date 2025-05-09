import panel as pn
import param
from kedro_graphql.ui.decorators import UI_PLUGINS
from kedro_graphql.client import KedroGraphqlClient


class PipelineFormFactory(pn.viewable.Viewer):

    form = param.String(default=None)
    pipeline = param.String(default=None)
    options = param.List(default=[])
    client = param.ClassSelector(class_=KedroGraphqlClient)

    def __init__(self, **params):
        super().__init__(**params)

        if not UI_PLUGINS["FORMS"].get(self.pipeline, None):
            self.options = []
        else:
            for f in UI_PLUGINS["FORMS"][self.pipeline]:
                self.options.append(f.__name__)

    @param.depends("form", "pipeline", "client")
    async def build_form(self):
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        form = None
        for f in UI_PLUGINS["FORMS"][self.pipeline]:
            if f.__name__ == self.form:
                form = f
        f = pn.bind(form, client=self.param.client)
        yield f

    def __panel__(self):
        pn.state.location.sync(self, {"pipeline": "pipeline", "form": "form"})
        select = pn.widgets.Select.from_param(self.param.form,
                                              name='Select a form', options=self.options, value=self.param.form)

        if len(self.options) > 1:
            return pn.Column(
                pn.Row(select),
                pn.Row(self.build_form)
            )
        else:
            return pn.Row(self.build_form)
