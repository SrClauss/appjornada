"""
Testes dos endpoints de veículos: /veiculos/
"""
import pytest


class TestCriarVeiculo:
    async def test_admin_cria_veiculo(self, client, admin_headers):
        resp = await client.post("/veiculos/", json={
            "id_placa": "ABC1D23",
            "marca_modelo": "VW/GOL",
            "cor": "PRATA",
        }, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id_placa"] == "ABC1D23"
        assert data["situacao"] == "RODANDO"

    async def test_gestor_cria_veiculo(self, client, gestor_headers):
        resp = await client.post("/veiculos/", json={
            "id_placa": "XYZ9K88",
            "marca_modelo": "HYU/HB20",
            "cor": "AZUL",
        }, headers=gestor_headers)
        assert resp.status_code == 201

    async def test_motorista_nao_pode_criar(self, client, motorista_headers):
        resp = await client.post("/veiculos/", json={
            "id_placa": "MOT1234",
            "marca_modelo": "FIAT/MOBI",
            "cor": "BRANCO",
        }, headers=motorista_headers)
        assert resp.status_code == 403

    async def test_sem_token_retorna_401(self, client):
        resp = await client.post("/veiculos/", json={
            "id_placa": "SEM1234",
            "marca_modelo": "X",
            "cor": "X",
        })
        assert resp.status_code == 401

    async def test_placa_duplicada_retorna_409(self, client, veiculo, admin_headers):
        resp = await client.post("/veiculos/", json={
            "id_placa": "TST1A23",  # já criado pela fixture
            "marca_modelo": "OUTRO",
            "cor": "PRETO",
        }, headers=admin_headers)
        assert resp.status_code == 409


class TestListarVeiculos:
    async def test_motorista_lista_veiculos(self, client, veiculo, motorista_headers):
        resp = await client.get("/veiculos/", headers=motorista_headers)
        assert resp.status_code == 200
        placas = [v["id_placa"] for v in resp.json()]
        assert "TST1A23" in placas

    async def test_filtro_por_situacao(self, client, veiculo, admin_headers):
        resp = await client.get("/veiculos/?situacao=RODANDO", headers=admin_headers)
        assert resp.status_code == 200
        assert all(v["situacao"] == "RODANDO" for v in resp.json())


class TestGetVeiculo:
    async def test_admin_ve_veiculo(self, client, veiculo, admin_headers):
        resp = await client.get(f"/veiculos/{veiculo['id_placa']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id_placa"] == "TST1A23"

    async def test_motorista_ve_veiculo(self, client, veiculo, motorista_headers):
        resp = await client.get(f"/veiculos/{veiculo['id_placa']}", headers=motorista_headers)
        assert resp.status_code == 200

    async def test_placa_inexistente_retorna_404(self, client, admin_headers):
        resp = await client.get("/veiculos/NAOEXI", headers=admin_headers)
        assert resp.status_code == 404


class TestAtualizarVeiculo:
    async def test_gestor_atualiza_km(self, client, veiculo, gestor_headers):
        resp = await client.patch(
            f"/veiculos/{veiculo['id_placa']}",
            json={"km_atual": 55000.0},
            headers=gestor_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["km_atual"] == 55000.0

    async def test_motorista_nao_atualiza(self, client, veiculo, motorista_headers):
        resp = await client.patch(
            f"/veiculos/{veiculo['id_placa']}",
            json={"km_atual": 55000.0},
            headers=motorista_headers,
        )
        assert resp.status_code == 403


class TestDeletarVeiculo:
    async def test_admin_deleta_veiculo(self, client, veiculo, admin_headers, db):
        resp = await client.delete(
            f"/veiculos/{veiculo['id_placa']}", headers=admin_headers
        )
        assert resp.status_code == 204
        doc = await db["veiculos"].find_one({"_id": "TST1A23"})
        assert doc is None

    async def test_gestor_nao_deleta(self, client, veiculo, gestor_headers):
        resp = await client.delete(
            f"/veiculos/{veiculo['id_placa']}", headers=gestor_headers
        )
        assert resp.status_code == 403
