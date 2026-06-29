"""
Fixtures compartilhadas para toda a suite de testes.

Dependências necessárias (instalar uma vez):
    pip install mongomock-motor pytest-asyncio httpx

A suite usa:
- mongomock-motor: banco MongoDB totalmente em memória, sem conexão real
- httpx.AsyncClient + ASGITransport: cliente HTTP assíncrono para testar FastAPI
- dependency_overrides: substitui get_db() pelo banco em memória em cada teste
"""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

from app.main import app
from app.db.database import get_db
from app.core.security import hash_senha, criar_access_token


# ── Helpers ────────────────────────────────────────────────────────────────

def extract_id(data: dict) -> str:
    """Extrai o ID de uma resposta JSON, suportando 'id' e '_id'."""
    return str(data.get("id") or data.get("_id", ""))


# ── Banco em memória ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    """Banco MongoDB em memória isolado por teste."""
    client = AsyncMongoMockClient()
    yield client["appjornada"]


# ── Cliente HTTP ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db):
    """
    AsyncClient apontado para o app FastAPI.
    - Sobrescreve get_db com o banco em memória.
    - Mocka connect_db / close_db e o scheduler para não tocar no MongoDB real.
    """
    app.dependency_overrides[get_db] = lambda: db

    with (
        patch("app.main.connect_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        patch("app.main.criar_scheduler") as mock_sched,
    ):
        mock_sched.return_value.start = lambda: None
        mock_sched.return_value.shutdown = lambda **kw: None

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Usuários ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(db):
    uid = ObjectId()
    await db["users"].insert_one({
        "_id": uid,
        "nome": "Admin Teste",
        "email": "admin@test.com",
        "senha_hash": hash_senha("senha123"),
        "pin_hash": hash_senha("0000"),
        "role": "ADMIN",
        "situacao": "Ativo",
        "perfil_motorista": None,
    })
    return {"id": str(uid), "nome": "Admin Teste", "email": "admin@test.com", "role": "ADMIN"}


@pytest_asyncio.fixture
async def gestor_user(db):
    uid = ObjectId()
    await db["users"].insert_one({
        "_id": uid,
        "nome": "Gestor Teste",
        "email": "gestor@test.com",
        "senha_hash": hash_senha("senha123"),
        "pin_hash": None,
        "role": "GESTOR",
        "situacao": "Ativo",
        "perfil_motorista": None,
    })
    return {"id": str(uid), "nome": "Gestor Teste", "email": "gestor@test.com", "role": "GESTOR"}


@pytest_asyncio.fixture
async def motorista_user(db):
    uid = ObjectId()
    await db["users"].insert_one({
        "_id": uid,
        "nome": "Motorista Teste",
        "email": "motorista@test.com",
        "senha_hash": hash_senha("senha123"),
        "pin_hash": hash_senha("1234"),
        "role": "MOTORISTA",
        "situacao": "Ativo",
        "perfil_motorista": {
            "cpf": "111.111.111-11",
            "telefone": "27999999999",
            "nivel_id": "N1",
            "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
            "dados_bancarios": {
                "banco": "077 - INTER",
                "agencia": "1",
                "conta": "12345678-9",
                "operador": None,
                "cnpj": "11.111.111/0001-11",
                "empresa": "Empresa Teste LTDA",
            },
        },
    })
    return {
        "id": str(uid),
        "nome": "Motorista Teste",
        "email": "motorista@test.com",
        "role": "MOTORISTA",
    }


# ── Cabeçalhos de autenticação ─────────────────────────────────────────────

@pytest.fixture
def admin_headers(admin_user):
    token = criar_access_token({"sub": admin_user["id"], "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def gestor_headers(gestor_user):
    token = criar_access_token({"sub": gestor_user["id"], "role": "GESTOR"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def motorista_headers(motorista_user):
    token = criar_access_token({"sub": motorista_user["id"], "role": "MOTORISTA"})
    return {"Authorization": f"Bearer {token}"}


# ── Veículo ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def veiculo(db):
    doc = {
        "_id": "TST1A23",
        "id_placa": "TST1A23",
        "marca_modelo": "FIAT/UNO ATTRACTIVE 1.0",
        "ano_modelo": "2022/2022",
        "cor": "BRANCO",
        "situacao": "RODANDO",
        "km_atual": 50000.0,
        "vencimento_ipva": None,
        "imagem_clrv_url": None,
    }
    await db["veiculos"].insert_one(dict(doc))
    return doc


# ── Jornada aberta ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def jornada_aberta(db, motorista_user, veiculo):
    today = date.today().isoformat()
    jornada_id = f"Motorista Teste-TST1A23-16052026080000"
    doc = {
        "_id": jornada_id,
        "data": today,
        "motorista_id": ObjectId(motorista_user["id"]),
        "veiculo_id": "TST1A23",
        "status": "ABERTA",
        "pin": "1234",
        "km": {"inicial": 50000.0, "final": None, "rodados": None, "morta": 0.0},
        "localizacao_inicial": {"lat": -20.219344, "lon": -40.264764},
        "localizacao_final": None,
        "horario": {"inicio": "08:00:00", "fim": None, "total_horas_segundos": None},
        "fotos": {"km_inicial_url": None, "km_final_url": None},
        "faturamento": {
            "uber": 0.0, "noventa_nove": 0.0, "outros": 0.0, "total_dia": 0.0,
            "comprovante_uber_url": None, "comprovante_99_url": None,
            "comprovante_outros_url": None,
        },
        "jornada_diaria_clt": 8.0,
        "jornada_semanal_clt": 44.0,
        "jornada_mensal_clt": 220.0,
        "saldo_horas_dia": None,
        "bonus_dia": 0.0,
        "faturamento_acumulado_semana": None,
        "bonus_acumulado_semana": None,
        "faturamento_acumulado_mes": None,
        "bonus_acumulado_mes": None,
        "observacoes": None,
        "uso_pessoal": False,
        "comprovante_uso_pessoal_url": None,
        "justificativa_uso_pessoal": None,
        "pausas": [],
        "abastecimentos": [],
        "sinistros": [],
    }
    await db["jornadas"].insert_one(dict(doc))
    return doc


# ── Jornada encerrada (para testes de resumo CLT) ──────────────────────────

@pytest_asyncio.fixture
async def jornada_encerrada(db, motorista_user, veiculo):
    ontem = (date.today() - timedelta(days=1)).isoformat()
    jornada_id = f"Motorista Teste-TST1A23-ontem"
    doc = {
        "_id": jornada_id,
        "data": ontem,
        "motorista_id": ObjectId(motorista_user["id"]),
        "veiculo_id": "TST1A23",
        "status": "ENCERRADA",
        "pin": "1234",
        "km": {"inicial": 50000.0, "final": 50200.0, "rodados": 200.0, "morta": 0.0},
        "localizacao_inicial": {"lat": -20.21, "lon": -40.26},
        "localizacao_final": {"lat": -20.22, "lon": -40.27},
        "horario": {
            "inicio": "08:00:00",
            "fim": "17:00:00",
            "total_horas_segundos": 32400,  # 9 horas
        },
        "fotos": {"km_inicial_url": None, "km_final_url": None},
        "faturamento": {
            "uber": 150.0, "noventa_nove": 100.0, "outros": 0.0, "total_dia": 250.0,
            "comprovante_uber_url": None, "comprovante_99_url": None,
            "comprovante_outros_url": None,
        },
        "jornada_diaria_clt": 8.0,
        "jornada_semanal_clt": 44.0,
        "jornada_mensal_clt": 220.0,
        "saldo_horas_dia": 1.0,
        "bonus_dia": 0.0,
        "faturamento_acumulado_semana": 250.0,
        "bonus_acumulado_semana": 0.0,
        "faturamento_acumulado_mes": 250.0,
        "bonus_acumulado_mes": 0.0,
        "observacoes": None,
        "uso_pessoal": False,
        "comprovante_uso_pessoal_url": None,
        "justificativa_uso_pessoal": None,
        "pausas": [],
        "abastecimentos": [],
        "sinistros": [],
    }
    await db["jornadas"].insert_one(dict(doc))
    return doc


# ── CSVs de exemplo ────────────────────────────────────────────────────────

UBER_CSV_VALIDO = (
    "ID da viagem,Nome próprio,E-mail,ID do colaborador,"
    "Endereço de recolha,Endereço de entrega,"
    "Data/Hora de início,Data/Hora de término,"
    "Programa / Grupo,Tipo de transação,Montante da transação,"
    "Moeda,Total de débitos,Outras Promoções,Método de pagamento,URL da fatura\n"
    # trip-001: 2 linhas (Tarifa base + Gorjeta) → deve ser agrupada
    "trip-uber-001,Motorista Teste,mot@test.com,FROTA_01,"
    "Origem A,Destino B,"
    "2026-05-15 10:00:00,2026-05-15 10:30:00,"
    "Grupo A,Tarifa base,30.00,BRL,30.00,0.0,Uber_Conta,https://r.uber.com/1\n"
    "trip-uber-001,Motorista Teste,mot@test.com,FROTA_01,"
    "Origem A,Destino B,"
    "2026-05-15 10:00:00,2026-05-15 10:30:00,"
    "Grupo A,Gorjeta,5.00,BRL,35.00,0.0,Uber_Conta,https://r.uber.com/1\n"
    # trip-002: linha única
    "trip-uber-002,Outro Motorista,outro@test.com,FROTA_02,"
    "Origem C,Destino D,"
    "2026-05-15 11:00:00,2026-05-15 11:20:00,"
    "Grupo B,Tarifa base,20.00,BRL,20.00,0.0,Uber_Conta,https://r.uber.com/2\n"
)

NOVENOVECSVVALIDO = (
    "ID da Corrida,Nome do Motorista,Centro de Custo,"
    "Data e Hora de Solicitação,Origem,Destino,"
    "Distância Percorrida (km),Duração da Corrida (min),"
    "Tarifa Bruta (R$),Forma de Pagamento,"
    "Taxa de Intermediação (R$),Descontos / Campanhas (R$),"
    "Valor Líquido / Repasse (R$),Status da Corrida\n"
    # concluída — deve ser importada
    "99-001,Motorista Teste,VEICULO_01,"
    "2026-05-15 08:00:00,Origem A,Destino B,"
    "10.5,25,40.0,Cartao_Maquininha,-7.5,0.0,32.5,Concluída\n"
    # cancelada — NÃO deve ser importada
    "99-002,Motorista Teste,VEICULO_01,"
    "2026-05-15 09:00:00,Origem C,Destino D,"
    "0.0,0,6.0,Dinheiro,-1.2,0.0,4.8,Cancelada_Pelo_Passageiro\n"
    # outro motorista, concluída
    "99-003,Outro Motorista,VEICULO_02,"
    "2026-05-15 10:00:00,Origem E,Destino F,"
    "15.0,35,55.0,Voucher_App,-9.0,0.0,46.0,Concluída\n"
)
