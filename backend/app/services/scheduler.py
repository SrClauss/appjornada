"""
Background scheduler para encerramento automático de jornadas.

Roda todos os dias às 23:30 (horário do servidor) e fecha qualquer
jornada com status ABERTA ou EM_ANDAMENTO, exatamente como o
Google Apps Script fazia no Excel.
"""
from datetime import datetime, timezone, date, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.database import get_db

_scheduler: AsyncIOScheduler | None = None

HORA_ENCERRAMENTO = 23
MINUTO_ENCERRAMENTO = 30


async def _encerrar_jornadas_abertas() -> None:
    """Fecha todas as jornadas ainda abertas. Chamado pelo scheduler."""
    db = get_db()
    agora = datetime.now(timezone.utc)
    hora_str = agora.time().isoformat(timespec="seconds")

    resultado = await db["jornadas"].update_many(
        {"status": {"$in": ["ABERTA", "EM_ANDAMENTO", "EM_PAUSA"]}},
        {
            "$set": {
                "status": "ENCERRADA",
                "horario.fim": hora_str,
                "observacoes": f"⚠️ Encerrado automaticamente pelo sistema às {hora_str}",
            }
        },
    )

    if resultado.modified_count > 0:
        # Registra no log — em produção substitua por logger estruturado
        print(
            f"[scheduler] {resultado.modified_count} jornada(s) encerrada(s) "
            f"automaticamente às {hora_str}"
        )


def criar_scheduler() -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
    _scheduler.add_job(
        _encerrar_jornadas_abertas,
        CronTrigger(hour=HORA_ENCERRAMENTO, minute=MINUTO_ENCERRAMENTO),
        id="encerrar_jornadas",
        replace_existing=True,
        misfire_grace_time=300,  # tolera até 5 min de atraso
    )
    return _scheduler


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler
