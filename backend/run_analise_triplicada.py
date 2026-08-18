#!/usr/bin/env python3
"""
Script de Análise Triplicada (3 rodadas por vídeo) de todos os 23 vídeos de extrato.
Mede a reprodutibilidade, consistência e precisão da IA/OpenCV no endpoint /ocr/extrato-video.
"""

import os
import json
import time
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VIDEOS_DIR = "/home/claus/src/app_jornada/backend/videos_extrato"
BACKEND_URL = "https://rafael.arkana.fun/api/ocr/extrato-video"
OUTPUT_JSON = "/home/claus/src/app_jornada/backend/analise_triplicada_resultados.json"

def main():
    if not os.path.exists(VIDEOS_DIR):
        print(f"Diretório não encontrado: {VIDEOS_DIR}")
        return

    videos = sorted([f for f in os.listdir(VIDEOS_DIR) if f.endswith(".mp4")])
    print("=" * 80)
    print(f"INICIANDO ANÁLISE TRIPLICADA (3 RODADAS) DE {len(videos)} VÍDEOS")
    print(f"Endpoint Backend: {BACKEND_URL}")
    print("=" * 80)

    resultados_globais = {}

    for idx, video_name in enumerate(videos, 1):
        video_path = os.path.join(VIDEOS_DIR, video_name)
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        
        print(f"\n[{idx}/{len(videos)}] 📹 {video_name} ({file_size_mb:.2f} MB)")
        print("─" * 60)

        rodadas = []
        for rodada_num in range(1, 4):
            print(f"  ▶️ Rodada #{rodada_num}...", end="", flush=True)
            
            with open(video_path, "rb") as f:
                files = {"file": (video_name, f, "video/mp4")}
                t0 = time.time()
                try:
                    resp = requests.post(BACKEND_URL, files=files, timeout=120, verify=False)
                    elapsed = time.time() - t0
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        corridas = data.get("corridas", [])
                        total = data.get("faturamento_total", 0)
                        if not total and corridas:
                            total = sum(c.get("valor_reais", 0) for c in corridas if isinstance(c.get("valor_reais"), (int, float)))
                        
                        rodadas.append({
                            "rodada": rodada_num,
                            "sucesso": True,
                            "qtd_corridas": len(corridas),
                            "faturamento": round(total, 2),
                            "tempo_s": round(elapsed, 1),
                            "historico_completo": data.get("historico_completo"),
                            "necessita_mais_frames": data.get("necessita_mais_frames"),
                            "corridas_detalhe": corridas
                        })
                        print(f" ✅ Sucesso ({elapsed:.1f}s) | {len(corridas)} corridas | R$ {total:.2f}")
                    else:
                        print(f" ❌ Erro HTTP {resp.status_code}: {resp.text[:100]}")
                        rodadas.append({
                            "rodada": rodada_num,
                            "sucesso": False,
                            "erro": f"HTTP {resp.status_code}"
                        })
                except Exception as e:
                    print(f" ❌ Exceção: {e}")
                    rodadas.append({
                        "rodada": rodada_num,
                        "sucesso": False,
                        "erro": str(e)
                    })
            
            time.sleep(1.5) # Pequena pausa entre requisições

        # Cálculo de consistência do vídeo
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
            "tamanho_mb": round(file_size_mb, 2),
            "consistencia_perfeita": perfeita,
            "variacao_faturamento_rs": var_faturamento,
            "rodadas": rodadas
        }

    # Salva os resultados completos
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados_globais, f, indent=2, ensure_ascii=False)

    print("\n\n" + "=" * 90)
    print("RELATÓRIO SÍNTESE - ANÁLISE TRIPLICADA DE PRECISÃO")
    print("=" * 90)
    print(f"{'Vídeo':<38} | {'Rodada 1':>16} | {'Rodada 2':>16} | {'Rodada 3':>16} | {'Status':>10}")
    print("─" * 105)

    tot_perfeitos = 0
    tot_processados = len(videos)

    for v_name, res in resultados_globais.items():
        rds = res["rodadas"]
        str_rds = []
        for r in rds:
            if r.get("sucesso"):
                str_rds.append(f"{r['qtd_corridas']}c R${r['faturamento']:.2f}")
            else:
                str_rds.append("ERRO")
        
        status_str = "PERFEITO" if res["consistencia_perfeita"] else (f"Δ R${res['variacao_faturamento_rs']:.2f}" if any(r.get("sucesso") for r in rds) else "FALHA")
        if res["consistencia_perfeita"]:
            tot_perfeitos += 1

        print(f"{v_name:<38} | {str_rds[0]:>16} | {str_rds[1]:>16} | {str_rds[2]:>16} | {status_str:>10}")

    precisao_pct = (tot_perfeitos / tot_processados) * 100 if tot_processados > 0 else 0
    print("─" * 105)
    print(f"🎯 TAXA DE CONCORDÂNCIA PERFEITA (100% IDÊNTICA NAS 3 RODADAS): {tot_perfeitos}/{tot_processados} ({precisao_pct:.1f}%)")
    print("=" * 90)
    print(f"📄 Resultado detalhado salvo em: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
