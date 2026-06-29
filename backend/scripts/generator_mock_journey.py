import os
import sys
import asyncio
import argparse
import json
from datetime import datetime, date, time, timedelta, timezone
from bson import ObjectId
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
import pytz

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/appjornada")

# Routing helper
async def get_route(http_client, from_lon, from_lat, to_lon, to_lat):
    for base_url in [os.getenv("OSRM_URL", "http://osrm:5000"), "http://localhost:5000"]:
        try:
            r = await http_client.get(
                f"{base_url}/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}?overview=full&geometries=geojson",
                timeout=3.0
            )
            if r.status_code == 200:
                res_json = r.json()
                if "routes" in res_json and len(res_json["routes"]) > 0:
                    return res_json["routes"][0]["geometry"]["coordinates"]
        except Exception:
            pass
    # Fallback linear interpolation
    num_points = 50
    coords = []
    for i in range(num_points):
        t = i / (num_points - 1)
        lon = from_lon + t * (to_lon - from_lon)
        lat = from_lat + t * (to_lat - from_lat)
        coords.append([lon, lat])
    return coords

async def run_generation(args):
    print(f"Iniciando simulação de jornada...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_default_database()

    local_tz = pytz.timezone("America/Sao_Paulo")
    
    # Parse inputs
    driver_email = args.driver
    vehicle_plate = args.vehicle
    target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    start_hour, start_min = map(int, args.start_time.split(":"))
    km_inicial = float(args.km_inicial)
    uber_rev = float(args.uber)
    n99_rev = float(args.n99)

    # 1. Fetch driver and vehicle
    driver = await db["users"].find_one({"email": driver_email, "role": "MOTORISTA"})
    if not driver:
        print(f"ERRO: Motorista {driver_email} não encontrado!")
        return False

    vehicle = await db["veiculos"].find_one({"_id": vehicle_plate})
    if not vehicle:
        # Create temporary vehicle if not found
        vehicle = {"_id": vehicle_plate, "id_placa": vehicle_plate, "marca_modelo": "Mock Vehicle", "ano_modelo": "2023", "cor": "Branco", "situacao": "RODANDO", "km_atual": km_inicial}
        await db["veiculos"].insert_one(vehicle)

    motorista_id = driver["_id"]
    driver_name_clean = driver["nome"].replace(" ", "")
    jornada_id = f"{driver_name_clean}-{vehicle_plate}-{target_date.strftime('%Y%m%d')}"

    # Clean old records
    await db["jornadas"].delete_many({"_id": jornada_id})
    await db["historico_gps"].delete_many({"jornada_id": jornada_id})
    await db["corridas_uber"].delete_many({"trip_id": {"$regex": f"^{jornada_id}"}})
    await db["corridas_99"].delete_many({"trip_id": {"$regex": f"^{jornada_id}"}})

    # Coordinates
    lon_carapina, lat_carapina = -40.2694, -20.2446
    lon_rodoviaria, lat_rodoviaria = -40.3444, -20.3204

    async with httpx.AsyncClient() as http_client:
        route_go = await get_route(http_client, lon_carapina, lat_carapina, lon_rodoviaria, lat_rodoviaria)
        route_back = await get_route(http_client, lon_rodoviaria, lat_rodoviaria, lon_carapina, lat_carapina)

    start_dt = local_tz.localize(datetime.combine(target_date, time(start_hour, start_min, 0)))
    current_dt = start_dt

    gps_points = []
    
    # 20 trips total (10 before lunch, 10 after lunch)
    # Each trip is 20 minutes (80 points of 15 seconds)
    trip_points_len = 80
    dist_trip_m = 15800.0 # ~15.8 km
    
    # First half: 10 trips
    for trip_idx in range(10):
        is_going = (trip_idx % 2 == 0)
        route = route_go if is_going else route_back
        
        for p_idx in range(trip_points_len):
            t = p_idx / (trip_points_len - 1)
            coord_idx = int(t * (len(route) - 1))
            lon, lat = route[coord_idx]
            
            gps_points.append({
                "timestamp": current_dt.astimezone(timezone.utc),
                "motorista_id": motorista_id,
                "jornada_id": jornada_id,
                "localizacao": {"type": "Point", "coordinates": [lon, lat]},
                "distancia_ultima_m": dist_trip_m / trip_points_len,
                "status": "CONDUZINDO"
            })
            current_dt += timedelta(seconds=15)
            
    # Lunch break (1 hour -> 240 points stationary)
    lunch_start_dt = current_dt
    last_lon, last_lat = gps_points[-1]["localizacao"]["coordinates"]
    for _ in range(240):
        gps_points.append({
            "timestamp": current_dt.astimezone(timezone.utc),
            "motorista_id": motorista_id,
            "jornada_id": jornada_id,
            "localizacao": {"type": "Point", "coordinates": [last_lon, last_lat]},
            "distancia_ultima_m": 0.0,
            "status": "PARADO"
        })
        current_dt += timedelta(seconds=15)
    lunch_end_dt = current_dt

    # Second half: 10 trips
    for trip_idx in range(10):
        is_going = (trip_idx % 2 == 1)
        route = route_go if is_going else route_back
        
        for p_idx in range(trip_points_len):
            t = p_idx / (trip_points_len - 1)
            coord_idx = int(t * (len(route) - 1))
            lon, lat = route[coord_idx]
            
            gps_points.append({
                "timestamp": current_dt.astimezone(timezone.utc),
                "motorista_id": motorista_id,
                "jornada_id": jornada_id,
                "localizacao": {"type": "Point", "coordinates": [lon, lat]},
                "distancia_ultima_m": dist_trip_m / trip_points_len,
                "status": "CONDUZINDO"
            })
            current_dt += timedelta(seconds=15)
            
    end_dt = current_dt

    # Save GPS Points
    if gps_points:
        await db["historico_gps"].insert_many(gps_points)
        print(f"  Inseridos {len(gps_points)} pontos de telemetria GPS.")

    # Calculate final odometer
    km_final = km_inicial + 180.0

    # Insert journey doc
    jornada = {
        "_id": jornada_id,
        "motorista_id": motorista_id,
        "veiculo_id": vehicle_plate,
        "data": target_date.isoformat(),
        "status": "FINALIZADA",
        "km_inicial": km_inicial,
        "km_final": km_final,
        "foto_odometro_inicial_url": "https://placehold.co/600x400?text=Odometro+Inicial",
        "foto_odometro_final_url": "https://placehold.co/600x400?text=Odometro+Final",
        "eventos": [
            {"tipo": "INICIO_JORNADA", "timestamp": start_dt.astimezone(timezone.utc), "km": km_inicial},
            {"tipo": "INICIO_INTERVALO", "timestamp": lunch_start_dt.astimezone(timezone.utc), "km": km_inicial + 90.0},
            {"tipo": "FIM_INTERVALO", "timestamp": lunch_end_dt.astimezone(timezone.utc), "km": km_inicial + 90.0},
            {"tipo": "FIM_JORNADA", "timestamp": end_dt.astimezone(timezone.utc), "km": km_final}
        ],
        "created_at": datetime.now(timezone.utc)
    }
    await db["jornadas"].insert_one(jornada)

    # Seed mock App Rides (Uber & 99) for dashboard discrepancy checking
    uber_trip = {
        "trip_id": f"{jornada_id}-uber-1",
        "motorista_id": str(motorista_id),
        "veiculo_id": vehicle_plate,
        "timestamp_solicitacao": (start_dt + timedelta(minutes=30)).astimezone(timezone.utc).isoformat(),
        "timestamp_viagem": (start_dt + timedelta(minutes=45)).astimezone(timezone.utc).isoformat(),
        "distancia_metros": 15800.0,
        "tempo_segundos": 1800,
        "valor_faturamento": uber_rev,
        "tarifa_aplicativo": uber_rev * 0.25,
        "valor_liquido": uber_rev * 0.75,
        "status": "COMPLETADA",
        "jornada_id": jornada_id
    }
    await db["corridas_uber"].insert_one(uber_trip)

    n99_trip = {
        "trip_id": f"{jornada_id}-n99-1",
        "motorista_id": str(motorista_id),
        "veiculo_id": vehicle_plate,
        "timestamp_solicitacao": (start_dt + timedelta(hours=6)).astimezone(timezone.utc).isoformat(),
        "timestamp_viagem": (start_dt + timedelta(hours=6, minutes=15)).astimezone(timezone.utc).isoformat(),
        "distancia_metros": 15800.0,
        "tempo_segundos": 1800,
        "valor_faturamento": n99_rev,
        "tarifa_aplicativo": n99_rev * 0.2,
        "valor_liquido": n99_rev * 0.8,
        "status": "COMPLETADA",
        "jornada_id": jornada_id
    }
    await db["corridas_99"].insert_one(n99_trip)

    print(f"Jornada e corridas de simulação criadas para {driver_email}!")
    return True

# GUI Implementation
def run_gui():
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("Erro: tkinter não disponível. Rodando em modo CLI.")
        return False

    class MockGeneratorApp:
        def __init__(self, root):
            self.root = root
            self.root.title("Gerador Dinâmico de Mocks - App Jornada")
            self.root.geometry("460x520")

            main_frame = ttk.Frame(root, padding="20")
            main_frame.grid(row=0, column=0, sticky="nsew")

            ttk.Label(main_frame, text="Gerar Jornada de Trabalho Simulada", font=("Helvetica", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))

            # Driver
            ttk.Label(main_frame, text="Email do Motorista:").grid(row=1, column=0, sticky="w", pady=5)
            self.driver_ent = ttk.Entry(main_frame, width=32)
            self.driver_ent.insert(0, "motorista@test.com")
            self.driver_ent.grid(row=1, column=1, pady=5)

            # Vehicle
            ttk.Label(main_frame, text="Placa do Veículo:").grid(row=2, column=0, sticky="w", pady=5)
            self.vehicle_ent = ttk.Entry(main_frame, width=32)
            self.vehicle_ent.insert(0, "CCC-3C33")
            self.vehicle_ent.grid(row=2, column=1, pady=5)

            # Date
            ttk.Label(main_frame, text="Data (YYYY-MM-DD):").grid(row=3, column=0, sticky="w", pady=5)
            self.date_ent = ttk.Entry(main_frame, width=32)
            self.date_ent.insert(0, datetime.now().strftime("%Y-%m-%d"))
            self.date_ent.grid(row=3, column=1, pady=5)

            # Start Time
            ttk.Label(main_frame, text="Horário Início (HH:MM):").grid(row=4, column=0, sticky="w", pady=5)
            self.start_ent = ttk.Entry(main_frame, width=32)
            self.start_ent.insert(0, "08:00")
            self.start_ent.grid(row=4, column=1, pady=5)

            # KM Inicial
            ttk.Label(main_frame, text="KM Inicial:").grid(row=5, column=0, sticky="w", pady=5)
            self.km_ent = ttk.Entry(main_frame, width=32)
            self.km_ent.insert(0, "20000.0")
            self.km_ent.grid(row=5, column=1, pady=5)

            # Uber Revenue
            ttk.Label(main_frame, text="Faturamento Uber (R$):").grid(row=6, column=0, sticky="w", pady=5)
            self.uber_ent = ttk.Entry(main_frame, width=32)
            self.uber_ent.insert(0, "150.00")
            self.uber_ent.grid(row=6, column=1, pady=5)

            # 99 Revenue
            ttk.Label(main_frame, text="Faturamento 99 (R$):").grid(row=7, column=0, sticky="w", pady=5)
            self.n99_ent = ttk.Entry(main_frame, width=32)
            self.n99_ent.insert(0, "90.00")
            self.n99_ent.grid(row=7, column=1, pady=5)

            # Submit
            self.submit_btn = ttk.Button(main_frame, text="Gerar Mock", command=self.on_submit)
            self.submit_btn.grid(row=8, column=0, columnspan=2, pady=(20, 0))

        def on_submit(self):
            class Args:
                pass
            args = Args()
            args.driver = self.driver_ent.get()
            args.vehicle = self.vehicle_ent.get()
            args.date = self.date_ent.get()
            args.start_time = self.start_ent.get()
            args.km_inicial = self.km_ent.get()
            args.uber = self.uber_ent.get()
            args.n99 = self.n99_ent.get()

            try:
                asyncio.run(run_generation(args))
                messagebox.showinfo("Sucesso", "Jornada de Simulação gerada com sucesso no MongoDB!")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha na geração:\n{e}")

    root = tk.Tk()
    app = MockGeneratorApp(root)
    root.mainloop()
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador de Mocks de Jornada e Telemetria")
    parser.add_argument("--driver", default="motorista@test.com", help="Email do motorista")
    parser.add_argument("--vehicle", default="CCC-3C33", help="Placa do veículo")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Data (YYYY-MM-DD)")
    parser.add_argument("--start-time", default="08:00", help="Horário de início (HH:MM)")
    parser.add_argument("--km-inicial", default="20000.0", help="KM inicial")
    parser.add_argument("--uber", default="150.00", help="Faturamento Uber")
    parser.add_argument("--n99", default="90.00", help="Faturamento 99")
    parser.add_argument("--gui", action="store_true", help="Forçar abertura em modo GUI")

    # If args are passed, run CLI mode, else run GUI mode (if GUI requested or if no arguments and tkinter is available)
    if len(sys.argv) > 1 and not "--gui" in sys.argv:
        args = parser.parse_args()
        asyncio.run(run_generation(args))
    else:
        # Try to run GUI, fallback to CLI if it fails
        if not run_gui():
            args = parser.parse_args()
            asyncio.run(run_generation(args))