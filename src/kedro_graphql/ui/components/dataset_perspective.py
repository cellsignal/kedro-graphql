import panel as pn
import param
from kedro.io import AbstractDataset

pn.extension("perspective")


class DatasetPerspective(pn.viewable.Viewer):
    """A Kedro Dataframe viewer that loads a dataset from a presigned URL and displays it using panel Perspective."""

    presigned_url = param.String(doc="The presigned URL to load data from")
    spec = param.Dict(default={})
    ds_name = param.String(doc="The name of the dataset")
    ds_type = param.String(doc="The type of the dataset")

    def __init__(self, **params):
        super().__init__(**params)

        self.perspective = pn.pane.Markdown("Loading...", height=400)

        self._load_data()

    def _load_data(self):
        """Loads data from the URL and updates the Perspective pane."""
        presigned_url = self.presigned_url or pn.state.location.query_params.get("presigned_url")
        self.ds_name = self.ds_name or pn.state.location.query_params.get("ds_name")
        self.ds_type = self.ds_type or pn.state.location.query_params.get("ds_type")

        if not presigned_url:
            self.perspective.object = "**Missing `presigned_url` query parameter.**"
            return

        if not self.ds_name:
            self.perspective.object = "**Missing `ds_name` query parameter.**"
            return

        if not self.ds_type:
            self.perspective.object = "**Missing `ds_name` or `ds_type` query parameter.**"
            return

        try:
            df = AbstractDataset.from_config(name=self.ds_name, config={
                                             "type": self.ds_type, "filepath": presigned_url}).load()

            self.perspective = pn.pane.Perspective(df, width=1000, height=1000, sizing_mode="stretch_width", styles={
                "font-size": "20px",
            }, theme="pro-dark", editable=False)
        except Exception as e:
            self.perspective.object = f"Error loading data from URL: {str(e)}"

    def __panel__(self):
        return pn.Column(
            "# Dataset Perspective",
            self.perspective,
            sizing_mode="stretch_width",
        )
