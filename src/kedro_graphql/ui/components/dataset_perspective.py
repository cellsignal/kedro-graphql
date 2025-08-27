import asyncio
import panel as pn
import param
import requests
from kedro.io import AbstractDataset

pn.extension("perspective")

class DatasetPerspective(pn.viewable.Viewer):
    """
    A Panel component that loads a Kedro dataset from a presigned URL and displays it using pn.pane.Perspective.

    Attributes:
        spec (dict): Kedro GraphQL UI specification
        presigned_url (str): The presigned URL to load data from.
        ds_name (str): The name of the dataset.
        ds_type (str): The type of the dataset.
        file_size_limit_mb (int): Maximum file size limit in MB to prevent loading large datasets
    """

    spec = param.Dict(default={}, doc="Kedro GraphQL UI specification")
    presigned_url = param.String(doc="The presigned URL to load data from")
    ds_name = param.String(doc="The name of the Kedro dataset")
    ds_type = param.String(doc="The type of the Kedro dataset")
    file_size_limit_mb = param.Integer(doc="Maximum file size limit in MB")

    def __init__(self, **params):
        super().__init__(**params)

    async def build_component(self):
        yield pn.Column(
            pn.indicators.LoadingSpinner(value=True, width=25, height=25),
            pn.pane.Markdown("Fetching data... This may take some time if the dataset is large."),
            sizing_mode="stretch_width",
        )

        query = pn.state.location.query_params

        presigned_url = query.get("presigned_url")
        ds_name = query.get("ds_name")
        ds_type = query.get("ds_type")

        if not presigned_url:
            yield pn.Column(
                "# Dataset Perspective",
                pn.pane.Markdown("**Missing `presigned_url` query parameter.**"),
                sizing_mode="stretch_width",
            )

        if not ds_name:
            yield pn.Column(
                "# Dataset Perspective",
                pn.pane.Markdown("**Missing `ds_name` query parameter.**"),
                sizing_mode="stretch_width",
            )

        if not ds_type:
            yield pn.Column(
                "# Dataset Perspective",
                pn.pane.Markdown("**Missing `ds_name` or `ds_type` query parameter.**"),
                sizing_mode="stretch_width",
            )

        try:
            # Check file size before loading
            headers = {"Range": "bytes=0-0"}
            response = requests.get(presigned_url, headers=headers)
            if response.status_code in (200, 206):
                size_str = response.headers.get('Content-Range') or response.headers.get('Content-Length')
                if size_str:
                    if 'Content-Range' in response.headers:
                        # Format: bytes 0-0/123456
                        size_bytes = int(size_str.split('/')[-1])
                    else:
                        size_bytes = int(size_str)
                    max_size = self.file_size_limit_mb * 1024 * 1024  # 10 MB
                    if size_bytes > max_size:
                        yield pn.Column("# Dataset Perspective", pn.pane.Markdown(f"### File size {size_bytes/1024/1024:.2f} MB exceeds {self.file_size_limit_mb} MB limit."))
                        return

            dataset = AbstractDataset.from_config(
                name=self.ds_name,
                config={
                    "type": ds_type,
                    "filepath": presigned_url
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
