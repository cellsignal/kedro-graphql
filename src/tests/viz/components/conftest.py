import pytest
from kedro_graphql.tasks import run_pipeline
from kedro_graphql.models import Pipeline, DataSet, Parameter, Tag
import json

def mock_pipeline_factory(mock_app, mock_text_in, mock_text_out, tags, parent = None):
    """
    
    """

 
    input_dict = {"type": "text.TextDataSet", 
               "filepath": str(mock_text_in), 
            }
    
    output_dict = {"type": "text.TextDataSet", 
                "filepath": str(mock_text_out), 
                }
    
    parameters = [{"name":"example", "value":"hello"}]
    data_catalog = [{"name": "text_in", "config": json.dumps(input_dict)},
                    {"name": "text_out", "config": json.dumps(output_dict)}] 
    #tags = [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]
 
    p = Pipeline(
        name = "example00",
        parent = parent,
        data_catalog = [DataSet(**d) for d in data_catalog],
        parameters = [Parameter(**p) for p in parameters],
        tags = [Tag(**p) for p in tags],
        task_name = str(run_pipeline),
    )

    serial = p.serialize()

    result = run_pipeline.apply_async(kwargs = {"name": "example00", 
                                                 "inputs": serial["inputs"], 
                                                 "outputs": serial["outputs"],
                                                 "parameters": serial["parameters"]}, countdown=0.1)
    p.task_id = result.id
    p.status = result.status
    p.task_kwargs = str(
            {"name": serial["name"], 
            "inputs": serial["inputs"], 
            "outputs": serial["outputs"], 
            "parameters": serial["parameters"]}
    )

    print(f'Starting {p.name} pipeline with task_id: ' + str(p.task_id))
    p = mock_app.backend.create(p)
    return p

@pytest.mark.usefixtures('mock_celery_session_app')
@pytest.mark.usefixtures('celery_session_worker')
@pytest.mark.usefixtures('depends_on_current_app')
@pytest.fixture
def mock_pipeline_batch(mock_app, mock_text_in, mock_text_out):

    tags = [[{"key": "author", "value": "you"},{"key":"location", "value":"here"}],
            [{"key": "author", "value": "me"},{"key":"location", "value":"there"}],
            [{"key": "author", "value": "them"},{"key":"location", "value":"nowhere"}],
            [{"key": "author", "value": "they"},{"key":"location", "value":"everywhere"}],
            [{"key": "author", "value": "it"},{"key":"location", "value":"between"}],
            [{"key": "author", "value": "no-one"},{"key":"location", "value":"below"}],
           ]
    batch = mock_pipeline_factory(mock_app, mock_text_in, mock_text_out, tags[0])

    for t in tags:
        mock_pipeline_factory(mock_app, mock_text_in, mock_text_out, t, parent = batch.task_id)
    return batch