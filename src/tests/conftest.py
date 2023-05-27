import pytest
from pathlib import Path
from kedro.framework.project import settings
from kedro.config import ConfigLoader
from kedro.framework.context import KedroContext
from kedro.framework.hooks import _create_hook_manager
from kedro_graphql.backends import init_backend
from kedro_graphql.tasks import run_pipeline
from kedro_graphql.models import Pipeline, DataSet, Parameter, Tag
from unittest.mock import patch
from uuid import uuid4
from io import BytesIO



@pytest.fixture(scope="session")
def config_loader():
    return ConfigLoader(conf_source=str(Path.cwd() / settings.CONF_SOURCE))


@pytest.fixture(scope='session')
def project_context(config_loader):
    return KedroContext(
        package_name="kedro_graphql",
        project_path=Path.cwd(),
        config_loader=config_loader,
        hook_manager=_create_hook_manager(),
    )

@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'redis://',
        'result_backend': 'redis://',
        'result_extened': True,
        'worker_send_task_events': True,
        'task_send_sent_event': True,
        'task_store_eager_result': True,
        'task_always_eager': False,
        'task_ignore_result': False,
        'imports': ["kedro_graphql.config", "kedro_graphql.tasks"]

    }


@pytest.fixture(scope="session")
def celery_worker_parameters():
    return {"without_heartbeat": False}

@pytest.fixture
def mock_backend():
    return init_backend()

@pytest.fixture
def mock_info_context(mock_backend):
    class App():
        backend = mock_backend

    class Request():
        app = App()

    with patch("strawberry.types.Info.context", {"request": Request()}) as m:
        yield m


## refer to https://docs.pytest.org/en/7.1.x/how-to/tmp_path.html for info on tmp_path fixture
@pytest.fixture
def mock_text_in(tmp_path):
    #tmp_path.mkdir()
    text_in = tmp_path / "text_in.txt"
    text_in.write_text("hello")
    return text_in

@pytest.fixture
def mock_text_out(tmp_path):
    #tmp_path.mkdir()
    text_out = tmp_path / "text_out.txt"
    text_out.write_text("good bye")
    return text_out

@pytest.fixture
def mock_pipeline(mock_backend, tmp_path, mock_text_in, mock_text_out):

    inputs = [{"name": "text_in", "type": "text.TextDataSet", "filepath": str(mock_text_in)}]
    outputs = [{"name":"text_out", "type": "text.TextDataSet", "filepath": str(mock_text_out)}]
    parameters = [{"name":"example", "value":"hello"}]
    tags = [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]

    p = Pipeline(
        name = "example00",
        inputs = [DataSet(**i) for i in inputs],
        outputs = [DataSet(**o) for o in outputs],
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
    p = mock_backend.create(p)
    return p

@pytest.fixture
def mock_pipeline2(mock_backend, tmp_path, mock_text_in, mock_text_out):

    inputs = [{"name": "text_in", "type": "text.TextDataSet", "filepath": str(mock_text_in)}]
    outputs = [{"name":"text_out", "type": "text.TextDataSet", "filepath": str(mock_text_out)}]
    parameters = [{"name":"example", "value":"hello"}]
    tags = [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]

    p = Pipeline(
        name = "example00",
        inputs = [DataSet(**i) for i in inputs],
        outputs = [DataSet(**o) for o in outputs],
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
    p = mock_backend.create(p)
    return p

@pytest.fixture
def s3_client():
    from minio import Minio

    return Minio(
            "localhost:9000",
            access_key="admin",
            secret_key="password",
            secure=False
        )

@pytest.fixture
def s3_object(s3_client):
    """
    https://min.io/docs/minio/linux/developers/python/API.html#put_object

    Run ```make dev-cluster``` to start minio service.
    """
    from minio.error import S3Error
    
    try:

        # Make 'my-bucket' bucket if not exist.
        found = s3_client.bucket_exists("my-bucket")
        if not found:
            s3_client.make_bucket("my-bucket")
        else:
            print("Bucket 'my-bucket' already exists")


        fname = "text_in_"+str(uuid4())+".txt"
        # Upload contents as object name
        # 'text_in.txt' to bucket 'my-bucket'.
        s3_client.put_object(
            "my-bucket", fname, BytesIO(b"hello"), 5,
            content_type="text"
        )
        print(
            "'"+fname+"' is successfully uploaded as "
            "object '"+fname+"' to bucket 'my-bucket'."
        )

        ## https://docs.pytest.org/en/6.2.x/fixture.html#teardown-cleanup-aka-fixture-finalization
        yield "s3://my-bucket/" + fname
        
        ## cleanup
        s3_client.remove_object("my-bucket", fname)       
        
        print(
            "object '"+fname+"' successfully removed from "
            "bucket 'my-bucket'."
        )
    except S3Error as exc:
        print("error occurred.", exc)

@pytest.fixture
def mock_pipeline_s3(mock_backend, s3_object, s3_client):
    """
    
    """
    out_fname = "text_out_"+str(uuid4())+".txt"
    
    inputs = [{"name": "text_in", "type": "text.TextDataSet", 
               "filepath": s3_object, 
               "credentials": {"key":"admin", 
                               "secret":"password", 
                               "client_kwargs":{
                                   "endpoint_url": 'http://localhost:9000'
                                }}
            }]
    
    outputs = [{"name":"text_out", "type": "text.TextDataSet", 
                "filepath": "s3://my-bucket/"+out_fname, 
                "credentials": {"key":"admin", 
                                "secret":"password", 
                                "client_kwargs":{
                                    "endpoint_url": 'http://localhost:9000'
                                }}
                }]
    
    parameters = [{"name":"example", "value":"hello"}]
    
    tags = [{"key": "author", "value": "opensean"},{"key":"package", "value":"kedro-graphql"}]

    p = Pipeline(
        name = "example00",
        inputs = [DataSet(**i) for i in inputs],
        outputs = [DataSet(**o) for o in outputs],
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
    p = mock_backend.create(p)
    yield p
    ## cleanup
    s3_client.remove_object("my-bucket", out_fname)


@pytest.fixture
def mock_env_runner_argo_workflows(monkeypatch):
    monkeypatch.setenv("KEDRO_GRAPHQL_RUNNER", "KedroGraphQL.runner.argo.ArgoWorkflowsRunner")