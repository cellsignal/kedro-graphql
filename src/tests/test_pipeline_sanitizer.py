import pytest
from kedro_graphql.schema import PipelineSanitizer, DataSetConfigException
from kedro_graphql.models import PipelineInput
import json


class TestSchemaExtensions:

    @pytest.mark.asyncio
    async def test_pipeline_sanitizer_mask_filepaths(self, mock_pipeline_staged):
        """
         Test that the kedro_graphql.schema.PipelineSanitizer correctly masks filepaths in a PipelineInput's data catalog.
        """
        result = mock_pipeline_staged.encode(encoder="input")
        assert isinstance(result, PipelineInput)

        masks = [{"prefix": "./data/", "mask": "./REDACTED/"}]
        masked = PipelineSanitizer.mask_filepaths(result, masks)
        for d in masked.data_catalog:
            c = json.loads(d.config)
            if c.get("filepath"):
                assert not c["filepath"].startswith("./data/")
                assert c["filepath"].startswith("./REDACTED/")

    @pytest.mark.asyncio
    async def test_pipeline_sanitizer_unmask_filepaths(self, mock_pipeline_staged):
        """
         Test that the kedro_graphql.schema.PipelineSanitizer correctly unmasks filepaths in a PipelineInput's data catalog.
        """
        result = mock_pipeline_staged.encode(encoder="input")
        assert isinstance(result, PipelineInput)

        masks = [{"prefix": "./data/", "mask": "./REDACTED/"}]
        masked = PipelineSanitizer.mask_filepaths(result, masks)
        unmasked = PipelineSanitizer.unmask_filepaths(masked, masks)
        for d in unmasked.data_catalog:
            c = json.loads(d.config)
            if c.get("filepath"):
                assert not c["filepath"].startswith("./REDACTED/")
                assert c["filepath"].startswith("./data/")

    @pytest.mark.asyncio
    async def test_pipeline_sanitizer_sanitize_filepaths(self, mock_pipeline_staged):
        """
         Test that the kedro_graphql.schema.PipelineSanitizer correctly validates filepaths in a PipelineInput's data catalog against allowed prefixes.
        """
        result = mock_pipeline_staged.encode(encoder="input")
        assert isinstance(result, PipelineInput)
        allowed_roots = ["./data/"]
        sanitized = PipelineSanitizer.sanitize_filepaths(result, allowed_roots)

        allowed_roots = ["./tmp/"]
        try:
            sanitized = PipelineSanitizer.sanitize_filepaths(result, allowed_roots)
        except DataSetConfigException as e:
            assert "filepath ./data/01_raw/text_in.csv not allowed" in str(e)
