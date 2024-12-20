## some code commented out because it has not been implemented
import param
#from kedro_graphql.client import KedroGraphqlClient
import panel as pn
from kedro_graphql.viz.decorators import discover_plugins, VIZ_PLUGINS
from kedro_graphql.config import config

class PipelineCards(pn.viewable.Viewer):
#    client = param.ClassSelector(default=KedroGraphqlClient(), class_=KedroGraphqlClient)
    config = param.Dict()
    pathname_form = param.String(default = "/pipeline/form")

    def _get_gql_forms(self):
        """
        Return allthe @gql_form plugins registered in the project.
        
        Returns:
            [@gql_form plugin (panel.viewable.Viewer)] 
        """
        ## more logic need to handle cases such as:
        ## "If more than one @gql_form component matches to a pipeline name the component should render the components as seperate tabs or a selection menu"
        discover_plugins(config)
        return VIZ_PLUGINS["FORMS"]
    
    def navigate(self, event, pipeline = None, form = None):
            pn.state.location.pathname = self.pathname_form
            pn.state.location.search = "?pipeline=" + pipeline + "&form=" + form.__name__
            pn.state.location.reload = True


    def __panel__(self):

        plugins =  self._get_gql_forms()
        cards = []
        for pipeline, forms in plugins.items():
            for form in forms:
                run_button = pn.widgets.Button(name='Run', button_type='success')
                explore_button = pn.widgets.Button(name='Explore', button_type='primary')
                cards.append(pn.Card(form.__name__, pn.Row(
                          run_button, 
                          explore_button
                        ),
                        sizing_mode = "stretch_width",
                        title=pipeline))
                pn.bind(self.navigate, run_button, pipeline = pipeline, form = form, watch=True)

        return pn.FlexBox(*cards)
 