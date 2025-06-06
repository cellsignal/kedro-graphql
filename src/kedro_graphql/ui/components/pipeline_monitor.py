import panel as pn
import param
import pandas as pd
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import Pipeline

pn.extension('tabulator', css_files=[
             "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"])
pn.extension('terminal')


class PipelineMonitor(pn.viewable.Viewer):
    """A component that monitors the state of a Kedro pipeline and displays its status and logs.
    This component allows users to view the current status of a pipeline and its logs in real-time.

    Attributes:
        pipeline (Pipeline): The Kedro pipeline to monitor.
        client (KedroGraphqlClient): The client used to interact with the Kedro GraphQL API.
    """
    pipeline = param.ClassSelector(class_=Pipeline)
    client = param.ClassSelector(class_=KedroGraphqlClient)

    def __init__(self, **params):
        super().__init__(**params)

    @param.depends('pipeline', 'client')
    async def build_table(self):
        """Builds a table displaying the current status of the pipeline.
        This method fetches the pipeline status from the client and updates the table in real-time as events occur.

        Yields:
            pn.widgets.Tabulator: A table displaying the pipeline status.
        """
        yield pn.indicators.LoadingSpinner(value=True, width=25, height=25)
        p = await self.client.read_pipeline(id=self.pipeline.id)
        df = pd.DataFrame({
            'name': [p.name],
            'id': [p.id],
            'status': str(p.status[-1].state),
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

    @param.depends('pipeline', 'client')
    async def build_terminal(self):
        """Builds a terminal that displays the logs of the pipeline in real-time.
        This method connects to the pipeline logs and updates the terminal as new log messages are received.

        Yields:
            pn.widgets.Terminal: A terminal displaying the pipeline logs.
        """
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
