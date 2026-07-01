from datetime import datetime, timezone
from typing import Dict, Any, Optional

async def registrar_auditoria(db, user: dict, acao: str, detalhes: Optional[Dict[str, Any]] = None):
    """
    Registra uma ação sensível ou destrutiva no banco de dados.
    A coleção 'audit_logs' não possui endpoints de exclusão, garantindo imutabilidade.
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc),
        "user_id": str(user.get("id", "")),
        "user_email": user.get("email", ""),
        "acao": acao,
        "detalhes": detalhes or {}
    }
    await db["audit_logs"].insert_one(log_entry)
