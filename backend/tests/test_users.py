"""
Testes dos endpoints de usuários: /users/
Cobre CRUD, restrições por role e soft delete.
"""
import pytest
from bson import ObjectId


class TestListarUsers:
    async def test_admin_lista_todos(self, client, admin_user, motorista_user, admin_headers):
        resp = await client.get("/users/", headers=admin_headers)
        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()]
        assert admin_user["email"] in emails
        assert motorista_user["email"] in emails

    async def test_gestor_lista_usuarios(self, client, admin_user, gestor_headers):
        resp = await client.get("/users/", headers=gestor_headers)
        assert resp.status_code == 200

    async def test_motorista_nao_pode_listar(self, client, motorista_headers):
        resp = await client.get("/users/", headers=motorista_headers)
        assert resp.status_code == 403

    async def test_filtro_por_role(self, client, motorista_user, admin_user, admin_headers):
        resp = await client.get("/users/?role=MOTORISTA", headers=admin_headers)
        assert resp.status_code == 200
        roles = [u["role"] for u in resp.json()]
        assert all(r == "MOTORISTA" for r in roles)

    async def test_filtro_por_situacao(self, client, admin_user, admin_headers, db):
        from app.core.security import hash_senha
        await db["users"].insert_one({
            "_id": ObjectId(),
            "nome": "Inativo", "email": "inativo2@test.com",
            "senha_hash": hash_senha("x"), "pin_hash": None,
            "role": "MOTORISTA", "situacao": "Inativo", "perfil_motorista": None,
        })
        resp = await client.get("/users/?situacao=Inativo", headers=admin_headers)
        assert resp.status_code == 200
        assert all(u["situacao"] == "Inativo" for u in resp.json())

    async def test_paginacao_skip_limit(self, client, admin_user, admin_headers):
        resp = await client.get("/users/?skip=0&limit=1", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 1

    async def test_sem_token_retorna_401(self, client):
        resp = await client.get("/users/")
        assert resp.status_code == 401


class TestGetUser:
    async def test_admin_ve_qualquer_usuario(
        self, client, motorista_user, admin_headers
    ):
        resp = await client.get(f"/users/{motorista_user['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == motorista_user["email"]

    async def test_motorista_ve_si_mesmo(self, client, motorista_user, motorista_headers):
        resp = await client.get(
            f"/users/{motorista_user['id']}", headers=motorista_headers
        )
        assert resp.status_code == 200

    async def test_motorista_nao_ve_outro_usuario(
        self, client, admin_user, motorista_headers
    ):
        resp = await client.get(f"/users/{admin_user['id']}", headers=motorista_headers)
        assert resp.status_code == 403

    async def test_usuario_inexistente_retorna_404(self, client, admin_headers):
        uid_falso = str(ObjectId())
        resp = await client.get(f"/users/{uid_falso}", headers=admin_headers)
        assert resp.status_code == 404

    async def test_resposta_nao_contem_senha_hash(
        self, client, motorista_user, admin_headers
    ):
        resp = await client.get(f"/users/{motorista_user['id']}", headers=admin_headers)
        assert "senha_hash" not in resp.json()
        assert "pin_hash" not in resp.json()


class TestAtualizarUser:
    async def test_admin_atualiza_nome(self, client, motorista_user, admin_headers):
        resp = await client.patch(
            f"/users/{motorista_user['id']}",
            json={"nome": "Motorista Atualizado"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["nome"] == "Motorista Atualizado"

    async def test_motorista_atualiza_proprio_perfil(
        self, client, motorista_user, motorista_headers
    ):
        resp = await client.patch(
            f"/users/{motorista_user['id']}",
            json={"nome": "Meu Novo Nome"},
            headers=motorista_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["nome"] == "Meu Novo Nome"

    async def test_motorista_nao_atualiza_outro(
        self, client, admin_user, motorista_headers
    ):
        resp = await client.patch(
            f"/users/{admin_user['id']}",
            json={"nome": "Tentativa"},
            headers=motorista_headers,
        )
        assert resp.status_code == 403

    async def test_atualizar_trocar_pin(
        self, client, motorista_user, admin_headers, db
    ):
        """Trocar o PIN deve salvar o hash, não o PIN em texto claro."""
        resp = await client.patch(
            f"/users/{motorista_user['id']}",
            json={"pin": "9999"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        doc = await db["users"].find_one({"_id": ObjectId(motorista_user["id"])})
        assert doc["pin_hash"] is not None
        assert doc.get("pin") is None  # pin em texto não deve ser salvo

    async def test_atualizar_trocar_senha(
        self, client, motorista_user, admin_headers, db
    ):
        resp = await client.patch(
            f"/users/{motorista_user['id']}",
            json={"senha": "nova_senha_123"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        doc = await db["users"].find_one({"_id": ObjectId(motorista_user["id"])})
        # Senha não pode ser a string em plain text
        assert doc["senha_hash"] != "nova_senha_123"


class TestDeletarUser:
    async def test_admin_inativa_usuario_soft_delete(
        self, client, motorista_user, admin_headers, db
    ):
        resp = await client.delete(
            f"/users/{motorista_user['id']}", headers=admin_headers
        )
        assert resp.status_code == 204
        doc = await db["users"].find_one({"_id": ObjectId(motorista_user["id"])})
        assert doc is not None  # documento ainda existe (soft delete)
        assert doc["situacao"] == "Inativo"

    async def test_gestor_nao_pode_deletar(
        self, client, motorista_user, gestor_headers
    ):
        resp = await client.delete(
            f"/users/{motorista_user['id']}", headers=gestor_headers
        )
        assert resp.status_code == 403

    async def test_motorista_nao_pode_deletar(
        self, client, motorista_user, motorista_headers
    ):
        resp = await client.delete(
            f"/users/{motorista_user['id']}", headers=motorista_headers
        )
        assert resp.status_code == 403

    async def test_deletar_usuario_inexistente_retorna_404(
        self, client, admin_headers
    ):
        uid_falso = str(ObjectId())
        resp = await client.delete(f"/users/{uid_falso}", headers=admin_headers)
        assert resp.status_code == 404
