import os
from pymongo import MongoClient

# Carrega do .env se existir (no diretório do script ou no diretório pai backend)
for candidate in [os.path.join(os.path.dirname(__file__), ".env"), os.path.join(os.path.dirname(__file__), "..", ".env")]:
    if os.path.exists(candidate):
        with open(candidate) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2:
                        key, val = parts
                        os.environ.setdefault(key, val)
        break

# Pega o MONGO_URL do env
mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/appjornada")
if "mongodb://mongo:" in mongo_url and not os.path.exists("/.dockerenv"):
    # Se rodar fora do docker, substitui 'mongo' por 'localhost'
    mongo_url = mongo_url.replace("mongodb://mongo:", "mongodb://localhost:")

print(f"Conectando ao banco de dados em: {mongo_url}")

client = MongoClient(mongo_url)
db = client.get_default_database()

# 1. Limpar coleções a serem esvaziadas
collections_to_clear = [
    "jornadas",
    "historico_gps",
    "gps",
    "auditorias",
    "auditoria",
    "manutencoes",
    "metas",
    "corridas_uber",
    "corridas_99",
    "corridas_particulares",
]

for col in collections_to_clear:
    count = db[col].delete_many({}).deleted_count
    print(f"Coleção '{col}': {count} registros removidos.")

# 2. Em 'users', apagar todos os MOTORISTAS exceto o com nome/email contendo 'clausemberg'
# E manter administradores / gestores
users_col = db["users"]
# Vamos ver quem está cadastrado primeiro
all_users = list(users_col.find({}))
print("\nUsuários existentes antes da limpeza:")
for u in all_users:
    print(f"- Nome: {u.get('nome')}, Email: {u.get('email')}, Role: {u.get('role')}")

# Identifica clausemberg
clausemberg_user = users_col.find_one({
    "$or": [
        {"email": {"$regex": "clausemberg", "$options": "i"}},
        {"nome": {"$regex": "clausemberg", "$options": "i"}}
    ]
})

if not clausemberg_user:
    print("\nAVISO: Usuário 'clausemberg' não encontrado!")
else:
    print(f"\nUsuário 'clausemberg' encontrado: ID={clausemberg_user['_id']}, Nome={clausemberg_user['nome']}")

# Deleta todos os motoristas exceto clausemberg
delete_filter = {
    "role": "MOTORISTA"
}
if clausemberg_user:
    delete_filter["_id"] = {"$ne": clausemberg_user["_id"]}

deleted_drivers = users_col.delete_many(delete_filter).deleted_count
print(f"Motoristas removidos (exceto clausemberg): {deleted_drivers}")

# 3. Veículos (carros) — o usuário pediu: "deixe também os carros"
# Então NÃO limpamos a coleção 'veiculos'
veiculos_count = db["veiculos"].count_documents({})
print(f"Coleção 'veiculos' mantida intacta com {veiculos_count} carros.")

print("\nLimpeza de banco concluída!")
