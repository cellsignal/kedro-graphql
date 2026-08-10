# LOCAL-005 owner decisions

- Cause: security policy must be explicit before changing local transfer defaults and token validation.
- Affected phase: implementation authorization.
- Recommended secret policy: `local_file_provider_jwt_secret_key` defaults to `None`; local-provider startup rejects missing, blank, known-placeholder, or shorter-than-32-byte secrets.
- Recommended roots: download and upload roots default to empty lists; empty roots deny that direction; relative roots resolve once at startup.
- Recommended path policy: authorize resolved destinations; inside-root symlinks are allowed and escape symlinks denied. Concurrent symlink-swap protection using `openat`/`O_NOFOLLOW` is outside scope.
- Recommended upload policy: return `413` for actual streamed bytes over the limit; leave existing destination unchanged; remove temporary files on every failure.
- Recommended partition policy: explicit partitions are required for uploads for both providers.
- Recommended S3 ownership: close provider-created clients at shutdown; injected clients remain caller-owned.
- Open decision: add a JWT operation claim binding tokens to upload or download, or retain route-permission-only separation.
- Owner: user.
- Next action: confirm policies and authorize implementation.
- Jira: none; batch is local-only.
