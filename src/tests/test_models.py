import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from kedro_graphql.models import (
    DataSet,
    DataSetInput,
    DataSetPartitions,
    Node,
    Parameter,
    ParameterInput,
    ParameterType,
    Pipeline,
    PipelineInput,
    PipelineStatus,
    Pipelines,
    State,
    Tag,
    TagInput,
    parameter_inputs_from_mapping,
)
from .utilities import kedro_graphql_config


class TestDataSet:

    config = kedro_graphql_config()

    def test_serialize(self):
        params = {
            "name": "text_in",
            "config": json.dumps(
                {
                    "type": "text.TextDataset",
                    "filepath": "/tmp/test_in.csv",
                    "load_args": {"delimiter": "\t"},
                    "save_args": {"delimiter": "\t"},
                }
            ),
        }

        expected = {
            "text_in": {
                "type": "text.TextDataset",
                "filepath": "/tmp/test_in.csv",
                "load_args": {"delimiter": "\t"},
                "save_args": {"delimiter": "\t"},
            }
        }

        d = DataSet(**params)
        output = d.serialize()

        assert output == expected

    def test_does_exist_with_config(self, mock_text_in):
        params = {
            "name": "text_in",
            "config": f'{{"type": "text.TextDataset", "filepath": "{str(mock_text_in)}"}}',
        }

        d = DataSet(**params)
        assert d.exists() == True

    def test_does_not_exist_with_config(self):
        params = {
            "name": "text_in",
            "config": '{"type": "text.TextDataset", "filepath": "/tmp/does_not_exist.csv"}',
        }

        d = DataSet(**params)
        assert d.exists() == False

    def test_partitions(self):
        d = DataSet(
            name="test_partitioned_dataset",
            config=json.dumps(
                {
                    "type": "partitions.PartitionedDataset",
                    "path": str(Path("src/tests/data/partitioned_dataset/").resolve()),
                    "filename_suffix": ".txt",
                    "dataset": {"type": "text.TextDataset"},
                }
            ),
        )

        assert d.partitions() == ["part-0001", "part-0002"]


class TestParameterInput:

    def test_create_from_dict(self):
        correct = {
            "a": "b",
            "c": 0,
            "d": True,
            "e": 0.1,
        }

        incorrect = {**correct, "f": [1, 2]}

        params_input_list = parameter_inputs_from_mapping(correct)

        assert len(params_input_list) == 4
        assert any(p.name == "a" and p.value == "b" for p in params_input_list)
        assert (
            next(p for p in params_input_list if p.name == "c").type
            is ParameterType.INTEGER
        )
        assert (
            next(p for p in params_input_list if p.name == "d").type
            is ParameterType.BOOLEAN
        )

        with pytest.raises(ValueError):
            parameter_inputs_from_mapping(incorrect)


