import panel as pn
import param
import pandas as pd
import datetime as dt
from kedro_graphql.viz.client import KedroGraphqlClient
from kedro_graphql.config import config

pn.extension('tabulator', css_files=["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"])
pn.extension('terminal')


class PipelineMonitor(pn.viewable.Viewer):
    id = param.String()
    pipeline = param.String()

    def navigate(self, event, df):
            ## event.column and event.row are accessible
            print("EVENT", event)
            if event.column == "Open":
                pn.state.location.pathname = config["KEDRO_GRAPHQL_VIZ_BASEPATH"] + "/data"
                pn.state.location.search = "?pipeline=" + df.loc[event.row, "name"] + "&id=" + df.loc[event.row, "id"]
                pn.state.location.reload = True
    
    async def build_table(self):
        client = KedroGraphqlClient()
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        result = await client.readPipeline(self.id)
        df = pd.DataFrame({
            'name': [result.name],
            'id': [result.id],
            'created': [dt.date(2019, 1, 1)],
            'tag:submitted by': ["username"],
        }, index=[0])

        df_widget = pn.widgets.Tabulator(df, 
                                         buttons={'Open': "<i class='fa fa-folder-open'></i>"}, 
                                         theme='materialize',
                                         show_index=False)
        df_widget.on_click(
            lambda e: self.navigate(e, df)
        )

        yield df_widget
        ## subscribe to pipeline events
        async for event in client.pipelineEvents(self.id):
            df.loc[0, "status"] = event.status
            df_widget.value = df
            ##yield df_widget
            if event.status == "COMPLETED":
                break

    async def build_terminal(self):
        client = KedroGraphqlClient()
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        terminal =  pn.widgets.Terminal(
            "Welcome to the Panel Terminal!\nI'm based on xterm.js\n\n",
            options={"cursorBlink": True}, 
            sizing_mode='stretch_width'
        )
        terminal.clear()
        yield terminal
        async for message in client.pipelineLogs(self.id):
             terminal.write(message.time + " " + message.message + "\n")
            
    def __panel__(self):

        pn.state.location.sync(self)
        return pn.Row(
            pn.Card(pn.Row(
                      self.build_table,
                    ),
                    self.build_terminal,
                    sizing_mode = "stretch_width",
                    title="Monitor"),
        )
