"""
Testes da camada de banco de dados: get_client, get_db,
_tentar_criar_indice, connect_db, close_db.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


class TestGetClientGetDb:
    def test_get_client_retorna_instancia_motor(self):
        """get_client deve retornar um AsyncIOMotorClient."""
        from motor.motor_asyncio import AsyncIOMotorClient
        import app.db.database as db_mod

        # Reseta o cliente global para garantir que seja criado neste teste
        original = db_mod._client
        db_mod._client = None
        try:
            with patch("app.db.database.AsyncIOMotorClient") as mock_cls:
                mock_cls.return_value = MagicMock(spec=AsyncIOMotorClient)
                client = db_mod.get_client()
                mock_cls.assert_called_once()
                assert client is not None
        finally:
            db_mod._client = original

    def test_get_client_reutiliza_instancia_existente(self):
        """get_client deve retornar o mesmo cliente quando já está inicializado."""
        import app.db.database as db_mod

        mock_client = MagicMock()
        original = db_mod._client
        db_mod._client = mock_client
        try:
            result = db_mod.get_client()
            assert result is mock_client
        finally:
            db_mod._client = original

    def test_get_db_retorna_database(self):
        """get_db deve retornar o banco padrão do cliente."""
        import app.db.database as db_mod

        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_client.get_default_database.return_value = mock_db

        original = db_mod._client
        db_mod._client = mock_client
        try:
            result = db_mod.get_db()
            assert result is mock_db
            mock_client.get_default_database.assert_called_once()
        finally:
            db_mod._client = original


class TestTentarCriarIndice:
    async def test_criar_indice_sucesso(self):
        """_tentar_criar_indice deve chamar create_index com os parâmetros corretos."""
        from app.db.database import _tentar_criar_indice

        mock_collection = MagicMock()
        mock_collection.create_index = AsyncMock(return_value="email_1")

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        await _tentar_criar_indice(mock_db, "users", "email", unique=True)
        mock_collection.create_index.assert_called_once_with("email", unique=True)

    async def test_criar_indice_timeout_loga_aviso(self):
        """_tentar_criar_indice deve logar aviso e não lançar exceção em timeout."""
        from app.db.database import _tentar_criar_indice

        async def _mock_create_index(*args, **kwargs):
            await asyncio.sleep(999)

        mock_collection = MagicMock()
        mock_collection.create_index = _mock_create_index

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.db.database.asyncio.wait_for", side_effect=asyncio.TimeoutError):
            # Não deve lançar exceção
            await _tentar_criar_indice(mock_db, "jornadas", "status")

    async def test_criar_indice_excecao_geral_loga_aviso(self):
        """_tentar_criar_indice deve logar aviso e não lançar exceção em erros gerais."""
        from app.db.database import _tentar_criar_indice

        mock_collection = MagicMock()
        mock_collection.create_index = AsyncMock(side_effect=Exception("falha simulada"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        # Não deve lançar exceção
        await _tentar_criar_indice(mock_db, "historico_gps", "motorista_id")


class TestCriarIndices:
    async def test_criar_indices_chama_tentar_para_cada_colecao(self):
        """_criar_indices deve chamar _tentar_criar_indice para cada índice definido."""
        from app.db.database import _criar_indices

        chamadas = []

        async def mock_tentar(db, colecao, keys, **kwargs):
            chamadas.append(colecao)

        mock_db = MagicMock()

        with patch("app.db.database._tentar_criar_indice", side_effect=mock_tentar):
            await _criar_indices(mock_db)

        # Deve ter tentado criar índices em pelo menos: users, jornadas, historico_gps, manutencoes
        assert "users" in chamadas
        assert "jornadas" in chamadas
        assert "historico_gps" in chamadas
        assert "manutencoes" in chamadas


class TestConnectCloseDb:
    async def test_connect_db_chama_criar_indices(self):
        """connect_db deve chamar _criar_indices."""
        from app.db.database import connect_db

        mock_db = MagicMock()

        with (
            patch("app.db.database.get_db", return_value=mock_db),
            patch("app.db.database._criar_indices", new_callable=AsyncMock) as mock_indices,
        ):
            await connect_db()
            mock_indices.assert_called_once_with(mock_db)

    async def test_close_db_fecha_cliente(self):
        """close_db deve fechar o cliente e resetar _client para None."""
        import app.db.database as db_mod

        mock_client = MagicMock()
        original = db_mod._client
        db_mod._client = mock_client
        try:
            from app.db.database import close_db
            await close_db()
            mock_client.close.assert_called_once()
            assert db_mod._client is None
        finally:
            db_mod._client = original

    async def test_close_db_sem_cliente_nao_lanca_excecao(self):
        """close_db com _client=None não deve lançar exceção."""
        import app.db.database as db_mod

        original = db_mod._client
        db_mod._client = None
        try:
            from app.db.database import close_db
            await close_db()  # não deve lançar
        finally:
            db_mod._client = original