class TestParameter:

    def test_serialize_string(self):
        params = {"name": "delimiter", "value": "\t", "type": "string"}

        expected = {"delimiter": "\t"}

        p = Parameter.from_dict(params)
        output = p.serialize()
        assert output == expected

    def test_serialize_int(self):
        params = {"name": "delimiter", "value": "1", "type": "integer"}

        expected = {"delimiter": 1}

        p = Parameter.from_dict(params)
        output = p.serialize()
        assert output == expected

    def test_serialize_int_exception(self):
        params = {"name": "delimiter", "value": "0.1", "type": "integer"}

        p = Parameter.from_dict(params)
        try:
            output = p.serialize()
        except ValueError as e:
            assert True

    def test_serialize_float(self):
        params = {"name": "delimiter", "value": "0.1", "type": "float"}

        expected = {"delimiter": 0.1}

        p = Parameter.from_dict(params)
        output = p.serialize()
        assert output == expected

    def test_serialize_float_exception(self):
        params = {"name": "delimiter", "value": "hello", "type": "float"}

        p = Parameter.from_dict(params)
        try:
            output = p.serialize()
        except ValueError as e:
            assert True

    def test_serialize_bool(self):

        params = {"name": "delimiter", "value": "true", "type": "boolean"}

        expected = {"delimiter": True}

        p = Parameter.from_dict(params)
        output = p.serialize()
        assert output == expected

        params = {"name": "delimiter", "value": "True", "type": "boolean"}

        expected = {"delimiter": True}

        p = Parameter.from_dict(params)
        output = p.serialize()
        assert output == expected

        params = {"name": "delimiter", "value": "false", "type": "boolean"}

        expected = {"delimiter": False}

        p = Parameter.from_dict(params)
        output = p.serialize()
        assert output == expected

        params = {"name": "delimiter", "value": "False", "type": "boolean"}

        expected = {"delimiter": False}

        p = Parameter.from_dict(params)
        output = p.serialize()
        assert output == expected

    def test_serialize_bool_exception(self):

        params = {"name": "delimiter", "value": "rue", "type": "boolean"}

        p = Parameter.from_dict(params)
        try:
            output = p.serialize()
        except ValueError as e:
            assert True

    def test_dotlist_notation_to_omega_conf(self):
        """
        Tests serialized Parameter objects with dotlist notation names can be converted to OmegaConf
        which is used to construct the DataCatalog with the add_feed_dict method in tasks.py.
        """
        parameter_inputs = [
            {"name": "example", "value": "hello", "type": "string"},
            {"name": "duration", "value": "0.1", "type": "float"},
            {
                "name": "model_options.model_params.learning_date",
                "value": "2023-11-01",
                "type": "string",
            },
            {
                "name": "model_options.model_params.training_date",
                "value": "2023-11-01",
                "type": "string",
            },
            {
                "name": "model_options.model_params.data_ratio",
                "value": "14",
                "type": "float",
            },
            {"name": "data_options.step_size", "value": "123123", "type": "float"},
        ]

        parameters = [Parameter.from_dict(p) for p in parameter_inputs]

        serialized_parameters = {}

        for p in parameters:
            serialized_parameters.update(p.serialize())

        parameters_dotlist = [
            f"{key}={value}" for key, value in serialized_parameters.items()
        ]
        conf_parameters = OmegaConf.from_dotlist(parameters_dotlist)
        kedro_parameters = {"parameters": conf_parameters}

        assert kedro_parameters == {
            "parameters": {
                "example": "hello",
                "duration": 0.1,
                "model_options": {
                    "model_params": {
                        "learning_date": "2023-11-01",
                        "training_date": "2023-11-01",
                        "data_ratio": 14,
                    }
                },
                "data_options": {"step_size": 123123},
            }
        }

        params_dotlist = [
            f"params:{key}={value}" for key, value in serialized_parameters.items()
        ]
        kedro_params = OmegaConf.from_dotlist(params_dotlist)

        assert kedro_params == {
            "params:example": "hello",
            "params:duration": 0.1,
            "params:model_options": {
                "model_params": {
                    "learning_date": "2023-11-01",
                    "training_date": "2023-11-01",
                    "data_ratio": 14,
                }
            },
            "params:data_options": {"step_size": 123123},
        }

    def test_pipeline_encode_as_input(self, mock_pipeline_staged):
        """
        Tests the Pipeline.to_input() method returns a PipelineInput object
        """
        result = mock_pipeline_staged.to_input()
        assert isinstance(result, PipelineInput)
        assert result.name == mock_pipeline_staged.name
        assert len(result.data_catalog) == len(mock_pipeline_staged.data_catalog)
        assert len(result.parameters) == len(mock_pipeline_staged.parameters)
        assert len(result.tags) == len(mock_pipeline_staged.tags)

    def test_pipeline_input_preserves_editable_persisted_values(self):
        pipeline = Pipeline(
            name="example",
            data_catalog=[
                DataSet(
                    name="input",
                    config="{}",
                    tags=[Tag(key="kind", value="source")],
                )
            ],
            tags=[Tag(key="owner", value="platform")],
            parent="parent-id",
            status=[
                PipelineStatus(state=State.STAGED, runner="ParallelRunner"),
                PipelineStatus(state=State.READY, runner="ThreadRunner"),
            ],
            hooks=["audit", "metrics"],
        )

        result = pipeline.to_input()

        assert result.data_catalog[0].tags == [
            TagInput(key="kind", value="source")
        ]
        assert result.tags == [TagInput(key="owner", value="platform")]
        assert result.parent == "parent-id"
        assert result.runner == "ThreadRunner"
        assert result.hooks == ["audit", "metrics"]

    def test_pipeline_input_without_status_has_no_runner(self):
        result = Pipeline(name="example").to_input()

        assert result.runner is None


