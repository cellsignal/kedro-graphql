# some code commented out because it has not been implemented
import panel as pn
import param
import json


class PipelineViz(pn.viewable.Viewer):
    spec = param.Dict(default={})
    pipeline = param.String(default="")
    sid = param.String(default=None)
    height = param.Integer(default=800)

    def __init__(self, **params):
        super().__init__(**params)
        # self.viz_json = self.load_viz_json()

    def load_viz_json(self):
        """Not currently used, but can be used to load a static viz JSON file.
        This will be useful to programmtically hightlight nodes in the visualization,
        however, the kedro-graphql api does not currently support emitting events that 
        indicate which nodes are currently being processed.

        Returns:
            dict: The JSON data for the visualization.
        """
        with open(self.spec["config"]["viz_static"] + "api/main") as f:
            data = json.load(f)
        return data

    @param.depends("pipeline")
    async def build_viz(self):
        """Builds the visualization iframe for the specified pipeline.

        Returns:
            pn.pane.HTML: The HTML pane containing the iframe for the pipeline visualization.
        """
        iframe = """
        <iframe frameBorder="0" style="height:100%; width:100%" src="{prefix}pipeline/viz-build/index.html?pid={pipeline}"></iframe>
        """.format(pipeline=self.pipeline, prefix=self.spec["panel_get_server_kwargs"]["prefix"])
        if self.sid:
            iframe = """
            <iframe frameBorder="0" style="height:100%; width:100%" src="{prefix}pipeline/viz-build/index.html?pid={pipeline}&sid={sid}"></iframe>
            """.format(
                pipeline=self.pipeline,
                sid=self.sid,
                prefix=self.spec["panel_get_server_kwargs"]["prefix"]
            )

        yield pn.pane.HTML(iframe, height=self.height, sizing_mode="stretch_width")

    def __panel__(self):
        pn.state.location.sync(self, {"pipeline": "pipeline", "sid": "sid"})
        return pn.Card(
            self.build_viz,
            title="Pipeline Visualization",
            sizing_mode="stretch_width",
        )
