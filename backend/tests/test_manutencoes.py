"""
Testes dos endpoints de manutenções: /manutencoes/
"""
import pytest
from bson import ObjectId


class TestCriarManutencao:
    async def test_qualquer_autenticado_registra(
        self, client, veiculo, motorista_user, motorista_headers
    ):
        resp = await client.post("/manutencoes/", json={
            "veiculo_id": "TST1A23",
            "motorista_id": motorista_user["id"],
            "entrada": "2026-05-15T08:00:00",
            "oficina": "Auto Center",
            "servico": {"descricao": "Troca de óleo", "valor": 150.0},
        }, headers=motorista_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["veiculo_id"] == "TST1A23"
        assert data["oficina"] == "Auto Center"

    async def test_sem_token_retorna_401(self, client, veiculo):
        resp = await client.post("/manutencoes/", json={
            "veiculo_id": "TST1A23",
            "tipo": "CORRETIVA",
        })
        assert resp.status_code == 401


class TestListarManutencoes:
    async def test_motorista_ve_apenas_proprias(
        self, client, motorista_user, gestor_user, motorista_headers, admin_headers, db
    ):
        """Motorista só vê manutenções ligadas ao seu ID."""
        m_id = ObjectId(motorista_user["id"])
        g_id = ObjectId(gestor_user["id"])

        await db["manutencoes"].insert_many([
            {"_id": ObjectId(), "veiculo_id": "TST1A23", "motorista_id": m_id, "tipo": "PREVENTIVA"},
            {"_id": ObjectId(), "veiculo_id": "TST1A23", "motorista_id": g_id, "tipo": "CORRETIVA"},
        ])

        resp = await client.get("/manutencoes/", headers=motorista_headers)
        assert resp.status_code == 200
        for item in resp.json():
            assert str(item["motorista_id"]) == motorista_user["id"]

    async def test_admin_ve_todas(self, client, motorista_user, db, admin_headers):
        await db["manutencoes"].insert_many([
            {"_id": ObjectId(), "veiculo_id": "T1", "motorista_id": ObjectId(motorista_user["id"]), "tipo": "A"},
            {"_id": ObjectId(), "veiculo_id": "T2", "motorista_id": ObjectId(), "tipo": "B"},
        ])
        resp = await client.get("/manutencoes/", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_filtro_por_veiculo(self, client, db, admin_headers):
        await db["manutencoes"].insert_many([
            {"_id": ObjectId(), "veiculo_id": "PLACA1", "tipo": "PREVENTIVA"},
            {"_id": ObjectId(), "veiculo_id": "PLACA2", "tipo": "PREVENTIVA"},
        ])
        resp = await client.get("/manutencoes/?veiculo_id=PLACA1", headers=admin_headers)
        assert resp.status_code == 200
        assert all(m["veiculo_id"] == "PLACA1" for m in resp.json())


class TestGetManutencao:
    async def test_get_por_id(self, client, db, admin_headers):
        oid = ObjectId()
        await db["manutencoes"].insert_one({
            "_id": oid, "veiculo_id": "TST1A23", "tipo": "PREVENTIVA"
        })
        resp = await client.get(f"/manutencoes/{oid}", headers=admin_headers)
        assert resp.status_code == 200

    async def test_id_inexistente_retorna_404(self, client, admin_headers):
        resp = await client.get(f"/manutencoes/{ObjectId()}", headers=admin_headers)
        assert resp.status_code == 404


class TestAtualizarManutencao:
    async def test_gestor_atualiza_saida(self, client, db, gestor_headers):
        oid = ObjectId()
        await db["manutencoes"].insert_one({
            "_id": oid, "veiculo_id": "TST1A23", "tipo": "PREVENTIVA"
        })
        resp = await client.patch(
            f"/manutencoes/{oid}",
            json={"saida": "2026-05-16T10:00:00", "custo_total": 300.0},
            headers=gestor_headers,
        )
        assert resp.status_code == 200

    async def test_motorista_nao_atualiza(self, client, db, motorista_headers):
        oid = ObjectId()
        await db["manutencoes"].insert_one({
            "_id": oid, "veiculo_id": "TST1A23", "tipo": "PREVENTIVA"
        })
        resp = await client.patch(
            f"/manutencoes/{oid}",
            json={"custo_total": 999.0},
            headers=motorista_headers,
        )
        assert resp.status_code == 403
