# some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
import json
from kedro_graphql.models import Pipelines

pn.extension('ace', 'jsoneditor')
pn.extension('tabulator', css_files=[
             "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"])


class PipelineSearchModel(param.Parameterized):
    """Parameters for the PipelineSearch component."""
    spec = param.Dict(default={},
                      doc="The specification for the UI, including configuration and client.")
    search = param.String(
        default="", doc="Enter search terms to find relevant pipelines.")
    results_per_page = param.Integer(default=10, bounds=(
        1, 100), doc="Number of results per page.")
    # show_lineage = param.Boolean(
    #     default=False, doc="Whether to show lineage information.")
    load_more = param.Action(lambda x: x.load_more_results(),
                             label="Load More",
                             doc="Action to load more results.")
    load_prev = param.Action(lambda x: x.load_prev_results(),
                             label="Load Previous",
                             doc="Action to load previous results.")
    filter = param.String(
        default="", doc="Computed filter string for searching pipelines")

    cursor = param.String(default=None, doc="Cursor for pagination.")
    cursors = param.List(
        default=[], doc="List of cursors for pagination.")
    result = param.ClassSelector(
        class_=Pipelines, default=None, doc="The result of the pipeline search.")
    search_params = param.Dict(default={})

    @param.depends('search', watch=True)
    def compute_filter(self):
        """Compute the filter string based on the search input.

        Returns:
            str: A filter string in JSON format e.g. "{\"tags.key\": \"unique\", \"tags.value\": \"unique\"}"
        """
        filter = {"$or": []}
        parts = self.search.split(",")
        names = [p for p in parts if "name" in p]
        status = [p for p in parts if "state" in p]
        tags = [p for p in parts if "tag" in p]

        for name in names:
            if len(name.split("=")) > 1:
                n = name.split("=")[1]
                f = {"name": {"$regex": "^" + n}}
                filter["$or"].append(f)

        for s in status:
            if len(s.split("=")) > 1:
                n = s.split("=")[1]
                f = {"status.state": {"$regex": "^" + n}}
                filter["$or"].append(f)

        for tag in tags:
            if len(tag.split(":")) > 1:
                key_value = tag.split(":")[1]
                key = key_value.split("=")[0]
                value = key_value.split("=")[1]
                t = {
                    "tags.key": {"$regex": "^" + key},
                    "tags.value": {"$regex": "^" + value}
                }
                filter["$or"].append(t)

        if len(filter["$or"]) == 0 and len(self.search) > 0:
            # default to searching all fields for the raw string
            f = {
                "$or": [
                    {"name": {"$regex": "^" + self.search}},
                    {"status.state": {"$regex": "^" + self.search}},
                    {"tags.key": {"$regex": "^" + self.search}},
                    {"tags.value": {"$regex": "^" + self.search}}
                ]
            }
            self.filter = json.dumps(f)
        elif len(self.search) == 0:
            self.filter = ""
        else:
            self.filter = json.dumps(filter)

    @param.depends('search', watch=True)
    async def reset_cursor_history(self):
        """Reset the cursor history when the search input changes."""
        self.cursors = []
        self.cursor = ""

    @param.depends('load_more', watch=True)
    def load_more_results(self):
        """Load more results based on the current cursor."""
        if self.result.page_meta and self.result.page_meta.next_cursor:
            if self.cursor:
                if len(self.cursors) > 0 and self.cursors[-1] != self.cursor:
                    self.cursors.append(self.cursor)
                else:
                    self.cursors = [self.cursor]
                # print("CURSORS", self.cursors)
            # print("NEXT CURSOR", self.result.page_meta.next_cursor)
            self.cursor = self.result.page_meta.next_cursor

    @param.depends('load_prev', watch=True)
    def load_prev_results(self):
        """Load previous results based on the cursor history."""
        if len(self.cursors) > 0:
            self.cursor = self.cursors.pop()
            # print("CURSORS", self.cursors)
        else:
            self.cursor = ""

    @param.depends('results_per_page', 'cursor', 'filter', watch=True)
    async def build_search_params(self):
        """Build the search parameters for the API request."""
        if not self.cursor or len(self.cursor) == 0:
            cursor = None
        else:
            cursor = self.cursor
        self.search_params = {
            "limit": self.results_per_page,
            "cursor": cursor,
            "filter": self.filter
        }

    @param.depends('load_more_results', 'load_prev_results', 'build_search_params', watch=True)
    async def execute_search(self):
        """Execute the search based on the current filter and pagination parameters."""
        # print("Executing search with params:", self.search_params)
        self.result = await self.spec["config"]["client"].read_pipelines(
            limit=self.search_params.get("limit", self.results_per_page),
            cursor=self.search_params.get("cursor", self.cursor),
            filter=self.search_params.get("filter", self.filter)
        )


