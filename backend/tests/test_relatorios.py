"""
Testes dos endpoints de relatórios: importação CSV e comparativo.
Inclui testes unitários dos parsers _parse_uber_csv e _parse_99_csv.
"""
import io
import pytest
from datetime import date, timedelta

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
