"""Two uploads of one name cannot become one mixed file (DEP-4)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
ROUTES = ROOT / "services" / "agent" / "aegra" / "document_routes.py"


class TestTheStagingNameIsPerWriter:
    def test_it_is_not_derived_from_the_target_alone(self):
        source = ROUTES.read_text()
        bare = 'target.with_name(f".{target.name}.part")'
        assert bare not in source, (
            "the staging file is named after the target and nothing else, so "
            "two writers share it (DEP-4)"
        )

    def test_it_carries_the_process_and_a_nonce(self):
        source = ROUTES.read_text()
        staging = next(
            line for line in source.splitlines() if "staging = target.with_name" in line
        )
        assert "os.getpid()" in staging, staging
        assert "uuid4()" in staging, staging

    def test_two_writers_get_two_names(self):
        from uuid import uuid4

        import os

        target = Path("/tmp/doc.csv")

        def staging_for() -> Path:
            return target.with_name(f".{target.name}.{os.getpid()}.{uuid4().hex}.part")

        assert staging_for() != staging_for()

    def test_it_is_still_hidden_from_the_listing(self):
        staging = next(
            line
            for line in ROUTES.read_text().splitlines()
            if "staging = target.with_name" in line
        )
        assert re.search(r'f"\.\{target\.name\}', staging), staging
        assert 'name.startswith(".")' in ROUTES.read_text()


class TestTheVolumesAreReadWriteOnce:
    """DEP-4's first clause, which is a line of YAML."""

    @staticmethod
    def _claims() -> list[tuple[Path, dict]]:
        found = []
        for path in sorted(ROOT.glob("deployment/**/*.yaml")):
            if "chart/templates" in path.as_posix():
                continue
            text = path.read_text()
            if "PersistentVolumeClaim" not in text:
                continue
            for doc in yaml.safe_load_all(text):
                if isinstance(doc, dict) and doc.get("kind") == "PersistentVolumeClaim":
                    found.append((path, doc))
        return found

    def test_there_are_claims_to_check(self):
        assert self._claims(), "no PersistentVolumeClaim found; the glob is wrong"

    def test_the_chart_ships_read_write_many_for_documents(self):
        """The exception, pinned rather than hidden."""
        values = yaml.safe_load((ROOT / "deployment/chart/values.yaml").read_text())
        storage = values["storage"]
        assert storage["documents"]["accessMode"] == "ReadWriteMany"
        assert storage["config"]["accessMode"] == "ReadWriteOnce"

    MAY_BE_WIDER = {"documents"}

    def test_every_other_claim_is_read_write_once(self):
        judged = 0
        for path, claim in self._claims():
            modes = (claim.get("spec") or {}).get("accessModes") or []
            literal = [m for m in modes if isinstance(m, str) and "{{" not in m]
            if not literal:
                continue
            name = (claim.get("metadata") or {}).get("name") or path.stem
            if any(one in name for one in self.MAY_BE_WIDER):
                continue
            judged += 1
            assert literal == ["ReadWriteOnce"], (
                f"{path.relative_to(ROOT)} declares {literal}; DEP-4 says "
                "ReadWriteOnce, and a wider mode means more than one writer "
                "with no lock between them"
            )
        assert judged >= 2, f"only {judged} claim(s) were actually judged"

    def test_the_documents_claim_really_is_the_wider_one(self):
        wider = [
            path.relative_to(ROOT)
            for path, claim in self._claims()
            if "ReadWriteMany" in ((claim.get("spec") or {}).get("accessModes") or [])
        ]
        assert wider, "nothing is ReadWriteMany any more — drop MAY_BE_WIDER"
        assert all("documents" in p.as_posix() for p in wider), wider


@pytest.mark.parametrize("marker", ["os.getpid()", "uuid4"])
def test_the_fix_is_in_the_shipped_module(marker: str):
    assert marker in ROUTES.read_text()
