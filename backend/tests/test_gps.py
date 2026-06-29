"""
Testes dos endpoints de GPS: /gps/
"""
import pytest
from datetime import datetime, timezone
from bson import ObjectId


class TestRegistrarPontoGPS:
    async def test_registrar_ponto_basico(
        self, client, motorista_user, jornada_aberta, motorista_headers
    ):
        resp = await client.post("/gps/", json={
            "motorista_id": motorista_user["id"],
            "jornada_id": jornada_aberta["_id"],
            "localizacao": {
                "type": "Point",
                "coordinates": [-40.264764, -20.219344],
            },
        }, headers=motorista_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["motorista_id"] == motorista_user["id"]
        assert data["localizacao"]["type"] == "Point"

    async def test_registrar_ponto_com_timestamp(
        self, client, motorista_user, jornada_aberta, motorista_headers
    ):
        ts = datetime.now(timezone.utc).isoformat()
        resp = await client.post("/gps/", json={
            "motorista_id": motorista_user["id"],
            "jornada_id": jornada_aberta["_id"],
            "localizacao": {"type": "Point", "coordinates": [-40.26, -20.21]},
            "timestamp": ts,
        }, headers=motorista_headers)
        assert resp.status_code == 201

    async def test_sem_token_retorna_401(self, client, motorista_user, jornada_aberta):
        resp = await client.post("/gps/", json={
            "motorista_id": motorista_user["id"],
            "jornada_id": jornada_aberta["_id"],
            "localizacao": {"type": "Point", "coordinates": [-40.26, -20.21]},
        })
        assert resp.status_code == 401


class TestHistoricoMotorista:
    async def test_motorista_ve_proprio_historico(
        self, client, motorista_user, jornada_aberta, db, motorista_headers
    ):
        m_id = ObjectId(motorista_user["id"])
        await db["historico_gps"].insert_many([
            {
                "_id": ObjectId(),
                "motorista_id": m_id,
                "jornada_id": jornada_aberta["_id"],
                "localizacao": {"type": "Point", "coordinates": [-40.26, -20.21]},
                "timestamp": datetime.now(timezone.utc),
            },
            {
                "_id": ObjectId(),
                "motorista_id": m_id,
                "jornada_id": jornada_aberta["_id"],
                "localizacao": {"type": "Point", "coordinates": [-40.27, -20.22]},
                "timestamp": datetime.now(timezone.utc),
            },
        ])
        resp = await client.get(
            f"/gps/motorista/{motorista_user['id']}", headers=motorista_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_filtro_por_jornada(
        self, client, motorista_user, jornada_aberta, jornada_encerrada, db, motorista_headers
    ):
        m_id = ObjectId(motorista_user["id"])
        await db["historico_gps"].insert_many([
            {
                "_id": ObjectId(),
                "motorista_id": m_id,
                "jornada_id": jornada_aberta["_id"],
                "localizacao": {"type": "Point", "coordinates": [-40.26, -20.21]},
                "timestamp": datetime.now(timezone.utc),
            },
            {
                "_id": ObjectId(),
                "motorista_id": m_id,
                "jornada_id": jornada_encerrada["_id"],
                "localizacao": {"type": "Point", "coordinates": [-40.27, -20.22]},
                "timestamp": datetime.now(timezone.utc),
            },
        ])
        resp = await client.get(
            f"/gps/motorista/{motorista_user['id']}?jornada_id={jornada_aberta['_id']}",
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        assert all(p["jornada_id"] == jornada_aberta["_id"] for p in resp.json())

    async def test_motorista_nao_ve_historico_de_outro(
        self, client, admin_user, motorista_headers
    ):
        resp = await client.get(
            f"/gps/motorista/{admin_user['id']}", headers=motorista_headers
        )
        assert resp.status_code == 403


class TestAlertasInatividade:
    async def test_somente_gestor_e_admin_acessa(
        self, client, gestor_headers, motorista_headers
    ):
        resp = await client.get("/gps/alertas-inatividade", headers=gestor_headers)
        assert resp.status_code == 200

        resp = await client.get("/gps/alertas-inatividade", headers=motorista_headers)
        assert resp.status_code == 403

    async def test_sem_jornadas_abertas_retorna_lista_vazia(
        self, client, admin_headers
    ):
        resp = await client.get("/gps/alertas-inatividade", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("alertas"), list)

    async def test_retorna_lista(self, client, admin_headers, jornada_aberta):
        resp = await client.get("/gps/alertas-inatividade", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "alertas" in data
        assert "total_alertas" in data


class TestAlertasInatividadeConfiguravel:
    async def test_alerta_com_limiar_configurado(
        self, client, admin_headers, motorista_user, jornada_aberta, db
    ):
        from datetime import timedelta
        # 1. Configurar o limiar de inatividade no perfil do motorista para 5 minutos
        await db["users"].update_one(
            {"_id": ObjectId(motorista_user["id"])},
            {"$set": {"perfil_motorista.limiar_inatividade_minutos": 5}}
        )

        # 2. Inserir pontos de GPS simulando inatividade de 6 minutos atrás
        m_id = ObjectId(motorista_user["id"])
        ts_antigo = datetime.now(timezone.utc) - timedelta(minutes=6)
        await db["historico_gps"].insert_many([
            {
                "motorista_id": m_id,
                "jornada_id": jornada_aberta["_id"],
                "localizacao": {"type": "Point", "coordinates": [-40.264764, -20.219344]},
                "distancia_ultima_m": 10.0,
                "timestamp": ts_antigo,
            },
            {
                "motorista_id": m_id,
                "jornada_id": jornada_aberta["_id"],
                "localizacao": {"type": "Point", "coordinates": [-40.264760, -20.219340]},
                "distancia_ultima_m": 5.0,
                "timestamp": datetime.now(timezone.utc),
            }
        ])

        # 3. Consultar os alertas e verificar se o motorista com o limiar de 5 minutos foi detectado
        resp = await client.get("/gps/alertas-inatividade", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_alertas"] >= 1
        alerta = data["alertas"][0]
        assert alerta["motorista_id"] == motorista_user["id"]
        assert alerta["minutos_parado"] == 5
        assert "Lat: -20.2193, Lon: -40.2648" in alerta["ultima_posicao"]

