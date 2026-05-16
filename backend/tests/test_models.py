"""
Testes unitários dos modelos Pydantic.
Valida campos, tipos, aliases e regras de negócio dos models.
"""
import pytest
from bson import ObjectId
from datetime import date, time

from app.models.base import PyObjectId
from app.models.user import Role, User, UserPublic, UserCreate
from app.models.motorista import CNH, DadosBancarios, PerfilMotorista
from app.models.veiculo import Veiculo, VeiculoCreate
from app.models.jornada import (
    Jornada, JornadaBase, Localizacao, KmJornada,
    HorarioJornada, Faturamento, Pausa, Abastecimento, Sinistro,
)
from app.models.historico_gps import GeoPoint, HistoricoGPS
from app.models.manutencao import Manutencao, Servico
from app.models.meta_bonus import MetaBonus
from app.models.token import Token, TokenData


class TestPyObjectId:
    def test_aceita_string_hex_valida(self):
        oid_str = str(ObjectId())
        resultado = PyObjectId.validate(oid_str)
        assert isinstance(resultado, ObjectId)
        assert str(resultado) == oid_str

    def test_aceita_objectid_direto(self):
        oid = ObjectId()
        resultado = PyObjectId.validate(oid)
        assert resultado == oid

    def test_rejeita_string_invalida(self):
        with pytest.raises(ValueError):
            PyObjectId.validate("nao_e_um_objectid")

    def test_rejeita_string_vazia(self):
        with pytest.raises(ValueError):
            PyObjectId.validate("")


class TestRoleEnum:
    def test_roles_existem(self):
        assert Role.MOTORISTA == "MOTORISTA"
        assert Role.GESTOR == "GESTOR"
        assert Role.ADMIN == "ADMIN"

    def test_role_e_string(self):
        assert isinstance(Role.MOTORISTA, str)


class TestUserModels:
    def test_user_create_requer_campos_obrigatorios(self):
        u = UserCreate(
            nome="João",
            email="joao@example.com",
            senha="senha123",
            role=Role.MOTORISTA,
        )
        assert u.nome == "João"
        assert u.email == "joao@example.com"
        assert u.pin is None

    def test_user_create_com_pin(self):
        u = UserCreate(
            nome="João",
            email="joao@example.com",
            senha="senha123",
            role=Role.MOTORISTA,
            pin="1234",
        )
        assert u.pin == "1234"

    def test_user_public_alias(self):
        uid = ObjectId()
        u = UserPublic(
            **{
                "_id": str(uid),
                "nome": "Teste",
                "email": "t@t.com",
                "role": "ADMIN",
                "situacao": "Ativo",
            }
        )
        assert u.id == str(uid)

    def test_user_public_sem_senha_hash(self):
        """UserPublic nunca deve ter o campo senha_hash."""
        campos = UserPublic.model_fields
        assert "senha_hash" not in campos

    def test_situacao_default_ativo(self):
        u = UserCreate(nome="X", email="x@x.com", senha="abc", role=Role.GESTOR)
        assert u.situacao == "Ativo"


class TestPerfilMotorista:
    def test_nivel_id_presente(self):
        """nivel_id (ID_NIVEL do Excel) deve existir no model."""
        p = PerfilMotorista(cpf="111.111.111-11", nivel_id="N2")
        assert p.nivel_id == "N2"

    def test_cnh_model(self):
        cnh = CNH(vencimento=date(2030, 1, 1))
        assert cnh.vencimento == date(2030, 1, 1)
        assert cnh.imagem_url is None

    def test_dados_bancarios_cnpj(self):
        db = DadosBancarios(cnpj="11.111.111/0001-11", empresa="Empresa LTDA")
        assert db.cnpj == "11.111.111/0001-11"


class TestVeiculoModels:
    def test_veiculo_create(self):
        v = VeiculoCreate(id_placa="RMQ8H57", marca_modelo="FIAT/UNO", cor="BRANCO")
        assert v.situacao == "RODANDO"

    def test_veiculo_alias(self):
        v = Veiculo(**{"_id": "RMQ8H57", "id_placa": "RMQ8H57", "marca_modelo": "FIAT"})
        assert v.id == "RMQ8H57"


class TestJornadaModels:
    def test_localizacao(self):
        loc = Localizacao(lat=-20.21, lon=-40.26)
        assert loc.lat == -20.21

    def test_km_jornada_defaults(self):
        km = KmJornada()
        assert km.morta == 0.0
        assert km.rodados is None

    def test_faturamento_defaults(self):
        f = Faturamento()
        assert f.uber == 0.0
        assert f.total_dia == 0.0

    def test_pausa_tipo_default(self):
        p = Pausa(id="abc123")
        assert p.tipo == "PAUSA_MOTORISTA"

    def test_sinistro_imagens_vazia(self):
        s = Sinistro(id="sin001")
        assert s.imagens_urls == []

    def test_jornada_clt_defaults(self):
        uid = ObjectId()
        j = Jornada(**{
            "_id": "teste-TST-001",
            "motorista_id": str(uid),
            "veiculo_id": "TST1234",
        })
        assert j.jornada_diaria_clt == 8.0
        assert j.jornada_semanal_clt == 44.0
        assert j.jornada_mensal_clt == 220.0

    def test_jornada_pin_opcional(self):
        uid = ObjectId()
        j = Jornada(**{
            "_id": "teste-TST-002",
            "motorista_id": str(uid),
            "veiculo_id": "TST1234",
        })
        assert j.pin is None

    def test_jornada_status_default(self):
        uid = ObjectId()
        j = Jornada(**{
            "_id": "teste-TST-003",
            "motorista_id": str(uid),
            "veiculo_id": "TST1234",
        })
        assert j.status == "ABERTA"

    def test_jornada_subdocumentos_vazios(self):
        uid = ObjectId()
        j = Jornada(**{
            "_id": "teste-TST-004",
            "motorista_id": str(uid),
            "veiculo_id": "TST1234",
        })
        assert j.pausas == []
        assert j.abastecimentos == []
        assert j.sinistros == []


class TestGPSModels:
    def test_geopoint_type_default(self):
        gp = GeoPoint(coordinates=[-40.26, -20.21])
        assert gp.type == "Point"
        assert gp.coordinates == [-40.26, -20.21]

    def test_geopoint_coordenadas_ordem(self):
        """GeoJSON usa [longitude, latitude]."""
        gp = GeoPoint(coordinates=[-40.26, -20.21])
        assert gp.coordinates[0] == -40.26  # longitude
        assert gp.coordinates[1] == -20.21  # latitude


class TestTokenModels:
    def test_token_type_default(self):
        t = Token(access_token="abc")
        assert t.token_type == "bearer"

    def test_token_data_opcional(self):
        td = TokenData()
        assert td.user_id is None
        assert td.role is None


class TestMetaBonusModel:
    def test_referencia_default_geral(self):
        m = MetaBonus(**{
            "_id": str(ObjectId()),
            "tipo": "META 430",
        })
        assert m.referencia == "GERAL"
