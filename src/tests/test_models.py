import json

import pytest
from omegaconf import OmegaConf

from kedro_graphql.models import DataSet, Parameter


class TestDataSet:

    def test_serialize(self):
        params = {"name": "text_in",
                  "config": json.dumps({"type": "text.TextDataset",
                                        "filepath": "/tmp/test_in.csv",
                                        "load_args": {"delimiter": "\t"},
                                        "save_args": {"delimiter": "\t"}})
                  }

        expected = {"text_in": {
            "type": "text.TextDataset",
            "filepath": "/tmp/test_in.csv",
            "load_args": {
                "delimiter": "\t"
            },
            "save_args": {
                "delimiter": "\t"
            }
        }
        }

        d = DataSet(**params)
        output = d.serialize()

        assert output == expected

    def test_pre_signed_url_create_config_no_filepath(self):
        d = DataSet(name="text_in", config='{"type":"text.TextDataset"}')

        with pytest.raises(ValueError):
            output = d.pre_signed_url_create()

    def test_pre_signed_url_read_config_no_filepath(self):
        d = DataSet(name="text_in", config='{"type":"text.TextDataset"}')

        with pytest.raises(ValueError):
            output = d.pre_signed_url_read()

    def test_does_exist_with_config(self, mock_text_in):
        params = {
            "name": "text_in",
            "config": f'{{"type": "text.TextDataset", "filepath": "{str(mock_text_in)}"}}'
        }

        d = DataSet(**params)
        assert d.exists() == True

    def test_does_not_exist_with_config(self):
        params = {
            "name": "text_in",
            "config": '{"type": "text.TextDataset", "filepath": "/tmp/does_not_exist.csv"}'
        }

        d = DataSet(**params)
        assert d.exists() == False


class TestParameter:

    def test_serialize_string(self):
        params = {
            "name": "delimiter",
                    "value": "\t",
                    "type": "string"
        }

        expected = {
            "delimiter": "\t"
        }

        p = Parameter(**params)
        output = p.serialize()
        assert output == expected

    def test_serialize_int(self):
        params = {
            "name": "delimiter",
                    "value": "1",
                    "type": "integer"
        }

        expected = {
            "delimiter": 1
        }

        p = Parameter(**params)
        output = p.serialize()
        assert output == expected

    def test_serialize_int_exception(self):
        params = {
            "name": "delimiter",
                    "value": "0.1",
                    "type": "integer"
        }

        p = Parameter(**params)
        try:
            output = p.serialize()
        except ValueError as e:
            assert True

    def test_serialize_float(self):
        params = {
            "name": "delimiter",
                    "value": "0.1",
                    "type": "float"
        }

        expected = {
            "delimiter": 0.1
        }

        p = Parameter(**params)
        output = p.serialize()
        assert output == expected

    def test_serialize_float_exception(self):
        params = {
            "name": "delimiter",
                    "value": "hello",
                    "type": "float"
        }

        p = Parameter(**params)
        try:
            output = p.serialize()
        except ValueError as e:
            assert True

    def test_serialize_bool(self):

        params = {
            "name": "delimiter",
                    "value": "true",
                    "type": "boolean"
        }

        expected = {
            "delimiter": True
        }

        p = Parameter(**params)
        output = p.serialize()
        assert output == expected

        params = {
            "name": "delimiter",
                    "value": "True",
                    "type": "boolean"
        }

        expected = {
            "delimiter": True
        }

        p = Parameter(**params)
        output = p.serialize()
        assert output == expected

        params = {
            "name": "delimiter",
                    "value": "false",
                    "type": "boolean"
        }

        expected = {
            "delimiter": False
        }

        p = Parameter(**params)
        output = p.serialize()
        assert output == expected

        params = {
            "name": "delimiter",
                    "value": "False",
                    "type": "boolean"
        }

        expected = {
            "delimiter": False
        }

        p = Parameter(**params)
        output = p.serialize()
        assert output == expected

    def test_serialize_bool_exception(self):

        params = {
            "name": "delimiter",
                    "value": "rue",
                    "type": "boolean"
        }

        p = Parameter(**params)
        try:
            output = p.serialize()
        except ValueError as e:
            assert True

    def test_dotlist_notation_to_omega_conf(self):
        """
        Tests serialized Parameter objects with dotlist notation names can be converted to OmegaConf
        which is used to construct the DataCatalog with the add_feed_dict method in tasks.py.
        """
        parameter_inputs = [{"name": "example", "value": "hello", "type": "string"},
                            {"name": "duration", "value": "0.1", "type": "float"},
                            {"name": "model_options.model_params.learning_date", "value": "2023-11-01", "type": "string"},
                            {"name": "model_options.model_params.training_date", "value": "2023-11-01", "type": "string"},
                            {"name": "model_options.model_params.data_ratio", "value": "14", "type": "float"},
                            {"name": "data_options.step_size", "value": "123123", "type": "float"},
                            ]

        parameters = [Parameter.decode(p) for p in parameter_inputs]

        serialized_parameters = {}

        for p in parameters:
            serialized_parameters.update(p.serialize())

        parameters_dotlist = [f"{key}={value}" for key, value in serialized_parameters.items()]
        conf_parameters = OmegaConf.from_dotlist(parameters_dotlist)
        kedro_parameters = {"parameters": conf_parameters}

        assert kedro_parameters == {
            'parameters': {
                'example': 'hello',
                'duration': 0.1,
                'model_options': {
                    'model_params': {
                        'learning_date': '2023-11-01',
                        'training_date': '2023-11-01',
                        'data_ratio': 14
                    }
                },
                'data_options': {
                    'step_size': 123123
                }
            }
        }

        params_dotlist = [f"params:{key}={value}" for key, value in serialized_parameters.items()]
        kedro_params = OmegaConf.from_dotlist(params_dotlist)

        assert kedro_params == {
            'params:example': 'hello',
            'params:duration': 0.1,
            'params:model_options': {
                'model_params': {
                    'learning_date': '2023-11-01',
                    'training_date': '2023-11-01',
                    'data_ratio': 14
                }
            },
            'params:data_options': {
                'step_size': 123123
            }
        }
