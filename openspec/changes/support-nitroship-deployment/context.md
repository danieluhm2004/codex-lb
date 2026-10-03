# Nitroship deployment context

## Purpose and scope

Make the root Dockerfile route usable on [Nitroship](https://docs.nitroship.co) without changing application configuration or cryptography. The shell entrypoint converts an environment-provided Fernet key into the key file the application already expects; see the [delta requirements](specs/deployment-installation/spec.md).

## Constraints and decisions

- Nitroship has no persistent volumes. Use an external PostgreSQL database via `CODEX_LB_DATABASE_URL` and supply a stable `CODEX_LB_ENCRYPTION_KEY`; local SQLite and generated keys cannot survive a fresh filesystem.
- Keep the same key for the lifetime of the database. Losing or changing it causes the existing startup fingerprint enforcement to refuse that database and prevents decrypting stored credentials. Store a secure backup outside the deployment.
- `CODEX_LB_ENCRYPTION_KEY` is consumed only by `scripts/docker-entrypoint.sh`, not Settings or the distroless entrypoint. It has no default because secret material belongs to the operator. Unset or empty values preserve zero-config behavior.
- The Dockerfile already creates `/var/lib/codex-lb` for the runtime user. An explicit `CODEX_LB_ENCRYPTION_KEY_FILE` may override the default, but its parent directory must already exist and be writable. The entrypoint overwrites the file on startup using an owner-only creation mask, then removes the secret variable from child-process environments.
- Nitroship's template generator supplies 32 random bytes as 43-character unpadded base64url. The entrypoint appends one `=` for that length so Fernet accepts it. A conventional 44-character padded Fernet key is written unchanged.
- `nitroship.json` selects `kr-icn`, the available region, and port 2455 explicitly: otherwise the Dockerfile's `EXPOSE 2455 1455` lets Nitroship select the lower port, which is not the HTTP listener.
- Keep one always-on instance (`minInstances = maxInstances = 1`), rather than Nitroship's default 0–4 scaling. This avoids scale-to-zero and autoscaled replicas without bridge identity. Multi-replica deployment remains Helm-only; see the [deployment capability](../../specs/deployment-installation/spec.md).

## Deploy button flow

Use the Deploy on Nitroship button beside the README's Docker quick start. Pick your team and app slug, enter the external PostgreSQL URL, and retain the editable pre-generated secret encryption key. Copy the pre-generated `CODEX_LB_DASHBOARD_BOOTSTRAP_TOKEN`: Nitroship shows build/system events but not application stdout, so the auto-generated token codex-lb prints to logs is not reachable there. Nitroship then builds the root Dockerfile and deploys the app with the checked-in compute settings. Keep the generated key securely and reuse it when redeploying against the same database.

## CLI operator example

From the repository checkout, generate a Fernet key once using an environment with `cryptography` installed:

```sh
.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Keep this value securely and reuse it on every deployment. Create the app, enter the external PostgreSQL URL and generated key when prompted, and deploy:

```sh
ntro apps create codex-lb
ntro env add CODEX_LB_DATABASE_URL production --app codex-lb
ntro env add CODEX_LB_ENCRYPTION_KEY production --app codex-lb
ntro env add CODEX_LB_DASHBOARD_BOOTSTRAP_TOKEN production --app codex-lb --no-sensitive
ntro deploy . --app codex-lb --prod
```

After startup, open `https://codex-lb.ntro.run`, enter the `CODEX_LB_DASHBOARD_BOOTSTRAP_TOKEN` value to set the dashboard password (see [remote setup](../../../docs/getting-started.md#remote-setup-bootstrap-token)). Create [API keys](../../../docs/api-keys.md) for remote clients instead of leaving remote API access unauthenticated.

## Operational limits

External PostgreSQL and the stable key preserve database-backed state; they do not persist local archive or debug files. This change does not add volumes, modify Nitroship's rollout mechanics, or enable multi-replica bridge coordination.

Platform limits observed in the Nitroship source (operator/plan configurable):

- Readiness: HTTP GET on `healthPath` must succeed within 30 s of instance start; codex-lb runs migrations then app startup inside that window, hence the bytecode precompilation.
- Request bodies on compute routes are capped by the plan's function request limit (4,500,000 bytes on Free/Pro seeds); very large Codex payloads are rejected with 413 at the edge.
- Non-WebSocket requests (including SSE) end at the tier's max duration (300 s on `standard`). WebSocket connections live up to one hour and may be cut on redeploy; Codex clients reconnect.
- The container's TCP peer is the compute bridge gateway (not loopback), so codex-lb treats every request as remote: API keys and dashboard auth stay enforced.
- Rollout does not guarantee draining; in-flight streams can be cut when a new deployment replaces the instance.
