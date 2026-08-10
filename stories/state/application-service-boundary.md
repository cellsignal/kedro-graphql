# LOCAL-001 state

- Agent: `/root/local_001_plan`
- Phase: complete
- Parent branch: `codex/architecture-hardening`
- Story branch: `codex/local-001-application-service-boundary`
- Worktree: `/home/icossentino/code/work/local-001-application-service-boundary`
- Base commit: `8bc35ea377b4ee24866116ad0cd4fbfd178d7217`
- Dependency status: ready; no prerequisites
- Plan: add a function-based `pipeline_service.py`; move create/update/abort/event orchestration out of Strawberry; keep GraphQL and REST as adapters; delete the internal GraphQL query builder and static query document
- Changed files: none
- Commits: `93e7f41e0376d40eafa93e5fd19058cbc6477370` (`refactor(pipelines): add application service boundary`)
- Checks: focused tests 31 passed; story full suite 121 passed with one expected Argo skip; parent combined suite 121 passed with one expected Argo skip; strict MkDocs, compileall, diff, obsolete-query, and secret checks passed
- Blocker: none; Redis and MongoDB were restored on 2026-08-10
- Blocker link: `stories/blockers/application-service-boundary.md`
- Pending Jira sync: none; batch is local-only
- Next action: none; dependent stories may use accepted parent commit `b035069`
- Resume action: if follow-up is required, fast-forward the story branch to the current parent before adding new commits

## Integration

- Accepted story commit: `93e7f41e0376d40eafa93e5fd19058cbc6477370`
- Parent integration commit: `b035069`
- Integrated locally only; no push, PR, deployment, or merge to `main`

## Owner decision

- Authorized implementation on 2026-08-10.
- `/event/` requires only the explicit `create_event` permission after GraphQL self-execution is removed.

## Latest checkpoint

- Current action: implementation and local story commit complete
- Active command: none
- Completed checks: 31 focused tests passed; full `src/tests` passed 121 with one expected Argo skip; strict MkDocs passed; `compileall` passed; diff and obsolete-query scans passed; secret review passed; story worktree clean
- Blocker: none
- ETA category: complete

## Expected changes

- Add: `src/kedro_graphql/pipeline_service.py`, `src/tests/test_pipeline_service.py`
- Modify: `src/kedro_graphql/schema.py`, `src/kedro_graphql/asgi.py`, `src/kedro_graphql/utils.py`, focused mutation/event tests
- Delete if confirmed unused: `src/kedro_graphql/static/queries.gql`, its empty directory, and `MANIFEST.in`
- Preserve: GraphQL mutation schema, dry runs, filepath extensions, hook selection, app factory, `AppServices`, client API, and `DataSet.config` JSON representation

## Effective authority

- Commit: orchestrator allowed
- Push: user authorization required
- PR: forbidden
- Merge to `main`: forbidden
- Deploy: user authorization required; no deployment is in scope
