"""The image satisfies the restricted SCC, not just the manifests (DEP-1, TEST-4)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CONTAINERFILE = ROOT / "Containerfile"

MUST_BE_WRITABLE = (
    "/app/data",
    "/app/.cache",
)


@pytest.fixture(scope="module")
def dockerfile() -> str:
    return CONTAINERFILE.read_text()


class TestTheRestrictedSccCanWrite:
    @pytest.mark.parametrize("path", MUST_BE_WRITABLE)
    def test_the_path_is_created(self, path, dockerfile):
        assert re.search(rf"mkdir -p[^\n]*{re.escape(path)}\b", dockerfile), (
            f"{path} is never created in the image. If a volume mount makes "
            "it, the kubelet creates it root:root 755 and an arbitrary UID "
            "cannot write to it."
        )

    @pytest.mark.parametrize("path", MUST_BE_WRITABLE)
    def test_the_path_belongs_to_group_zero(self, path, dockerfile):
        assert re.search(
            rf"chown[^\n]*65532:(root|0)[^\n]*{re.escape(path)}\b", dockerfile
        ), f"{path} is not chowned to group 0"

    def test_the_data_directory_is_group_writable(self, dockerfile):
        assert re.search(r"chmod -R g\+rwX /app/data", dockerfile), (
            "/app/data is not group-writable. The UID is arbitrary under the "
            "restricted SCC; group 0 membership is the only guarantee."
        )

    def test_the_container_does_not_run_as_root(self, dockerfile):
        users = re.findall(r"^USER (\S+)", dockerfile, re.M)
        assert users and users[-1] == "65532", users


class TestWhatThisDoesNotCheck:
    def test_it_reads_the_containerfile_rather_than_the_image(self):
        """Said out loud, because it is the weakness."""
        assert CONTAINERFILE.is_file()
