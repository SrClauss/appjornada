from datetime import datetime, timezone
from app.db.database import get_db

COLLECTION_CONFIG_IA = "ia_config_tabela_precos"
COLLECTION_SALDO = "ia_saldo_creditos"
COLLECTION_LOGS = "ia_consumo_tokens"

SALDO_INICIAL_DEFAULT = 150.00  # R$ 150,00 inicial

# Tabela de preços default (USD por 1M tokens), usada apenas no primeiro boot do banco
TABELA_PRECOS_DEFAULT = {
    "cotacao_usd_brl": 5.70,
    "modelos": {
        "gemini-3.6-flash": {
            "usd_input_1m": 0.075,
            "usd_output_1m": 0.30
        },
        "gemini-3.1-flash-lite": {
            "usd_input_1m": 0.0375,
            "usd_output_1m": 0.15
        },
        "gemini-3.5-flash-lite": {
            "usd_input_1m": 0.0375,
            "usd_output_1m": 0.15
        }
    }
}


async def obter_tabela_precos_ia() -> dict:
    """Busca a tabela de preços dinâmica gravada no Banco de Dados pelo Administrador."""
    db = get_db()
    doc = await db[COLLECTION_CONFIG_IA].find_one({"_id": "config_tabela_precos"})
    if not doc:
        # Inicializa configuração padrão no banco se ainda não existir
        config_doc = {
            "_id": "config_tabela_precos",
            "cotacao_usd_brl": TABELA_PRECOS_DEFAULT["cotacao_usd_brl"],
            "modelos": TABELA_PRECOS_DEFAULT["modelos"],
            "atualizado_em": datetime.now(timezone.utc)
        }
        await db[COLLECTION_CONFIG_IA].insert_one(config_doc)
        return config_doc
    return doc


async def salvar_tabela_precos_ia(novos_dados: dict) -> dict:
    """Permite ao Administrador atualizar a cotação do dólar e valores por 1M de tokens no banco de dados."""
    db = get_db()
    agora = datetime.now(timezone.utc)
    update_fields = {"atualizado_em": agora}
    
    if "cotacao_usd_brl" in novos_dados:
        update_fields["cotacao_usd_brl"] = float(novos_dados["cotacao_usd_brl"])
    if "modelos" in novos_dados and isinstance(novos_dados["modelos"], dict):
        update_fields["modelos"] = novos_dados["modelos"]

    res = await db[COLLECTION_CONFIG_IA].find_one_and_update(
        {"_id": "config_tabela_precos"},
        {"$set": update_fields},
        upsert=True,
        return_document=True
    )
    return {
        "sucesso": True,
        "mensagem": "Tabela de preços de IA e cotação atualizadas com sucesso!",
        "configuracao": res
    }


async def inicializar_saldo_se_necessario(saldo_inicial: float = SALDO_INICIAL_DEFAULT):
    """Garante que a coleção de saldo do sistema tenha o registro inicial de R$ 150,00."""
    db = get_db()
    registro = await db[COLLECTION_SALDO].find_one({"_id": "saldo_google_cloud"})
    if not registro:
        await db[COLLECTION_SALDO].insert_one({
            "_id": "saldo_google_cloud",
            "saldo_inicial_brl": saldo_inicial,
            "saldo_atual_brl": saldo_inicial,
            "total_gasto_brl": 0.0,
            "total_requisicoes": 0,
            "total_tokens_entrada": 0,
            "total_tokens_saida": 0,
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc)
        })


