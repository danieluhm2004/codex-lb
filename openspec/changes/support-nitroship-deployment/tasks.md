## 1. Docker entrypoint and Nitroship configuration

- [x] 1.1 Materialize non-empty environment keys before migrations with an owner-only creation mask, normalize 43-character unpadded keys, export the resolved key path, and remove the secret from child-process environments.
- [x] 1.2 Ship single-instance Nitroship compute settings and a deployment template requiring external PostgreSQL and generating a secret encryption key.
- [x] 1.3 Add deployment buttons beside both README Docker quick starts and document button and CLI operator flows.
- [x] 1.4 Add focused real-entrypoint subprocess regression coverage for exact key contents, permissions, explicit paths, sanitized environments, unset behavior, and padded/unpadded Fernet keys.
- [x] 1.5 Precompile stdlib, venv, and `app` bytecode in the root Dockerfile so cold starts fit Nitroship's 30 s readiness deadline.
- [x] 1.6 Generate a readable `CODEX_LB_DASHBOARD_BOOTSTRAP_TOKEN` in the deploy template, since Nitroship does not expose application logs.

## 2. Verification

- [x] 2.1 Run the focused entrypoint and existing launcher tests, touched-Python Ruff checks, shell syntax check, relevant simplicity budget check, strict change validation, and main-spec validation.
- [x] 2.2 Smoke-run the real entrypoint with fresh temporary filesystems and confirm the supplied key remains usable across restarts.
- [x] 2.3 Docker smoke with PostgreSQL: same unpadded key across two fresh containers reaches `/health/ready`; a fresh container without the key fails the fingerprint check; time-to-ready measured before/after bytecode precompilation.
