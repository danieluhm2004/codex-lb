import base64
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

_SH = shutil.which("sh")
_REPO_ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.unit, pytest.mark.skipif(_SH is None, reason="sh is unavailable")]


def _run_entrypoint(
    tmp_path: Path,
    *,
    key: str | None = None,
    key_file: Path | None = None,
) -> list[dict[str, object]]:
    assert _SH is not None
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    capture = tmp_path / "invocations.jsonl"
    python = shim_dir / "python"
    python.write_text(
        f"#!{sys.executable}\n"
        "import json, os, stat, sys\n"
        "from pathlib import Path\n"
        "key_file = os.environ.get('CODEX_LB_ENCRYPTION_KEY_FILE')\n"
        "path = Path(key_file) if key_file else None\n"
        "record = {\n"
        "    'args': sys.argv[1:],\n"
        "    'env': {name: os.environ[name] for name in (\n"
        "        'CODEX_LB_ENCRYPTION_KEY', 'CODEX_LB_ENCRYPTION_KEY_FILE'\n"
        "    ) if name in os.environ},\n"
        "    'key_hex': path.read_bytes().hex() if path and path.exists() else None,\n"
        "    'key_mode': stat.S_IMODE(path.stat().st_mode) if path and path.exists() else None,\n"
        "}\n"
        "with open(os.environ['ENTRYPOINT_CAPTURE'], 'a', encoding='utf-8') as output:\n"
        "    output.write(json.dumps(record) + '\\n')\n",
        encoding="utf-8",
    )
    python.chmod(0o755)
    env = os.environ.copy()
    env.pop("CODEX_LB_ENCRYPTION_KEY", None)
    env.pop("CODEX_LB_ENCRYPTION_KEY_FILE", None)
    env.update(
        PATH=f"{shim_dir}{os.pathsep}{os.defpath}",
        ENTRYPOINT_CAPTURE=str(capture),
        CODEX_LB_DATABASE_MIGRATE_ON_STARTUP="true",
    )
    if key is not None:
        env["CODEX_LB_ENCRYPTION_KEY"] = key
    if key_file is not None:
        env["CODEX_LB_ENCRYPTION_KEY_FILE"] = str(key_file)
    subprocess.run(
        [_SH, str(_REPO_ROOT / "scripts/docker-entrypoint.sh")],
        cwd=tmp_path,
        env=env,
        umask=0o022,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    records = [json.loads(line) for line in capture.read_text(encoding="utf-8").splitlines()]
    assert [record["args"] for record in records] == [
        ["-m", "app.db.migrate", "upgrade"],
        ["-m", "app.cli", "--host", "0.0.0.0", "--port", "2455"],
    ]
    return records


def test_entrypoint_materializes_key_before_migration_and_removes_secret(tmp_path: Path) -> None:
    key = "-n secret%with\\literal\\slashes\nand whitespace \t"
    key_file = tmp_path / "custom encryption.key"
    key_file.write_bytes(b"stale key material that must be overwritten completely")
    key_file.chmod(0o644)

    records = _run_entrypoint(tmp_path, key=key, key_file=key_file)

    assert key_file.read_bytes() == key.encode("utf-8")
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
    for record in records:
        assert record["env"] == {"CODEX_LB_ENCRYPTION_KEY_FILE": str(key_file)}
        assert record["key_hex"] == key.encode("utf-8").hex()
        assert record["key_mode"] == 0o600


@pytest.mark.parametrize("padded", [False, True], ids=["nitroship-unpadded", "fernet-padded"])
def test_entrypoint_materializes_a_usable_fernet_key(tmp_path: Path, padded: bool) -> None:
    expected = base64.urlsafe_b64encode(bytes(range(32)))
    key = expected.decode("ascii") if padded else expected.decode("ascii").rstrip("=")
    key_file = tmp_path / "encryption.key"

    records = _run_entrypoint(tmp_path, key=key, key_file=key_file)

    contents = key_file.read_bytes()
    assert contents == expected
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
    for record in records:
        assert record["env"] == {"CODEX_LB_ENCRYPTION_KEY_FILE": str(key_file)}
        assert record["key_hex"] == expected.hex()
        assert record["key_mode"] == 0o600
    cipher = Fernet(contents)
    plaintext = b"stored account credential"
    assert cipher.decrypt(cipher.encrypt(plaintext)) == plaintext


def test_entrypoint_without_key_leaves_key_file_environment_unset(tmp_path: Path) -> None:
    records = _run_entrypoint(tmp_path)

    for record in records:
        assert record["env"] == {}
        assert record["key_hex"] is None
        assert record["key_mode"] is None
    assert {path.name for path in tmp_path.iterdir()} == {"bin", "invocations.jsonl"}
