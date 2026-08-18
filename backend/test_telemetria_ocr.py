import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.telemetria_ocr import classificar_horario_corrida

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['appjornada']
    
    motorista_id = "teste_ocr_123"
    data_str = "2026-08-18"
    horario_str = "18:36"
    
    # 1. Inserir ponto de GPS falso que simula a "Origem"
    # Horário da corrida: 16:36 (local) -> 19:36 (UTC)
    horario_str = "16:36"
    origem_ocr = "Avenida Eldes Scherrer Souza, Parque Res. Laranjeiras, Serra - ES"
    destino_ocr = "Rua Dom Pedro II, Colina de Laranjeiras, Serra - ES"
    
    # Inserir ponto de GPS falso que simula o DESTINO
    rua_falsa = "Rua Dom Pedro 2" # Simulando como o GPS traria (Pedro 2 ao invés de Pedro II)
    
    dt_utc = datetime(2026, 8, 18, 19, 36)
    timestamp_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    await db.historico_gps.insert_one({
        "motorista_id": motorista_id,
        "timestamp": timestamp_str,
        "rua": rua_falsa,
        "localizacao": {"type": "Point", "coordinates": [-40.0, -20.0]}
    })
    
    print("📍 Ponto de telemetria falso inserido:", rua_falsa, "às", timestamp_str, "(UTC)")

    # 2. Testar o algoritmo
    resultado = await classificar_horario_corrida(
        db=db,
        motorista_id=motorista_id,
        data_str=data_str,
        horario_str=horario_str,
        origem_ocr=origem_ocr,
        destino_ocr=destino_ocr
    )
    
    print("\n✅ Resultado da Classificação (Corrida das 16:36):")
    print(resultado)
    
    # 3. Limpar
    await db.historico_gps.delete_many({"motorista_id": motorista_id})

if __name__ == "__main__":
    asyncio.run(main())
