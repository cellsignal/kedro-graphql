import pytest
from kedro_graphql.tasks import run_pipeline
from kedro_graphql.models import Pipeline, DataSet, Parameter, Tag
from uuid import uuid4
from io import BytesIO
IN_DEV = True
REASON = "Argo runner in development"

@pytest.mark.skipif(IN_DEV, reason=REASON)
@pytest.fixture
def s3_client():
    from minio import Minio

    return Minio(
            "localhost:9000",
            access_key="admin",
            secret_key="password",
            secure=False
        )

@pytest.mark.skipif(IN_DEV, reason=REASON)
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



@pytest.mark.skipif(IN_DEV, reason=REASON)
@pytest.fixture
def mock_pipeline_argo(mock_app, s3_object, s3_client):
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
                                                 "parameters": serial["parameters"],
                                                 "runner": "kedro_graphql.runner.argo.ArgoWorkflowsRunner"}, countdown=0.1)
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
    yield p
    ## cleanup
    s3_client.remove_object("my-bucket", out_fname)