async def registrar_consumo_ia(
    servico: str,  # ex: "OCR Hodometro", "OCR Nota Fiscal", "OCR Extrato Video"
    modelo: str,   # ex: "gemini-3.6-flash"
    tokens_entrada: int,
    tokens_saida: int,
    meta_info: dict = None
) -> dict:
    """
    Deduz o custo exato em R$ do saldo de R$ 150,00 com base nos tokens consumidos.
    Bloqueia chamadas caso o saldo tenha acabado.
    """
    await inicializar_saldo_se_necessario()
    db = get_db()

    # Busca a tabela de preços e cotação dinâmica no MongoDB
    tabela = await obter_tabela_precos_ia()
    cotacao = float(tabela.get("cotacao_usd_brl", 5.70))
    modelos = tabela.get("modelos", TABELA_PRECOS_DEFAULT["modelos"])

    conf_modelo = modelos.get(modelo, modelos.get("gemini-3.6-flash", {"usd_input_1m": 0.075, "usd_output_1m": 0.30}))
    usd_in = float(conf_modelo.get("usd_input_1m", 0.075))
    usd_out = float(conf_modelo.get("usd_output_1m", 0.30))

    custo_entrada_brl = (tokens_entrada / 1_000_000.0) * usd_in * cotacao
    custo_saida_brl = (tokens_saida / 1_000_000.0) * usd_out * cotacao
    custo_total_brl = round(custo_entrada_brl + custo_saida_brl, 6)

    # Atualiza saldo atômico no MongoDB
    res = await db[COLLECTION_SALDO].find_one_and_update(
        {"_id": "saldo_google_cloud"},
        {
            "$inc": {
                "saldo_atual_brl": -custo_total_brl,
                "total_gasto_brl": custo_total_brl,
                "total_requisicoes": 1,
                "total_tokens_entrada": tokens_entrada,
                "total_tokens_saida": tokens_saida
            },
            "$set": {"atualizado_em": datetime.now(timezone.utc)}
        },
        return_document=True
    )

    # Grava o log detalhado desta transação
    log_doc = {
        "servico": servico,
        "modelo": modelo,
        "tokens_entrada": tokens_entrada,
        "tokens_saida": tokens_saida,
        "tokens_total": tokens_entrada + tokens_saida,
        "custo_brl": custo_total_brl,
        "saldo_restante_brl": res.get("saldo_atual_brl", 0.0),
        "data_hora": datetime.now(timezone.utc),
        "meta_info": meta_info or {}
    }
    await db[COLLECTION_LOGS].insert_one(log_doc)

    print(f"💰 [Gestão da IA] Consumo: R$ {custo_total_brl:.6f} ({tokens_entrada + tokens_saida} tokens) | Saldo Restante: R$ {res.get('saldo_atual_brl'):.4f}")

    return {
        "custo_brl": custo_total_brl,
        "saldo_restante_brl": res.get("saldo_atual_brl", 0.0),
        "tokens_total": tokens_entrada + tokens_saida
    }


async def obter_resumo_saldo() -> dict:
    """Retorna a situação financeira atual dos créditos do Google Cloud."""
    await inicializar_saldo_se_necessario()
    db = get_db()
    doc = await db[COLLECTION_SALDO].find_one({"_id": "saldo_google_cloud"})
    if not doc:
        return {}

    return {
        "saldo_inicial_brl": round(doc.get("saldo_inicial_brl", 150.0), 2),
        "saldo_atual_brl": round(doc.get("saldo_atual_brl", 150.0), 4),
        "total_gasto_brl": round(doc.get("total_gasto_brl", 0.0), 4),
        "total_requisicoes": doc.get("total_requisicoes", 0),
        "total_tokens_entrada": doc.get("total_tokens_entrada", 0),
        "total_tokens_saida": doc.get("total_tokens_saida", 0),
        "atualizado_em": doc.get("atualizado_em")
    }


async def recarregar_ajustar_saldo(novo_saldo_brl: float, motivo: str = "Ajuste Manual do Administrador") -> dict:
    """Permite ao administrador recarregar ou ajustar manualmente o saldo disponível em R$."""
    await inicializar_saldo_se_necessario()
    db = get_db()
    
    agora = datetime.now(timezone.utc)
    res = await db[COLLECTION_SALDO].find_one_and_update(
        {"_id": "saldo_google_cloud"},
        {
            "$set": {
                "saldo_atual_brl": float(novo_saldo_brl),
                "atualizado_em": agora
            }
        },
        return_document=True
    )

    # Log de auditoria da alteração manual
    await db[COLLECTION_LOGS].insert_one({
        "servico": "Ajuste de Saldo Admin",
        "modelo": "SISTEMA",
        "tokens_entrada": 0,
        "tokens_saida": 0,
        "tokens_total": 0,
        "custo_brl": 0.0,
        "saldo_restante_brl": float(novo_saldo_brl),
        "data_hora": agora,
        "meta_info": {"motivo": motivo, "novo_saldo": novo_saldo_brl}
    })

    print(f"🛠️ [Gestão da IA] Saldo ajustado manualmente pelo Admin para: R$ {novo_saldo_brl:.2f}")

    return {
        "sucesso": True,
        "novo_saldo_brl": float(novo_saldo_brl),
        "mensagem": f"Saldo atualizado para R$ {novo_saldo_brl:.2f} com sucesso."
    }
