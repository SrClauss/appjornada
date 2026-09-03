import pytest
from bson import ObjectId
from datetime import datetime, timedelta, timezone

class TestPrecosParticulares:
    async def test_admin_cria_preco_particular(self, client, admin_headers):
        resp = await client.post("/config/precos-particulares", json={
            "nome": "Diurno",
            "hora_inicio": "08:00",
            "hora_fim": "18:00",
            "preco_km": 2.50,
            "preco_minuto": 0.40,
        }, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["nome"] == "Diurno"
        assert data["preco_km"] == 2.50

    async def test_motorista_nao_autorizado_criar(self, client, motorista_headers):
        resp = await client.post("/config/precos-particulares", json={
            "nome": "Noturno",
            "hora_inicio": "18:00",
            "hora_fim": "23:59",
            "preco_km": 3.00,
            "preco_minuto": 0.60,
        }, headers=motorista_headers)
        assert resp.status_code == 403

    async def test_criacao_faixa_sobreposta_retorna_400(self, client, admin_headers):
        # Cria primeira
        await client.post("/config/precos-particulares", json={
            "nome": "Matutino",
            "hora_inicio": "06:00",
            "hora_fim": "12:00",
            "preco_km": 2.00,
            "preco_minuto": 0.50,
        }, headers=admin_headers)

        # Tenta criar faixa sobreposta
        resp = await client.post("/config/precos-particulares", json={
            "nome": "Almoco",
            "hora_inicio": "11:00",
            "hora_fim": "13:00",
            "preco_km": 2.20,
            "preco_minuto": 0.55,
        }, headers=admin_headers)
        assert resp.status_code == 400
        assert "sobrepõe" in resp.json()["detail"]

class TestCorridaParticularCalculo:
    async def test_corrida_particular_fluxo_completo(self, client, db, motorista_user, motorista_headers):
        # 1. Configurar faixa de preço
        # Vamos inserir direto no banco para evitar conflitos de hora no ambiente de teste
        await db["precos_particulares"].insert_one({
            "nome": "Teste Geral",
            "hora_inicio": "00:00",
            "hora_fim": "23:59",
            "preco_km": 3.00,
            "preco_minuto": 1.00,
        })

        # 2. Criar uma jornada aberta
        jornada_id = "test-jornada-particular-id"
        await db["jornadas"].insert_one({
            "_id": jornada_id,
            "motorista_id": motorista_user["id"],
            "veiculo_id": "ABC1D23",
            "status": "ABERTA",
            "data": "2026-06-29",
            "horario": {"inicio": "08:00:00"},
            "corridas_particulares": [],
            "faturamento": {"valor_uber": 0.0, "valor_99": 0.0, "valor_outros": 0.0}
        })

        # 3. Iniciar Corrida Particular
        resp_start = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/iniciar?km_inicio=100.0",
            headers=motorista_headers
        )
        assert resp_start.status_code == 200
        corrida = resp_start.json()
        assert corrida["status"] == "EM_ANDAMENTO"
        assert corrida["km_inicio"] == 100.0
        corrida_id = corrida["id"]

        # 4. Mockar horário de início da corrida para 10 minutos atrás para forçar cálculo de duração
        dez_min_atras = datetime.now(timezone.utc) - timedelta(minutes=10)
        await db["jornadas"].update_one(
            {"_id": jornada_id, "corridas_particulares.id": corrida_id},
            {"$set": {"corridas_particulares.$.horario_inicio": dez_min_atras.isoformat()}}
        )

        # 5. Finalizar Corrida Particular
        resp_end = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/{corrida_id}/finalizar?km_fim=110.0",
            headers=motorista_headers
        )
        assert resp_end.status_code == 200
        dados_finais = resp_end.json()
        assert dados_finais["status"] == "FINALIZADA"
        assert dados_finais["km_fim"] == 110.0
        assert dados_finais["km_rodados"] == 10.0
        # 10 km * R$ 3,00/km = R$ 30,00. 10 min * R$ 1,00/min = R$ 10,00. Total = R$ 40,00
        assert dados_finais["valor_calculado"] >= 40.0

    async def test_corrida_particular_sem_km_fim_com_justificativa(self, client, db, motorista_user, motorista_headers):
        # 1. Configurar faixa de preço
        await db["precos_particulares"].insert_one({
            "nome": "Teste Geral 2",
            "hora_inicio": "00:00",
            "hora_fim": "23:59",
            "preco_km": 3.00,
            "preco_minuto": 1.00,
        })

        # 2. Criar uma jornada aberta
        jornada_id = "test-jornada-particular-id-2"
        await db["jornadas"].insert_one({
            "_id": jornada_id,
            "motorista_id": motorista_user["id"],
            "veiculo_id": "ABC1D23",
            "status": "ABERTA",
            "data": "2026-06-29",
            "horario": {"inicio": "08:00:00"},
            "corridas_particulares": [],
            "faturamento": {"valor_uber": 0.0, "valor_99": 0.0, "valor_outros": 0.0}
        })

        # 3. Iniciar Corrida Particular com destino e mockar google_distancia_km
        resp_start = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/iniciar?km_inicio=100.0&destino_endereco=Av%20Paulista&destino_lat=-23.56&destino_lon=-46.65",
            headers=motorista_headers
        )
        assert resp_start.status_code == 200
        corrida = resp_start.json()
        corrida_id = corrida["id"]

        # Vamos atualizar a corrida no BD para ter google_distancia_km = 8.5 km
        await db["jornadas"].update_one(
            {"_id": jornada_id, "corridas_particulares.id": corrida_id},
            {"$set": {
                "corridas_particulares.$.google_distancia_km": 8.5,
                "corridas_particulares.$.google_duracao_minutos": 12.0
            }}
        )

        # 4. Finalizar sem km_fim e com justificativa (já que é término precoce, mas vamos testar a lógica geral)
        resp_end = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/{corrida_id}/finalizar?justificativa=Terminou%20mais%20cedo",
            headers=motorista_headers
        )
        assert resp_end.status_code == 200
        dados_finais = resp_end.json()
        assert dados_finais["status"] == "FINALIZADA"
        assert dados_finais["km_fim"] == 108.5
        assert dados_finais["km_rodados"] == 8.5
        assert dados_finais["justificativa"] == "Terminou mais cedo"

    async def test_corrida_particular_termino_precoce_sem_justificativa_sucesso(self, client, db, motorista_user, motorista_headers):
        # 1. Criar uma jornada aberta
        jornada_id = "test-jornada-particular-id-3"
        await db["jornadas"].insert_one({
            "_id": jornada_id,
            "motorista_id": motorista_user["id"],
            "veiculo_id": "ABC1D23",
            "status": "ABERTA",
            "data": "2026-06-29",
            "horario": {"inicio": "08:00:00"},
            "corridas_particulares": [],
            "faturamento": {"valor_uber": 0.0, "valor_99": 0.0, "valor_outros": 0.0}
        })

        # 2. Iniciar Corrida Particular
        resp_start = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/iniciar?km_inicio=100.0&destino_endereco=Av%20Paulista&destino_lat=-23.56&destino_lon=-46.65",
            headers=motorista_headers
        )
        assert resp_start.status_code == 200
        corrida = resp_start.json()
        corrida_id = corrida["id"]

        # Vamos atualizar a corrida no BD para ter google_distancia_km = 8.5 km
        await db["jornadas"].update_one(
            {"_id": jornada_id, "corridas_particulares.id": corrida_id},
            {"$set": {
                "corridas_particulares.$.google_distancia_km": 8.5,
                "corridas_particulares.$.google_duracao_minutos": 12.0
            }}
        )

        # 3. Finalizar com km_fim muito menor do que o início + google_distancia_km sem justificativa. Deve ter sucesso agora.
        resp_end = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/{corrida_id}/finalizar?km_fim=102.0",
            headers=motorista_headers
        )
        assert resp_end.status_code == 200
        dados_finais = resp_end.json()
        assert dados_finais["status"] == "FINALIZADA"
        assert dados_finais["km_fim"] == 102.0
        assert dados_finais["km_rodados"] == 2.0

    async def test_corrida_particular_com_faturamento_null(self, client, db, motorista_user, motorista_headers):
        # Testar se encerrar corrida particular funciona quando a jornada tem faturamento: None em vez de objeto
        jornada_id = "test-jornada-faturamento-null"
        await db["jornadas"].insert_one({
            "_id": jornada_id,
            "motorista_id": motorista_user["id"],
            "veiculo_id": "ABC1D23",
            "status": "ABERTA",
            "data": "2026-08-29",
            "horario": {"inicio": "08:00:00"},
            "corridas_particulares": [],
            "faturamento": None
        })

        resp_start = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/iniciar?km_inicio=100.0",
            headers=motorista_headers
        )
        assert resp_start.status_code == 200
        corrida_id = resp_start.json()["id"]

        resp_end = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/{corrida_id}/finalizar?km_fim=110.0",
            headers=motorista_headers
        )
        assert resp_end.status_code == 200
        assert resp_end.json()["status"] == "FINALIZADA"

        jornada_doc = await db["jornadas"].find_one({"_id": jornada_id})
        assert jornada_doc["faturamento"] is not None
        assert "outros" in jornada_doc["faturamento"]

    async def test_corrida_particular_preco_minimo(self, client, db, motorista_user, motorista_headers):
        # 1. Configurar faixa horária com preco_minimo = 15.00
        await db["precos_particulares"].delete_many({})
        await db["precos_particulares"].insert_one({
            "nome": "Faixa Com Minimo",
            "hora_inicio": "00:00",
            "hora_fim": "23:59",
            "preco_km": 1.00,
            "preco_minuto": 0.10,
            "preco_minimo": 15.00
        })

        jornada_id = "test-jornada-preco-minimo"
        await db["jornadas"].insert_one({
            "_id": jornada_id,
            "motorista_id": motorista_user["id"],
            "veiculo_id": "ABC1D23",
            "status": "ABERTA",
            "data": "2026-08-29",
            "horario": {"inicio": "08:00:00"},
            "corridas_particulares": [],
            "faturamento": {}
        })

        resp_start = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/iniciar?km_inicio=100.0",
            headers=motorista_headers
        )
        assert resp_start.status_code == 200
        corrida_id = resp_start.json()["id"]

        # Finalizar com apenas 1 km rodado (calculado daria R$ 1,00 + minutos, menor que R$ 15,00)
        resp_end = await client.post(
            f"/jornadas/{jornada_id}/corridas-particulares/{corrida_id}/finalizar?km_fim=101.0",
            headers=motorista_headers
        )
        assert resp_end.status_code == 200
        dados = resp_end.json()
        assert dados["valor_calculado"] == 15.00




