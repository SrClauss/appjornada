"""
Testes dos endpoints de relatórios: importação CSV e comparativo.
Inclui testes unitários dos parsers _parse_uber_csv e _parse_99_csv.
"""
import io
import pytest
from datetime import date, datetime, timedelta, time

from tests.conftest import UBER_CSV_VALIDO, NOVENOVECSVVALIDO


# ── Testes unitários dos parsers ───────────────────────────────────────────

class TestParseUberCSV:
    def test_duas_linhas_do_mesmo_trip_viram_uma_corrida(self):
        from app.routers.relatorios import _parse_uber_csv

        corridas = _parse_uber_csv(UBER_CSV_VALIDO)
        ids = [c.id_viagem for c in corridas]
        # trip-uber-001 aparece 2x no CSV mas deve gerar 1 registro
        assert ids.count("trip-uber-001") == 1

    def test_gorjeta_somada_ao_total_bruto(self):
        from app.routers.relatorios import _parse_uber_csv

        corridas = _parse_uber_csv(UBER_CSV_VALIDO)
        trip1 = next(c for c in corridas if c.id_viagem == "trip-uber-001")
        assert trip1.tarifa_base == 30.0
        assert trip1.gorjeta == 5.0
        assert trip1.total_bruto == 35.0

    def test_segunda_corrida_importada_separadamente(self):
        from app.routers.relatorios import _parse_uber_csv

        corridas = _parse_uber_csv(UBER_CSV_VALIDO)
        ids = [c.id_viagem for c in corridas]
        assert "trip-uber-002" in ids

    def test_total_corridas(self):
        from app.routers.relatorios import _parse_uber_csv

        corridas = _parse_uber_csv(UBER_CSV_VALIDO)
        assert len(corridas) == 2  # 2 trip_ids únicos

    def test_csv_vazio_retorna_lista_vazia(self):
        from app.routers.relatorios import _parse_uber_csv

        header = (
            "ID da viagem,Nome próprio,E-mail,ID do colaborador,"
            "Endereço de recolha,Endereço de entrega,"
            "Data/Hora de início,Data/Hora de término,"
            "Programa / Grupo,Tipo de transação,Montante da transação,"
            "Moeda,Total de débitos,Outras Promoções,Método de pagamento,URL da fatura\n"
        )
        corridas = _parse_uber_csv(header)
        assert corridas == []


class TestParse99CSV:
    def test_somente_concluidas_importadas(self):
        from app.routers.relatorios import _parse_99_csv

        corridas = _parse_99_csv(NOVENOVECSVVALIDO)
        # CSV tem 3 linhas: 1 Concluída, 1 Cancelada, 1 Concluída de outro motorista
        # Todas as Concluídas devem ser importadas (independente de motorista)
        status_vals = [c.status.lower() for c in corridas]
        assert all("conclu" in s for s in status_vals)

    def test_cancelada_nao_importada(self):
        from app.routers.relatorios import _parse_99_csv

        corridas = _parse_99_csv(NOVENOVECSVVALIDO)
        ids = [c.id_corrida for c in corridas]
        assert "99-002" not in ids  # cancelada

    def test_concluidas_importadas_corretamente(self):
        from app.routers.relatorios import _parse_99_csv

        corridas = _parse_99_csv(NOVENOVECSVVALIDO)
        assert len(corridas) == 2  # 99-001 e 99-003

    def test_campos_corretos(self):
        from app.routers.relatorios import _parse_99_csv

        corridas = _parse_99_csv(NOVENOVECSVVALIDO)
        c1 = next(c for c in corridas if c.id_corrida == "99-001")
        assert c1.distancia_km == 10.5
        assert c1.tarifa_bruta == 40.0
        assert c1.valor_liquido == 32.5

    def test_csv_vazio_retorna_lista_vazia(self):
        from app.routers.relatorios import _parse_99_csv

        header = (
            "ID da Corrida,Nome do Motorista,Centro de Custo,"
            "Data e Hora de Solicitação,Origem,Destino,"
            "Distância Percorrida (km),Duração da Corrida (min),"
            "Tarifa Bruta (R$),Forma de Pagamento,"
            "Taxa de Intermediação (R$),Descontos / Campanhas (R$),"
            "Valor Líquido / Repasse (R$),Status da Corrida\n"
        )
        corridas = _parse_99_csv(header)
        assert corridas == []


# ── Testes de integração: importação via HTTP ──────────────────────────────

