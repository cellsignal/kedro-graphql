import pytest
from unittest.mock import MagicMock

from kedro.pipeline import Pipeline, node

from kedro_graphql.exceptions import InvalidPipeline
from kedro_graphql.pipeline_config import (
    filter_only_missing_pipeline,
    filter_pipeline,
    normalize_pipeline_config,
    validate_pipeline_config,
)


def identity(*values):
    return values[-1]


@pytest.fixture
def factory_pipeline():
    return Pipeline([
        node(identity, ["raw", "params:wanted"], "A_output", name="first"),
        node(identity, "A_output", "B_output", name="second"),
    ])


def test_normalize_pipeline_config_resolves_patterns_and_filters(factory_pipeline):
    catalog, parameters, sources = normalize_pipeline_config(
        factory_pipeline,
        {
            "raw": {"type": "MemoryDataset"},
            "{branch}_output": {
                "type": "pickle.PickleDataset",
                "filepath": "/tmp/{branch}.pkl",
            },
            "unrelated": {"type": "MemoryDataset"},
        },
        {"wanted": 1, "unrelated": 2},
    )

    assert set(catalog) == {"raw", "A_output", "B_output"}
    assert catalog["A_output"]["filepath"] == "/tmp/A.pkl"
    assert catalog["B_output"]["filepath"] == "/tmp/B.pkl"
    assert parameters == {"wanted": 1}
    assert sources["A_output"] == "{branch}_output"


def test_explicit_config_wins_over_pattern(factory_pipeline):
    catalog, _, sources = normalize_pipeline_config(
        factory_pipeline,
        {
            "raw": {"type": "MemoryDataset"},
            "A_output": {"type": "MemoryDataset"},
            "{branch}_output": {
                "type": "pickle.PickleDataset",
                "filepath": "/tmp/{branch}.pkl",
            },
        },
        {"wanted": 1},
    )

    assert catalog["A_output"] == {"type": "MemoryDataset"}
    assert sources["A_output"] == "A_output"


def test_sliced_validation_uses_only_selected_dag(factory_pipeline):
    selected = filter_pipeline(
        factory_pipeline, [{"slice": "node_names", "args": ["second"]}]
    )
    catalog = {
        "A_output": {
            "type": "pickle.PickleDataset",
            "filepath": "/tmp/A.pkl",
        }
    }

    # raw and params:wanted belong to the excluded node and are not required.
    validate_pipeline_config(selected, catalog, {})

    with pytest.raises(InvalidPipeline, match="A_output"):
        validate_pipeline_config(selected, {}, {})


def test_runner_can_reject_memory_datasets(factory_pipeline):
    selected = filter_pipeline(
        factory_pipeline, [{"slice": "node_names", "args": ["second"]}]
    )
    persistent = {
        name: {
            "type": "pickle.PickleDataset",
            "filepath": f"/tmp/{name}.pkl",
        }
        for name in ("A_output", "B_output")
    }
    validate_pipeline_config(selected, persistent, {}, supports_memory_datasets=False)

    with pytest.raises(InvalidPipeline, match="B_output"):
        validate_pipeline_config(
            selected,
            {**persistent, "B_output": {"type": "MemoryDataset"}},
            {},
            supports_memory_datasets=False,
        )


def test_only_missing_filter_is_isolated(factory_pipeline):
    catalog = MagicMock()
    catalog.list.return_value = ["raw", "A_output", "B_output"]
    catalog.exists.side_effect = lambda name: name != "B_output"

    filtered = filter_only_missing_pipeline(factory_pipeline, catalog)

    assert [pipeline_node.name for pipeline_node in filtered.nodes] == ["second"]
