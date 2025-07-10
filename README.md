<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/light-logo.png">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/dark-logo.png">
    <img src="https://raw.githubusercontent.com/cellsignal/kedro-graphql/refs/heads/main/docs/light-logo.png" alt="KedroGraphQL Light Logo">
  </picture>
</p>

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/cellsignal/kedro-graphql)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Latest Release](https://img.shields.io/pypi/v/kedro-graphql.svg)](https://pypi.org/project/kedro-graphql/)

## Overview

Kedro-graphql is a [kedro-plugin](https://docs.kedro.org/en/stable/extend_kedro/plugins.html)
for serving kedro projects as a graphql api.  It leverages
[Strawberry](https://strawberry.rocks/), [FastAPI](https://fastapi.tiangolo.com/),
and [Celery](https://docs.celeryq.dev/en/stable/index.html) to turn any
 [Kedro](https://docs.kedro.org/en/stable/) project into a GraphqlQL api
 with features such as:

- a distributed task queue
- subscribe to pipline events and logs via GraphQL subscriptions
- storage
  - persist and track all pipelines executed via the API

```mermaid
flowchart  TB
  api[GraphQL API<br/><i>strawberry + FastAPI</i>]
  mongodb[(db: 'pipelines'<br/>collection: 'pipelines'<br/><i>mongoDB</i>)]
  redis[(task queue<br/><i>redis</i>)]
  worker[worker<br/><i>celery</i>]

  api<-->mongodb
  api<-->redis
  worker<-->mongodb
  worker<-->redis

```

Figure 1. Architecture
