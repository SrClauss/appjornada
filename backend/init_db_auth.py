import os
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, GEOSPHERE

# Carrega do .env se existir
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split("=", 1)
                if len(parts) == 2:
                    key, val = parts
                    os.environ.setdefault(key, val)

# Pega o MONGO_URL do env
mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/appjornada")
if "mongodb://mongo:" in mongo_url and not os.path.exists("/.dockerenv"):
    mongo_url = mongo_url.replace("mongodb://mongo:", "mongodb://localhost:")

print(f"Conectando ao MongoDB em: {mongo_url}")
client = MongoClient(mongo_url)
db = client.get_default_database()

# 1. Limpar banco de dados
print("Limpando dados anteriores...")
collections = [
    "users", "jornadas", "historico_gps", "gps", 
    "auditorias", "auditoria", "manutencoes", "metas", 
    "corridas_uber", "corridas_99", "corridas_particulares", "veiculos"
]

for col in collections:
    db[col].drop()
    print(f"Coleção '{col}' limpa.")

# 2. Criar índices
print("Criando índices...")
db["users"].create_index("email", unique=True)
db["jornadas"].create_index([("motorista_id", ASCENDING), ("data", ASCENDING)])
db["jornadas"].create_index("status")
db["historico_gps"].create_index([("motorista_id", ASCENDING), ("timestamp", ASCENDING)])
db["historico_gps"].create_index([("localizacao", GEOSPHERE)])
db["veiculos"].create_index("id_placa", unique=True)

# 3. Inserir Usuários (Admin e Clausemberg)
drivers_data = [
    {
        "_id": ObjectId("6a403ff7734db0687aa06ee1"),
        "nome": "Admin",
        "email": "admin@admin.com",
        "senha_hash": "$2b$12$mJdkPTweFJfPoVmNPiC56eG90uekBKrq/2ngjQm/hRc7JtaDVBVHS", # senha: admin
        "pin_hash": None,
        "role": "ADMIN",
        "situacao": "Ativo",
        "perfil_motorista": None
    },
    {
        "_id": ObjectId("6a40670ec7008f9c4eeb44e2"),
        "nome": "Clausemberg Rodrigues de Olvierira",
        "email": "clausemberg@yahoo.com.br",
        "senha_hash": "$2b$12$2OWrXjry1kOAOidIHbrkyuqCukhwTuUZv/JHusciFjoJ8V5WapfIO", # senha: admin
        "pin_hash": "$2b$12$dgHe73q3RrPBNxYz/NKnuuyFIvu92FyMwGCdIfoY571.WfENo9/Le", # PIN: 1234
        "role": "MOTORISTA",
        "situacao": "Ativo",
        "perfil_motorista": {
            "cpf": "777.777.777-77", "telefone": "27999990007", "nivel_id": "N1",
            "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
            "dados_bancarios": {"banco": "077 - INTER", "agencia": "1", "conta": "12345-7", "cnpj": "77.777.777/0001-77", "empresa": "Parceiro Clausemberg LTDA"},
            "limiar_inatividade_minutos": 15
        }
    }
]
db["users"].insert_many(drivers_data)
print("Usuários Admin e Clausemberg inseridos!")

# 4. Inserir Veículos
veiculos_data = [
    {"_id": "AAA-1A11", "id_placa": "AAA-1A11", "marca_modelo": "Hyundai HB20", "ano_modelo": "2023", "cor": "Prata", "situacao": "RODANDO", "km_atual": 20120.0},
    {"_id": "BBB-2B22", "id_placa": "BBB-2B22", "marca_modelo": "Chevrolet Onix", "ano_modelo": "2022", "cor": "Preto", "situacao": "RODANDO", "km_atual": 15300.0},
    {"_id": "CCC-3C33", "id_placa": "CCC-3C33", "marca_modelo": "Fiat Cronos", "ano_modelo": "2023", "cor": "Branco", "situacao": "RODANDO", "km_atual": 9045.0},
    {"_id": "DDD-4D44", "id_placa": "DDD-4D44", "marca_modelo": "Toyota Yaris", "ano_modelo": "2023", "cor": "Cinza", "situacao": "RODANDO", "km_atual": 43550.0},
    {"_id": "EEE-5E55", "id_placa": "EEE-5E55", "marca_modelo": "Renault Logan", "ano_modelo": "2021", "cor": "Branco", "situacao": "RODANDO", "km_atual": 27250.0}
]
db["veiculos"].insert_many(veiculos_data)
print("5 Veículos inseridos!")

print("Banco de dados reinicializado com sucesso!")
