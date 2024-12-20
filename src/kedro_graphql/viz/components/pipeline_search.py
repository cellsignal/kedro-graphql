## some code commented out because it has not been implemented
import panel as pn
import param
import pandas as pd
from kedro_graphql.viz.client import KedroGraphqlClient
from kedro_graphql.config import config
from fastapi.encoders import jsonable_encoder
import json

pn.extension('tabulator', css_files=["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"])

class PipelineSearch(pn.viewable.Viewer):
    limit = param.Integer(default = 10)
    cursor = param.String(default = None)
    filter = param.String(default = "")
    prev_cursor = param.String(default = None)
    next_cursor = param.String(default = None)
    more_clicks = param.Integer(default = 0)
    prev_clicks = param.Integer(default = 0)
    cursors = param.List(default = [])
    cursor_index = param.Integer(default = 0)


    def navigate(self, event, df):
            ## event.column and event.row are accessible
            print("EVENT", event)
            if event.column == "Open":
                pn.state.location.pathname = config['KEDRO_GRAPHQL_VIZ_BASEPATH'] + "/data"
                pn.state.location.search = "?pipeline=" + df.loc[event.row, "name"]+"&id=" + df.loc[event.row, "id"]
                pn.state.location.reload = True

    def build_filter(self, raw):
        filter = {"$or":[]}
        parts = raw.split(",")
        names = [p for p in parts if "name" in p]
        status = [p for p in parts if "status" in p]
        tags = [p for p in parts if "tag" in p]

        for name in names:
            if len(name.split("=")) > 1:
                n = name.split("=")[1]
                f = {"name":{ "$regex": "^"+n}} 
                filter["$or"].append(f)

        for s in status:
            if len(s.split("=")) > 1:
                n = s.split("=")[1]
                f = {"status":{ "$regex": "^"+n}} 
                filter["$or"].append(f)

        for tag in tags:
            if len(tag.split(":")) > 1:
                key_value = tag.split(":")[1]
                key = key_value.split("=")[0]
                value = key_value.split("=")[1]
                #t = {"tags":{"key": {"$regex": "^"+key}, "value": {"$regex": "^"+value}}} 
                t = {"tags":{"key": key, "value": value}} 
                filter["$or"].append(t)

        if len(filter["$or"]) == 0:
            return ""
        else:
            return json.dumps(filter)

    async def build_table(self, limit, filter, load_more, load_prev, show_lineage):
        ## TO DO enable switching to a searchable dataset view grouped by pipeline
        client = KedroGraphqlClient()
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        f = self.build_filter(filter)

        if load_more > self.more_clicks:
            result = await client.readPipelines(limit = limit, 
                                                cursor = self.next_cursor, 
                                                filter = f)
            if self.cursors[-1] != self.next_cursor:
                self.cursors.append(self.next_cursor)
            if result.page_meta.next_cursor:
                self.next_cursor = result.page_meta.next_cursor
            self.more_clicks = load_more

        elif load_prev > self.prev_clicks:
            if len(self.cursors) > 1:
                cursor = self.cursors[-2]
                self.next_cursor = self.cursors[-1]
                self.cursors = self.cursors[:-1]
            else:
                cursor = None
                self.cursors = [None]

            result = await client.readPipelines(limit = limit, 
                                                cursor = cursor, 
                                                filter = f)

            self.prev_clicks = load_prev

        else:
            result = await client.readPipelines(limit = limit, 
                                                cursor = None, 
                                                filter = f)
            self.cursors = [None]
            self.next_cursor = result.page_meta.next_cursor


        if len(result.pipelines) == 0:
             yield pn.pane.Alert('No results found.')
        else:
            df = pd.DataFrame.from_records([jsonable_encoder(p) for p in result.pipelines]
                                           )
            
            ## flatten tags into seperate columns
            tags = []
            for index, row in df.iterrows():
                 inner_tags = []
                 for i in row["tags"]: 
                     inner_tags.append(pd.DataFrame({"tag: " + i["key"]:i["value"]}, index = [index]))
                  
                 tags.append(pd.concat(inner_tags, axis = 1))
                 
            tags = pd.concat(tags)

            df = df.merge(tags, left_index = True, right_index = True)
            
            ## visible columns
            cols_show = ["parent","id", "name", "status"] + list(tags.columns)

            if "Show Lineage" in show_lineage:
                groupby = ["parent"]
            else:
                groupby = []

            df_widget = pn.widgets.Tabulator(df[cols_show],                                              
                                             buttons={'Open': "<i class='fa fa-folder-open'></i>"}, 
                                             theme='materialize',
                                             groupby = groupby,
                                             hidden_columns = ["parent"],
                                             disabled = True,
                                             sizing_mode = "stretch_width",
                                             )
            df_widget.on_click(
                lambda e: self.navigate(e, df)
            )
            yield df_widget

    def __panel__(self):
        search = pn.widgets.TextInput(
                           name='Search', 
                           placeholder='Write something here')
        results_per_page = pn.widgets.Select(name='Results per page', options={'5': 5, '10': 10, '20': 20, '50': 50}, value=10)
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
                     search, results_per_page, show_lineage
                   ),
                   pn.Row(
                     t
                   ),
                   pn.Row(
                        load_prev, load_more
                   ),
                   styles ={"background": None},
                   sizing_mode = "stretch_width"
                   )
