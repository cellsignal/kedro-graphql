import asyncio
import json
import param
import panel as pn
import pandas as pd
from kedro_graphql.models import Pipeline, DataSetInput, SignedUrl, SignedUrls

pn.extension(notifications=True)


class DataCatalogExplorer(pn.viewable.Viewer):
    """
    A Panel component that displays the data catalog of a Kedro pipeline, allowing users to filter, view,
    and download datasets using their pre-signed URL implementation of choice.

    Attributes:
        pipeline (kedro_graphql.models.Pipeline): The Kedro pipeline object
        spec (dict): Kedro GraphQL UI specification
        dataset_map (dict): A mapping of Kedro dataset types to their corresponding rendering Panel components
    """

    pipeline = param.ClassSelector(class_=Pipeline, doc="The Kedro pipeline object")
    spec = param.Dict(default={}, doc="Kedro GraphQL UI specification")
    dataset_map = param.Dict(
        default={}, doc="A mapping of Kedro dataset types to their corresponding rendering Panel components")

    def __init__(self, **params):
        super().__init__(**params)

        # this is used to inject JS dynamically
        self.js_download = pn.pane.HTML("", width=0, height=0)
        self.partitions_widget = pn.widgets.Tabulator(
            pd.DataFrame({"Name": [], "Type": [], "Filepath": [], "Signed URL": []}),
            disabled=True,
            buttons={
                'Download': "<i class='fa fa-download'></i>",
                "Popout": "<i class='fa fa-external-link'></i>"
            },
            theme='materialize',
            selectable="checkbox",
            show_index=False,
            hidden_columns=["Signed URL", "Partitioned Dataset Name"]
        )
        self.partitions_download_button = pn.widgets.Button(
            name='Download', button_type='primary')
        self.partitions_download_button.on_click(lambda event: asyncio.create_task(
            self.on_partitions_download_click(event, self.partitions_widget.value)))
        self.partitions_modal = pn.Modal(self.partitions_download_button, self.partitions_widget, name="Partitions",
                                         margin=20, background_close=True, show_close_button=True)

        if not self.pipeline or not self.spec:
            self._content = pn.Column(
                pn.pane.Markdown(
                    "**Missing required parameters: `pipeline`, or `spec`.**"),
                sizing_mode="stretch_width"
            )
        else:
            # Show loading spinner until the dashboard is built
            self._content = pn.Column(
                pn.indicators.LoadingSpinner(value=True, width=50, height=50),
                pn.pane.Markdown("Fetching Data..."),
                sizing_mode='stretch_width'
            )

            # Ensures build after panel server is fully loaded to avoid race conditions
            pn.state.onload(lambda: asyncio.create_task(
                asyncio.to_thread(self.build_component)))

    def build_component(self):
        df_data = self._build_dataframe()
        ds_widget = self._build_widget(df_data)
        self.partitions_widget.on_click(lambda event: asyncio.create_task(
            self.on_partition_row_click(event, self.partitions_widget.value)))
        self._content[:] = pn.Column(
            pn.Card(ds_widget, title="Data Catalog"),
            self.js_download,
            self.partitions_modal,
            sizing_mode="stretch_width"
        )

    def _build_dataframe(self):
        base_df = pd.DataFrame({
            'Name': [ds.name for ds in self.pipeline.data_catalog],
            'Type': [ds.parse_config()["type"] for ds in self.pipeline.data_catalog],
            'Filepath': [ds.parse_config().get("filepath", ds.parse_config().get("path", "")) for ds in self.pipeline.data_catalog],
        })

        tags_list = []
        for idx, ds in enumerate(self.pipeline.data_catalog):
            tag_data = {}
            if ds.tags:
                for tag in ds.tags:
                    tag_data[f"Tag:{tag.key}"] = tag.value
            tags_list.append(pd.Series(tag_data, name=idx))

        tags_df = pd.DataFrame(tags_list).fillna("")
        return pd.concat([base_df, tags_df], axis=1)

    def _build_widget(self, ds_df):
        filters = {
            "Name": {"type": "input", "placeholder": "Filter by name", "func": "like"},
            "Type": {"type": "list", "placeholder": "Select dataset type(s)",
                     "func": "in", "valuesLookup": True, "multiselect": True},
            "Filepath": {"type": "input", "placeholder": "Filter by filepath", "func": "like"}
        }

        for tag in ds_df.columns[3:]:
            filters[tag] = {
                "type": "list",
                "placeholder": "Select tag(s)",
                "func": "in",
                "valuesLookup": True,
                "multiselect": True
            }

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
        ds_widget.on_click(lambda event: asyncio.create_task(
            self.on_row_click(event, ds_df)))
        return ds_widget

    def trigger_popout(self, url):
        """
        Trigger a popout window for the specified URL. Default browser rendering is used.
        """

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

        self.js_download.object = js_code
        self.js_download.object = None

    def trigger_download(self, url, filepath):
        """
        Trigger a browser download for the specified URL. Name is derived from the filepath.
        """

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

        self.js_download.object = js_code
        self.js_download.object = None

    def open_dataset_viewer(self, page, presigned_url, ds_name, ds_type):
        """
        Open custom dataset viewer in a new browser tab provided from the dataset_map.
        """

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

        self.js_download.object = js_code
        self.js_download.object = None

    async def on_partitions_download_click(self, event, df):
        """
        Handle download button click events in the partitions table.
        """
        print("PARTITIONS DOWNLOAD CLICKED:", event)
        print("DATAFRAME:", df)
        selected_rows = self.partitions_widget.selection
        for row in selected_rows:
            dataset_name = df.iloc[row]['Name']
            dataset_filepath = df.iloc[row]['Filepath']
            dataset_type = df.iloc[row]['Type']
            presigned_url = df.iloc[row]['Signed URL']
            self.trigger_download(
                presigned_url, dataset_filepath)

    async def on_partition_row_click(self, event, df):
        """
        Handle row click events in the partitions table.
        """
        print("PARTITION ROW CLICKED:", event)
        print("DATAFRAME:", df)
        row = event.row
        dataset_name = df.iloc[row]['Name']
        dataset_filepath = df.iloc[row]['Filepath']
        dataset_type = df.iloc[row]['Type']
        presigned_url = df.iloc[row]['Signed URL']
        partitioned_dataset_name = df.iloc[row]["Partitioned Dataset Name"]

        for ds in self.pipeline.data_catalog:
            if ds.name == partitioned_dataset_name:
                dataset = ds

        if event.column != 'Download' and event.column != 'Popout':
            return

        elif event.column == 'Download':
            self.trigger_download(
                presigned_url, dataset_filepath)

        elif event.column == 'Popout':
            # Check dataset_map for custom viewer
            for dataset_type, panel_page in self.dataset_map.items():
                if dataset.parse_config()["type"] == dataset_type:
                    self.open_dataset_viewer(
                        panel_page, presigned_url, dataset_name, dataset_type)
                    return
            # Default to raw data viewer
            self.trigger_popout(presigned_url)

    def open_partition_viewer(self, dataset, presigned_urls):
        ds_config = dataset.parse_config()
        self.partitions_widget.value = pd.DataFrame(
            {"Name": [url.file for url in presigned_urls.urls],
             "Type": [ds_config["dataset"]["type"] for url in presigned_urls.urls],
             "Signed URL": [u.url for u in presigned_urls.urls],
             "Partitioned Dataset Name": [dataset.name for u in presigned_urls.urls],
             "Filepath": ["/".join([ds_config.get("path", ""), url.file]) for url in presigned_urls.urls],

             })

        self.partitions_modal.show()

    async def on_row_click(self, event, ds_df):
        """
        Handle row click events in the dataset table and triggers appropriate actions for 'Download' or 'Popout' column clicks.
        """
        try:
            if event.column != 'Download' and event.column != 'Popout':
                return

            row = event.row
            dataset_name = ds_df.iloc[row]['Name']
            dataset_filepath = ds_df.iloc[row]['Filepath']
            dataset_type = ds_df.iloc[row]['Type']

            for ds in self.pipeline.data_catalog:
                if ds.name == dataset_name:

                    if dataset_type == "partitions.IncrementalDataset":
                        pn.state.notifications.warning(
                            f"Actions for IncrementalDatasets are not supported yet: {dataset_name}", duration=10000)
                        return

                    else:
                        presigned_urls = await self.spec["config"]["client"].read_datasets(
                            id=self.pipeline.id, datasets=[DataSetInput(name=ds.name)], expires_in_sec=3600)

                        presigned_url = presigned_urls[0]

                        if event.column == 'Download':
                            if dataset_type == "partitions.PartitionedDataset":
                                self.open_partition_viewer(ds, presigned_url)
                            elif isinstance(presigned_url, SignedUrl):
                                self.trigger_download(
                                    presigned_url.url, dataset_filepath)
                            else:
                                pn.state.notifications.warning(
                                    f"Download not available for {dataset_name}", duration=10000)
                            return

                        elif event.column == 'Popout':
                            if dataset_type == "partitions.PartitionedDataset":
                                self.open_partition_viewer(ds, presigned_url)
                            elif presigned_url:
                                # Check dataset_map for custom viewer
                                for dataset_type, panel_page in self.dataset_map.items():
                                    if ds.parse_config()["type"] == dataset_type:
                                        self.open_dataset_viewer(
                                            panel_page, presigned_url.url, dataset_name, dataset_type)
                                        return
                                # Default to raw data viewer
                                self.trigger_popout(presigned_url.url)
                            else:
                                pn.state.notifications.warning(
                                    f"No signed URL available for {dataset_name}", duration=10000)
                            return
        except Exception as e:
            pn.state.notifications.error(
                f"Error processing action for dataset {dataset_name}: {str(e)}", duration=10000)

    def __panel__(self):
        return self._content
