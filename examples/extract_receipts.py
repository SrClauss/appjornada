import base64
import json
import os
import urllib.request
import urllib.parse
import ssl

def load_env_keys():
    gemini_key = ""
    google_key = ""
    # Tenta ler do .env do backend
    env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    gemini_key = line.strip().split("=", 1)[1]
                elif line.startswith("GOOGLE_API_KEY="):
                    google_key = line.strip().split("=", 1)[1]
    if not gemini_key:
        gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not google_key:
        google_key = os.getenv("GOOGLE_API_KEY", "")
    return gemini_key, google_key

def geocode_address(address, google_api_key):
    if not address or not google_api_key:
        return None
    try:
        query = urllib.parse.quote(address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={query}&key={google_api_key}"
        req = urllib.request.Request(url, method="GET")
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            if res_json.get("status") == "OK" and res_json.get("results"):
                loc = res_json["results"][0]["geometry"]["location"]
                return {"lat": loc["lat"], "lon": loc["lng"]}
    except Exception as e:
        print(f"Erro ao geocodificar '{address}': {e}")
    return None

def extract_info(image_path, gemini_key, google_key):
    if not os.path.exists(image_path):
        print(f"Erro: Arquivo {image_path} não encontrado.")
        return None

    print(f"Processando {os.path.basename(image_path)}...")
    with open(image_path, "rb") as f:
        image_data = f.read()

    base64_image = base64.b64encode(image_data).decode("utf-8")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    
    prompt = (
        "Você é um assistente especializado em ler prints de faturamento ou de corridas de motoristas (Uber, 99 ou outros).\n"
        "Extraia as seguintes informações do print de forma extremamente precisa:\n"
        "1. Plataforma (UBER, 99 ou OUTROS)\n"
        "2. Valor total da corrida ou do faturamento selecionado (represente como float, ex: 15.50)\n"
        "3. Local de Origem / Partida (se visível)\n"
        "4. Local de Destino / Chegada (se visível)\n"
        "5. Data e hora da corrida (se visível)\n\n"
        "Retorne estritamente um JSON no formato:\n"
        "{\n"
        "  \"plataforma\": \"UBER\" ou \"99\" ou \"OUTROS\",\n"
        "  \"valor\": float,\n"
        "  \"origem\": string ou null,\n"
        "  \"destino\": string ou null,\n"
        "  \"data_hora\": string ou null\n"
        "}\n"
        "Não retorne nenhuma marcação markdown ou texto explicativo, retorne apenas o JSON puro."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    }

    req_data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            text_response = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            if "```" in text_response:
                text_response = text_response.split("```")[-2].replace("json", "").strip()
            
            result = json.loads(text_response)
            
            # Adiciona geocodificação
            if result.get("origem"):
                print(f"Geocodificando origem: {result['origem']} ...")
                result["origem_coords"] = geocode_address(result["origem"], google_key)
            else:
                result["origem_coords"] = None
                
            if result.get("destino"):
                print(f"Geocodificando destino: {result['destino']} ...")
                result["destino_coords"] = geocode_address(result["destino"], google_key)
            else:
                result["destino_coords"] = None
                
            return result
    except Exception as e:
        print(f"Erro na requisição para {os.path.basename(image_path)}: {e}")
        return None

if __name__ == "__main__":
    gemini_key, google_key = load_env_keys()
    if not gemini_key:
        print("Erro: GEMINI_API_KEY não encontrada no .env do backend ou no ambiente.")
        exit(1)

    dir_path = os.path.dirname(__file__)
    images = [
        os.path.join(dir_path, "99.jpeg"),
        os.path.join(dir_path, "6ade2222-c083-4eed-b9d4-4e7d95006b4d.jpeg")
    ]

    for img in images:
        result = extract_info(img, gemini_key, google_key)
        if result:
            print("\nResultado Extraído:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("-" * 50)
