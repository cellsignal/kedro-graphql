import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import fsspec

from kedro_graphql.archived_logs import (
    ArchiveAvailability, _cursor, _offset, _read_chunk, pipeline_archived_logs,
)
from kedro_graphql.exceptions import InvalidPipeline
from kedro_graphql.models import PipelineStatus, State


class ArchiveChunkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.prefix = self.temp.name
        self.path = Path(self.prefix) / 'runs/pipeline/task/events.jsonl'
        self.path.parent.mkdir(parents=True)

    def test_tail_and_earlier_pages_cover_utf8_records_once(self):
        records = [json.dumps({'message': f'{i}: α🙂'}, ensure_ascii=False) for i in range(100)]
        self.path.write_text('\n'.join(records) + '\n')
        pages = []
        offset = None
        while True:
            chunk = _read_chunk(self.prefix, 'pipeline', 'task', offset, 91)
            self.assertLessEqual(len(chunk.text.encode()), 91)
            pages.insert(0, chunk.text.splitlines())
            if not chunk.earlier_cursor:
                break
            offset = _offset(chunk.earlier_cursor, 'pipeline', 'task')
        self.assertEqual([line for page in pages for line in page], records)

    def test_memory_storage_uses_the_same_seekable_read(self):
        fs = fsspec.filesystem('memory')
        fs.pipe('/archive-test/runs/pipeline/task/events.jsonl', b'{"message":"done"}\n')
        self.addCleanup(fs.rm, '/archive-test', recursive=True)
        self.assertIn('done', _read_chunk('memory:///archive-test', 'pipeline', 'task', None, 65536).text)

    def test_s3_reader_seeks_and_never_reads_the_entire_object(self):
        import io
        content = b'{"message":"log"}\n' * 10000
        stream = Mock(wraps=io.BytesIO(content))
        context = Mock()
        context.__enter__ = Mock(return_value=stream)
        context.__exit__ = Mock(return_value=False)
        fs = Mock()
        fs.size.return_value = len(content)
        fs.open.return_value = context
        with patch('kedro_graphql.archived_logs.fsspec.core.url_to_fs', return_value=(fs, 'bucket/logs')):
            chunk = _read_chunk('s3://bucket/logs', 'pipeline', 'task', None, 65536)
        fs.open.assert_called_once_with('bucket/logs/runs/pipeline/task/events.jsonl', 'rb', block_size=65536)
        stream.seek.assert_called_once_with(len(content) - 65536)
        stream.read.assert_called_once_with(65536)
        self.assertEqual(chunk.availability, ArchiveAvailability.AVAILABLE)

    def test_malformed_and_oversized_content_is_bounded(self):
        self.path.write_bytes(b'{"message":"' + b'x' * 5000 + b'"}\ninvalid\n{"message":"last"}\n')
        chunk = _read_chunk(self.prefix, 'pipeline', 'task', None, 80)
        self.assertTrue(chunk.skipped_content)
        self.assertIn('last', chunk.text)
        self.assertLessEqual(len(chunk.text.encode()), 80)
        self.assertIsNotNone(chunk.earlier_cursor)

    def test_cursor_is_bound_to_pipeline_and_attempt(self):
        token = _cursor('pipeline', 'task', 42)
        self.assertEqual(_offset(token, 'pipeline', 'task'), 42)
        for pipeline, task in [('other', 'task'), ('pipeline', 'other')]:
            with self.assertRaises(InvalidPipeline):
                _offset(token, pipeline, task)
        for token in ['bad', _cursor('pipeline', 'task', -1), 'x' * 1025]:
            with self.assertRaises(InvalidPipeline):
                _offset(token, 'pipeline', 'task')

    def test_invalid_offsets_and_path_segments_are_rejected(self):
        self.path.write_bytes(b'{}\n')
        with self.assertRaises(InvalidPipeline):
            _read_chunk(self.prefix, 'pipeline', 'task', 900, 64)
        with self.assertRaises(ValueError):
            _read_chunk(self.prefix, '../outside', 'task', None, 64)


