import param
import panel as pn
from kedro_graphql.ui.decorators import discover_plugins, UI_PLUGINS
from kedro_graphql.config import config


class PipelineCards(pn.viewable.Viewer):
    """
    A component that displays cards for each pipeline with registered @ui_form plugins.
    This component allows users to navigate to a form for running a pipeline or exploring it.

    Attributes:
        spec (dict): The specification for the UI, including configuration and pages.
        explore_page (str): The page to navigate to when a pipeline is explored.
        form_page (str): The page to navigate to when a form is selected.
    """
    spec = param.Dict(default={})
    explore_page = param.String(
        default="explore", doc="The page to navigate to when a pipeline is explored.")
    form_page = param.String(
        default="form", doc="The page to navigate to when a form is selected.")

    def __init__(self, **params):
        super().__init__(**params)

    def _get_gql_forms(self):
        """Return all the @ui_form plugins registered in the project.

        Returns:
            [@ui_form plugin (panel.viewable.Viewer)] 
        """
        discover_plugins(config)
        return UI_PLUGINS["FORMS"]

    def navigate(self, button_click, event=None, pipeline=None, form=None):
        """Navigate to the specified page with the given pipeline and form.

        Args:
            button_click (pn.widgets.Button): The button that was clicked.
            event (str): The event that triggered the navigation, either "run" or "explore".
            pipeline (str): The name of the pipeline to navigate to.
            form (panel.viewable.Viewer): The form to navigate to.
        """

        if event == "run":
            pn.state.location.search = "?page=" + self.form_page + \
                "&pipeline=" + pipeline + "&form=" + form.__name__
        elif event == "explore":
            pn.state.location.search = "?page=" + self.explore_page + \
                "&pipeline=" + pipeline

    @param.depends("explore_page", "form_page")
    async def build_component(self):
        """Builds the pipeline cards component, displaying all pipelines that have a @ui_form plugin registered.

        Yields:
            pn.FlexBox: A flexible box containing cards for each pipeline.
        """
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
