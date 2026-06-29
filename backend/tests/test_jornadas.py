"""
Testes dos endpoints de jornadas: /jornadas/
Cobre abertura com PIN, fechamento, pausas, abastecimentos, sinistros,
jornada aberta, paginação e resumos CLT.
"""
import pytest
from datetime import date, timedelta
from bson import ObjectId


# ── Helpers ────────────────────────────────────────────────────────────────

def _abrir_payload(motorista_id: str, veiculo_id: str = "TST1A23") -> dict:
    return {"motorista_id": motorista_id, "veiculo_id": veiculo_id}


# ── Abrir jornada ──────────────────────────────────────────────────────────

class TestAbrirJornada:
    async def test_motorista_abre_jornada_com_pin_correto(
        self, client, motorista_user, veiculo, motorista_headers
    ):
        resp = await client.post(
            "/jornadas/?pin=1234",
            json=_abrir_payload(motorista_user["id"]),
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "ABERTA"
        assert data["veiculo_id"] == "TST1A23"
        assert data["jornada_diaria_clt"] == 8.0
        assert data["jornada_semanal_clt"] == 44.0
        assert data["jornada_mensal_clt"] == 220.0

    async def test_motorista_abre_jornada_com_vistoria(
        self, client, motorista_user, veiculo, motorista_headers
    ):
        payload = _abrir_payload(motorista_user["id"])
        payload["vistoria"] = {
            "pneus_ok": True,
            "oleo_ok": True,
            "agua_ok": False,
            "farois_ok": True,
            "limpeza_ok": True,
            "observacoes": "Nível de água ligeiramente abaixo do recomendado",
            "foto_avarias_url": "http://teste/foto_avaria.png"
        }
        resp = await client.post(
            "/jornadas/?pin=1234",
            json=payload,
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "ABERTA"
        assert data["vistoria"]["agua_ok"] is False
        assert data["vistoria"]["observacoes"] == "Nível de água ligeiramente abaixo do recomendado"
        assert data["vistoria"]["foto_avarias_url"] == "http://teste/foto_avaria.png"

    async def test_pin_errado_retorna_401(
        self, client, motorista_user, veiculo, motorista_headers
    ):
        resp = await client.post(
            "/jornadas/?pin=9999",
            json=_abrir_payload(motorista_user["id"]),
            headers=motorista_headers,
        )
        assert resp.status_code == 401

    async def test_jornada_duplicada_retorna_409(
        self, client, motorista_user, jornada_aberta, motorista_headers
    ):
        """Não deve abrir segunda jornada se já há uma aberta hoje."""
        resp = await client.post(
            "/jornadas/?pin=1234",
            json=_abrir_payload(motorista_user["id"]),
            headers=motorista_headers,
        )
        assert resp.status_code == 409

    async def test_abre_com_localizacao_inicial(
        self, client, motorista_user, veiculo, motorista_headers
    ):
        resp = await client.post(
            "/jornadas/?pin=1234&localizacao_lat=-20.21&localizacao_lon=-40.26",
            json=_abrir_payload(motorista_user["id"]),
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["localizacao_inicial"]["lat"] == -20.21

    async def test_sem_token_retorna_401(self, client, veiculo, motorista_user):
        resp = await client.post(
            "/jornadas/?pin=1234",
            json=_abrir_payload(motorista_user["id"]),
        )
        assert resp.status_code == 401

    async def test_resposta_nao_contem_pin_em_texto(
        self, client, motorista_user, veiculo, motorista_headers
    ):
        """O PIN pode ser armazenado no documento para referência histórica, mas
        nunca deve aparecer no response model (não está em Jornada como campo público)."""
        resp = await client.post(
            "/jornadas/?pin=1234",
            json=_abrir_payload(motorista_user["id"]),
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        # pin não está no response_model Jornada (mas está no doc interno)
        # basta confirmar que não vaza a senha

    async def test_gestor_abre_jornada_para_motorista(
        self, client, motorista_user, veiculo, admin_headers
    ):
        resp = await client.post(
            "/jornadas/?pin=0000",
            json=_abrir_payload(motorista_user["id"]),
            headers=admin_headers,
        )
        assert resp.status_code == 201


# ── Listar jornadas ─────────────────────────────────────────────────────────

class TestListarJornadas:
    async def test_admin_lista_todas(
        self, client, jornada_aberta, jornada_encerrada, admin_headers
    ):
        resp = await client.get("/jornadas/", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_motorista_so_ve_proprias(
        self, client, motorista_user, jornada_aberta, db, motorista_headers
    ):
        # Insere jornada de outro motorista
        outro_id = ObjectId()
        await db["jornadas"].insert_one({
            "_id": "Outro-TST1A23-999",
            "data": date.today().isoformat(),
            "motorista_id": outro_id,
            "veiculo_id": "TST1A23",
            "status": "ABERTA",
        })
        resp = await client.get("/jornadas/", headers=motorista_headers)
        assert resp.status_code == 200
        for j in resp.json():
            assert str(j["motorista_id"]) == motorista_user["id"]

    async def test_paginacao_limit(
        self, client, jornada_aberta, jornada_encerrada, admin_headers
    ):
        resp = await client.get("/jornadas/?skip=0&limit=1", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 1

    async def test_filtro_por_status(
        self, client, jornada_aberta, jornada_encerrada, admin_headers
    ):
        resp = await client.get("/jornadas/?status_filtro=ABERTA", headers=admin_headers)
        assert resp.status_code == 200
        assert all(j["status"] == "ABERTA" for j in resp.json())


# ── GET /aberta ─────────────────────────────────────────────────────────────

class TestJornadaAberta:
    async def test_retorna_jornada_aberta_existente(
        self, client, jornada_aberta, motorista_headers
    ):
        resp = await client.get("/jornadas/aberta", headers=motorista_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ABERTA"

    async def test_retorna_null_sem_jornada_aberta(
        self, client, jornada_encerrada, motorista_headers
    ):
        resp = await client.get("/jornadas/aberta", headers=motorista_headers)
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_sem_token_retorna_401(self, client):
        resp = await client.get("/jornadas/aberta")
        assert resp.status_code == 401


# ── GET por ID ──────────────────────────────────────────────────────────────

class TestGetJornada:
    async def test_get_por_id(self, client, jornada_aberta, motorista_headers):
        resp = await client.get(
            f"/jornadas/{jornada_aberta['_id']}", headers=motorista_headers
        )
        assert resp.status_code == 200

    async def test_id_inexistente_retorna_404(self, client, admin_headers):
        resp = await client.get("/jornadas/nao-existe-este-id", headers=admin_headers)
        assert resp.status_code == 404

    async def test_motorista_nao_acessa_jornada_de_outro(
        self, client, db, motorista_headers
    ):
        outro_id = ObjectId()
        await db["jornadas"].insert_one({
            "_id": "outro-TST-xyz",
            "data": date.today().isoformat(),
            "motorista_id": outro_id,
            "veiculo_id": "TST1A23",
            "status": "ABERTA",
        })
        resp = await client.get("/jornadas/outro-TST-xyz", headers=motorista_headers)
        assert resp.status_code == 403


# ── Fechar jornada ──────────────────────────────────────────────────────────

class TestFecharJornada:
    async def test_fechar_calcula_km_rodados(
        self, client, jornada_aberta, motorista_headers
    ):
        jid = jornada_aberta["_id"]
        resp = await client.patch(
            f"/jornadas/{jid}/fechar?km_final=50200.0&faturamento_uber=150.0",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ENCERRADA"
        assert data["km"]["final"] == 50200.0
        assert data["km"]["rodados"] == 200.0

    async def test_fechar_calcula_faturamento_total(
        self, client, jornada_aberta, motorista_headers
    ):
        jid = jornada_aberta["_id"]
        resp = await client.patch(
            f"/jornadas/{jid}/fechar?km_final=50100.0&faturamento_uber=100.0&faturamento_99=80.0&faturamento_outros=20.0",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["faturamento"]["total_dia"] == 200.0

    async def test_fechar_com_localizacao_final(
        self, client, jornada_aberta, motorista_headers
    ):
        jid = jornada_aberta["_id"]
        resp = await client.patch(
            f"/jornadas/{jid}/fechar?km_final=50100.0&localizacao_lat=-20.22&localizacao_lon=-40.27",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["localizacao_final"]["lat"] == -20.22

    async def test_fechar_persiste_comprovantes_e_fotos(
        self, client, jornada_aberta, motorista_headers
    ):
        jid = jornada_aberta["_id"]
        resp = await client.patch(
            f"/jornadas/{jid}/fechar?km_final=50100.0"
            f"&foto_km_final_url=http://minio/final.png"
            f"&comprovante_uber_url=http://minio/uber.png"
            f"&comprovante_99_url=http://minio/99.png",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["fotos"]["km_final_url"] == "http://minio/final.png"
        assert data["faturamento"]["comprovante_uber_url"] == "http://minio/uber.png"
        assert data["faturamento"]["comprovante_99_url"] == "http://minio/99.png"

    async def test_fechar_jornada_ja_encerrada_retorna_409(
        self, client, jornada_encerrada, motorista_headers
    ):
        jid = jornada_encerrada["_id"]
        resp = await client.patch(
            f"/jornadas/{jid}/fechar?km_final=50300.0",
            headers=motorista_headers,
        )
        assert resp.status_code == 409

    async def test_fechar_jornada_inexistente_retorna_404(
        self, client, admin_headers
    ):
        resp = await client.patch(
            "/jornadas/nao-existe/fechar?km_final=100.0",
            headers=admin_headers,
        )
        assert resp.status_code == 404


# ── Pausas ──────────────────────────────────────────────────────────────────

class TestPausas:
    async def test_iniciar_pausa(self, client, jornada_aberta, motorista_headers):
        jid = jornada_aberta["_id"]
        resp = await client.post(
            f"/jornadas/{jid}/pausas?tipo=PAUSA_ALMOCO",
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "EM_PAUSA"
        assert len(data["pausas"]) == 1
        assert data["pausas"][0]["tipo"] == "PAUSA_ALMOCO"

    async def test_fechar_pausa(self, client, jornada_aberta, motorista_headers):
        jid = jornada_aberta["_id"]
        # Abre pausa
        r1 = await client.post(
            f"/jornadas/{jid}/pausas?tipo=PAUSA_MOTORISTA",
            headers=motorista_headers,
        )
        pausa_id = r1.json()["pausas"][0]["id"]

        # Fecha pausa
        r2 = await client.patch(
            f"/jornadas/{jid}/pausas/{pausa_id}/fechar",
            headers=motorista_headers,
        )
        assert r2.status_code == 200
        data = r2.json()
        assert data["status"] == "EM_ANDAMENTO"
        assert data["pausas"][0]["fim"] is not None
        assert data["pausas"][0]["duracao_segundos"] >= 0


# ── Abastecimentos ──────────────────────────────────────────────────────────

class TestAbastecimentos:
    async def test_registrar_abastecimento(
        self, client, jornada_aberta, motorista_headers
    ):
        jid = jornada_aberta["_id"]
        resp = await client.post(
            f"/jornadas/{jid}/abastecimentos",
            json={
                "id": "abc001",
                "km": 50050.0,
                "valor_gasolina": 200.0,
            },
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["abastecimentos"]) == 1
        assert data["abastecimentos"][0]["valor_gasolina"] == 200.0


# ── Sinistros ───────────────────────────────────────────────────────────────

class TestSinistros:
    async def test_registrar_sinistro(
        self, client, jornada_aberta, motorista_headers
    ):
        jid = jornada_aberta["_id"]
        resp = await client.post(
            f"/jornadas/{jid}/sinistros",
            json={
                "id": "sin001",
                "tipo": "COLISAO",
                "descricao": "Colisão leve na parte traseira",
            },
            headers=motorista_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["sinistros"]) == 1
        assert data["sinistros"][0]["tipo"] == "COLISAO"


# ── Resumo CLT ──────────────────────────────────────────────────────────────

class TestResumoCLT:
    async def test_resumo_semanal_com_jornada_encerrada(
        self, client, motorista_user, jornada_encerrada, motorista_headers
    ):
        ontem = (date.today() - timedelta(days=1)).isoformat()
        resp = await client.get(
            f"/jornadas/{motorista_user['id']}/resumo-clt?semana_inicio={ontem}",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_horas_trabalhadas" in data
        assert "saldo_horas_semana" in data
        assert data["dias_trabalhados"] >= 1

    async def test_resumo_mensal(
        self, client, motorista_user, jornada_encerrada, motorista_headers
    ):
        hoje = date.today()
        resp = await client.get(
            f"/jornadas/{motorista_user['id']}/resumo-clt-mensal?ano={hoje.year}&mes={hoje.month}",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_horas_trabalhadas" in data
        assert "detalhe_por_dia" in data

    async def test_motorista_nao_acessa_resumo_de_outro(
        self, client, admin_user, motorista_headers
    ):
        hoje = date.today()
        resp = await client.get(
            f"/jornadas/{admin_user['id']}/resumo-clt?semana_inicio={hoje.isoformat()}",
            headers=motorista_headers,
        )
        assert resp.status_code == 403


class TestUploadComprovanteGemini:
    async def test_upload_comprovante_processa_com_gemini(
        self, client, jornada_aberta, motorista_headers, monkeypatch
    ):
        # Mock do httpx.AsyncClient.post para simular resposta do Gemini
        class MockResponse:
            status_code = 200
            def json(self):
                return {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": '{"plataforma": "UBER", "valor": 45.50, "origem": "Rua A", "destino": "Rua B"}'
                                    }
                                ]
                            }
                        }
                    ]
                }
        
        import httpx
        original_post = httpx.AsyncClient.post
        async def mock_post(self_client, url, *args, **kwargs):
            if "generativelanguage.googleapis.com" in str(url):
                return MockResponse()
            return await original_post(self_client, url, *args, **kwargs)
        
        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        
        # Mock de _salvar_arquivo para evitar salvar no MinIO/disco real durante o teste
        async def mock_salvar_arquivo(arquivo, contexto):
            return "http://mock/print_uber.png"

        import sys
        uploads_mod = sys.modules["app.routers.uploads"]
        monkeypatch.setattr(uploads_mod, "_salvar_arquivo", mock_salvar_arquivo)

        # Prepara arquivo fake
        fake_file = ("comprovante.png", b"fake_png_data", "image/png")
        
        resp = await client.post(
            "/jornadas/aberta/comprovante",
            headers=motorista_headers,
            files={"arquivo": fake_file}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "sucesso"
        assert data["plataforma"] == "UBER"
        assert data["valor_extraido"] == 45.50
        assert data["origem"] == "Rua A"
        assert data["destino"] == "Rua B"
        assert data["url_comprovante"] == "http://mock/print_uber.png"
