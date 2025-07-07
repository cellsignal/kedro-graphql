import panel as pn
import param
import pandas as pd
import json

from kedro_graphql.models import Pipeline


class DataCatalogExplorer(pn.viewable.Viewer):
    """Main class for the Data Catalog Explorer UI"""

    pipeline = param.ClassSelector(class_=Pipeline)
    spec = param.Dict(default={})

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):

        ds_df = pd.DataFrame({
            'name': [i.name for i in self.pipeline.data_catalog],
            'type': [json.loads(i.config)["type"] for i in self.pipeline.data_catalog],
            'filepath': [json.loads(i.config).get("filepath", "") for i in self.pipeline.data_catalog],
            'tags': [", ".join([f"{tag.key}={tag.value}" for tag in i.tags]) if i.tags else "" for i in self.pipeline.data_catalog],
        }, index=[i for i in range(len(self.pipeline.data_catalog))])

        # JS pane (invisible) used to inject JS dynamically
        js_download = pn.pane.HTML("", width=0, height=0)

        def trigger_download(url):
            js_code = f"""
            <script>
            (function() {{
                const a = document.createElement('a');
                a.href = "{url}";
                a.target = "_blank";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }})();
            </script>
            """

            js_download.object = js_code

        def open_data_frame_viewer(page, presigned_url, ds_name, ds_type):
            js_code = f"""
            <script>
            (function() {{
                const presigned_url = "{presigned_url}";
                const page = "{page}";
                const ds_name = "{ds_name}";
                const ds_type = "{ds_type}";
                const viewerUrl = `${{window.location.origin}}/?page=${{page}}&presigned_url=${{encodeURIComponent(presigned_url)}}&ds_name=${{encodeURIComponent(ds_name)}}&ds_type=${{encodeURIComponent(ds_type)}}`;
                window.open(viewerUrl, '_blank');
            }})();
            </script>
            """
            js_download.object = js_code

        def download_action(event):
            if event.column != 'Download':
                return

            row = event.row

            dataset_name = ds_df.iloc[row]['name']
            for ds in self.pipeline.data_catalog:
                if ds.name == dataset_name:
                    presigned_url = ds.pre_signed_url_read(expires_in_sec=100)
                    for dataset_type, panel_page in self.spec["dataset_viewer"].items():
                        if json.loads(ds.config)["type"] == dataset_type:
                            open_data_frame_viewer(panel_page, presigned_url, ds.name, json.loads(ds.config)["type"])
                            return
                    if presigned_url:
                        trigger_download(presigned_url)
                    else:
                        print(f"No presigned URL available for {dataset_name}")

        ds_widget = pn.widgets.Tabulator(
            ds_df,
            disabled=True,
            buttons={
                'Download': "<i class='fa fa-download'></i>"
            },
            theme='materialize',
            selectable=False,
            show_index=False,
        )
        ds_widget.on_click(download_action)

        return pn.Column(
            pn.Row(
                pn.pane.Markdown(
                    """Search for datasets with the following syntax:
- Search by name: `name=example`
- Search by tags: `tag:key=value`
                                 """)),
            pn.Card(ds_widget, title="Data Catalog", sizing_mode="stretch_width"),
            js_download,
            pn.pane.Markdown("# Download datasets using AbstractDataset.from_config().load()"),
            # pn.widgets.FileDownload(
            #     callback=lambda: io.BytesIO(AbstractDataset.from_config(
            #         self.pipeline.data_catalog[3].name, json.loads(self.pipeline.data_catalog[3].config)).load()),
            #     filename=self.pipeline.data_catalog[3].name),
            # pn.widgets.FileDownload(
            #     callback=lambda: io.StringIO(AbstractDataset.from_config(
            #         self.pipeline.data_catalog[4].name, json.loads(self.pipeline.data_catalog[4].config)).load()),
            #     filename=self.pipeline.data_catalog[4].name),
            # pn.widgets.FileDownload(
            #     callback=lambda: io.StringIO(AbstractDataset.from_config(
            #         self.pipeline.data_catalog[5].name, json.loads(self.pipeline.data_catalog[5].config)).load()),
            #     filename=self.pipeline.data_catalog[5].name),
            sizing_mode="stretch_width",)
