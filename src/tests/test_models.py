"""
This module contains an example test.

Tests should be placed in ``src/tests``, in modules that mirror your
project's structure, and in files named test_*.py. They are simply functions
named ``test_*`` which test a unit of logic.

To run the tests, run ``kedro test`` from the project root directory.
"""


import pytest
from kedro_graphql.models import DataSet, Parameter

class TestDataSet:

    def test_serialize(self):
        params = {"name": "text_in", 
                  "type": "text.TextDataSet", 
                  "filepath": "/tmp/test_in.csv",
                  "load_args":[Parameter(**{
                    "name": "delimiter",
                    "value": "\t" 
                  })],
                  "save_args":[Parameter(**{
                    "name":"delimiter",
                    "value": "\t"  
                  })]}

        expected = {"text_in":{ 
                      "type": "text.TextDataSet", 
                      "filepath": "/tmp/test_in.csv",
                      "load_args":{
                        "delimiter" :"\t" 
                      },
                      "save_args":{
                        "delimiter": "\t"  
                      },
                      "credentials": None
                    }
                   }

        d = DataSet(**params)
        output = d.serialize()
        print(output)
        assert output == expected
    
