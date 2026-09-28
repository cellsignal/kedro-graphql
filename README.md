<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/light-logo.png">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/dark-logo.png">
    <img src="https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/light-logo.png" alt="KedroGraphQL Light Logo">
  </picture>
</p>

<!-- [![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/cellsignal/kedro-graphql) -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Latest Release](https://img.shields.io/pypi/v/kedro-graphql.svg)](https://pypi.org/project/kedro-graphql/)


**kedro-graphql** is a [kedro-plugin](https://docs.kedro.org/en/stable/extend_kedro/plugins.html) that adds powerful, production-ready features to any Kedro project by exposing your data pipelines as a secure and extensible GraphQL API.

`createPipeline` and `updatePipeline` accept `dryRun: true` to validate and return the projected pipeline response without saving it or submitting a task. The response uses the normal GraphQL field names (for example, `dataCatalog` and `createdAt`); a dry-run create has no `id`, so it cannot project `uniquePaths`.

API pipeline runs execute only hooks listed in the pipeline's `hooks` input and `always_hooks` configured for the API. Hook names are installed `kedro.hooks` entry-point names, such as `kedro-graphql-validation`; configure always-on hooks with `KEDRO_GRAPHQL_ALWAYS_HOOKS`.

## Why Use kedro-graphql?

Execution archives are owned by the worker. Set `KEDRO_GRAPHQL_LOG_PATH_PREFIX`
to a persistent directory or S3 prefix to write
`runs/<pipeline-id>/<task-id>/manifest.json` and `events.jsonl`.
The manifest records resolved configuration, selected nodes, versions, runner
metadata, and execution outcome. JSONL events retain structured log fields.
MongoDB remains authoritative for current pipeline status.

In 1.5.2.dev6, remove `kedro-graphql-logging` from configured and submitted hook
lists. Archiving no longer requires a hook or injects `gql_meta`/`gql_logs`
datasets. Historical archives can remain in storage. Mount persistent storage
for local archives and `KEDRO_GRAPHQL_LOG_TMP_DIR` so recovery files survive
worker replacement if an upload fails. The live `pipelineLogs` subscription
continues to expose messages and timestamps; the archive retains the full
structured records.

Events are spooled locally and uploaded once after the task's log handlers
close. An external cancellation can leave the manifest at `ABORTING` with no
`finished_at`; `worker_finished_at` only marks the worker's exit. Consult MongoDB
for the reconciled external result.

- **Unified API for Data Pipelines:** Interact with all your Kedro pipelines, datasets, and parameters through a single GraphQL endpoint with fllexible queries, mutations, and subscriptions—ideal for frontend, automation, and integration use cases.
- **Track & Audit Pipeline Runs:** Persist and track all pipeline executions, parameters, data catalogs, and results.
- **Distributed & Scalable Execution:** Offload pipeline runs to distributed workers with support for custom runners, enabling horizontal scaling and robust task management.
- **Event & Log Subscriptions:** Subscribe to real-time pipeline events and logs via GraphQL subscriptions for monitoring, automation, and integration.
- **Authentication & Authorization:** Secure your API with fine-grained, configurable permissions (including RBAC).
- **FAIR Data Principles:** kedro-graphql helps teams enable FAIR (Findable, Accessible, Interoperable, Reusable) data practices. Features such as flexible pipeline and dataset tagging make it easy to organize, discover, and reuse data assets and workflows across projects and teams. The project aims to deliver more capabilities in the near future such as a more a powerful search and a web user interface for controlling pipeline execution, dataset
exploration and visualization.

By leveraging kedro-graphql, teams can build robust, API first, data platforms, and integrate Kedro with modern cloud and enterprise systems.
