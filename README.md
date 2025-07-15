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

## Why Use kedro-graphql?

- **Unified API for Data Pipelines:** Interact with all your Kedro pipelines, datasets, and parameters through a single GraphQL endpoint with fllexible queries, mutations, and subscriptions—ideal for frontend, automation, and integration use cases.
- **Track & Audit Pipeline Runs:** Persist and track all pipeline executions, parameters, data catalogs, and results.
- **Distributed & Scalable Execution:** Offload pipeline runs to distributed workers with support for custom runners, enabling horizontal scaling and robust task management.
- **Event & Log Subscriptions:** Subscribe to real-time pipeline events and logs via GraphQL subscriptions for monitoring, automation, and integration.
- **Authentication & Authorization:** Secure your API with fine-grained, configurable permissions (including RBAC).
- **FAIR Data Principles:** kedro-graphql helps teams enable FAIR (Findable, Accessible, Interoperable, Reusable) data practices. Features such as flexible pipeline and dataset tagging make it easy to organize, discover, and reuse data assets and workflows across projects and teams. The project aims to deliver more capabilities in the near future such as a more a powerful search and a web user interface for controlling pipeline execution, dataset
exploration and visualization.

By leveraging kedro-graphql, teams can build robust, API first, data platforms, and integrate Kedro with modern cloud and enterprise systems.