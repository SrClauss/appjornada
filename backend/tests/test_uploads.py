"""
Testes dos endpoints de upload de arquivos: /uploads/{contexto}
"""
import io
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_file(filename: str, content: bytes = b"data", content_type: str = "image/jpeg"):
    return {"arquivo": (filename, io.BytesIO(content), content_type)}


class TestUploadArquivo:
    async def test_upload_jpg_valido(self, client, motorista_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        resp = await client.post(
            "/uploads/km_inicial",
            files=_make_file("foto.jpg"),
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "url" in data
        assert "km_inicial" in data["url"]
        assert data["url"].endswith(".jpg")

    async def test_upload_png_valido(self, client, motorista_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        resp = await client.post(
            "/uploads/cnh",
            files=_make_file("cnh.png", content_type="image/png"),
            headers=motorista_headers,
        )
        assert resp.status_code == 201

    async def test_upload_pdf_valido(self, client, motorista_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        resp = await client.post(
            "/uploads/comprovante",
            files=_make_file("doc.pdf", content_type="application/pdf"),
            headers=motorista_headers,
        )
        assert resp.status_code == 201

    async def test_extensao_invalida_retorna_415(
        self, client, motorista_headers, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        resp = await client.post(
            "/uploads/km_inicial",
            files=_make_file("malware.exe", content_type="application/octet-stream"),
            headers=motorista_headers,
        )
        assert resp.status_code == 415

    async def test_arquivo_grande_demais_retorna_413(
        self, client, motorista_headers, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        # 11 MB > 10 MB limite
        arquivo_grande = b"A" * (11 * 1024 * 1024)
        resp = await client.post(
            "/uploads/outros",
            files=_make_file("grande.jpg", content=arquivo_grande),
            headers=motorista_headers,
        )
        assert resp.status_code == 413

    async def test_contexto_invalido_retorna_400(
        self, client, motorista_headers, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        resp = await client.post(
            "/uploads/contexto_invalido",
            files=_make_file("foto.jpg"),
            headers=motorista_headers,
        )
        assert resp.status_code == 400

    async def test_sem_autenticacao_retorna_401(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        resp = await client.post(
            "/uploads/km_inicial",
            files=_make_file("foto.jpg"),
        )
        assert resp.status_code == 401

    async def test_todos_contextos_validos_aceitos(
        self, client, motorista_headers, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        contextos_validos = [
            "km_inicial", "km_final", "cnh", "clrv",
            "comprovante", "sinistro", "nota_fiscal", "outros",
        ]
        for ctx in contextos_validos:
            resp = await client.post(
                f"/uploads/{ctx}",
                files=_make_file(f"arquivo_{ctx}.jpg"),
                headers=motorista_headers,
            )
            assert resp.status_code == 201, (
                f"Contexto '{ctx}' falhou com status {resp.status_code}"
            )

    async def test_url_retornada_tem_caminho_estatico(
        self, client, motorista_headers, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        resp = await client.post(
            "/uploads/km_final",
            files=_make_file("km.jpg"),
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["url"].startswith("/static/uploads/")