def test_pipeline_decode_normalizes_and_converts_declared_fields():
    payload = {
        "id": "pipeline-id",
        "name": "example",
        "createdAt": datetime(2026, 8, 7, 12),
        "hooks": ["logging"],
        "nodes": [{"name": "first", "inputs": ["in"], "outputs": ["out"], "tags": []}],
        "dataCatalog": [
            {"name": "in", "config": "{}", "tags": [{"key": "owner", "value": "data"}]}
        ],
        "parameters": [{"name": "count", "value": "1", "type": "INTEGER"}],
        "status": [
            {
                "state": "READY",
                "session": "session-id",
                "filteredNodes": ["first"],
                "abortRequestedAt": "2026-08-07T12:01:00",
            }
        ],
        "tags": [{"key": "owner", "value": "platform"}],
    }

    pipeline = Pipeline.from_dict(payload)

    assert pipeline.created_at == datetime(2026, 8, 7, 12, tzinfo=timezone.utc)
    assert pipeline.hooks == ["logging"]
    assert pipeline.nodes[0].name == "first"
    assert pipeline.data_catalog[0].tags[0].value == "data"
    assert pipeline.parameters[0].type.value == "integer"
    assert pipeline.status[0].state is State.READY
    assert pipeline.status[0].filtered_nodes == ["first"]
    assert pipeline.status[0].abort_requested_at == datetime(
        2026, 8, 7, 12, 1, tzinfo=timezone.utc
    )
    pipeline_input = PipelineInput(name="example", hooks=["logging"])
    assert Pipeline.from_input(pipeline_input).hooks == ["logging"]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"_id": "mongo-id", "name": "example"}, "Unknown Pipeline field.*_id"),
        ({"name": "example", "unexpected": True}, "Unknown Pipeline field.*unexpected"),
        (
            {"name": "example", "status": [{"state": "READY", "surprise": True}]},
            "Unknown PipelineStatus field.*surprise",
        ),
        (
            {"name": "example", "nodes": [{"name": "node", "mystery": True}]},
            "Unknown Node field.*mystery",
        ),
        (
            {
                "name": "example",
                "dataCatalog": [
                    {"name": "dataset", "config": "{}", "unknownField": True}
                ],
            },
            "Unknown DataSet field.*unknown_field",
        ),
        (
            {
                "name": "example",
                "parameters": [
                    {"name": "count", "value": "1", "unknownField": True}
                ],
            },
            "Unknown Parameter field.*unknown_field",
        ),
    ],
)
def test_pipeline_decode_rejects_unknown_fields(payload, message):
    with pytest.raises(ValueError, match=message):
        Pipeline.from_dict(payload)


def test_pipeline_decode_accepts_partial_nested_graphql_fields():
    pipeline = Pipeline.from_dict(
        {
            "name": "example",
            "nodes": [{"name": "node"}],
            "status": [{"state": "READY"}],
        }
    )

    assert pipeline.nodes == [Node(name="node", inputs=[], outputs=[], tags=[])]
    assert pipeline.status == [PipelineStatus(state=State.READY)]


def test_pipeline_from_input_deliberately_ignores_command_fields():
    pipeline = Pipeline.from_input(
        PipelineInput.from_dict(
            {
                "name": "example",
                "state": "READY",
                "runner": "ThreadRunner",
                "slices": [{"slice": "TAGS", "args": ["selected"]}],
                "onlyMissing": True,
            }
        )
    )

    assert pipeline == Pipeline(name="example")


def test_pipelines_decode_normalizes_page_and_pipeline_keys():
    pipelines = Pipelines.from_graphql(
        {
            "readPipelines": {
                "pageMeta": {"nextCursor": "cursor"},
                "pipelines": [
                    {"name": "example", "createdAt": "2026-08-07T08:00:00-04:00"}
                ],
            }
        }
    )

    assert pipelines.page_meta.next_cursor == "cursor"
    assert pipelines.pipelines[0].created_at == datetime(
        2026, 8, 7, 12, tzinfo=timezone.utc
    )


class TestDataSetInput:

    def test_encode(self):
        """
        Tests the DataSet.encode() method returns a DataSetInput object
        """
        dataset = DataSetInput(
            name="text_in",
            config=json.dumps(
                {
                    "type": "text.TextDataset",
                    "filepath": "/tmp/test_in.csv",
                    "load_args": {"delimiter": "\t"},
                    "save_args": {"delimiter": "\t"},
                }
            ),
        )

        result = dataset.to_graphql()
        assert isinstance(result, dict)
        assert result["name"] == dataset.name
        assert result["config"] == dataset.config

    def test_encode_list_partitions(self):
        dataset = DataSetInput(name="my_partitioned_dataset", list_partitions=True)

        result = dataset.to_graphql()
        assert isinstance(result, dict)
        assert result["name"] == dataset.name
        assert result["listPartitions"] is True


def test_pipeline_input_encodes_nested_dataset_fields_for_graphql():
    result = PipelineInput(
        name="example",
        data_catalog=[DataSetInput(name="dataset", list_partitions=True)],
    ).to_graphql()

    assert result["dataCatalog"][0]["listPartitions"] is True
    assert "list_partitions" not in result["dataCatalog"][0]


def test_collection_defaults_are_independent_and_null_payloads_are_normalized():
    first = PipelineInput(name="first")
    second = PipelineInput(name="second")
    first.tags.append(TagInput(key="owner", value="platform"))

    pipeline = Pipeline.from_dict({"name": "example", "tags": None, "nodes": None})

    assert second.tags == []
    assert pipeline.tags == []
    assert pipeline.nodes == []
