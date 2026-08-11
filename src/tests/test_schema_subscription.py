import pytest
import asyncio
import time


class TestSchemaSubscriptions:
    @pytest.mark.asyncio
    async def test_pipeline(self, mock_app, mock_info_context, mock_pipeline):
        """Requires Redis to run.
        """

        query = """
    	  subscription {
          	pipeline(id:""" + '"' + str(mock_pipeline.id) + '"' + """) {
              id
              taskId
              status
              result
              timestamp
              traceback
            }
    	  }
        """
        sub = await mock_app.state.services.schema.subscribe(query)

        async for result in sub:
            assert not result.errors

    @pytest.mark.asyncio
    async def test_pipeline_logs(self, mock_app, mock_info_context, mock_pipeline, mock_pipeline2):
        """Requires Redis to run.
        This test runs two pipelines simultaneously to ensure logs messages are scoped
        to the correct pipeline.

        """

        query = """
    	  subscription {
          	pipelineLogs(id:""" + '"' + str(mock_pipeline.id) + '"' + """) {
              id
              message
              messageId
              taskId
              time
            }
    	  }
        """

        sub = await mock_app.state.services.schema.subscribe(query)

        async for result in sub:
            assert not result.errors
            assert result.data["pipelineLogs"]["id"] == str(mock_pipeline.id)
            assert result.data["pipelineLogs"]["taskId"] == str(
                mock_pipeline.status[-1].task_id)

        query2 = """
    	  subscription {
          	pipelineLogs(id:""" + '"' + str(mock_pipeline2.id) + '"' + """) {
              id
              message
              messageId
              taskId
              time
            }
    	  }
        """

        sub2 = await mock_app.state.services.schema.subscribe(query2)

        async for result in sub2:
            assert not result.errors
            assert result.data["pipelineLogs"]["id"] == str(mock_pipeline2.id)
            assert result.data["pipelineLogs"]["taskId"] == str(
                mock_pipeline2.status[-1].task_id)

    @pytest.mark.asyncio
    async def test_pipeline_subscription_non_blocking(self, mock_app, mock_info_context, mock_pipeline, mock_pipeline2):
        """Test that pipeline subscriptions don't block the event loop.
        
        This test runs two pipeline subscriptions concurrently and verifies they execute
        in parallel rather than sequentially. If the subscriptions were blocking, they would
        run serially and take much longer.
        
        Requires Redis to run.
        """
        
        async def subscribe_to_pipeline(pipeline_id):
            """Helper to subscribe to a single pipeline and collect events."""
            query = """
              subscription {
                pipeline(id:""" + '"' + str(pipeline_id) + '"' + """) {
                  id
                  taskId
                  status
                  result
                  timestamp
                  traceback
                }
              }
            """
            events = []
            start_time = time.time()
            
            sub = await mock_app.state.services.schema.subscribe(query)
            async for result in sub:
                assert not result.errors
                events.append(result.data["pipeline"])
                
            elapsed = time.time() - start_time
            return {"pipeline_id": pipeline_id, "events": events, "elapsed": elapsed}
        
        # Run both subscriptions concurrently
        start_time = time.time()
        results = await asyncio.gather(
            subscribe_to_pipeline(mock_pipeline.id),
            subscribe_to_pipeline(mock_pipeline2.id)
        )
        total_elapsed = time.time() - start_time
        
        # Verify both subscriptions completed
        assert len(results) == 2
        assert all(len(r["events"]) > 0 for r in results)
        
        # Verify the subscriptions ran concurrently (not sequentially)
        # If they ran sequentially, total time would be sum of individual times
        # If they ran concurrently, total time should be close to the max of individual times
        individual_times_sum = sum(r["elapsed"] for r in results)
        max_individual_time = max(r["elapsed"] for r in results)
        
        # Total elapsed time should be much closer to max individual time than to sum
        # This indicates concurrent execution. Allow some overhead tolerance.
        assert total_elapsed < individual_times_sum * 0.75, \
            f"Subscriptions appear to be blocking. Total time ({total_elapsed:.2f}s) " \
            f"is too close to sequential execution time ({individual_times_sum:.2f}s). " \
            f"Expected closer to max individual time ({max_individual_time:.2f}s)."
        
        # Verify we got events for both pipelines
        pipeline_ids = {r["events"][0]["id"] for r in results}
        assert str(mock_pipeline.id) in pipeline_ids
        assert str(mock_pipeline2.id) in pipeline_ids

    @pytest.mark.asyncio
    async def test_pipeline_subscription_high_concurrency(self, mock_app, mock_info_context, mock_pipeline, mock_pipeline2):
        """Test that many concurrent pipeline subscriptions don't block each other.
        
        This test simulates a more realistic scenario with multiple clients
        connecting simultaneously. If blocking occurs, we'll see significantly
        degraded performance.
        
        Requires Redis to run.
        """
        
        async def subscribe_and_count(pipeline_id, subscription_num):
            """Subscribe and count events received."""
            query = """
              subscription {
                pipeline(id:""" + '"' + str(pipeline_id) + '"' + """, interval: 0.1) {
                  id
                  status
                }
              }
            """
            count = 0
            start_time = time.time()
            
            sub = await mock_app.state.services.schema.subscribe(query)
            async for result in sub:
                assert not result.errors
                count += 1
                
            elapsed = time.time() - start_time
            return {"subscription": subscription_num, "count": count, "elapsed": elapsed}
        
        # Run 6 concurrent subscriptions (3 per pipeline)
        start_time = time.time()
        results = await asyncio.gather(
            subscribe_and_count(mock_pipeline.id, 1),
            subscribe_and_count(mock_pipeline.id, 2),
            subscribe_and_count(mock_pipeline.id, 3),
            subscribe_and_count(mock_pipeline2.id, 4),
            subscribe_and_count(mock_pipeline2.id, 5),
            subscribe_and_count(mock_pipeline2.id, 6),
        )
        total_elapsed = time.time() - start_time
        
        # All subscriptions should complete
        assert len(results) == 6
        assert all(r["count"] > 0 for r in results)
        
        # With true concurrency, total time should not scale linearly with number of subscriptions
        # If blocking, 6 subscriptions would take ~6x the time of 1 subscription
        # With concurrency, should take approximately the same as 1 subscription (plus overhead)
        individual_times_sum = sum(r["elapsed"] for r in results)
        max_individual_time = max(r["elapsed"] for r in results)
        
        # Total time should be MUCH less than sum (indicates parallel execution)
        # Allow for some overhead but should be closer to max than to sum
        assert total_elapsed < individual_times_sum * 0.5, \
            f"High concurrency test suggests blocking. Total time ({total_elapsed:.2f}s) " \
            f"is too high compared to sequential time ({individual_times_sum:.2f}s). " \
            f"With {len(results)} concurrent subscriptions, expected ~{max_individual_time:.2f}s."

    @pytest.mark.asyncio
    async def test_pipeline_logs_subscription_non_blocking(self, mock_app, mock_info_context, mock_pipeline, mock_pipeline2):
        """Test that pipeline_logs subscriptions don't block the event loop.
        
        This test runs two pipeline_logs subscriptions concurrently and verifies they execute
        in parallel rather than sequentially. If the subscriptions were blocking, they would
        run serially and take much longer.
        
        Requires Redis to run.
        """
        
        async def subscribe_to_pipeline_logs(pipeline_id):
            """Helper to subscribe to a single pipeline's logs and collect messages."""
            query = """
              subscription {
                pipelineLogs(id:""" + '"' + str(pipeline_id) + '"' + """) {
                  id
                  message
                  messageId
                  taskId
                  time
                }
              }
            """
            messages = []
            start_time = time.time()
            
            sub = await mock_app.state.services.schema.subscribe(query)
            async for result in sub:
                assert not result.errors
                messages.append(result.data["pipelineLogs"])
                
            elapsed = time.time() - start_time
            return {"pipeline_id": pipeline_id, "messages": messages, "elapsed": elapsed}
        
        # Run both subscriptions concurrently
        start_time = time.time()
        results = await asyncio.gather(
            subscribe_to_pipeline_logs(mock_pipeline.id),
            subscribe_to_pipeline_logs(mock_pipeline2.id)
        )
        total_elapsed = time.time() - start_time
        
        # Verify both subscriptions completed
        assert len(results) == 2
        assert all(len(r["messages"]) > 0 for r in results)
        
        # Verify the subscriptions ran concurrently (not sequentially)
        # If they ran sequentially, total time would be sum of individual times
        # If they ran concurrently, total time should be close to the max of individual times
        individual_times_sum = sum(r["elapsed"] for r in results)
        max_individual_time = max(r["elapsed"] for r in results)
        
        # Total elapsed time should be much closer to max individual time than to sum
        # This indicates concurrent execution. Allow some overhead tolerance.
        assert total_elapsed < individual_times_sum * 0.75, \
            f"Pipeline logs subscriptions appear to be blocking. Total time ({total_elapsed:.2f}s) " \
            f"is too close to sequential execution time ({individual_times_sum:.2f}s). " \
            f"Expected closer to max individual time ({max_individual_time:.2f}s)."
        
        # Verify we got log messages for both pipelines with correct pipeline IDs
        pipeline_ids = {r["messages"][0]["id"] for r in results}
        assert str(mock_pipeline.id) in pipeline_ids
        assert str(mock_pipeline2.id) in pipeline_ids
        
        # Verify task IDs match the pipeline task IDs
        for result in results:
            pipeline_id = result["pipeline_id"]
            task_id = result["messages"][0]["taskId"]
            if str(pipeline_id) == str(mock_pipeline.id):
                assert task_id == str(mock_pipeline.status[-1].task_id)
            else:
                assert task_id == str(mock_pipeline2.status[-1].task_id)

    @pytest.mark.asyncio
    async def test_event_loop_responsiveness_during_subscriptions(self, mock_app, mock_info_context, mock_pipeline, mock_pipeline2):
        """Test that the event loop remains responsive during active subscriptions.
        
        This test runs subscriptions and simultaneously checks if the event loop
        can handle other async tasks. If subscriptions block, other tasks will be delayed.
        
        Requires Redis to run.
        """
        
        # Track when simple tasks complete
        task_completion_times = []
        
        async def simple_task(task_num, delay=0.1):
            """A simple async task that should complete quickly if event loop is free."""
            start = time.time()
            await asyncio.sleep(delay)
            completion_time = time.time() - start
            task_completion_times.append({
                "task": task_num,
                "expected_delay": delay,
                "actual_delay": completion_time
            })
        
        async def subscribe_to_pipeline(pipeline_id):
            """Subscribe to pipeline events."""
            query = """
              subscription {
                pipeline(id:""" + '"' + str(pipeline_id) + '"' + """, interval: 0.1) {
                  id
                  status
                }
              }
            """
            count = 0
            sub = await mock_app.state.services.schema.subscribe(query)
            async for result in sub:
                assert not result.errors
                count += 1
            return count
        
        # Start subscriptions and simple tasks concurrently
        # If subscriptions block, simple tasks will take much longer than expected
        await asyncio.gather(
            subscribe_to_pipeline(mock_pipeline.id),
            subscribe_to_pipeline(mock_pipeline2.id),
            simple_task(1, 0.1),
            simple_task(2, 0.2),
            simple_task(3, 0.3),
            simple_task(4, 0.1),
            simple_task(5, 0.2),
        )
        
        # Verify all simple tasks completed
        assert len(task_completion_times) == 5
        
        # Check that simple tasks completed close to their expected time
        # If the event loop was blocked, delays would be much longer
        for task_info in task_completion_times:
            # Allow 50% overhead for task scheduling and other async operations
            # If blocking occurs, delays would be 2x-10x longer
            max_acceptable_delay = task_info["expected_delay"] * 1.5
            assert task_info["actual_delay"] < max_acceptable_delay, \
                f"Task {task_info['task']} took {task_info['actual_delay']:.3f}s " \
                f"when it should have taken ~{task_info['expected_delay']:.3f}s. " \
                f"This suggests the event loop was blocked by subscriptions."

    @pytest.mark.asyncio
    async def test_pipeline_logs_subscription_high_concurrency(self, mock_app, mock_info_context, mock_pipeline, mock_pipeline2):
        """Test high concurrency scenario with 6 concurrent log subscriptions.
        
        This is a more robust test that simulates realistic high-load conditions.
        If any blocking occurs, it will be more apparent with more concurrent connections.
        
        Requires Redis to run.
        """
        
        async def subscribe_to_pipeline_logs(pipeline_id, sub_num):
            """Helper to subscribe to a single pipeline's logs and collect messages."""
            query = """
              subscription {
                pipelineLogs(id:""" + '"' + str(pipeline_id) + '"' + """) {
                  id
                  message
                  messageId
                  taskId
                  time
                }
              }
            """
            messages = []
            start_time = time.time()
            
            sub = await mock_app.state.services.schema.subscribe(query)
            async for result in sub:
                assert not result.errors
                messages.append(result.data["pipelineLogs"])
                
            elapsed = time.time() - start_time
            return {
                "sub_num": sub_num,
                "pipeline_id": pipeline_id,
                "messages": messages,
                "elapsed": elapsed
            }
        
        # Run 6 subscriptions concurrently (3 for each pipeline)
        start_time = time.time()
        results = await asyncio.gather(
            subscribe_to_pipeline_logs(mock_pipeline.id, 1),
            subscribe_to_pipeline_logs(mock_pipeline.id, 2),
            subscribe_to_pipeline_logs(mock_pipeline.id, 3),
            subscribe_to_pipeline_logs(mock_pipeline2.id, 4),
            subscribe_to_pipeline_logs(mock_pipeline2.id, 5),
            subscribe_to_pipeline_logs(mock_pipeline2.id, 6),
        )
        total_elapsed = time.time() - start_time
        
        # Verify all subscriptions completed
        assert len(results) == 6
        assert all(len(r["messages"]) > 0 for r in results)
        
        # Calculate timing metrics
        individual_times_sum = sum(r["elapsed"] for r in results)
        max_individual_time = max(r["elapsed"] for r in results)
        avg_individual_time = individual_times_sum / len(results)
        
        # With 6 concurrent subscriptions, if they run truly in parallel,
        # total time should be close to max individual time.
        # If blocking occurs, total time approaches sum of all times.
        # Use stricter threshold for high concurrency test
        assert total_elapsed < individual_times_sum * 0.5, \
            f"High concurrency log subscription test shows blocking behavior. " \
            f"Total time: {total_elapsed:.2f}s, " \
            f"Sum of individual times: {individual_times_sum:.2f}s, " \
            f"Max individual time: {max_individual_time:.2f}s, " \
            f"Avg individual time: {avg_individual_time:.2f}s. " \
            f"Expected total time close to max ({max_individual_time:.2f}s), " \
            f"but got {total_elapsed:.2f}s which is too close to sequential execution."
        
        # Verify we got messages for both pipelines
        pipeline_ids = {r["messages"][0]["id"] for r in results}
        assert str(mock_pipeline.id) in pipeline_ids
        assert str(mock_pipeline2.id) in pipeline_ids
        
        # Verify task IDs are correct for each pipeline
        for result in results:
            pipeline_id = result["pipeline_id"]
            task_id = result["messages"][0]["taskId"]
            if str(pipeline_id) == str(mock_pipeline.id):
                assert task_id == str(mock_pipeline.status[-1].task_id)
            else:
                assert task_id == str(mock_pipeline2.status[-1].task_id)
