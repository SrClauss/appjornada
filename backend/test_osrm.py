import httpx
import asyncio

POIS = [
    {"id": 1, "nome": "Igreja Velha", "lat": -18.7214, "lon": -39.8551},
    {"id": 2, "nome": "Catedral de São Mateus", "lat": -18.7205, "lon": -39.8543},
    {"id": 3, "nome": "Sítio Histórico", "lat": -18.7221, "lon": -39.8562},
    {"id": 4, "nome": "Museu Municipal", "lat": -18.7230, "lon": -39.8545},
    {"id": 5, "nome": "Praça Mesquita Neto", "lat": -18.7185, "lon": -39.8571},
    {"id": 6, "nome": "Igreja São Benedito", "lat": -18.7202, "lon": -39.8580},
    {"id": 7, "nome": "Mercado Municipal", "lat": -18.7191, "lon": -39.8555},
    {"id": 8, "nome": "Praça São Benedito", "lat": -18.7211, "lon": -39.8585},
    {"id": 9, "nome": "Shopping São Mateus", "lat": -18.7150, "lon": -39.8500},
    {"id": 10, "nome": "Rio Cricaré", "lat": -18.7240, "lon": -39.8590},
    {"id": 11, "nome": "Praia de Guriri", "lat": -18.7100, "lon": -39.7500},
    {"id": 12, "nome": "Projeto Tamar (Guriri)", "lat": -18.7150, "lon": -39.7520},
    {"id": 13, "nome": "Guriri Beach Acqua Park", "lat": -18.7120, "lon": -39.7540},
    {"id": 14, "nome": "Praia de Barra Nova", "lat": -18.6500, "lon": -39.7200},
    {"id": 15, "nome": "Bosque da Praia", "lat": -18.7130, "lon": -39.7510},
    {"id": 16, "nome": "Feirinha da Ilha", "lat": -18.7140, "lon": -39.7530},
    {"id": 17, "nome": "Casa de Cabeça p/ Baixo", "lat": -18.7160, "lon": -39.7550},
    {"id": 18, "nome": "Espaço Beira Rio", "lat": -18.7200, "lon": -39.8560},
    {"id": 19, "nome": "Praça Vinícius C. Mileri", "lat": -18.7110, "lon": -39.7525},
    {"id": 20, "nome": "Praia do Caramujo", "lat": -18.7050, "lon": -39.7480},
]

OSRM_URL = "http://app_jornada_osrm:5000/route/v1/driving"

async def main():
    async with httpx.AsyncClient() as client:
        for p1 in POIS[:3]:
            for p2 in POIS[3:]:
                coords = f"{p1['lon']},{p1['lat']};{p2['lon']},{p2['lat']}"
                url = f"{OSRM_URL}/{coords}?overview=full&geometries=geojson"
                try:
                    res = await client.get(url, timeout=5.0)
                    data = res.json()
                    code = data.get("code")
                    if code == "Ok":
                        print(f"✅ OSRM OK: {p1['nome']} -> {p2['nome']} ({len(data['routes'][0]['geometry']['coordinates'])} pts)")
                    else:
                        print(f"❌ OSRM ERROR ({code}): {p1['nome']} -> {p2['nome']}")
                except Exception as e:
                    print(f"💥 OSRM EXCEPTION ({e}): {p1['nome']} -> {p2['nome']}")

asyncio.run(main())