class PipelineSearch(pn.viewable.Viewer):
    """A component that allows users to search for pipelines in the Kedro GraphQL UI.
    This component provides a search bar, results per page selection, and buttons to load more or previous results.
    It displays the results in a table format with clickable rows to navigate to the pipeline details.

    Attributes:
        spec (dict): The specification for the UI, including configuration and client.
        limit (int): The number of results to display per page.
        cursor (str): The cursor for pagination.
        filter (str): The filter string for searching pipelines.
        prev_cursor (str): The cursor for the previous page.
        next_cursor (str): The cursor for the next page.
        more_clicks (int): The number of clicks on the "Load More" button.
        prev_clicks (int): The number of clicks on the "Load Previous" button.
        cursors (list): A list of cursors for pagination.
        cursor_index (int): The index of the current cursor in the cursors list.
        dashboard_page (str): The page to navigate to when a pipeline is clicked.
    """
    spec = param.Dict(default={})
    search_model = param.ClassSelector(
        class_=PipelineSearchModel, default=PipelineSearchModel())
    dashboard_page = param.String(
        default="dashboard", doc="The page to navigate to when a pipeline is clicked.")

    def __init__(self, **params):
        super().__init__(**params)
        self.search_model = PipelineSearchModel(spec=self.spec)

    def navigate(self, event, df):
        """Navigate to the pipeline details page when a row is clicked.
        Args:
            event (pn.widgets.Tabulator.ClickEvent): The event triggered by clicking a row.
            df (pd.DataFrame): The DataFrame containing pipeline data.
        """
        if event.column == "Open":
            pn.state.location.pathname = self.spec["panel_get_server_kwargs"]["prefix"] + self.dashboard_page.lower()
            pn.state.location.search = "?pipeline=" + df.loc[event.row, "name"] + "&id=" + df.loc[event.row, "id"]
            pn.state.location.reload = True

    @param.depends('search_model.result')
    async def build_table(self):
        """Builds a table of pipelines based on the provided filter and pagination parameters.
        Args:
            limit (int): The number of results to display per page.
            filter (str): The filter string for searching pipelines.
            load_more (int): The number of clicks on the "Load More" button.
            load_prev (int): The number of clicks on the "Load Previous" button.
            show_lineage (list): A list indicating whether to show lineage in the table.
        Yields:
            pn.widgets.Tabulator: A table displaying the pipelines with clickable rows.
        """
        if not self.search_model.result or not self.search_model.result.pipelines:
            yield pn.pane.Markdown("No pipelines found matching the search criteria.")
        else:
            pipelines = self.search_model.result.pipelines

            df = pd.DataFrame.from_records([p.encode(encoder="dict") for p in pipelines])

            # flatten tags into seperate columns
            tags = []
            for index, row in df.iterrows():
                inner_tags = []
                if row["tags"]:
                    for i in row["tags"]:
                        inner_tags.append(
                            pd.DataFrame({"tag: " + i["key"]: i["value"]}, index=[index])
                        )

                    tags.append(pd.concat(inner_tags, axis=1))
                else:
                    tags.append(pd.DataFrame(index=[index]))

            tags = pd.concat(tags).fillna("")

            df = df.merge(tags, left_index=True, right_index=True)

            # parse latest state
            df["state"] = df["status"].apply(lambda x: x[-1]["state"])

            # visible columns
            cols_show = ["parent", "id", "name", "state"] + list(tags.columns)

            df_widget = pn.widgets.Tabulator(
                df[cols_show],
                buttons={'Open': "<i class='fa fa-folder-open'></i>"},
                theme='materialize',
                hidden_columns=["parent"],
                disabled=True,
                sizing_mode="stretch_width",
                show_index=False
            )
            df_widget.on_click(lambda e: self.navigate(e, df))
            yield df_widget

    def __panel__(self):
        pn.state.onload(self.search_model.execute_search)
        return pn.Card(
            pn.Row(
                pn.pane.Markdown("""Search for pipelines with the following syntax:
- Search by name: `name=example`
- Search by status: `state=STAGED`
- Search by tags: `tag:key=value`
- Search by multiple tags: `tag:key1=value1,tag:key2=value2`
- Search by multiple fields: `name=example,state=STAGED,tag:key=value`
- Search by pipeline id: `id=67ca04f127d86d04151c90eb`
                                 """)
            ),
            pn.Row(
                pn.Param(
                    self.search_model,
                    name="",
                    parameters=["search", "results_per_page", "load_more", "load_prev"],
                    show_name=False,
                    display_threshold=0,
                    default_layout=pn.Row,
                    widgets={
                        "load_more_clicks": pn.widgets.Button,
                        "load_prev_clicks": pn.widgets.Button,
                    }
                )
            ),
            pn.Row(
                self.build_table,
                sizing_mode="stretch_width"
            ),
            sizing_mode="stretch_width"
        )
