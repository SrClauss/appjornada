"""
Testes dos endpoints de autenticação: /auth/registrar, /auth/login, /auth/me
"""
import pytest


class TestRegistrar:
    async def test_registrar_motorista_sucesso(self, client):
        resp = await client.post("/auth/registrar", json={
            "nome": "Novo Motorista",
            "email": "novo@example.com",
            "pin": "1234",
            "role": "MOTORISTA",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "novo@example.com"
        assert data["nome"] == "Novo Motorista"
        assert data["role"] == "MOTORISTA"

    async def test_registrar_gestor(self, client):
        resp = await client.post("/auth/registrar", json={
            "nome": "Novo Gestor",
            "email": "gestor_novo@example.com",
            "senha": "senha123",
            "role": "GESTOR",
        })
        assert resp.status_code == 201

    async def test_registrar_com_perfil_motorista(self, client):
        resp = await client.post("/auth/registrar", json={
            "nome": "Motorista Completo",
            "email": "completo@example.com",
            "role": "MOTORISTA",
            "pin": "5678",
            "perfil_motorista": {
                "cpf": "222.222.222-22",
                "telefone": "27988888888",
                "nivel_id": "N1",
                "cnh": {"vencimento": "2032-06-15", "imagem_url": None},
            },
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["perfil_motorista"]["cpf"] == "222.222.222-22"
        assert data["perfil_motorista"]["nivel_id"] == "N1"

    async def test_registrar_email_duplicado_retorna_409(self, client):
        payload = {
            "nome": "Dup",
            "email": "dup@example.com",
            "pin": "1234",
            "role": "MOTORISTA",
        }
        await client.post("/auth/registrar", json=payload)
        resp = await client.post("/auth/registrar", json=payload)
        assert resp.status_code == 409

    async def test_registrar_email_invalido_retorna_422(self, client):
        resp = await client.post("/auth/registrar", json={
            "nome": "X",
            "email": "nao_e_email",
            "pin": "1234",
            "role": "MOTORISTA",
        })
        assert resp.status_code == 422

    async def test_resposta_nao_expoe_senha_hash(self, client):
        resp = await client.post("/auth/registrar", json={
            "nome": "Seguro",
            "email": "seguro@example.com",
            "pin": "1234",
            "role": "MOTORISTA",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "senha_hash" not in data
        assert "pin_hash" not in data


    async def test_registrar_motorista_sem_pin_retorna_422(self, client):
        resp = await client.post("/auth/registrar", json={
            "nome": "Sem Pin",
            "email": "sempin@example.com",
            "role": "MOTORISTA",
        })
        assert resp.status_code == 422

    async def test_registrar_gestor_sem_senha_retorna_422(self, client):
        resp = await client.post("/auth/registrar", json={
            "nome": "Sem Senha",
            "email": "semsenha@example.com",
            "role": "GESTOR",
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_sucesso(self, client):
        await client.post("/auth/registrar", json={
            "nome": "Login OK",
            "email": "loginok@test.com",
            "senha": "senha123",
            "role": "GESTOR",
        })
        resp = await client.post("/auth/login", data={
            "username": "loginok@test.com",
            "password": "senha123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_senha_errada(self, client):
        await client.post("/auth/registrar", json={
            "nome": "Errado",
            "email": "errado@test.com",
            "senha": "senha123",
            "role": "GESTOR",
        })
        resp = await client.post("/auth/login", data={
            "username": "errado@test.com",
            "password": "senhaerrada",
        })
        assert resp.status_code == 401

    async def test_login_email_inexistente(self, client):
        resp = await client.post("/auth/login", data={
            "username": "naoexiste@test.com",
            "password": "abc",
        })
        assert resp.status_code == 401

    async def test_login_usuario_inativo(self, client, db):
        """Usuário com situacao='Inativo' não consegue logar."""
        from app.core.security import hash_senha
        from bson import ObjectId

        await db["users"].insert_one({
            "_id": ObjectId(),
            "nome": "Inativo",
            "email": "inativo@test.com",
            "senha_hash": hash_senha("senha123"),
            "pin_hash": None,
            "role": "MOTORISTA",
            "situacao": "Inativo",
            "perfil_motorista": None,
        })
        resp = await client.post("/auth/login", data={
            "username": "inativo@test.com",
            "password": "senha123",
        })
        assert resp.status_code == 403

    async def test_token_permite_acesso_me(self, client):
        await client.post("/auth/registrar", json={
            "nome": "Token Test",
            "email": "tokentest@test.com",
            "senha": "senha123",
            "role": "ADMIN",
        })
        login_resp = await client.post("/auth/login", data={
            "username": "tokentest@test.com",
            "password": "senha123",
        })
        token = login_resp.json()["access_token"]
        me_resp = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "tokentest@test.com"


class TestMe:
    async def test_me_retorna_usuario_autenticado(self, client, admin_user, admin_headers):
        resp = await client.get("/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == admin_user["email"]
        assert data["role"] == "ADMIN"

    async def test_me_sem_token_retorna_401(self, client):
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

    async def test_me_token_invalido_retorna_401(self, client):
        resp = await client.get(
            "/auth/me", headers={"Authorization": "Bearer token.invalido.aqui"}
        )
        assert resp.status_code == 401

    async def test_me_nao_expoe_senha(self, client, motorista_user, motorista_headers):
        resp = await client.get("/auth/me", headers=motorista_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "senha_hash" not in data
        assert "pin_hash" not in data


class TestSetupNeeded:
    async def test_setup_needed_true_quando_sem_usuarios(self, client, db):
        """Retorna setup_needed=True quando não há usuários no banco."""
        resp = await client.get("/auth/setup-needed")
        assert resp.status_code == 200
        assert resp.json()["setup_needed"] is True

    async def test_setup_needed_false_quando_ha_usuarios(
        self, client, admin_user
    ):
        """Retorna setup_needed=False quando já há ao menos um usuário."""
        resp = await client.get("/auth/setup-needed")
        assert resp.status_code == 200
        assert resp.json()["setup_needed"] is False


class TestDependenciesEdgeCases:
    async def test_token_sem_sub_retorna_401(self, client):
        """Token JWT sem campo 'sub' deve retornar 401."""
        from app.core.security import criar_access_token

        token = criar_access_token({"role": "ADMIN"})  # sem 'sub'
        resp = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    async def test_token_usuario_deletado_retorna_401(self, client, db):
        """Token válido mas usuário inexistente no banco deve retornar 401."""
        from app.core.security import criar_access_token
        from bson import ObjectId

        uid_inexistente = str(ObjectId())
        token = criar_access_token({"sub": uid_inexistente, "role": "ADMIN"})
        resp = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401


class TestAuthService:
    async def test_buscar_usuario_por_id_sucesso(self, db, admin_user):
        """buscar_usuario_por_id deve retornar UserPublic quando usuário existe."""
        from app.services.auth_service import buscar_usuario_por_id

        result = await buscar_usuario_por_id(db, admin_user["id"])
        assert result.email == admin_user["email"]
        assert result.role == "ADMIN"

    async def test_buscar_usuario_por_id_nao_encontrado_retorna_404(self, db):
        """buscar_usuario_por_id deve lançar HTTPException 404 quando não encontrado."""
        from fastapi import HTTPException
        from app.services.auth_service import buscar_usuario_por_id
        from bson import ObjectId

        uid_inexistente = str(ObjectId())
        with pytest.raises(HTTPException) as exc_info:
            await buscar_usuario_por_id(db, uid_inexistente)
        assert exc_info.value.status_code == 404
