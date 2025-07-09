import panel as pn
import param
import pandas as pd
import json

from kedro_graphql.models import Pipeline

pn.extension(notifications=True)


class DataCatalogExplorer(pn.viewable.Viewer):
    """A component that displays the data catalog of a Kedro pipeline, allowing users to filter, view,
    and download datasets using their pre-signed URL implementation of choice."""

    pipeline = param.ClassSelector(class_=Pipeline)
    spec = param.Dict(default={})
    dataset_map = param.Dict(default={})

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):

        base_df = pd.DataFrame({
            'Name': [ds.name for ds in self.pipeline.data_catalog],
            'Type': [json.loads(ds.config)["type"] for ds in self.pipeline.data_catalog],
            'Filepath': [json.loads(ds.config).get("filepath", "") for ds in self.pipeline.data_catalog],
        }, index=[i for i in range(len(self.pipeline.data_catalog))])

        # Create column for each tag
        tags_list = []
        for idx, ds in enumerate(self.pipeline.data_catalog):
            tag_data = {}
            if ds.tags:
                for tag in ds.tags:
                    tag_data[f"Tag:{tag.key}"] = tag.value
            tags_list.append(pd.Series(tag_data, name=idx))

        tags_df = pd.DataFrame(tags_list).fillna("")
        ds_df = pd.concat([base_df, tags_df], axis=1)

        js_download = pn.pane.HTML("", width=0, height=0)  # this is used to inject JS dynamically

        def trigger_popout(url):
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
            js_download.object = None

        def trigger_download(url, filepath):
            js_code = f"""
            <script>
            (async function() {{
                const response = await fetch("{url}");
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', "{filepath.split("/")[-1]}");
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
            }})();
            </script>
            """

            js_download.object = js_code
            js_download.object = None

        def open_dataset_viewer(page, presigned_url, ds_name, ds_type):
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

        def on_row_click(event):
            row = event.row
            dataset_name = ds_df.iloc[row]['Name']
            dataset_filepath = ds_df.iloc[row]['Filepath']
            dataset_type = ds_df.iloc[row]['Type']
            if event.column == 'Download':
                for ds in self.pipeline.data_catalog:
                    if ds.name == dataset_name:
                        presigned_url = ds.pre_signed_url_read(expires_in_sec=3600)
                        if presigned_url:
                            trigger_download(presigned_url, dataset_filepath)
                        else:
                            pn.state.notifications.warning(f"No presigned URL available for {dataset_name}", duration=10000)
                            return
            if event.column == 'Popout':
                for ds in self.pipeline.data_catalog:
                    if ds.name == dataset_name:
                        presigned_url = ds.pre_signed_url_read(expires_in_sec=3600)
                        for dataset_type, panel_page in self.dataset_map.items():
                            if json.loads(ds.config)["type"] == dataset_type:
                                open_dataset_viewer(panel_page, presigned_url, dataset_name, dataset_type)
                                return
                        if presigned_url:
                            trigger_popout(presigned_url)
                        else:
                            pn.state.notifications.warning(f"No presigned URL available for {dataset_name}", duration=10000)
                            return

        filters = {
            "Name": {"type": "input", "placeholder": "Filter by name", "func": "like"},
            "Type":
            {"type": "list", "placeholder": "Select dataset type(s)", "func": "in", "valuesLookup": True, "multiselect": True},
            "Filepath": {"type": "input", "placeholder": "Filter by filepath", "func": "like"}}

        for tag in tags_df.columns.tolist():
            filters[tag] = {"type": "list", "placeholder": "Select tag(s)",
                            "func": "in", "valuesLookup": True, "multiselect": True}

        ds_widget = pn.widgets.Tabulator(
            ds_df,
            disabled=True,
            buttons={
                'Download': "<i class='fa fa-download'></i>",
                "Popout": "<i class='fa fa-external-link'></i>"
            },
            theme='materialize',
            selectable=False,
            show_index=False,
            header_filters=filters,
        )
        ds_widget.on_click(on_row_click)

        return pn.Column(
            pn.Card(ds_widget, title="Data Catalog Explorer", sizing_mode="stretch_width"),
            js_download,
            sizing_mode="stretch_width",)
