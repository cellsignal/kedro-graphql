import panel as pn
import param
import asyncio
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

    @param.depends("presigned_url", "spec", "ds_name", "ds_type")
    async def build_component(self):
        yield pn.Column(
            pn.indicators.LoadingSpinner(value=True, width=25, height=25),
            pn.pane.Markdown("Fetching data... This may take some time if the dataset is large."),
            sizing_mode="stretch_width",
        )

        self.presigned_url = pn.state.location.query_params.get("presigned_url")
        self.ds_name = pn.state.location.query_params.get("ds_name")
        self.ds_type = pn.state.location.query_params.get("ds_type")

        if not self.presigned_url:
            yield pn.Column(
                "# Dataset Perspective",
                pn.pane.Markdown("**Missing `presigned_url` query parameter.**"),
                sizing_mode="stretch_width",
            )

        if not self.ds_name:
            yield pn.Column(
                "# Dataset Perspective",
                pn.pane.Markdown("**Missing `ds_name` query parameter.**"),
                sizing_mode="stretch_width",
            )

        if not self.ds_type:
            yield pn.Column(
                "# Dataset Perspective",
                pn.pane.Markdown("**Missing `ds_name` or `ds_type` query parameter.**"),
                sizing_mode="stretch_width",
            )

        try:
            dataset = AbstractDataset.from_config(
                name=self.ds_name,
                config={
                    "type": self.ds_type,
                    "filepath": self.presigned_url
                }
            )
            df = await asyncio.to_thread(dataset.load)

            yield pn.Column(
                "# Dataset Perspective",
                pn.pane.Perspective(
                    df, height=1000, sizing_mode="stretch_width", theme="pro-dark",
                    editable=False, settings=False),
                sizing_mode="stretch_width",
            )

        except Exception as e:
            yield pn.Column(
                "# Dataset Perspective",
                pn.pane.Markdown(f"**Error loading data from URL:** {str(e)}"),
                sizing_mode="stretch_width",
            )

    def __panel__(self):
        return self.build_component
