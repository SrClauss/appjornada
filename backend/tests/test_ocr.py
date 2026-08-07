import pytest
from unittest.mock import patch

class TestOcrNotaFiscal:
    async def test_processar_nota_fiscal_sucesso(self, client):
        mock_response = {
            "sucesso": True,
            "valor_total": 200.0,
            "litros": 35.0,
            "preco_litro": 5.71,
            "posto_combustivel": "Posto Shell Vitoria",
            "tipo_combustivel": "GASOLINA",
            "confianca": "ALTA",
            "observacao": "Cupom fiscal legível"
        }

        with patch("app.routers.ocr._chamar_gemini_nota_fiscal", return_value=mock_response), \
             patch("app.routers.ocr._salvar_arquivo", return_value="http://localhost:9000/jornada-uploads/abastecimento/foto.jpg"):
            
            files = {"file": ("nota.jpg", b"fake image bytes", "image/jpeg")}
            resp = await client.post("/ocr/nota-fiscal", files=files)
            
            assert resp.status_code == 200
            data = resp.json()
            assert data["sucesso"] is True
            assert data["valor_total"] == 200.0
            assert data["litros"] == 35.0
            assert data["preco_litro"] == 5.71
            assert data["posto_combustivel"] == "Posto Shell Vitoria"
            assert data["tipo_combustivel"] == "GASOLINA"
            assert data["foto_url"] == "http://localhost:9000/jornada-uploads/abastecimento/foto.jpg"

    async def test_processar_nota_fiscal_tipo_arquivo_invalido(self, client):
        files = {"file": ("documento.pdf", b"fake pdf bytes", "application/pdf")}
        resp = await client.post("/ocr/nota-fiscal", files=files)
        assert resp.status_code == 400
        assert "imagem" in resp.json()["detail"].lower()
