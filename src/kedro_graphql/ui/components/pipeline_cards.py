import param
import panel as pn
from kedro_graphql.ui.decorators import UI_PLUGINS


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

    def navigate(self, button_click, event=None, pipeline=None, form=None):
        """Navigate to the specified page with the given pipeline and form.

        Args:
            button_click (pn.widgets.Button): The button that was clicked.
            event (str): The event that triggered the navigation, either "run" or "explore".
            pipeline (str): The name of the pipeline to navigate to.
            form (panel.viewable.Viewer): The form to navigate to.
        """

        if event == "run":
            pn.state.location.pathname = self.spec["panel_get_server_kwargs"]["prefix"] + self.form_page
            pn.state.location.search = "?pipeline=" + pipeline + "&form=" + form.__name__
            pn.state.location.reload = True
        elif event == "explore":
            pn.state.location.pathname = self.spec["panel_get_server_kwargs"]["prefix"] + self.explore_page
            pn.state.location.search = "?pipeline=" + pipeline
            pn.state.location.reload = True

    @param.depends("explore_page", "form_page")
    async def build_component(self):
        """Builds the pipeline cards component, displaying all pipelines that have a @ui_form plugin registered.

        Yields:
            pn.FlexBox: A flexible box containing cards for each pipeline.
        """
        p_cards = []
        for pipeline, forms in UI_PLUGINS["FORMS"].items():
            p_card = pn.Card(title=pipeline, sizing_mode='stretch_width')
            run_button = pn.widgets.Button(name='Run', button_type='success')
            explore_button = pn.widgets.Button(name='Explore', button_type='default')
            p_card = pn.Card(
                pipeline,
                pn.Row(run_button, explore_button),
                title=pipeline
            )
            p_cards.append(p_card)
            pn.bind(
                self.navigate,
                run_button,
                event="run",
                pipeline=pipeline,
                form=forms[0],
                watch=True
            )
            pn.bind(
                self.navigate,
                explore_button,
                event="explore",
                pipeline=pipeline,
                form=forms[0],
                watch=True
            )

        yield pn.FlexBox(*p_cards)

    def __panel__(self):
        return self.build_component
