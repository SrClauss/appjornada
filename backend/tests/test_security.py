"""
Testes unitários de segurança: hash de senha e JWT.
Não dependem de banco nem do app FastAPI.
"""
from datetime import timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    criar_access_token,
    decodificar_token,
    hash_senha,
    verificar_senha,
)


class TestHashSenha:
    def test_hash_diferente_da_original(self):
        h = hash_senha("minha_senha")
        assert h != "minha_senha"

    def test_hash_bcrypt_prefix(self):
        h = hash_senha("abc")
        assert h.startswith("$2")

    def test_senhas_iguais_geram_hashes_diferentes(self):
        """bcrypt usa salt aleatório — dois hashes da mesma senha são distintos."""
        h1 = hash_senha("senha")
        h2 = hash_senha("senha")
        assert h1 != h2

    def test_verificar_senha_correta(self):
        h = hash_senha("senha123")
        assert verificar_senha("senha123", h) is True

    def test_verificar_senha_errada(self):
        h = hash_senha("senha123")
        assert verificar_senha("errada", h) is False

    def test_verificar_senha_vazia(self):
        h = hash_senha("senha123")
        assert verificar_senha("", h) is False

    def test_hash_pin_curto(self):
        """PINs de 4 dígitos devem funcionar normalmente."""
        h = hash_senha("1234")
        assert verificar_senha("1234", h) is True
        assert verificar_senha("1235", h) is False


class TestJWT:
    def test_criar_e_decodificar_token(self):
        token = criar_access_token({"sub": "user123", "role": "MOTORISTA"})
        payload = decodificar_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["role"] == "MOTORISTA"

    def test_token_expirado(self):
        token = criar_access_token(
            {"sub": "user123"},
            expires_delta=timedelta(seconds=-1),
        )
        payload = decodificar_token(token)
        assert payload is None

    def test_token_adulterado(self):
        token = criar_access_token({"sub": "user123"})
        partes = token.split(".")
        token_adulterado = partes[0] + "." + partes[1] + ".assinatura_invalida"
        payload = decodificar_token(token_adulterado)
        assert payload is None

    def test_token_invalido_completo(self):
        payload = decodificar_token("nao.e.um.jwt")
        assert payload is None

    def test_token_contem_exp(self):
        token = criar_access_token({"sub": "u1"})
        payload = decodificar_token(token)
        assert "exp" in payload

    def test_token_com_delta_customizado(self):
        token = criar_access_token({"sub": "u1"}, expires_delta=timedelta(hours=1))
        payload = decodificar_token(token)
        assert payload is not None

    def test_algoritmo_correto(self):
        token = criar_access_token({"sub": "u1"})
        header = jwt.get_unverified_header(token)
        assert header["alg"] == settings.ALGORITHM
