import panel as pn
import param
import pandas as pd
from kedro_graphql.client import KedroGraphqlClient
from kedro_graphql.models import Pipeline

pn.extension('tabulator', css_files=[
             "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"])


class PipelineMonitor(param.Parameterized):
    """Model for the PipelineMonitor component that handles the logic for fetching pipeline status and logs."""
    pipeline = param.ClassSelector(class_=Pipeline)
    client = param.ClassSelector(class_=KedroGraphqlClient)
    status = param.String()
    logs = param.String()

    def __init__(self, spec=None, pipeline=None, **params):
        """Initializes the Kedro GraphQL client with the provided specification.

        Kwargs:
            spec (dict): The specification for the UI, including configuration and pages.
            pipeline (Pipeline): The Kedro pipeline for which the monitor is built.
            **params: Additional parameters for the PipelineMonitor component.

        """
        super().__init__(**params)

        if pn.state.cookies:
            cookies = pn.state.cookies
        else:
            cookies = None

        self.client = KedroGraphqlClient(
            uri_graphql=spec["config"]["client_uri_graphql"],
            uri_ws=spec["config"]["client_uri_ws"],
            cookies=cookies
        )
        self.pipeline = pipeline

    @param.depends('pipeline', watch=True)
    async def subscribe_to_pipeline_events(self):
        """Fetches the current status of the pipeline."""

        # subscribe to pipeline events
        async for event in self.client.pipeline_events(id=self.pipeline.id):
            self.status = event.status
        await self.client.close_sessions()

    @param.depends('pipeline', watch=True)
    async def subscribe_to_logs(self):
        """Builds a terminal that displays the logs of the pipeline in real-time.
        This method connects to the pipeline logs and updates the terminal as new log messages are received.

        Yields:
        pn.widgets.Terminal: A terminal displaying the pipeline logs.
        """

        async for message in self.client.pipeline_logs(id=self.pipeline.id):
            if not self.logs:
                self.logs = ""
            self.logs += f"{message.time} - {message.message}\n"
        await self.client.close_sessions()

    def __panel__(self):
        return pn.Column(
            pn.Param(
                self,
                name="",
                parameters=["status", "logs"],
                widgets={
                    "status": pn.widgets.StaticText,
                    "logs": pn.widgets.TextAreaInput(
                        name="Live Log Stream",
                        sizing_mode='stretch_width',
                        height=400
                    )
                }
            ),
            sizing_mode='stretch_width'
        )
