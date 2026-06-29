import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from bson import ObjectId
from pymongo import ASCENDING, GEOSPHERE

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/appjornada")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)

async def main():
    print(f"Conectando ao MongoDB em {MONGO_URL}...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_default_database()

    print("Limpando todas as coleções do banco de dados...")
    await db["users"].drop()
    await db["veiculos"].drop()
    await db["jornadas"].drop()
    await db["historico_gps"].drop()
    await db["corridas_uber"].drop()
    await db["corridas_99"].drop()

    print("Criando índices...")
    await db["users"].create_index("email", unique=True)
    await db["jornadas"].create_index([("motorista_id", ASCENDING), ("data", ASCENDING)])
    await db["jornadas"].create_index("status")
    await db["historico_gps"].create_index([("motorista_id", ASCENDING), ("timestamp", ASCENDING)])
    await db["historico_gps"].create_index([("localizacao", GEOSPHERE)])

    users = [
        {
            "_id": ObjectId("6a3ff9067110907bfff38f51"),
            "nome": "Carlos Silva",
            "email": "carlos@test.com",
            "senha_hash": hash_senha("123456"),
            "pin_hash": hash_senha("1234"),
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "111.111.111-11",
                "telefone": "27999990001",
                "nivel_id": "N1",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "077 - INTER", "agencia": "1", "conta": "12345-1", "cnpj": "11.111.111/0001-11", "empresa": "Parceiro A LTDA"},
                "limiar_inatividade_minutos": 15
            }
        },
        {
            "_id": ObjectId("6a3ff9067110907bfff38f52"),
            "nome": "Bruno Souza",
            "email": "bruno@test.com",
            "senha_hash": hash_senha("123456"),
            "pin_hash": hash_senha("1234"),
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "222.222.222-22",
                "telefone": "27999990002",
                "nivel_id": "N2",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "260 - NUBANK", "agencia": "1", "conta": "12345-2", "cnpj": "22.222.222/0001-22", "empresa": "Parceiro B LTDA"},
                "limiar_inatividade_minutos": 15
            }
        },
        {
            "_id": ObjectId("6a3ff9067110907bfff38f53"),
            "nome": "Marcos Santos",
            "email": "motorista@test.com",
            "senha_hash": hash_senha("123456"),
            "pin_hash": hash_senha("1234"),
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "333.333.333-33",
                "telefone": "27999990003",
                "nivel_id": "N1",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "341 - ITAU", "agencia": "1", "conta": "12345-3", "cnpj": "33.333.333/0001-33", "empresa": "Parceiro C LTDA"},
                "limiar_inatividade_minutos": 15
            }
        }
    ]

    await db["users"].insert_many(users)
    print(f"{len(users)} usuários semeados com sucesso!")

    # Seed Vehicles
    veiculos = [
        {"_id": "AAA-1A11", "id_placa": "AAA-1A11", "marca_modelo": "Hyundai HB20", "ano_modelo": "2023", "cor": "Prata", "situacao": "RODANDO", "km_atual": 20120.0},
        {"_id": "BBB-2B22", "id_placa": "BBB-2B22", "marca_modelo": "Chevrolet Onix", "ano_modelo": "2022", "cor": "Preto", "situacao": "RODANDO", "km_atual": 15300.0},
        {"_id": "CCC-3C33", "id_placa": "CCC-3C33", "marca_modelo": "Fiat Cronos", "ano_modelo": "2023", "cor": "Branco", "situacao": "RODANDO", "km_atual": 9045.0}
    ]
    await db["veiculos"].insert_many(veiculos)
    print(f"{len(veiculos)} veículos semeados com sucesso!")

if __name__ == "__main__":
    asyncio.run(main())