# some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
from kedro_graphql.client import KedroGraphqlClient
import json

pn.extension('tabulator', css_files=[
             "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"])

# TO DO: Implement a search bar that filters pipelines by name, status, and tags, use https://panel.holoviz.org/reference/widgets/MultiChoice.html
# TO DO: Implement a button that allows the usser to search by datasets


class PipelineSearch(pn.viewable.Viewer):
    client = param.ClassSelector(class_=KedroGraphqlClient)
    limit = param.Integer(default=10)
    cursor = param.String(default=None)
    filter = param.String(default="")
    prev_cursor = param.String(default=None)
    next_cursor = param.String(default=None)
    more_clicks = param.Integer(default=0)
    prev_clicks = param.Integer(default=0)
    cursors = param.List(default=[])
    cursor_index = param.Integer(default=0)
    dashboard = param.String(default="dashboard")

    def navigate(self, event, df):
        if event.column == "Open":
            pn.state.location.search = "?component="+self.dashboard+"&pipeline=" + \
                df.loc[event.row, "name"]+"&id=" + df.loc[event.row, "id"]

    def build_filter(self, raw):
        """Build a filter string from  a raw string.

        Args:
            raw (str): Text input by user.

        Returns:
            str: A filter string in JSON format e.g. "{\"tags.key\": \"unique\", \"tags.value\": \"unique\"}"
        """
        filter = {"$or": []}
        parts = raw.split(",")
        names = [p for p in parts if "name" in p]
        status = [p for p in parts if "state" in p]
        tags = [p for p in parts if "tag" in p]

        for name in names:
            if len(name.split("=")) > 1:
                n = name.split("=")[1]
                f = {"name": {"$regex": "^"+n}}
                filter["$or"].append(f)

        for s in status:
            if len(s.split("=")) > 1:
                n = s.split("=")[1]
                f = {"status.state": {"$regex": "^"+n}}
                filter["$or"].append(f)

        for tag in tags:
            if len(tag.split(":")) > 1:
                key_value = tag.split(":")[1]
                key = key_value.split("=")[0]
                value = key_value.split("=")[1]
                t = {"tags.key": {"$regex": "^"+key},
                     "tags.value": {"$regex": "^"+value}}
                filter["$or"].append(t)

        if len(filter["$or"]) == 0 and len(raw) > 0:
            # default to searching all fields for the raw string
            f = {"$or": [{"name": {"$regex": "^"+raw}},
                         {"status.state": {"$regex": "^"+raw}},
                         {"tags.key": {"$regex": "^"+raw}},
                         {"tags.value": {"$regex": "^"+raw}}]}
            return json.dumps(f)
        elif len(raw) == 0:
            return ""
        else:
            return json.dumps(filter)

    async def build_table(self, limit, filter, load_more, load_prev, show_lineage):
        # TO DO enable switching to a searchable dataset view grouped by pipeline
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        f = self.build_filter(filter)
        if load_more > self.more_clicks and "id=" not in filter:
            result = await self.client.read_pipelines(limit=limit,
                                                      cursor=self.next_cursor,
                                                      filter=f)
            pipelines = result.pipelines
            if self.cursors[-1] != self.next_cursor:
                self.cursors.append(self.next_cursor)
            if result.page_meta.next_cursor:
                self.next_cursor = result.page_meta.next_cursor
            self.more_clicks = load_more

        elif load_prev > self.prev_clicks and "id=" not in filter:
            if len(self.cursors) > 1:
                cursor = self.cursors[-2]
                self.next_cursor = self.cursors[-1]
                self.cursors = self.cursors[:-1]
            else:
                cursor = None
                self.cursors = [None]

            result = await self.client.read_pipelines(limit=limit,
                                                      cursor=cursor,
                                                      filter=f)
            pipelines = result.pipelines
            self.prev_clicks = load_prev

        else:
            if "id=" in filter:
                id = filter.split("id=")[1]
                id = id.split(",")[0]
                result = await self.client.read_pipeline(id=id)
                pipelines = [result]
                self.cursors = [None]
            else:
                cursor = None

                result = await self.client.read_pipelines(limit=limit,
                                                          cursor=cursor,
                                                          filter=f)
                pipelines = result.pipelines
                self.cursors = [None]
                self.next_cursor = result.page_meta.next_cursor

        if len(pipelines) == 0:
            yield pn.pane.Alert('No results found.')
        else:

            df = pd.DataFrame.from_records(
                [p.encode(encoder="dict") for p in pipelines])

            # flatten tags into seperate columns
            tags = []
            for index, row in df.iterrows():
                inner_tags = []
                for i in row["tags"]:
                    inner_tags.append(pd.DataFrame(
                        {"tag: " + i["key"]: i["value"]}, index=[index]))

                tags.append(pd.concat(inner_tags, axis=1))

            tags = pd.concat(tags)

            df = df.merge(tags, left_index=True, right_index=True)

            # parse latest state
            df["state"] = df["status"].apply(lambda x: x[-1]["state"])

            # visible columns
            cols_show = ["parent", "id", "name", "state"] + list(tags.columns)

            if "Show Lineage" in show_lineage:
                groupby = ["parent"]
            else:
                groupby = []

            df_widget = pn.widgets.Tabulator(df[cols_show],
                                             buttons={
                                                 'Open': "<i class='fa fa-folder-open'></i>"},
                                             theme='materialize',
                                             groupby=groupby,
                                             hidden_columns=["parent"],
                                             disabled=True,
                                             sizing_mode="stretch_width",
                                             show_index=False
                                             )
            df_widget.on_click(
                lambda e: self.navigate(e, df)
            )
            yield df_widget

    def __panel__(self):
        search = pn.widgets.TextInput(
            name='Search',
            placeholder='Write something here')
        results_per_page = pn.widgets.Select(name='Results per page', options={
                                             '5': 5, '10': 10, '20': 20, '50': 50}, value=10)
        show_lineage = pn.widgets.CheckButtonGroup(name='Check Button Group',
                                                   button_style='solid',
                                                   value=[],
                                                   options=['Show Lineage'])
        pn.state.location.sync(search, {"value_input": "filter"})

        load_more = pn.widgets.Button(name="Load More")
        load_prev = pn.widgets.Button(name="Load Previous")

        t = pn.bind(self.build_table,
                    limit=results_per_page,
                    filter=search,
                    load_more=load_more.param.clicks,
                    load_prev=load_prev.param.clicks,
                    show_lineage=show_lineage)

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
                search, results_per_page, show_lineage
            ),
            pn.Row(
                t
            ),
            pn.Row(
                load_prev, load_more
            ),
            styles={"background": None},
            sizing_mode="stretch_width"
        )
