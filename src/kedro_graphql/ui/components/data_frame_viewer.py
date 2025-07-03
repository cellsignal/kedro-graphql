import panel as pn
import param
import pandas as pd
import requests
from io import StringIO, BytesIO

pn.extension("perspective")


class DataFrameViewer(pn.viewable.Viewer):
    """A Panel Viewer that loads a dataset from a presigned URL and displays it using Perspective."""

    url = param.String(doc="The presigned URL to load data from")
    file_type = param.String(default="csv", doc="The file format: 'csv' or 'parquet'")
    spec = param.Dict(default={})

    def __init__(self, **params):
        super().__init__(**params)

        self.perspective = pn.pane.Markdown("Loading...", height=400)

        self._load_data()

    def _load_data(self):
        """Loads data from the URL and updates the Perspective pane."""
        url = self.url or pn.state.location.query_params.get("url")

        if not url:
            self.perspective.object = "**Missing `url` query parameter.**"
            return

        try:
            response = requests.get(url)
            response.raise_for_status()

            if self.file_type == "csv":
                df = pd.read_csv(StringIO(response.text))
            elif self.file_type == "parquet":
                df = pd.read_parquet(BytesIO(response.content))
            else:
                self.perspective.object = f"Unsupported file type: {self.file_type}"
                return

            self.perspective = pn.pane.Perspective(df, width=1000, height=1000, sizing_mode="stretch_width", styles={
                "font-size": "20px",
            }, theme="pro-dark", editable=False)
        except requests.HTTPError as http_err:
            if response.status_code == 403:
                self.perspective.object = "**Access denied (403 Forbidden).**"
            else:
                self.perspective.object = f"HTTP error occurred: {http_err}"
        except Exception as e:
            self.perspective.object = f"Error loading data from URL: {str(e)}"

    def __panel__(self):
        return pn.Column(
            "# DataFrameViewer",
            self.perspective,
            sizing_mode="stretch_width",
        )
