# some code commented out because it has not been implemented
import panel as pn
import param
import json


class PipelineViz(pn.viewable.Viewer):
    viz_static = param.String(default="")
    pipeline = param.String(default="")
    sid = param.String(default=None)
    height = param.Integer(default=800)

    def __init__(self, **params):
        super().__init__(**params)
        self.viz_json = self.load_viz_json()

    def load_viz_json(self):
        with open(self.viz_static + "api/main") as f:
            data = json.load(f)
        return data

    async def build_viz(self):
        iframe = """
        <iframe frameBorder="0"  style="height:100%; width:100%" src="http://localhost:5006/pipeline/viz-build/index.html?pid={pipeline}"></iframe>
        """.format(pipeline=self.pipeline)
        if self.sid:
            iframe = """
            <iframe frameBorder="0" style="height:100%; width:100%" src="http://localhost:5006/pipeline/viz-build/index.html?pid={pipeline}&sid={sid}"></iframe>
            """.format(pipeline=self.pipeline, sid=self.sid)

        return pn.pane.HTML(iframe, height=self.height, sizing_mode="stretch_width")

    def __panel__(self):
        pn.state.location.sync(self, {"pipeline": "pipeline", "sid": "sid"})
        return pn.Card(
            self.build_viz,
            title="Pipeline Visualization",
            sizing_mode="stretch_width",
        )
