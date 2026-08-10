# Architecture hardening batch

## Batch contract

- Local-only batch: no Jira issue, Jira synchronization, remote story branch, or story PR.
- Proposed parent branch: `codex/architecture-hardening`.
- Parent base: `e7560e63fb3ec01670e18559b56e1045ec28187f` (`codex/feat-pipeline-hooks`).
- Each implementation story uses an isolated local worktree and commits locally.
- The orchestrator may commit and integrate accepted story branches locally.
- Pushes require user authorization. PR creation and merges to `main` are forbidden for this batch. Deployment remains user-controlled.
- No Kubernetes changes are in scope.
- Pivots replace superseded interfaces; do not add compatibility branches or deprecated wrappers.
- `DataSet.config` remains JSON text at the public and persistence boundaries.
- MongoDB is the only supported persistence implementation; the backend abstraction and backend-selection configuration are removed.

## Stories

| Story | Model/reasoning | Depends on | Primary ownership | Main overlap risk |
| --- | --- | --- | --- | --- |
| `LOCAL-001 application-service-boundary` | big/high | — | pipeline mutations and event ingestion | Establishes interfaces used by later stories |
| `LOCAL-002 execution-state-transitions` | big/xhigh | 001 | worker lifecycle and run status | `tasks.py`, pipeline service |
| `LOCAL-003 task-publication-subscriptions` | small/high | 002 | task IDs and subscriptions | worker submission and subscription resolvers |
| `LOCAL-004 mongo-storage-boundary` | big/xhigh | 003, 005 | concrete Mongo persistence for API and workers | app services, config, and Celery callbacks |
| `LOCAL-005 dataset-transfer-hardening` | big/high | 001 | uploads, downloads, signed URLs | `asgi.py`, dataset resolvers, config |
| `LOCAL-007 plugin-config-cleanup` | med/high | 004 | plugin discovery, CLI configuration | `config.py`, `asgi.py` after Mongo simplification |
| `LOCAL-008 experimental-surface-pruning` | small/medium | 007 | optional dependencies, UI startup, Argo | `pyproject.toml`, docs |
| `LOCAL-009 quality-gates` | med/high | 002–008 | test collection and CI gates | touches tests/config only after behavior settles |

## Implementation waves

1. Wave 1: `LOCAL-001`.
2. Wave 2: `LOCAL-002` and `LOCAL-005` in parallel. Their file ownership is deliberately separated by function; reconcile small application-service conflicts during parent integration.
3. Wave 3: `LOCAL-003`.
4. Wave 4: `LOCAL-004`.
5. Wave 5: `LOCAL-007`.
6. Wave 6: `LOCAL-008`.
7. Wave 7: `LOCAL-009`.

Planning-only agents may run for every dependency-ready story in a wave. Implementation requires a separate user authorization after their plans and overlap table have been reviewed.

## Local naming

- Branch: `codex/local-<number>-<slug>`
- Worktree: `~/code/work/local-<number>-<slug>`
- Runtime state: `stories/state/<slug>.md`, created only when the story launches
- Blocker record: `stories/blockers/<slug>.md`, created only when blocked

## Combined validation

After each accepted story is integrated, run its focused checks plus:

```bash
conda run -n abd pytest -q src/tests
conda run -n abd mkdocs build --strict
git diff --check
```

The bare repository-root `pytest` command is not the batch check because historical source archives below `data/tmp` can be collected as duplicate test packages.
