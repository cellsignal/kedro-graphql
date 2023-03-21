broker_url = 'redis://localhost'
result_backend = 'redis://localhost'
result_extended = True

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
enable_utc = True


worker_send_task_events = True
task_send_sent_event = True
imports = "kedro_graphql.tasks"