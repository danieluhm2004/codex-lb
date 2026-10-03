## ADDED Requirements

### Requirement: Docker entrypoint materializes the encryption key from the environment

When `CODEX_LB_ENCRYPTION_KEY` is non-empty, the Docker shell entrypoint SHALL write its contents without a trailing newline to the resolved key file (`CODEX_LB_ENCRYPTION_KEY_FILE` when non-empty, otherwise `/var/lib/codex-lb/encryption.key`) with owner-only permissions before migrations. The entrypoint SHALL append one `=` when the supplied key is exactly 43 characters, restoring padding for Nitroship's generated base64url keys, and SHALL write already padded 44-character Fernet keys unchanged. The entrypoint SHALL remove `CODEX_LB_ENCRYPTION_KEY` from the environment of the migration and application processes and SHALL export the resolved `CODEX_LB_ENCRYPTION_KEY_FILE` to both processes. When the key variable is unset or empty, the entrypoint SHALL leave existing key-file and generated-key behavior unchanged.

#### Scenario: Key provided across fresh-filesystem restarts

- **GIVEN** an operator supplies the same non-empty `CODEX_LB_ENCRYPTION_KEY` on each restart
- **AND** the container filesystem is fresh on each restart
- **WHEN** the Docker entrypoint starts migrations and the application
- **THEN** the resolved key file contains the same exact key with owner-only permissions before either Python process starts
- **AND** both processes receive the resolved key-file path but not the secret key variable

#### Scenario: Nitroship generates an unpadded encryption key

- **GIVEN** Nitroship's deployment template supplies a 43-character unpadded base64url key
- **WHEN** the Docker entrypoint materializes the key before migrations
- **THEN** the file contains the supplied key followed by one `=`, without a newline
- **AND** the file contents are a valid Fernet key

#### Scenario: Existing generated-key behavior when unset

- **GIVEN** `CODEX_LB_ENCRYPTION_KEY` is unset
- **WHEN** the Docker entrypoint starts
- **THEN** it does not write a key file or introduce a key-file environment override
- **AND** the existing application behavior loads or generates its encryption key as before

### Requirement: Repository ships a Nitroship deployment config

The repository MUST ship a root `nitroship.json` that selects region `kr-icn`, pins the HTTP port to 2455, sets exactly one instance (`minInstances` and `maxInstances` both 1), and sets the health path to `/health/ready`. Its `template.env` MUST declare `CODEX_LB_DATABASE_URL` as required and secret, `CODEX_LB_ENCRYPTION_KEY` as a required, generated, secret string, and `CODEX_LB_DASHBOARD_BOOTSTRAP_TOKEN` as a required, generated, non-secret string so the operator can read it back for first remote login without application log access.

#### Scenario: Deploying the repository through Nitroship's Dockerfile route

- **WHEN** Nitroship deploys the repository using its root Dockerfile and `nitroship.json`
- **THEN** the deployment selects `kr-icn` and routes HTTP to port 2455
- **AND** its minimum and maximum instance counts are both 1
- **AND** readiness is checked through `/health/ready`

#### Scenario: Deploy button collects persistent-state configuration

- **WHEN** an operator selects the README's Deploy on Nitroship button
- **THEN** the deployment flow lets the operator choose a team and app slug and enter an external PostgreSQL URL
- **AND** it supplies an editable pre-generated secret encryption key before building and deploying the root Dockerfile
- **AND** it supplies an editable pre-generated dashboard bootstrap token that the operator can copy

### Requirement: Docker image ships precompiled Python bytecode

The root Dockerfile runtime image MUST contain precompiled bytecode for the Python standard library, the virtual environment, and the `app` package, so container starts do not recompile sources while `PYTHONDONTWRITEBYTECODE` prevents runtime caching.

#### Scenario: Cold start does not compile sources

- **WHEN** the runtime image is inspected
- **THEN** `__pycache__` bytecode exists for the standard library, `/opt/venv` packages, and `/app/app` modules
