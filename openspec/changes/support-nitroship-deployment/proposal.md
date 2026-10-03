## Why

Nitroship builds the root Dockerfile but provides neither persistent volumes nor secret files. With an external PostgreSQL database, losing the generated Fernet key on each fresh filesystem makes the startup fingerprint check reject the existing database. Operators need a stable encryption key supplied through Nitroship's environment configuration.

## What Changes

- Let the Docker shell entrypoint materialize `CODEX_LB_ENCRYPTION_KEY` into `CODEX_LB_ENCRYPTION_KEY_FILE` (default `/var/lib/codex-lb/encryption.key`) before migrations, with an owner-only creation mask, then remove the secret variable before launching Python processes. Restore Fernet padding for Nitroship's 43-character generated keys; already padded keys remain unchanged.
- Ship `nitroship.json` for `kr-icn`, HTTP port 2455, one always-on instance, `/health/ready` readiness checks, and a deployment template requiring external PostgreSQL and generating a secret encryption key plus a readable dashboard bootstrap token (Nitroship exposes build/system events, not application stdout, so the auto-generated token printed to logs is unreachable).
- Precompile Python bytecode in the root Dockerfile (`UV_COMPILE_BYTECODE=1` for the venv, `compileall` for the stdlib and `app`). The slim base image ships no stdlib bytecode and `PYTHONDONTWRITEBYTECODE=1` disables caching, so every start recompiled everything; measured time-to-ready dropped from ~26 s to ~12 s, inside Nitroship's 30 s readiness deadline.
- Add Deploy on Nitroship buttons beside the existing Docker quick starts, document button and CLI operator flows in this change's context, and cover entrypoint behavior with focused subprocess regression tests.

The new environment variable cannot have a default because it contains operator-owned secret material. It is consumed only when non-empty, so zero-configuration deployments retain their existing generated-key behavior. It is an entrypoint input, not a Settings field.

## Capabilities

### Modified Capabilities

- deployment-installation: Support environment-provided encryption keys in the Docker entrypoint and ship explicit Nitroship deployment settings.

## Impact

Only the Docker shell entrypoint, the root Dockerfile's bytecode step, root Nitroship configuration, README deployment buttons, regression coverage, and these change artifacts are affected. Settings, crypto implementation, and distroless launch paths remain unchanged. Nitroship remains a single-instance deployment; multi-replica deployments use Helm.
