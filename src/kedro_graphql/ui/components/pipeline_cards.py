import param
import panel as pn
from kedro_graphql.ui.decorators import discover_plugins, UI_PLUGINS
from kedro_graphql.config import config


class PipelineCards(pn.viewable.Viewer):
    config = param.Dict()
    form = param.String(default="form")
    explore = param.String(default="explore")

    def __init__(self, **params):
        super().__init__(**params)

    def _get_gql_forms(self):
        """
        Return allthe @gql_form plugins registered in the project.

        Returns:
            [@gql_form plugin (panel.viewable.Viewer)] 
        """
        discover_plugins(config)
        return UI_PLUGINS["FORMS"]

    def navigate(self, button_click, event=None, pipeline=None, form=None):

        if event == "run":
            pn.state.location.search = "?component="+self.form + \
                "&pipeline=" + pipeline + "&form=" + form.__name__
        elif event == "explore":
            pn.state.location.search = "?component="+self.explore + \
                "&pipeline=" + pipeline

    async def build_component(self):
        plugins = self._get_gql_forms()
        p_cards = []
        for pipeline, forms in plugins.items():
            p_card = pn.Card(title=pipeline, sizing_mode='stretch_width')
            run_button = pn.widgets.Button(name='Run', button_type='success')
            explore_button = pn.widgets.Button(name='Explore', button_type='default')
            p_card = pn.Card(pipeline, pn.Row(
                run_button,
                explore_button
            ),
                title=pipeline)
            p_cards.append(p_card)
            pn.bind(self.navigate, run_button, event="run",
                    pipeline=pipeline, form=forms[0], watch=True)
            pn.bind(self.navigate, explore_button, event="explore",
                    pipeline=pipeline, form=forms[0], watch=True)

        yield pn.FlexBox(*p_cards)

    def __panel__(self):
        return self.build_component
