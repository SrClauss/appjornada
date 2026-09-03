import os
import sys
import io
import re
from pathlib import Path
from datetime import datetime
from minio import Minio
from pymongo import MongoClient

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "jornadaAdminAccess")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "jornadaAdminSecretKeySecure2026!")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "app-jornada")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://admin_jornada:b824b0f9-a9a7-47b0-8e1f-7b6e927c3da8@mongo:27017/appjornada?authSource=admin"
)

def sync_apk(apk_path: str, versao_str: str = "1.2.4"):
    p = Path(apk_path)
    if not p.exists():
        print(f"[sync_apk] ERRO: Arquivo APK '{apk_path}' não foi encontrado.")
        sys.exit(1)

    conteudo = p.read_bytes()
    tamanho_mb = len(conteudo) / (1024 * 1024)

    # Trata formato "1.2.4+17" ou "1.2.4"
    if "+" in str(versao_str):
        parts = str(versao_str).split("+")
        nome_versao = parts[0]
        build_number = int(parts[1]) if parts[1].isdigit() else 17
        versao_completa = str(versao_str)
    else:
        nome_versao = str(versao_str)
        build_number = 17
        versao_completa = f"{nome_versao}+{build_number}"

    target_filename = f"app-jornada-v{nome_versao}.apk"
    object_name = f"apk/{target_filename}"

    # 1. Sincroniza com o MinIO (Garante 1 único APK no MinIO)
    print(f"==> [sync_apk] Conectando ao MinIO ({MINIO_ENDPOINT})...")
    minio_endpoint = MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
    client = Minio(
        minio_endpoint,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )

    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
    except Exception as err:
        print(f"==> [sync_apk] Aviso ao verificar bucket: {err}")

    # Remove qualquer APK antigo no prefixo 'apk/' para manter apenas UMA versão no MinIO
    print("==> [sync_apk] Removendo APKs anteriores do MinIO...")
    try:
        old_objs = list(client.list_objects(MINIO_BUCKET, prefix="apk/"))
        for o in old_objs:
            print(f"   - Removendo APK antigo no MinIO: {o.object_name}")
            client.remove_object(MINIO_BUCKET, o.object_name)
    except Exception as err:
        print(f"   [AVISO] Erro ao limpar APKs antigos: {err}")

    # Envia o novo APK
    print(f"==> [sync_apk] Uploading {target_filename} ({tamanho_mb:.1f} MB) para MinIO...")
    stream = io.BytesIO(conteudo)
    client.put_object(
        MINIO_BUCKET,
        object_name,
        stream,
        len(conteudo),
        content_type="application/vnd.android.package-archive"
    )
    print(f"==> [sync_apk] Upload concluído: /{MINIO_BUCKET}/{object_name}")

    # Backup local
    try:
        local_dir = Path("/tmp/app_jornada_uploads/apk")
        local_dir.mkdir(parents=True, exist_ok=True)
        for f in local_dir.glob("*.apk"):
            try:
                f.unlink()
            except Exception:
                pass
        (local_dir / target_filename).write_bytes(conteudo)
    except Exception as err:
        print(f"   [AVISO] Falha ao salvar backup local: {err}")

    # 2. Atualiza no MongoDB (Garante 1 único registro no BD)
    print(f"==> [sync_apk] Conectando ao MongoDB para registrar a versão {nome_versao}...")
    mongo_client = MongoClient(MONGO_URL)
    
    db_name = "appjornada"
    if "/" in MONGO_URL.split("://")[-1]:
        part = MONGO_URL.split("://")[-1].split("/")[1]
        if "?" in part:
            db_name = part.split("?")[0]
        elif part:
            db_name = part

    db = mongo_client[db_name]

    config_apk = {
        "_id": "config_apk",
        "versao": nome_versao,
        "build_number": build_number,
        "versao_completa": versao_completa,
        "nome_arquivo": target_filename,
        "tamanho_mb": f"{tamanho_mb:.1f} MB",
        "minio_object_name": object_name,
        "url_download": "/api/config/apk/download",
        "minio_url": f"/{MINIO_BUCKET}/{object_name}",
        "updated_at": datetime.utcnow().isoformat()
    }

    db["configuracoes"].update_one(
        {"_id": "config_apk"},
        {"$set": config_apk},
        upsert=True
    )

    print(f"==> [sync_apk] SUCESSO: Versão v{nome_versao} registrada no MongoDB e MinIO com sucesso!")

if __name__ == "__main__":
    apk = sys.argv[1] if len(sys.argv) > 1 else "/app/app-release.apk"
    ver = sys.argv[2] if len(sys.argv) > 2 else "1.2.4"
    sync_apk(apk, ver)
