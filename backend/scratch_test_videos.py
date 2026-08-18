#!/usr/bin/env python3
"""
Script para re-testar os 3 piores vídeos de faturamento do bucket MinIO de produção.
Baixa os vídeos via SSH/mc e envia ao endpoint /ocr/extrato-video do backend local ou de produção.
Executa 2 amostragens de cada para medir repetibilidade.
"""

import subprocess
import requests
import json
import os
import sys
import time

# === CONFIGURAÇÃO ===
PROD_SERVER = "root@2.24.121.189"
MINIO_CONTAINER = "app_jornada_minio"
BUCKET_PATH = "local/app-jornada/extrato_video"

# Backend de produção (via SSH tunnel ou direto pelo nginx)
BACKEND_URL = "https://rafael.arkana.fun/api/ocr/extrato-video"

# Os 3 piores vídeos da conversa anterior (maior discrepância entre rodadas)
PIORES_VIDEOS = [
    "5742f1329bd74f4492df5b358960e0c1.mp4",   # Variação de +1 corrida e R$50+ entre rodadas
    "8576ecc7c2144a17a9fb05ffb31fabeb.mp4",   # +2 corridas e R$22+ de variação
    "57b2b3dbc97f44b2ad32584a3a658ad9.mp4",   # Variação de ~R$16.99
]

LOCAL_DIR = "/tmp/app_jornada_test_videos"
RESULTADOS = {}


def baixar_video(video_name: str) -> str:
    """Baixa vídeo do MinIO de produção via SSH+mc para local."""
    local_path = os.path.join(LOCAL_DIR, video_name)
    if os.path.exists(local_path):
        print(f"  ✅ {video_name} já existe localmente ({os.path.getsize(local_path)} bytes)")
        return local_path

    print(f"  ⬇️  Baixando {video_name} do bucket de produção...")
    cmd = (
        f"ssh -o StrictHostKeyChecking=no {PROD_SERVER} "
        f"\"docker exec {MINIO_CONTAINER} sh -c '"
        f"mc alias set local http://localhost:9000 \\$(printenv MINIO_ROOT_USER) \\$(printenv MINIO_ROOT_PASSWORD) 2>/dev/null; "
        f"mc cat {BUCKET_PATH}/{video_name}'\""
    )
    with open(local_path, "wb") as f:
        proc = subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.PIPE, timeout=120)
    
    if proc.returncode != 0:
        print(f"  ❌ Erro ao baixar: {proc.stderr.decode()[:200]}")
        return ""
    
    size_mb = os.path.getsize(local_path) / (1024 * 1024)
    print(f"  ✅ Baixado: {size_mb:.1f} MB")
    return local_path


def testar_video(video_path: str, nome: str, amostragem_num: int) -> dict:
    """Envia vídeo ao endpoint de extrato-video e retorna resultados."""
    print(f"\n  🎬 Testando {nome} (Amostragem #{amostragem_num})...")
    
    with open(video_path, "rb") as f:
        files = {"file": (os.path.basename(video_path), f, "video/mp4")}
        try:
            t0 = time.time()
            resp = requests.post(BACKEND_URL, files=files, timeout=120, verify=False)
            elapsed = time.time() - t0
            
            if resp.status_code == 200:
                data = resp.json()
                corridas = data.get("corridas", [])
                total = data.get("faturamento_total", 0)
                if not total and corridas:
                    total = sum(c.get("valor_reais", 0) for c in corridas if isinstance(c.get("valor_reais"), (int, float)))
                
                print(f"  ✅ Sucesso! {len(corridas)} corridas | R$ {total:.2f} | {elapsed:.1f}s")
                print(f"     historico_completo: {data.get('historico_completo')}")
                print(f"     necessita_mais_frames: {data.get('necessita_mais_frames')}")
                
                return {
                    "sucesso": True,
                    "corridas": len(corridas),
                    "faturamento": round(total, 2),
                    "tempo_s": round(elapsed, 1),
                    "historico_completo": data.get("historico_completo"),
                    "necessita_mais_frames": data.get("necessita_mais_frames"),
                    "detalhes_corridas": corridas,
                }
            else:
                print(f"  ❌ Erro HTTP {resp.status_code}: {resp.text[:200]}")
                return {"sucesso": False, "erro": resp.text[:200]}
        except Exception as e:
            print(f"  ❌ Exceção: {e}")
            return {"sucesso": False, "erro": str(e)}


def main():
    os.makedirs(LOCAL_DIR, exist_ok=True)
    
    print("=" * 70)
    print("RE-TESTE DOS 3 PIORES VÍDEOS DE FATURAMENTO")
    print(f"Backend: {BACKEND_URL}")
    print("=" * 70)
    
    for video_name in PIORES_VIDEOS:
        print(f"\n{'─' * 60}")
        print(f"📹 Vídeo: {video_name}")
        print(f"{'─' * 60}")
        
        video_path = baixar_video(video_name)
        if not video_path:
            RESULTADOS[video_name] = {"erro": "Falha ao baixar"}
            continue
        
        amostragens = []
        for i in range(1, 3):  # 2 amostragens
            resultado = testar_video(video_path, video_name, i)
            amostragens.append(resultado)
            if i < 2:
                time.sleep(2)  # Pausa entre amostragens
        
        RESULTADOS[video_name] = amostragens
    
    # === RELATÓRIO FINAL ===
    print("\n\n" + "=" * 70)
    print("RELATÓRIO COMPARATIVO - RE-TESTE PÓS MÓDULO DE NITIDEZ")
    print("=" * 70)
    
    print(f"\n{'Vídeo':<45} | {'Amost.1':>20} | {'Amost.2':>20} | {'Variação':>12}")
    print("─" * 105)
    
    for video_name in PIORES_VIDEOS:
        dados = RESULTADOS.get(video_name, {})
        if isinstance(dados, dict) and "erro" in dados:
            print(f"{video_name:<45} | {'ERRO':>20} | {'ERRO':>20} | {'N/A':>12}")
            continue
        
        a1 = dados[0] if len(dados) > 0 else {}
        a2 = dados[1] if len(dados) > 1 else {}
        
        a1_str = f"{a1.get('corridas', '?')} corr / R$ {a1.get('faturamento', 0):.2f}" if a1.get("sucesso") else "FALHA"
        a2_str = f"{a2.get('corridas', '?')} corr / R$ {a2.get('faturamento', 0):.2f}" if a2.get("sucesso") else "FALHA"
        
        if a1.get("sucesso") and a2.get("sucesso"):
            var_pct = abs(a1["faturamento"] - a2["faturamento"]) / max(a1["faturamento"], 1) * 100
            var_str = f"{var_pct:.2f}%"
        else:
            var_str = "N/A"
        
        print(f"{video_name:<45} | {a1_str:>20} | {a2_str:>20} | {var_str:>12}")
    
    print("\n" + "=" * 70)
    
    # Salvar JSON completo
    result_file = os.path.join(LOCAL_DIR, "resultados_reteste.json")
    with open(result_file, "w") as f:
        json.dump(RESULTADOS, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n📄 Resultados detalhados salvos em: {result_file}")


if __name__ == "__main__":
    main()
