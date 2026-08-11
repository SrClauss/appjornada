"""
Testes do serviço de scheduler: encerramento automático de jornadas
e criação/acesso do scheduler APScheduler.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class TestEncerrarJornadasAbertas:
    async def test_encerrar_jornadas_abertas_desativado(self):
        """_encerrar_jornadas_abertas foi desativado e não deve alterar o banco."""
        from app.services.scheduler import _encerrar_jornadas_abertas

        # Deve rodar sem erros e sem efetuar chamadas de banco
        await _encerrar_jornadas_abertas()


class TestCriarScheduler:
    def test_criar_scheduler_retorna_instancia(self):
        """criar_scheduler deve retornar um AsyncIOScheduler."""
        from app.services.scheduler import criar_scheduler
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        sched = criar_scheduler()
        assert isinstance(sched, AsyncIOScheduler)

    def test_criar_scheduler_tem_job_encerrar_jornadas(self):
        """O scheduler deve ter o job 'encerrar_jornadas' registrado."""
        from app.services.scheduler import criar_scheduler

        sched = criar_scheduler()
        job_ids = [job.id for job in sched.get_jobs()]
        assert "encerrar_jornadas" in job_ids

    def test_criar_scheduler_timezone_sao_paulo(self):
        """O scheduler deve usar timezone America/Sao_Paulo."""
        from app.services.scheduler import criar_scheduler

        sched = criar_scheduler()
        assert str(sched.timezone) == "America/Sao_Paulo"

    def test_criar_scheduler_atualiza_referencia_global(self):
        """Após criar_scheduler, get_scheduler deve retornar a mesma instância."""
        from app.services.scheduler import criar_scheduler, get_scheduler

        sched = criar_scheduler()
        assert get_scheduler() is sched


class TestGetScheduler:
    def test_get_scheduler_inicial_pode_ser_none_ou_instancia(self):
        """get_scheduler retorna None (antes de criar) ou uma instância válida."""
        from app.services.scheduler import get_scheduler
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        result = get_scheduler()
        assert result is None or isinstance(result, AsyncIOScheduler)

    def test_get_scheduler_retorna_instancia_criada(self):
        """Após criar_scheduler, get_scheduler deve retornar a instância correta."""
        from app.services.scheduler import criar_scheduler, get_scheduler
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        sched = criar_scheduler()
        assert isinstance(get_scheduler(), AsyncIOScheduler)