class ArchiveQueryTests(unittest.IsolatedAsyncioTestCase):
    def services(self, state=State.SUCCESS, task='task'):
        status = PipelineStatus(state=state, task_id=task)
        pipeline = SimpleNamespace(id='pipeline', current_status=status)
        return SimpleNamespace(backend=SimpleNamespace(read=AsyncMock(return_value=pipeline)),
                               config=SimpleNamespace(log_path_prefix='/archives'))

    async def test_missing_or_unreadable_archive_is_not_a_query_failure(self):
        for error, availability in [(FileNotFoundError(), ArchiveAvailability.UNAVAILABLE),
                                    (PermissionError('secret details'), ArchiveAvailability.UNREADABLE)]:
            with patch('kedro_graphql.archived_logs._read_chunk', side_effect=error):
                result = await pipeline_archived_logs(self.services(), 'pipeline')
            self.assertEqual(result.availability, availability)
            self.assertNotIn('secret', result.message)

    async def test_active_and_taskless_runs_do_not_access_storage(self):
        with patch('kedro_graphql.archived_logs._read_chunk') as read:
            for services in [self.services(State.STARTED), self.services(task=None)]:
                self.assertEqual((await pipeline_archived_logs(services, 'pipeline')).availability,
                                 ArchiveAvailability.UNAVAILABLE)
            read.assert_not_called()

    async def test_query_limits_and_missing_pipeline(self):
        for size in [0, 262145]:
            with self.assertRaises(InvalidPipeline):
                await pipeline_archived_logs(self.services(), 'pipeline', max_bytes=size)
        services = self.services()
        services.backend.read.return_value = None
        with self.assertRaises(InvalidPipeline):
            await pipeline_archived_logs(services, 'missing')

    async def test_blocking_storage_runs_off_event_loop(self):
        import threading
        main = threading.get_ident()
        def read(*args):
            self.assertNotEqual(threading.get_ident(), main)
            return 'result'
        with patch('kedro_graphql.archived_logs._read_chunk', side_effect=read):
            self.assertEqual(await pipeline_archived_logs(self.services(), 'pipeline'), 'result')

    async def test_query_requires_pipeline_and_log_permissions(self):
        from kedro_graphql.schema import Query
        field = next(field for field in Query.__strawberry_definition__.fields
                     if field.python_name == 'pipeline_archived_logs')
        self.assertEqual([permission.action for permission in field.extensions[0].permissions],
                         ['read_pipeline', 'subscribe_to_logs'])


    async def test_full_download_signs_all_terminal_states_without_reading_chunks(self):
        from kedro_graphql.archived_logs import pipeline_log_download
        from kedro_graphql.models import SignedUrl
        for state in [State.SUCCESS, State.FAILURE, State.ABORTED, State.REVOKED]:
            services = self.services(state)
            services.config.log_path_prefix = 's3://bucket/logs/'
            services.config.signed_url_max_expires_in_sec = 3600
            signed = SignedUrl(url='https://example.invalid/log', file='events.jsonl')
            with patch('kedro_graphql.signed_url.s3_provider.S3Provider.presigned_url', return_value=signed) as signer, patch('kedro_graphql.archived_logs._read_chunk') as reader:
                self.assertIs(await pipeline_log_download(services, None, 'pipeline'), signed)
                signer.assert_called_once_with('s3://bucket/logs/runs/pipeline/task/events.jsonl', 300, 'pipeline-task.jsonl')
                reader.assert_not_called()

    async def test_active_download_is_rejected_before_storage_access(self):
        from kedro_graphql.archived_logs import pipeline_log_download
        with patch('kedro_graphql.signed_url.s3_provider.S3Provider.presigned_url') as signer:
            with self.assertRaises(InvalidPipeline):
                await pipeline_log_download(self.services(State.STARTED), None, 'pipeline')
            signer.assert_not_called()

    async def test_download_requires_pipeline_and_log_permissions(self):
        from kedro_graphql.schema import Query
        field = next(field for field in Query.__strawberry_definition__.fields if field.python_name == 'pipeline_log_download')
        self.assertEqual([permission.action for permission in field.extensions[0].permissions], ['read_pipeline', 'subscribe_to_logs'])
