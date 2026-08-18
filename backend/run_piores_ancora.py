#!/usr/bin/env python3
import os
import time
import requests
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VIDEOS_DIR = "/home/claus/src/app_jornada/backend/videos_extrato"
BACKEND_URL = "https://rafael.arkana.fun/api/ocr/extrato-video"

PIORES_VIDEOS = [
    "13corridas_RS_315_63_276e94.mp4",
    "12corridas_RS_282_72_0efd6d.mp4",
    "10corridas_RS_249_77_7273cf.mp4"
]

def extrair_ancoras(nome_arquivo):
    # Formato: 13corridas_RS_315_63_276e94.mp4
    match = re.search(r'(\d+)corridas_RS_(\d+)_(\d+)', nome_arquivo)
    if match:
        corridas = int(match.group(1))
        reais = float(f"{match.group(2)}.{match.group(3)}")
        return corridas, reais
    return None, None

def main():
    print("=" * 80)
    print("INICIANDO ANÁLISE TRIPLICADA (3 RODADAS) COM ÂNCORAS - 3 PIORES VÍDEOS")
    print("=" * 80)

    resultados_globais = {}

    for idx, video_name in enumerate(PIORES_VIDEOS, 1):
        video_path = os.path.join(VIDEOS_DIR, video_name)
        if not os.path.exists(video_path):
            print(f"Vídeo não encontrado: {video_path}")
            continue
            
        corridas_ancora, faturamento_ancora = extrair_ancoras(video_name)
        
        print(f"\n[{idx}/3] 📹 {video_name}")
        print(f"📌 Âncoras extraídas do nome: {corridas_ancora} corridas | R$ {faturamento_ancora:.2f}")
        print("─" * 60)

        rodadas = []
        for rodada_num in range(1, 4):
            print(f"  ▶️ Rodada #{rodada_num}...", end="", flush=True)
            
            with open(video_path, "rb") as f:
                files = {"file": (video_name, f, "video/mp4")}
                data = {
                    "faturamento_ancora": str(faturamento_ancora),
                    "corridas_ancora": str(corridas_ancora)
                }
                t0 = time.time()
                try:
                    resp = requests.post(BACKEND_URL, files=files, data=data, timeout=120, verify=False)
                    elapsed = time.time() - t0
                    
                    if resp.status_code == 200:
                        res_data = resp.json()
                        corridas = res_data.get("corridas", [])
                        total = res_data.get("faturamento_total", 0)
                        if not total and corridas:
                            total = sum(c.get("valor_reais", 0) for c in corridas if isinstance(c.get("valor_reais"), (int, float)))
                        
                        rodadas.append({
                            "sucesso": True,
                            "qtd_corridas": len(corridas),
                            "faturamento": round(total, 2)
                        })
                        print(f" ✅ Sucesso ({elapsed:.1f}s) | {len(corridas)} corridas | R$ {total:.2f}")
                        # Print some origins/destinations to verify
                        for i, c in enumerate(corridas[:3]):
                            print(f"      - Corrida {i+1}: Origem: {c.get('origem')} -> Destino: {c.get('destino')}")
                        if len(corridas) > 3:
                            print(f"      - ... mais {len(corridas)-3} corridas extraídas com localizações")
                    else:
                        print(f" ❌ Erro HTTP {resp.status_code}: {resp.text[:100]}")
                        rodadas.append({"sucesso": False})
                except Exception as e:
                    print(f" ❌ Exceção: {e}")
                    rodadas.append({"sucesso": False})
            
            time.sleep(2)

        faturamentos = [r["faturamento"] for r in rodadas if r.get("sucesso")]
        corridas_count = [r["qtd_corridas"] for r in rodadas if r.get("sucesso")]
        
        perfeita = False
        var_faturamento = 0.0
        if len(faturamentos) == 3:
            diff_fat = max(faturamentos) - min(faturamentos)
            diff_corr = max(corridas_count) - min(corridas_count)
            perfeita = (diff_fat < 0.01 and diff_corr == 0)
            var_faturamento = round(diff_fat, 2)

        resultados_globais[video_name] = {
            "consistencia_perfeita": perfeita,
            "variacao_faturamento_rs": var_faturamento,
            "rodadas": rodadas
        }

    print("\n\n" + "=" * 90)
    print("RELATÓRIO SÍNTESE - ANÁLISE COM ÂNCORA (3 PIORES)")
    print("=" * 90)
    print(f"{'Vídeo':<38} | {'Rodada 1':>16} | {'Rodada 2':>16} | {'Rodada 3':>16} | {'Status':>10}")
    print("─" * 105)

    for v_name, res in resultados_globais.items():
        rds = res["rodadas"]
        str_rds = []
        for r in rds:
            if r.get("sucesso"):
                str_rds.append(f"{r['qtd_corridas']}c R${r['faturamento']:.2f}")
            else:
                str_rds.append("ERRO")
        
        status_str = "PERFEITO" if res["consistencia_perfeita"] else f"Δ R${res['variacao_faturamento_rs']:.2f}"
        print(f"{v_name:<38} | {str_rds[0]:>16} | {str_rds[1]:>16} | {str_rds[2]:>16} | {status_str:>10}")

if __name__ == "__main__":
    main()
