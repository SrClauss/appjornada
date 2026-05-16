"""
Testes dos endpoints de metas e bônus: /metas/
"""
import pytest
from bson import ObjectId


class TestCriarMeta:
    async def test_admin_cria_meta(self, client, admin_headers):
        resp = await client.post("/metas/", json={
            "tipo": "META 430",
            "faixa_minima": 430.0,
            "faixa_maxima": 499.99,
            "bonus": 50.0,
            "referencia": "GERAL",
        }, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["tipo"] == "META 430"
        assert data["bonus"] == 50.0

    async def test_gestor_cria_meta(self, client, gestor_headers):
        resp = await client.post("/metas/", json={
            "tipo": "META 500",
            "faixa_minima": 500.0,
            "bonus": 75.0,
        }, headers=gestor_headers)
        assert resp.status_code == 201

    async def test_motorista_nao_pode_criar(self, client, motorista_headers):
        resp = await client.post("/metas/", json={
            "tipo": "META 300",
            "bonus": 25.0,
        }, headers=motorista_headers)
        assert resp.status_code == 403

    async def test_sem_token_retorna_401(self, client):
        resp = await client.post("/metas/", json={"tipo": "X", "bonus": 10.0})
        assert resp.status_code == 401


class TestListarMetas:
    async def test_motorista_lista_metas(self, client, admin_headers, motorista_headers):
        await client.post("/metas/", json={
            "tipo": "META 430", "faixa_minima": 430.0, "bonus": 50.0,
        }, headers=admin_headers)
        resp = await client.get("/metas/", headers=motorista_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestAtualizarMeta:
    async def test_gestor_atualiza_bonus(self, client, db, gestor_headers):
        oid = ObjectId()
        await db["metas_bonus"].insert_one({
            "_id": oid, "tipo": "META 430", "bonus": 50.0, "referencia": "GERAL",
        })
        resp = await client.patch(
            f"/metas/{oid}",
            json={"bonus": 60.0},
            headers=gestor_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["bonus"] == 60.0

    async def test_motorista_nao_atualiza(self, client, db, motorista_headers):
        oid = ObjectId()
        await db["metas_bonus"].insert_one({"_id": oid, "tipo": "META 300", "bonus": 20.0})
        resp = await client.patch(
            f"/metas/{oid}", json={"bonus": 999.0}, headers=motorista_headers
        )
        assert resp.status_code == 403

    async def test_meta_inexistente_retorna_404(self, client, gestor_headers):
        resp = await client.patch(
            f"/metas/{ObjectId()}", json={"bonus": 10.0}, headers=gestor_headers
        )
        assert resp.status_code == 404


class TestDeletarMeta:
    async def test_admin_deleta_meta(self, client, db, admin_headers):
        oid = ObjectId()
        await db["metas_bonus"].insert_one({"_id": oid, "tipo": "META 999", "bonus": 1.0})
        resp = await client.delete(f"/metas/{oid}", headers=admin_headers)
        assert resp.status_code == 204
        doc = await db["metas_bonus"].find_one({"_id": oid})
        assert doc is None

    async def test_gestor_nao_deleta(self, client, db, gestor_headers):
        oid = ObjectId()
        await db["metas_bonus"].insert_one({"_id": oid, "tipo": "META 888", "bonus": 1.0})
        resp = await client.delete(f"/metas/{oid}", headers=gestor_headers)
        assert resp.status_code == 403


class TestCalcularBonus:
    async def test_faturamento_dentro_da_faixa(
        self, client, motorista_user, db, motorista_headers
    ):
        await db["metas_bonus"].insert_many([
            {"_id": ObjectId(), "tipo": "META 430", "faixa_minima": 430.0, "faixa_maxima": 499.99, "bonus": 50.0},
            {"_id": ObjectId(), "tipo": "META 500", "faixa_minima": 500.0, "faixa_maxima": None, "bonus": 75.0},
        ])
        resp = await client.get(
            f"/metas/calcular-bonus/{motorista_user['id']}?faturamento_dia=460.0",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["bonus"] == 50.0

    async def test_faturamento_abaixo_de_todas_as_faixas(
        self, client, motorista_user, db, motorista_headers
    ):
        await db["metas_bonus"].insert_one({
            "_id": ObjectId(), "tipo": "META 430", "faixa_minima": 430.0, "faixa_maxima": None, "bonus": 50.0
        })
        resp = await client.get(
            f"/metas/calcular-bonus/{motorista_user['id']}?faturamento_dia=100.0",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["bonus"] == 0

    async def test_faturamento_na_faixa_superior(
        self, client, motorista_user, db, motorista_headers
    ):
        await db["metas_bonus"].insert_many([
            {"_id": ObjectId(), "tipo": "META 430", "faixa_minima": 430.0, "faixa_maxima": 499.99, "bonus": 50.0},
            {"_id": ObjectId(), "tipo": "META 500", "faixa_minima": 500.0, "faixa_maxima": None, "bonus": 75.0},
        ])
        resp = await client.get(
            f"/metas/calcular-bonus/{motorista_user['id']}?faturamento_dia=600.0",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["bonus"] == 75.0