class TestImportarUber:
    async def test_importar_csv_uber_sucesso(self, client, gestor_headers):
        arquivo = ("corridas_uber.csv", io.BytesIO(UBER_CSV_VALIDO.encode()), "text/csv")
        resp = await client.post(
            "/relatorios/importar/uber",
            files={"arquivo": arquivo},
            headers=gestor_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["importadas"] == 2  # 2 trip_ids únicos

    async def test_motorista_nao_pode_importar(self, client, motorista_headers):
        arquivo = ("corridas.csv", io.BytesIO(UBER_CSV_VALIDO.encode()), "text/csv")
        resp = await client.post(
            "/relatorios/importar/uber",
            files={"arquivo": arquivo},
            headers=motorista_headers,
        )
        assert resp.status_code == 403

    async def test_importacao_idempotente(self, client, gestor_headers):
        """Importar o mesmo CSV duas vezes não deve duplicar registros."""
        arquivo1 = ("c.csv", io.BytesIO(UBER_CSV_VALIDO.encode()), "text/csv")
        arquivo2 = ("c.csv", io.BytesIO(UBER_CSV_VALIDO.encode()), "text/csv")
        resp1 = await client.post(
            "/relatorios/importar/uber",
            files={"arquivo": arquivo1},
            headers=gestor_headers,
        )
        resp2 = await client.post(
            "/relatorios/importar/uber",
            files={"arquivo": arquivo2},
            headers=gestor_headers,
        )
        assert resp1.json()["importadas"] == resp2.json()["importadas"]

    async def test_csv_sem_corridas_validas_retorna_422(self, client, gestor_headers):
        header_apenas = (
            "ID da viagem,Nome próprio,E-mail,ID do colaborador,"
            "Endereço de recolha,Endereço de entrega,"
            "Data/Hora de início,Data/Hora de término,"
            "Programa / Grupo,Tipo de transação,Montante da transação,"
            "Moeda,Total de débitos,Outras Promoções,Método de pagamento,URL da fatura\n"
        )
        arquivo = ("vazio.csv", io.BytesIO(header_apenas.encode()), "text/csv")
        resp = await client.post(
            "/relatorios/importar/uber",
            files={"arquivo": arquivo},
            headers=gestor_headers,
        )
        assert resp.status_code == 422


class TestImportar99:
    async def test_importar_csv_99_sucesso(self, client, admin_headers):
        arquivo = ("corridas_99.csv", io.BytesIO(NOVENOVECSVVALIDO.encode()), "text/csv")
        resp = await client.post(
            "/relatorios/importar/99",
            files={"arquivo": arquivo},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["importadas"] == 2  # Apenas as Concluídas

    async def test_motorista_nao_pode_importar(self, client, motorista_headers):
        arquivo = ("c.csv", io.BytesIO(NOVENOVECSVVALIDO.encode()), "text/csv")
        resp = await client.post(
            "/relatorios/importar/99",
            files={"arquivo": arquivo},
            headers=motorista_headers,
        )
        assert resp.status_code == 403


class TestComparativo:
    async def test_comparativo_retorna_estrutura_correta(
        self, client, jornada_encerrada, admin_headers
    ):
        ontem = (date.today() - timedelta(days=1)).isoformat()
        resp = await client.get(
            f"/relatorios/comparativo?data={ontem}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "motoristas" in data
        assert isinstance(data["motoristas"], list)

    async def test_comparativo_motorista_nao_acessa(
        self, client, jornada_encerrada, motorista_headers
    ):
        ontem = (date.today() - timedelta(days=1)).isoformat()
        resp = await client.get(
            f"/relatorios/comparativo?data={ontem}",
            headers=motorista_headers,
        )
        assert resp.status_code == 403

    async def test_comparativo_sem_jornadas_retorna_lista_vazia(
        self, client, admin_headers
    ):
        resp = await client.get(
            "/relatorios/comparativo?data=2000-01-01",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["motoristas"] == []

    async def test_comparativo_com_corridas_uber_importadas(
        self, client, db, jornada_encerrada, admin_headers, motorista_user
    ):
        """Corridas Uber importadas devem aparecer no comparativo do dia."""
        ontem = (date.today() - timedelta(days=1))
        inicio_dt = datetime.combine(ontem, time(8, 0, 0))
        fim_dt = datetime.combine(ontem, time(8, 30, 0))

        await db["corridas_uber"].insert_one({
            "id_viagem": "test-uber-cmp-001",
            "nome_motorista": "Motorista Teste",
            "inicio": inicio_dt,
            "fim": fim_dt,
            "tarifa_base": 50.0,
            "gorjeta": 0.0,
            "pedagio": 0.0,
            "ajuste_tarifa": 0.0,
            "total_bruto": 50.0,
            "total_cobrado": 50.0,
            "origem": "A",
            "destino": "B",
        })

        resp = await client.get(
            f"/relatorios/comparativo?data={ontem.isoformat()}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        motoristas = data["motoristas"]
        assert len(motoristas) >= 1
        mot = next((m for m in motoristas if m["motorista_nome"] == "Motorista Teste"), None)
        assert mot is not None
        assert mot["total_corridas_uber"] == 1
        assert mot["faturamento_uber_relatorio"] == 50.0

    async def test_comparativo_gera_alerta_faturamento(
        self, client, db, jornada_encerrada, admin_headers
    ):
        """Delta de faturamento > 5% deve gerar alerta."""
        ontem = (date.today() - timedelta(days=1))
        inicio_dt = datetime.combine(ontem, time(9, 0, 0))
        fim_dt = datetime.combine(ontem, time(9, 30, 0))

        # Faturamento Uber no relatório = 200, mas jornada declarou 150
        await db["corridas_uber"].insert_one({
            "id_viagem": "test-alerta-uber-001",
            "nome_motorista": "Motorista Teste",
            "inicio": inicio_dt,
            "fim": fim_dt,
            "tarifa_base": 200.0,
            "gorjeta": 0.0,
            "pedagio": 0.0,
            "ajuste_tarifa": 0.0,
            "total_bruto": 200.0,
            "total_cobrado": 200.0,
            "origem": "X",
            "destino": "Y",
        })

        resp = await client.get(
            f"/relatorios/comparativo?data={ontem.isoformat()}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        mot = next(
            (m for m in data["motoristas"] if m["motorista_nome"] == "Motorista Teste"),
            None,
        )
        assert mot is not None
        # delta_uber = 200 - 150 = 50, que é 25% > 5% → deve haver alerta
        assert len(mot["alertas"]) >= 1
        assert any("Uber" in a for a in mot["alertas"])

    async def test_comparativo_corridas_sem_jornada_geram_alerta(
        self, client, db, admin_headers
    ):
        """Corridas importadas sem jornada correspondente devem gerar alerta."""
        data_alvo = date(2024, 6, 1)
        inicio_dt = datetime.combine(data_alvo, time(10, 0, 0))

        await db["corridas_99"].insert_one({
            "id_corrida": "99-sem-jornada-001",
            "nome_motorista": "Motorista Sem Jornada",
            "solicitacao": inicio_dt,
            "origem": "A",
            "destino": "B",
            "distancia_km": 5.0,
            "duracao_minutos": 15,
            "tarifa_bruta": 20.0,
            "valor_liquido": 16.0,
            "status": "Concluída",
        })

        resp = await client.get(
            f"/relatorios/comparativo?data={data_alvo.isoformat()}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data_resp = resp.json()
        mot = next(
            (m for m in data_resp["motoristas"] if m["motorista_nome"] == "Motorista Sem Jornada"),
            None,
        )
        assert mot is not None
        assert len(mot["corridas_fora_jornada"]) == 1
        assert mot["corridas_fora_jornada"][0]["motivo"] == "SEM_JORNADA"
        assert any("sem jornada" in a.lower() for a in mot["alertas"])

    async def test_comparativo_filtro_por_motorista_nome(
        self, client, db, admin_headers
    ):
        """filtro motorista_nome deve retornar apenas motoristas cujo nome contém o termo."""
        data_alvo = date(2024, 7, 1)
        inicio_dt = datetime.combine(data_alvo, time(8, 0, 0))

        for nome in ["Ana Motorista", "Carlos Motorista", "Gestor Silva"]:
            await db["corridas_99"].insert_one({
                "id_corrida": f"filtro-{nome}-001",
                "nome_motorista": nome,
                "solicitacao": inicio_dt,
                "origem": "A",
                "destino": "B",
                "distancia_km": 2.0,
                "duracao_minutos": 10,
                "tarifa_bruta": 10.0,
                "valor_liquido": 8.0,
                "status": "Concluída",
            })

        resp = await client.get(
            f"/relatorios/comparativo?data={data_alvo.isoformat()}&motorista_nome=Motorista",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        nomes = [m["motorista_nome"] for m in resp.json()["motoristas"]]
        assert all("Motorista" in n for n in nomes)
        assert "Gestor Silva" not in nomes

    async def test_comparativo_corrida_uber_fora_horario_jornada(
        self, client, db, jornada_encerrada, admin_headers
    ):
        """Corrida Uber fora do horário da jornada deve aparecer como FORA_DO_HORARIO."""
        ontem = (date.today() - timedelta(days=1))
        # Corrida às 22h, mas jornada vai até 17h
        inicio_dt = datetime.combine(ontem, time(22, 0, 0))
        fim_dt = datetime.combine(ontem, time(22, 30, 0))

        await db["corridas_uber"].insert_one({
            "id_viagem": "test-fora-horario-uber-001",
            "nome_motorista": "Motorista Teste",
            "inicio": inicio_dt,
            "fim": fim_dt,
            "tarifa_base": 30.0,
            "gorjeta": 0.0,
            "pedagio": 0.0,
            "ajuste_tarifa": 0.0,
            "total_bruto": 30.0,
            "total_cobrado": 30.0,
            "origem": "A",
            "destino": "B",
        })

        resp = await client.get(
            f"/relatorios/comparativo?data={ontem.isoformat()}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        mot = next(
            (m for m in resp.json()["motoristas"] if m["motorista_nome"] == "Motorista Teste"),
            None,
        )
        assert mot is not None
        foras = mot["corridas_fora_jornada"]
        assert any(f["motivo"] == "FORA_DO_HORARIO" and f["plataforma"] == "UBER" for f in foras)


# ── Testes unitários dos helpers ───────────────────────────────────────────

class TestHelpersRelatorios:
    def test_float_valor_valido(self):
        from app.routers.relatorios import _float
        assert _float("30.50") == 30.50

    def test_float_com_virgula(self):
        from app.routers.relatorios import _float
        assert _float("30,50") == 30.50

    def test_float_string_vazia(self):
        from app.routers.relatorios import _float
        assert _float("") == 0.0
        assert _float("  ") == 0.0

    def test_float_valor_invalido_retorna_zero(self):
        from app.routers.relatorios import _float
        assert _float("nao_e_numero") == 0.0
        assert _float("abc,def") == 0.0

    def test_dt_formato_iso(self):
        from app.routers.relatorios import _dt
        result = _dt("2026-05-15 10:00:00")
        assert result == datetime(2026, 5, 15, 10, 0, 0)

    def test_dt_formato_iso_com_t(self):
        from app.routers.relatorios import _dt
        result = _dt("2026-05-15T10:00:00")
        assert result == datetime(2026, 5, 15, 10, 0, 0)

    def test_dt_formato_br(self):
        from app.routers.relatorios import _dt
        result = _dt("15/05/2026 10:00")
        assert result == datetime(2026, 5, 15, 10, 0)

    def test_dt_formato_invalido_retorna_none(self):
        from app.routers.relatorios import _dt
        assert _dt("nao_e_data") is None
        assert _dt("") is None
        assert _dt("2026/05/15") is None  # formato não suportado

    def test_time_from_str_valido(self):
        from app.routers.relatorios import _time_from_str
        assert _time_from_str("08:30:00") == time(8, 30, 0)
        assert _time_from_str("08:30") == time(8, 30, 0)

    def test_time_from_str_none(self):
        from app.routers.relatorios import _time_from_str
        assert _time_from_str(None) is None
        assert _time_from_str("") is None

    def test_corrida_dentro_jornada_dentro(self):
        from app.routers.relatorios import _corrida_dentro_jornada
        jornada = {"horario": {"inicio": "08:00:00", "fim": "17:00:00"}}
        corrida_inicio = datetime(2026, 5, 15, 10, 0, 0)
        assert _corrida_dentro_jornada(corrida_inicio, None, jornada) is True

    def test_corrida_dentro_jornada_fora(self):
        from app.routers.relatorios import _corrida_dentro_jornada
        jornada = {"horario": {"inicio": "08:00:00", "fim": "17:00:00"}}
        corrida_inicio = datetime(2026, 5, 15, 22, 0, 0)
        assert _corrida_dentro_jornada(corrida_inicio, None, jornada) is False

    def test_corrida_dentro_jornada_sem_fim(self):
        """Jornada sem fim definido: corrida é válida se após o início."""
        from app.routers.relatorios import _corrida_dentro_jornada
        jornada = {"horario": {"inicio": "08:00:00", "fim": None}}
        corrida_antes = datetime(2026, 5, 15, 6, 0, 0)
        corrida_depois = datetime(2026, 5, 15, 10, 0, 0)
        assert _corrida_dentro_jornada(corrida_antes, None, jornada) is False
        assert _corrida_dentro_jornada(corrida_depois, None, jornada) is True

    def test_corrida_dentro_jornada_sem_horario(self):
        """Jornada sem horario definido retorna False."""
        from app.routers.relatorios import _corrida_dentro_jornada
        jornada = {"horario": None}
        corrida_inicio = datetime(2026, 5, 15, 10, 0, 0)
        assert _corrida_dentro_jornada(corrida_inicio, None, jornada) is False

    def test_parse_uber_csv_linha_sem_inicio_ignorada(self):
        """Linhas com Data/Hora de início vazia devem ser ignoradas."""
        from app.routers.relatorios import _parse_uber_csv
        csv_com_linha_invalida = (
            "ID da viagem,Nome próprio,E-mail,ID do colaborador,"
            "Endereço de recolha,Endereço de entrega,"
            "Data/Hora de início,Data/Hora de término,"
            "Programa / Grupo,Tipo de transação,Montante da transação,"
            "Moeda,Total de débitos,Outras Promoções,Método de pagamento,URL da fatura\n"
            "trip-invalido,Motorista X,x@test.com,F01,"
            "A,B,,,"
            ",Tarifa base,10.00,BRL,10.00,0.0,Uber_Conta,\n"
        )
        corridas = _parse_uber_csv(csv_com_linha_invalida)
        assert len(corridas) == 0

    def test_parse_uber_csv_ajuste_de_tarifa(self):
        """Tipo 'Ajuste de Tarifa' deve ser somado ao ajuste_tarifa."""
        from app.routers.relatorios import _parse_uber_csv
        csv = (
            "ID da viagem,Nome próprio,E-mail,ID do colaborador,"
            "Endereço de recolha,Endereço de entrega,"
            "Data/Hora de início,Data/Hora de término,"
            "Programa / Grupo,Tipo de transação,Montante da transação,"
            "Moeda,Total de débitos,Outras Promoções,Método de pagamento,URL da fatura\n"
            "trip-ajuste-001,Motorista X,x@test.com,F01,"
            "A,B,"
            "2026-05-15 10:00:00,2026-05-15 10:30:00,"
            "Grupo A,Tarifa base,25.00,BRL,25.00,0.0,Uber_Conta,\n"
            "trip-ajuste-001,Motorista X,x@test.com,F01,"
            "A,B,"
            "2026-05-15 10:00:00,2026-05-15 10:30:00,"
            "Grupo A,Ajuste de Tarifa,5.00,BRL,30.00,0.0,Uber_Conta,\n"
        )
        corridas = _parse_uber_csv(csv)
        assert len(corridas) == 1
        assert corridas[0].ajuste_tarifa == 5.0
        assert corridas[0].total_bruto == 30.0  # tarifa_base + ajuste

    def test_parse_uber_csv_pedagio(self):
        """Tipo 'Pedágio' deve ser somado ao pedagio mas não ao total_bruto."""
        from app.routers.relatorios import _parse_uber_csv
        csv = (
            "ID da viagem,Nome próprio,E-mail,ID do colaborador,"
            "Endereço de recolha,Endereço de entrega,"
            "Data/Hora de início,Data/Hora de término,"
            "Programa / Grupo,Tipo de transação,Montante da transação,"
            "Moeda,Total de débitos,Outras Promoções,Método de pagamento,URL da fatura\n"
            "trip-ped-001,Motorista Y,y@test.com,F02,"
            "C,D,"
            "2026-05-15 11:00:00,2026-05-15 11:30:00,"
            "Grupo B,Tarifa base,20.00,BRL,20.00,0.0,Uber_Conta,\n"
            "trip-ped-001,Motorista Y,y@test.com,F02,"
            "C,D,"
            "2026-05-15 11:00:00,2026-05-15 11:30:00,"
            "Grupo B,Pedágio,3.00,BRL,23.00,0.0,Uber_Conta,\n"
        )
        corridas = _parse_uber_csv(csv)
        assert len(corridas) == 1
        assert corridas[0].pedagio == 3.0
        assert corridas[0].total_bruto == 20.0  # pedágio não entra no bruto
