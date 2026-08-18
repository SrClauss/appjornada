import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.telemetria_ocr import reconstruir_trajeto_uber

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['appjornada']
    
    motorista_id = "teste_uber_15corridas"
    data_str = "2026-08-18"
    
    # Amostra das Corridas Uber lidas pelo OCR no vídeo:
    corridas_uber_ocr = [
        {
            "id": 1,
            "horario_ocr": "07:15",
            "origem": "Av. Primeira Avenida Laranjeiras Shopping, Parque Residencial Laranjeiras - Serra - ES",
            "destino": "Rua Lavrador José Barbosa da Silva, Serra - ES",
            "sim_embarque": "Primeira Avenida Laranjeiras",
            "sim_desembarque": "Rua Lavrador Jose Barbosa da Silva",
            "horario_embarque_sim": "07:15",
            "horario_desembarque_sim": "07:35"
        },
        {
            "id": 2,
            "horario_ocr": "08:30",
            "origem": "rua bem-ti-vi, Balneário de Carapebus - Serra - ES",
            "destino": "Av. Eldes Scherrer de Souza, Colina de Laranjeiras - Serra - ES",
            "sim_embarque": "rua bem-ti-vi",
            "sim_desembarque": "Av. Eldes Scherrer de Souza",
            "horario_embarque_sim": "08:30",
            "horario_desembarque_sim": "08:48"
        },
        {
            "id": 6,
            "horario_ocr": "12:04",
            "origem": "Av. Henrique Moscoso, Centro de Vila Velha - Vila Velha - ES",
            "destino": "Avenida Nossa Senhora dos Navegantes, Enseada do Suá - Vitória - ES",
            "sim_embarque": "Av. Henrique Moscoso",
            "sim_desembarque": "Avenida Nossa Senhora dos Navegantes",
            "horario_embarque_sim": "12:04",
            "horario_desembarque_sim": "12:28"
        }
    ]
    
    print("⏳ Populando banco com telemetria simulada da Uber (Varredura Progressiva)...")
    for c in corridas_uber_ocr:
        h_emb, m_emb = map(int, c["horario_embarque_sim"].split(":"))
        dt_emb_utc = datetime(2026, 8, 18, h_emb + 3, m_emb)
        await db.historico_gps.insert_one({
            "motorista_id": motorista_id,
            "timestamp": dt_emb_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "rua": c["sim_embarque"],
            "localizacao": {"type": "Point", "coordinates": [-40.2, -20.2]}
        })
        
        h_des, m_des = map(int, c["horario_desembarque_sim"].split(":"))
        dt_des_utc = datetime(2026, 8, 18, h_des + 3, m_des)
        await db.historico_gps.insert_one({
            "motorista_id": motorista_id,
            "timestamp": dt_des_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "rua": c["sim_desembarque"],
            "localizacao": {"type": "Point", "coordinates": [-40.2, -20.2]}
        })

    print("\n" + "="*80)
    print("🚗 RECONSTRUÇÃO DE CORRIDAS UBER (VARREDURA PROGRESSIVA: EMBARQUE ➔ DESEMBARQUE)")
    print("="*80)

    for c in corridas_uber_ocr:
        res = await reconstruir_trajeto_uber(
            db=db,
            motorista_id=motorista_id,
            data_str=data_str,
            horario_embarque_str=c["horario_ocr"],
            origem_ocr=c["origem"],
            destino_ocr=c["destino"]
        )
        
        print(f"\n🚙 CORRIDA UBER #{c['id']} (OCR Embarque: {c['horario_ocr']})")
        if res.get("sucesso"):
            emb = res["embarque"]
            des = res["desembarque"]
            print(f"   🟢 EMBARQUE:    {emb['horario_local']} na '{emb['rua']}'")
            print(f"   🔴 DESEMBARQUE: {des['horario_local']} na '{des['rua']}'")
            print(f"   ⏱️ Duração:     {res['duracao_minutos']} minutos")
            print(f"   📐 Janela:      {res['janela_telemetria_usada_min']} min")
        else:
            print(f"   ❌ Falha: {res.get('motivo')}")

    # Limpar banco
    await db.historico_gps.delete_many({"motorista_id": motorista_id})

if __name__ == "__main__":
    asyncio.run(main())
