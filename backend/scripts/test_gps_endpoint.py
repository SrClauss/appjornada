import httpx
import json

# Correto login password 123456 para a API /auth/login
r = httpx.post("http://localhost:8008/auth/login", data={"username": "motorista@test.com", "password": "123456"})
print("Login status:", r.status_code)
token_data = r.json()
print("Login response:", token_data)
token = token_data.get("access_token")

payload = {
    "motorista_id": "6a3ff9067110907bfff38f53",
    "jornada_id": "60c72b2f9b1d8b2e88a38118",
    "localizacao": {
        "type": "Point",
        "coordinates": [-40.264, -20.219]
    },
    "distancia_ultima_m": 0.0,
    "status": "PARADO"
}

# Consultando com barra
r = httpx.post(
    "http://localhost:8008/gps/",
    headers={"Authorization": f"Bearer {token}"},
    json=payload
)
print("GPS POST status:", r.status_code)
print("GPS POST response:", r.text)
