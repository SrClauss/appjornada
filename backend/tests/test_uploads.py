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
        import sys
        _mod = sys.modules["app.routers.uploads"]
        monkeypatch.setattr(_mod, "TAMANHO_MAXIMO_MB", 10)
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
        """Quando MinIO está desabilitado, a URL deve apontar para /static/uploads/."""
        import sys
        _mod = sys.modules["app.routers.uploads"]
        monkeypatch.setattr(_mod, "MINIO_ENABLED", False)
        monkeypatch.setattr(_mod, "UPLOAD_DIR", tmp_path)
        resp = await client.post(
            "/uploads/km_final",
            files=_make_file("km.jpg"),
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["url"].startswith("/static/uploads/")

    async def test_upload_sem_minio_cria_arquivo_local(
        self, client, motorista_headers, tmp_path, monkeypatch
    ):
        """Sem MinIO: arquivo é salvo localmente e URL segue padrão /static/uploads/."""
        import sys
        _mod = sys.modules["app.routers.uploads"]
        monkeypatch.setattr(_mod, "MINIO_ENABLED", False)
        monkeypatch.setattr(_mod, "UPLOAD_DIR", tmp_path)
        resp = await client.post(
            "/uploads/cnh",
            files=_make_file("cnh.png", content_type="image/png"),
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "cnh" in data["url"]
        assert data["url"].endswith(".png")
        # Arquivo deve ter sido criado no diretório tmp
        contexto_dir = tmp_path / "cnh"
        assert contexto_dir.exists()
        arquivos = list(contexto_dir.iterdir())
        assert len(arquivos) == 1

    async def test_upload_minio_habilitado_retorna_url_minio(
        self, client, motorista_headers, monkeypatch
    ):
        """Com MinIO mockado, URL deve ter o formato http://<endpoint>/<bucket>/..."""
        import sys
        from unittest.mock import MagicMock

        _mod = sys.modules["app.routers.uploads"]
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True

        monkeypatch.setattr(_mod, "MINIO_ENABLED", True)
        monkeypatch.setattr(_mod, "MINIO_CLIENT", mock_client)
        monkeypatch.setattr(_mod, "MINIO_BUCKET", "test-bucket")

        resp = await client.post(
            "/uploads/outros",
            files=_make_file("doc.pdf", content_type="application/pdf"),
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        mock_client.put_object.assert_called_once()

    async def test_ensure_minio_bucket_cria_quando_nao_existe(self):
        """_ensure_minio_bucket deve criar o bucket quando ele não existe."""
        import sys
        from unittest.mock import MagicMock

        _mod = sys.modules["app.routers.uploads"]
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False

        original_client = _mod.MINIO_CLIENT
        _mod.MINIO_CLIENT = mock_client
        try:
            _mod._ensure_minio_bucket()
            mock_client.make_bucket.assert_called_once()
            mock_client.set_bucket_policy.assert_called_once()
        finally:
            _mod.MINIO_CLIENT = original_client

    async def test_ensure_minio_bucket_sem_cliente_retorna_sem_erro(self):
        """_ensure_minio_bucket retorna silenciosamente quando MINIO_CLIENT é None."""
        import sys
        _mod = sys.modules["app.routers.uploads"]

        original_client = _mod.MINIO_CLIENT
        _mod.MINIO_CLIENT = None
        try:
            _mod._ensure_minio_bucket()  # não deve lançar exceção
        finally:
            _mod.MINIO_CLIENT = original_client


class TestDeleteUploads:
    async def test_deletar_contexto_deletavel_sucesso(self, client, gestor_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        import sys
        _mod = sys.modules["app.routers.uploads"]
        monkeypatch.setattr(_mod, "MINIO_ENABLED", False)
        monkeypatch.setattr(_mod, "UPLOAD_DIR", tmp_path)
        
        resp = await client.post(
            "/uploads/km_inicial",
            files=_make_file("foto.jpg"),
            headers=gestor_headers,
        )
        assert resp.status_code == 201
        filename = resp.json()["url"].split("/")[-1]
        
        del_resp = await client.delete(
            f"/uploads/km_inicial/{filename}",
            headers=gestor_headers,
        )
        assert del_resp.status_code == 204
        
    async def test_deletar_contexto_protegido_forbidden(self, client, gestor_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        import sys
        _mod = sys.modules["app.routers.uploads"]
        monkeypatch.setattr(_mod, "MINIO_ENABLED", False)
        monkeypatch.setattr(_mod, "UPLOAD_DIR", tmp_path)
        
        resp = await client.post(
            "/uploads/cnh",
            files=_make_file("cnh.png"),
            headers=gestor_headers,
        )
        assert resp.status_code == 201
        filename = resp.json()["url"].split("/")[-1]
        
        del_resp = await client.delete(
            f"/uploads/cnh/{filename}",
            headers=gestor_headers,
        )
        assert del_resp.status_code == 403
        
    async def test_bulk_delete_sucesso(self, client, gestor_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        import sys
        _mod = sys.modules["app.routers.uploads"]
        monkeypatch.setattr(_mod, "MINIO_ENABLED", False)
        monkeypatch.setattr(_mod, "UPLOAD_DIR", tmp_path)
        
        resp1 = await client.post(
            "/uploads/km_inicial",
            files=_make_file("foto1.jpg"),
            headers=gestor_headers,
        )
        resp2 = await client.post(
            "/uploads/vistoria",
            files=_make_file("foto2.jpg"),
            headers=gestor_headers,
        )
        
        filename1 = resp1.json()["url"].split("/")[-1]
        filename2 = resp2.json()["url"].split("/")[-1]
        
        bulk_resp = await client.post(
            "/uploads/bulk-delete",
            json={
                "items": [
                    {"contexto": "km_inicial", "filename": filename1},
                    {"contexto": "vistoria", "filename": filename2}
                ]
            },
            headers=gestor_headers,
        )
        assert bulk_resp.status_code == 200
        data = bulk_resp.json()
        assert len(data["sucessos"]) == 2
        assert len(data["erros"]) == 0

    async def test_bulk_delete_protegido_forbidden(self, client, gestor_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
        import sys
        _mod = sys.modules["app.routers.uploads"]
        monkeypatch.setattr(_mod, "MINIO_ENABLED", False)
        monkeypatch.setattr(_mod, "UPLOAD_DIR", tmp_path)
        
        resp = await client.post(
            "/uploads/cnh",
            files=_make_file("cnh.png"),
            headers=gestor_headers,
        )
        assert resp.status_code == 201
        filename = resp.json()["url"].split("/")[-1]
        
        bulk_resp = await client.post(
            "/uploads/bulk-delete",
            json={
                "items": [
                    {"contexto": "cnh", "filename": filename}
                ]
            },
            headers=gestor_headers,
        )
        assert bulk_resp.status_code == 403

