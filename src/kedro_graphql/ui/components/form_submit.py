from kedro_graphql.ui.client import client
from gql import gql


query = gql(
    """
    mutation createPipeline($pipeline: PipelineInput!) {
      pipeline(pipeline: $pipeline) {
        id
        name
        describe
        inputs {
          name
          filepath
          type
        }
        nodes {
          name
          inputs
          outputs
          tags
        }
        outputs {
          filepath
          name
          type
        }
        parameters {
          name
          value
        }
        status
        tags {
          key
          value
        }
        taskId
        taskName
        taskArgs
        taskKwargs
        taskRequest
        taskException
        taskTraceback
        taskEinfo
        taskResult
      }
    }
    """
    )

def form_submit(pipeline_template = {}):
    return client.execute(query, variable_values={"pipeline": pipeline_template})