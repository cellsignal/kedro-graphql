import pytest
import json


def test_parse_s3_filepath():
    from kedro_graphql.utils import parse_s3_filepath

    # Test with a valid S3 path
    s3_path = "s3://my-bucket/my-folder/my-file.csv"
    bucket, key, filename = parse_s3_filepath(s3_path)
    assert bucket == "my-bucket"
    assert key == "my-folder"
    assert filename == "my-file.csv"

    # Test with a path that has no folder structure
    s3_path = "s3://my-bucket/my-file.csv"
    bucket, key, filename = parse_s3_filepath(s3_path)
    assert bucket == "my-bucket"
    assert key == ""
    assert filename == "my-file.csv"

    # Test with an invalid S3 path
    with pytest.raises(ValueError):
        parse_s3_filepath("invalid-s3-path")


def test_unique_paths(mock_pipeline_staged):
    from kedro_graphql.utils import generate_unique_paths
    p = generate_unique_paths(mock_pipeline_staged, ["text_in", "text_out"])
    datasets = {d.name: json.loads(d.config) for d in p.data_catalog}

    assert datasets["text_in"]["filepath"] != "./data/01_raw/text_in.csv"
    assert datasets["text_in"]["filepath"] == "./data/01_raw/{id}/text_in.csv".format(
        id=p.id)
    assert datasets["text_out"]["filepath"] != "./data/01_raw/text_out.csv"
    assert datasets["text_out"]["filepath"] == "./data/01_raw/{id}/text_out.csv".format(
        id=p.id)


def test_unique_paths_partitioned_datasests():
    from kedro_graphql.utils import generate_unique_paths
    from kedro_graphql.models import Pipeline, DataSet

    mock_pipeline = Pipeline(id="00000001", name="test_pipeline", data_catalog=[DataSet(
        name="partitioned_dataset",
        config=json.dumps({
            "type": "partitions.PartitionedDataset",
            "path": "./data/02_intermediate/partitioned_dataset",
            "filename_suffix": ".txt",
            "dataset": {
                "type": "text.TextDataset"
            }
        })
    )])

    p = generate_unique_paths(
        mock_pipeline, ["partitioned_dataset"])

    datasets = {d.name: json.loads(d.config) for d in p.data_catalog}

    assert datasets["partitioned_dataset"]["path"] != "./data/02_intermediate/partitioned_dataset"
    assert datasets["partitioned_dataset"]["path"] == "./data/02_intermediate/{id}/partitioned_dataset".format(
        id=p.id)
