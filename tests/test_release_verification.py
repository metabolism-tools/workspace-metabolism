import importlib.util
from pathlib import Path
import hashlib
from zipfile import ZipFile

import pytest

spec = importlib.util.spec_from_file_location("verify_release", Path(__file__).parents[1] / "tools" / "verify_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def test_release_artifact_checks_digest_and_version(tmp_path):
    wheel = tmp_path / "test.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("workspace_metabolism-0.8.0.dist-info/METADATA", "Name: workspace-metabolism\nVersion: 0.8.0\n")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    release.verify_wheel(wheel, digest, "0.8.0")
    with pytest.raises(ValueError, match="digest"):
        release.verify_wheel(wheel, "0" * 64, "0.8.0")
    with pytest.raises(ValueError, match="version"):
        release.verify_wheel(wheel, digest, "0.9.0")
