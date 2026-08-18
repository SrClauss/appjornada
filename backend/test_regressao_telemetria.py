import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.telemetria_ocr import reconstruir_trajeto_corrida

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['appjornada']
    
    motorista_id = "teste_corrida_longa"
    data_str = "2026-08-18"
    
    # Simulação de uma corrida longa de 75 minutos (Intermunicipal / Trânsito intenso):
    # Embarque: 14:00 (Vitória - Enseada do Suá)
    # Desembarque: 15:15 (Guarapari - Praia do Morro)
    
    origem_ocr = "Av. Nossa Senhora dos Navegantes, Enseada do Suá, Vitória - ES"
    destino_ocr = "Av. Beira Mar, Praia do Morro, Guarapari - ES"
    horario_desembarque_str = "15:15"
    
    print("⏳ Populando banco com telemetria de uma corrida LONGA (75 minutos)...")
    
    # Ponto de Embarque às 14:00 (75 min antes das 15:15)
    dt_emb_utc = datetime(2026, 8, 18, 14 + 3, 0)
    await db.historico_gps.insert_one({
        "motorista_id": motorista_id,
        "timestamp": dt_emb_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "rua": "Av. Nossa Senhora dos Navegantes",
        "localizacao": {"type": "Point", "coordinates": [-40.3, -20.3]}
    })
    
    # Ponto de Desembarque às 15:15
    dt_des_utc = datetime(2026, 8, 18, 15 + 3, 15)
    await db.historico_gps.insert_one({
        "motorista_id": motorista_id,
        "timestamp": dt_des_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "rua": "Av. Beira Mar",
        "localizacao": {"type": "Point", "coordinates": [-40.4, -20.6]}
    })

    print("\n🔍 Testando algoritmo com Janela Inicial de 40 minutos...")
    print("   (Como a corrida durou 75 min, o sistema DEVE acionar o FALLBACK dinâmico até 90 min!)\n")

    res = await reconstruir_trajeto_corrida(
        db=db,
        motorista_id=motorista_id,
        data_str=data_str,
        horario_desembarque_str=horario_desembarque_str,
        origem_ocr=origem_ocr,
        destino_ocr=destino_ocr,
        janela_inicial_minutos=40,
        janela_maxima_minutos=180
    )

    if res.get("sucesso"):
        emb = res["embarque"]
        des = res["desembarque"]
        print("✅ FALLBACK EXECUTADO COM SUCESSO!")
        print(f"   🟢 EMBARQUE:    {emb['horario_local']} na '{emb['rua']}'")
        print(f"   🔴 DESEMBARQUE: {des['horario_local']} na '{des['rua']}'")
        print(f"   ⏱️ Duração:     {res['duracao_minutos']} minutos")
        print(f"   📐 Janela de busca acionada: {res['janela_telemetria_usada_min']} minutos")
    else:
        print(f"❌ Falha: {res.get('motivo')}")

    # Limpar banco
    await db.historico_gps.delete_many({"motorista_id": motorista_id})

if __name__ == "__main__":
    asyncio.run(main())
