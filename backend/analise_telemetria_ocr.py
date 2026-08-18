import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone

# Dados extraídos do vídeo 3corridas_RS_69_73_358d6c.mp4 (99)
corridas = [
    {
      "horario": "18:36",
      "plataforma": "99",
      "valor_reais": 23.2,
      "origem": "Rua Esméria Barros Deorce, Jardim Camburi, Vitória - ES",
      "destino": "Avenida Santarém, Barcelona, Serra - ES"
    },
    {
      "horario": "17:30",
      "plataforma": "99",
      "valor_reais": 24.83,
      "origem": "Hematologia e Oncologia, Civit II, Serra - ES",
      "destino": "Avenida Eng. Charles Bitran, Jardim Camburi, Vitória - ES"
    },
    {
      "horario": "08:06",
      "plataforma": "99",
      "valor_reais": 21.7,
      "origem": "Rua Gustavo Barroso, Guaraciaba, Serra - ES",
      "destino": "Mercado Livre SES1- Campo Log II, RQGC+JX - Av. Principal 1, 852 - Civit I..."
    }
]

DATA_DECLARADA = "2026-08-10"

async def pegar_telemetria_horario(db, data_str, horario_str, margem_minutos=3):
    """
    Busca os pontos de telemetria (GPS) ao redor de um horário específico no dia.
    margem_minutos: Busca X minutos antes e depois do horário exato.
    """
    # Converte para datetime
    dt_base_str = f"{data_str}T{horario_str}:00.000Z" # Formato ISO UTC
    # Como as corridas e timestamps podem estar em UTC ou local, vamos assumir que timestamp na base está em UTC
    # Mas o horário do app (ex: 18:36) geralmente é horário local (BRT, -03:00)
    # Se a base guarda UTC, 18:36 local seria 21:36 UTC.
    # Vamos verificar se o timestamp da base é UTC e tentar compensar o fuso.
    # Para simplificar, vou buscar comparando a string, mas melhor como datetime.
    
    # Assumindo que o timestamp do DB é string no formato: '2026-08-10T21:36:00.000Z' (UTC)
    # E o horário da corrida '18:36' é local (BRT).
    hora, minuto = map(int, horario_str.split(':'))
    dt_local = datetime(int(data_str[0:4]), int(data_str[5:7]), int(data_str[8:10]), hora, minuto)
    # Transforma pra UTC (+3h) para pesquisar no banco
    dt_utc = dt_local + timedelta(hours=3)
    
    start_time = dt_utc - timedelta(minutes=margem_minutos)
    end_time = dt_utc + timedelta(minutes=margem_minutos)
    
    start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.999Z")

    pontos = await db.historico_gps.find({
        "timestamp": {"$gte": start_str, "$lte": end_str}
    }).sort("timestamp", 1).to_list(length=100)
    
    return pontos, dt_utc.strftime("%H:%M:%S")

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['appjornada']
    
    print(f"=== ANÁLISE DE CORRELAÇÃO OCR vs TELEMETRIA ===")
    print(f"Data Base: {DATA_DECLARADA}")
    
    for c in corridas:
        horario = c['horario']
        print(f"\n--- Analisando Corrida das {horario} ---")
        print(f"📌 OCR Origem:  {c['origem']}")
        print(f"📌 OCR Destino: {c['destino']}")
        
        pontos, horario_utc = await pegar_telemetria_horario(db, DATA_DECLARADA, horario, margem_minutos=2)
        
        print(f"🔎 Buscando na Telemetria entre {horario_utc} UTC (+/- 2 min)...")
        if not pontos:
            print("❌ Nenhum ponto de telemetria encontrado neste intervalo.")
            continue
            
        print(f"✅ Encontrados {len(pontos)} pontos de GPS.")
        
        # Agrupar ruas para ver onde ele estava
        ruas = {}
        for p in pontos:
            r = p.get('rua', 'Desconhecida')
            ruas[r] = ruas.get(r, 0) + 1
            
        print("📍 Ruas detectadas na telemetria neste horário:")
        for r, cont in ruas.items():
            print(f"   - {r} ({cont} pontos)")

if __name__ == "__main__":
    asyncio.run(main())
