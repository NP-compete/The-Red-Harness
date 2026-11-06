"""The documents volume and its capacity guard."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from agent.aegra import document_routes as dr


@pytest.fixture(autouse=True)
def _authenticated(monkeypatch):
    """Every route authenticates; these tests are about the rest."""

    async def _ok(_request, **_kw):
        return "tester"

    monkeypatch.setattr(dr, "authenticated_user_id", _ok)


@pytest.fixture
def volume(tmp_path: Path, monkeypatch):
    root = tmp_path / "datasets"
    root.mkdir()
    monkeypatch.setenv("DOCUMENTS_PATH", str(root))
    monkeypatch.setenv("DOCUMENTS_MAX_BYTES", str(1024))
    return root


def _upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data), size=len(data))


class TestUsage:
    def test_reports_what_is_used(self, volume):
        (volume / "a.csv").write_bytes(b"x" * 512)
        usage = dr._usage(volume)
        assert usage["used_bytes"] == 512
        assert usage["capacity_bytes"] == 1024
        assert usage["percent_used"] == 50.0

    def test_warns_before_it_refuses(self, volume):
        (volume / "a.csv").write_bytes(b"x" * 700)
        assert dr._usage(volume)["warning"] is False
        (volume / "b.csv").write_bytes(b"x" * 200)
        assert dr._usage(volume)["warning"] is True


class TestUpload:
    @pytest.mark.asyncio
    async def test_accepts_a_file_that_fits(self, volume):
        out = await dr.upload_document(None, [_upload("ok.csv", b"x" * 100)])
        assert out["uploaded"][0]["bytes"] == 100
        assert (volume / "ok.csv").exists()

    @pytest.mark.asyncio
    async def test_refuses_before_writing_when_it_will_not_fit(self, volume):
        (volume / "existing.csv").write_bytes(b"x" * 900)
        with pytest.raises(HTTPException) as exc:
            await dr.upload_document(None, [_upload("big.csv", b"x" * 500)])
        assert exc.value.status_code == 507
        assert not (volume / "big.csv").exists()
        assert dr._used_bytes(volume) == 900

    @pytest.mark.asyncio
    async def test_a_lying_declared_size_is_still_caught(self, volume):
        liar = UploadFile(filename="liar.csv", file=io.BytesIO(b"x" * 5000), size=10)
        with pytest.raises(HTTPException) as exc:
            await dr.upload_document(None, [liar])
        assert exc.value.status_code == 507
        assert not (volume / "liar.csv").exists()

    @pytest.mark.asyncio
    async def test_rejects_an_unsupported_type(self, volume):
        with pytest.raises(HTTPException) as exc:
            await dr.upload_document(None, [_upload("payload.sh", b"echo hi")])
        assert exc.value.status_code == 415

    @pytest.mark.asyncio
    async def test_a_traversing_filename_cannot_escape(self, volume):
        with pytest.raises(HTTPException) as excinfo:
            await dr.upload_document(
                None, [_upload("../../../etc/evil.csv", b"x" * 10)]
            )
        assert excinfo.value.status_code == 400
        assert not (volume / "evil.csv").exists()
        assert not (volume.parent.parent / "etc" / "evil.csv").exists()


class TestDelete:
    @pytest.mark.asyncio
    async def test_removes_a_file_and_frees_space(self, volume):
        (volume / "a.csv").write_bytes(b"x" * 400)
        out = await dr.delete_document("a.csv", None)
        assert out["usage"]["used_bytes"] == 0

    @pytest.mark.asyncio
    async def test_cannot_delete_outside_the_volume(self, volume):
        outside = volume.parent / "secret.csv"
        outside.write_bytes(b"x")
        with pytest.raises(HTTPException) as exc:
            await dr.delete_document("../secret.csv", None)
        assert exc.value.status_code == 404
        assert outside.exists()


class TestReadAndWrite:
    @pytest.mark.asyncio
    async def test_reads_a_file_back(self, volume):
        (volume / "a.csv").write_text("id,amount\n1,10\n")
        out = await dr.read_document("a.csv", None)
        assert out["content"].startswith("id,amount")
        assert out["editable"] is True

    @pytest.mark.asyncio
    async def test_a_truncated_file_is_not_editable(self, volume, monkeypatch):
        monkeypatch.setattr(dr, "_MAX_EDITABLE_BYTES", 10)
        (volume / "big.csv").write_text("x" * 50)
        out = await dr.read_document("big.csv", None)
        assert out["truncated"] is True
        assert out["editable"] is False

    @pytest.mark.asyncio
    async def test_creates_and_replaces(self, volume):
        await dr.write_document("new.csv", dr.DocumentBody(content="a,b\n"), None)
        assert (volume / "new.csv").read_text() == "a,b\n"
        await dr.write_document("new.csv", dr.DocumentBody(content="c,d\n"), None)
        assert (volume / "new.csv").read_text() == "c,d\n"

    @pytest.mark.asyncio
    async def test_replacing_counts_the_space_being_freed(self, volume):
        (volume / "a.csv").write_text("x" * 1000)
        await dr.write_document("a.csv", dr.DocumentBody(content="y" * 1000), None)
        assert (volume / "a.csv").read_text() == "y" * 1000

    @pytest.mark.asyncio
    async def test_a_write_that_will_not_fit_is_refused(self, volume):
        with pytest.raises(HTTPException) as exc:
            await dr.write_document(
                "big.csv", dr.DocumentBody(content="x" * 2000), None
            )
        assert exc.value.status_code == 507

    @pytest.mark.asyncio
    async def test_reading_outside_the_volume_is_404(self, volume):
        (volume.parent / "secret.csv").write_text("nope")
        with pytest.raises(HTTPException) as exc:
            await dr.read_document("../secret.csv", None)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_writing_outside_the_volume_is_refused(self, volume):
        """400, not a 200 for a different path."""
        with pytest.raises(HTTPException) as excinfo:
            await dr.write_document(
                "../../escape.csv", dr.DocumentBody(content="x"), None
            )
        assert excinfo.value.status_code == 400
        assert not (volume / "escape.csv").exists()
        assert not (volume.parent / "escape.csv").exists()

    @pytest.mark.asyncio
    async def test_deleting_the_root_is_refused(self, volume):
        """`DELETE /documents/.` resolved to the volume and rmtree'd it."""
        (volume / "keep.txt").write_bytes(b"data")
        with pytest.raises(HTTPException):
            await dr.delete_document(".", None)
        assert (volume / "keep.txt").exists()


class TestAuth:
    @pytest.mark.asyncio
    async def test_routes_require_the_developer_role(self, volume, monkeypatch):
        seen: list[dict] = []

        async def _record(_request, **kw):
            seen.append(kw)
            return "tester"

        monkeypatch.setattr(dr, "authenticated_user_id", _record)
        await dr.list_documents(None)
        assert seen[0]["developer_only"] is True
        assert seen[0]["reject_anonymous"] is True

    @pytest.mark.asyncio
    async def test_routes_reject_a_caller_without_the_role(self, volume, monkeypatch):
        async def _deny(_request, **_kw):
            raise HTTPException(status_code=403, detail="Developer access required")

        monkeypatch.setattr(dr, "authenticated_user_id", _deny)
        for call in (
            dr.list_documents(None),
            dr.read_document("a.csv", None),
            dr.write_document("a.csv", dr.DocumentBody(content="x"), None),
            dr.delete_document("a.csv", None),
        ):
            with pytest.raises(HTTPException) as exc:
                await call
            assert exc.value.status_code == 403
