import panel as pn
import param
import pandas as pd
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import Pipeline

pn.extension('tabulator', css_files=[
             "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"])
pn.extension('terminal')


class PipelineMonitor(pn.viewable.Viewer):
    pipeline = param.ClassSelector(class_=Pipeline)
    client = param.ClassSelector(class_=KedroGraphqlClient)

    async def build_table(self):
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        df = pd.DataFrame({
            'name': [self.pipeline.name],
            'id': [self.pipeline.id],
            'status': str(self.pipeline.status[-1].state),
        }, index=[0])

        df_widget = pn.widgets.Tabulator(df,
                                         theme='materialize',
                                         disabled=True,
                                         show_index=False)
        yield pn.Card(
            df_widget,
        )
        # subscribe to pipeline events
        async for event in self.client.pipeline_events(id=self.pipeline.id):
            df.loc[0, "status"] = event.status
            df_widget.value = df
            # yield df_widget
            if event.status == "COMPLETED":
                break

    async def build_terminal(self):
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)

        terminal = pn.widgets.Terminal(
            "Welcome to the Panel Terminal!\nI'm based on xterm.js\n\n",
            options={"cursorBlink": True},
            sizing_mode='stretch_width'
        )
        terminal.clear()
        yield terminal
        async for message in self.client.pipeline_logs(id=self.pipeline.id):
            terminal.write(message.time + " " + message.message + "\n")

    def __panel__(self):

        return pn.Column(
            pn.Row("# State"),
            pn.Row(
                self.build_table
            ),
            pn.Row("# Logs"),
            pn.Row(
                self.build_terminal,
                sizing_mode='stretch_width'
            ),
        )
