"""
Testes do serviço de scheduler: encerramento automático de jornadas
e criação/acesso do scheduler APScheduler.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class TestEncerrarJornadasAbertas:
    async def test_encerra_jornadas_abertas_e_em_andamento(self):
        """_encerrar_jornadas_abertas deve chamar update_many no status correto."""
        from app.services.scheduler import _encerrar_jornadas_abertas

        mock_result = MagicMock()
        mock_result.modified_count = 3

        mock_collection = MagicMock()
        mock_collection.update_many = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.services.scheduler.get_db", return_value=mock_db):
            await _encerrar_jornadas_abertas()

        mock_collection.update_many.assert_called_once()
        call_args = mock_collection.update_many.call_args
        filtro = call_args[0][0]
        assert filtro["status"]["$in"] == ["ABERTA", "EM_ANDAMENTO", "EM_PAUSA"]

    async def test_encerra_define_status_encerrada(self):
        """O $set deve incluir status=ENCERRADA."""
        from app.services.scheduler import _encerrar_jornadas_abertas

        mock_result = MagicMock()
        mock_result.modified_count = 1

        mock_collection = MagicMock()
        mock_collection.update_many = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.services.scheduler.get_db", return_value=mock_db):
            await _encerrar_jornadas_abertas()

        call_args = mock_collection.update_many.call_args
        update = call_args[0][1]
        assert update["$set"]["status"] == "ENCERRADA"

    async def test_encerra_define_observacao_automatica(self):
        """Jornadas encerradas pelo scheduler devem ter observação indicando isso."""
        from app.services.scheduler import _encerrar_jornadas_abertas

        mock_result = MagicMock()
        mock_result.modified_count = 2

        mock_collection = MagicMock()
        mock_collection.update_many = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.services.scheduler.get_db", return_value=mock_db):
            await _encerrar_jornadas_abertas()

        call_args = mock_collection.update_many.call_args
        update = call_args[0][1]
        obs = update["$set"].get("observacoes", "")
        assert "automaticamente" in obs.lower() or "sistema" in obs.lower()

    async def test_sem_jornadas_abertas_nao_lanca_excecao(self):
        """Quando não há jornadas para encerrar, nenhuma exceção deve ser lançada."""
        from app.services.scheduler import _encerrar_jornadas_abertas

        mock_result = MagicMock()
        mock_result.modified_count = 0

        mock_collection = MagicMock()
        mock_collection.update_many = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.services.scheduler.get_db", return_value=mock_db):
            await _encerrar_jornadas_abertas()  # não deve lançar

    async def test_encerra_define_horario_fim(self):
        """O $set deve incluir horario.fim com a hora do encerramento."""
        from app.services.scheduler import _encerrar_jornadas_abertas

        mock_result = MagicMock()
        mock_result.modified_count = 1

        mock_collection = MagicMock()
        mock_collection.update_many = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.services.scheduler.get_db", return_value=mock_db):
            await _encerrar_jornadas_abertas()

        call_args = mock_collection.update_many.call_args
        update = call_args[0][1]
        assert "horario.fim" in update["$set"]


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
