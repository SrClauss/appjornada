"""
Relatórios: importação CSV Uber/99 e comparativo KM + faturamento vs jornada.

Lógica de comparativo:
- KM: jornada (KM_FINAL - KM_INICIAL) vs km declarado nas corridas da 99
  (Uber não fornece km — fica como "não disponível")
  → Delta positivo = km da jornada não explicados pelas plataformas (uso pessoal?)
- Faturamento: o que o motorista declarou na jornada vs o que os relatórios mostram
  → Delta positivo = motorista declarou MENOS do que as plataformas registraram
- Corridas fora da jornada: corridas cujo horário não se enquadra na jornada aberta
"""

import csv
import io
from collections import defaultdict
from datetime import date, datetime, time, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from bson import ObjectId

from app.db.database import get_db
from app.models.user import Role
from app.models.relatorio import (
    ComparativoMotorista,
    ComparativoResponse,
    CorridaForaJornada,
    NoveNoveCorrida,
    UberCorrida,
)
from app.core.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/relatorios", tags=["relatórios"])

# Tolerância de delta para emitir alerta (%)
LIMIAR_ALERTA_FATURAMENTO_PCT = 5.0
LIMIAR_ALERTA_KM_PCT = 20.0


# ─── Helpers de parse ────────────────────────────────────────────────────────

def _float(v: str) -> float:
    try:
        return float(v.replace(",", ".").strip()) if v.strip() else 0.0
    except ValueError:
        return 0.0


def _dt(v: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(v.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_uber_csv(conteudo: str) -> List[UberCorrida]:
    """
    Uber exporta múltiplas linhas por corrida (uma por tipo de transação).
    Agrupa por id_viagem + nome_motorista + inicio e consolida os valores.
    """
    reader = csv.DictReader(io.StringIO(conteudo))
    trips: dict = {}

    for row in reader:
        trip_id = row.get("ID da viagem", "").strip()
        nome = row.get("Nome próprio", "").strip()
        inicio_str = row.get("Data/Hora de início", "").strip()
        chave = f"{trip_id}|{nome}|{inicio_str}"

        tipo = row.get("Tipo de transação", "").strip()
        valor = _float(row.get("Montante da transação", "0"))
        total_cobrado = _float(row.get("Total de débitos", "0"))

        if chave not in trips:
            fim_str = row.get("Data/Hora de término", "").strip()
            inicio_dt = _dt(inicio_str)
            fim_dt = _dt(fim_str)
            duracao = 0
            if inicio_dt and fim_dt:
                duracao = max(0, int((fim_dt - inicio_dt).total_seconds() / 60))

            trips[chave] = {
                "id_viagem": trip_id,
                "nome_motorista": nome,
                "email_motorista": row.get("E-mail", "").strip(),
                "id_colaborador": row.get("ID do colaborador", "").strip(),
                "origem": row.get("Endereço de recolha", "").strip(),
                "destino": row.get("Endereço de entrega", "").strip(),
                "inicio": inicio_dt,
                "fim": fim_dt,
                "duracao_minutos": duracao,
                "programa": row.get("Programa / Grupo", "").strip(),
                "tarifa_base": 0.0,
                "gorjeta": 0.0,
                "pedagio": 0.0,
                "ajuste_tarifa": 0.0,
                "total_cobrado": 0.0,
                "metodo_pagamento": row.get("Método de pagamento", "").strip(),
                "url_fatura": row.get("URL da fatura", "").strip() or None,
            }

        t = trips[chave]
        if tipo == "Tarifa base":
            t["tarifa_base"] += valor
        elif tipo == "Gorjeta":
            t["gorjeta"] += valor
        elif tipo == "Pedágio":
            t["pedagio"] += valor
        elif tipo in ("Ajuste de Tarifa", "Ajuste"):
            t["ajuste_tarifa"] += valor

        # total_cobrado = maior valor acumulado da viagem
        if total_cobrado > t["total_cobrado"]:
            t["total_cobrado"] = total_cobrado

    corridas = []
    for t in trips.values():
        if t["inicio"] is None:
            continue
        t["total_bruto"] = t["tarifa_base"] + t["gorjeta"] + t["ajuste_tarifa"]
        corridas.append(UberCorrida(**t))
    return corridas


def _parse_99_csv(conteudo: str) -> List[NoveNoveCorrida]:
    reader = csv.DictReader(io.StringIO(conteudo))
    corridas = []
    for row in reader:
        status = row.get("Status da Corrida", "").strip()
        if status.lower() not in ("concluída", "concluida", "completed"):
            continue
        sol = _dt(row.get("Data e Hora de Solicitação", "").strip())
        if sol is None:
            continue
        corridas.append(NoveNoveCorrida(
            id_corrida=row.get("ID da Corrida", "").strip(),
            nome_motorista=row.get("Nome do Motorista", "").strip(),
            centro_custo=row.get("Centro de Custo", "").strip(),
            solicitacao=sol,
            origem=row.get("Origem", "").strip(),
            destino=row.get("Destino", "").strip(),
            distancia_km=_float(row.get("Distância Percorrida (km)", "0")),
            duracao_minutos=int(_float(row.get("Duração da Corrida (min)", "0"))),
            tarifa_bruta=_float(row.get("Tarifa Bruta (R$)", "0")),
            forma_pagamento=row.get("Forma de Pagamento", "").strip(),
            taxa_intermediacao=_float(row.get("Taxa de Intermediação (R$)", "0")),
            descontos=_float(row.get("Descontos / Campanhas (R$)", "0")),
            valor_liquido=_float(row.get("Valor Líquido / Repasse (R$)", "0")),
            status=status,
        ))
    return corridas


def _time_from_str(s: Optional[str]) -> Optional[time]:
    if not s:
        return None
    try:
        parts = s.split(":")
        return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except Exception:
        return None


def _corrida_dentro_jornada(
    corrida_inicio: datetime,
    corrida_fim: Optional[datetime],
    jornada: dict,
) -> bool:
    """Verifica se uma corrida se enquadra no horário da jornada."""
    horario = jornada.get("horario") or {}
    j_inicio = _time_from_str(horario.get("inicio"))
    j_fim = _time_from_str(horario.get("fim"))
    if not j_inicio:
        return False
    c_time = corrida_inicio.time()
    if j_fim:
        return j_inicio <= c_time <= j_fim
    return c_time >= j_inicio


# ─── Endpoints de importação ─────────────────────────────────────────────────

@router.post("/importar/uber", status_code=201)
async def importar_uber(
    arquivo: UploadFile = File(...),
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    conteudo = (await arquivo.read()).decode("utf-8-sig")
    corridas = _parse_uber_csv(conteudo)
    if not corridas:
        raise HTTPException(status_code=422, detail="Nenhuma corrida válida encontrada no CSV")

    docs = []
    for c in corridas:
        doc = c.model_dump()
        # Upsert por id_viagem + nome_motorista + inicio para evitar duplicatas
        await db["corridas_uber"].update_one(
            {
                "id_viagem": c.id_viagem,
                "nome_motorista": c.nome_motorista,
                "inicio": c.inicio,
            },
            {"$set": doc},
            upsert=True,
        )
        docs.append(c)

    return {"importadas": len(docs), "corridas": [d.model_dump() for d in docs]}


@router.post("/importar/99", status_code=201)
async def importar_99(
    arquivo: UploadFile = File(...),
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    conteudo = (await arquivo.read()).decode("utf-8-sig")
    corridas = _parse_99_csv(conteudo)
    if not corridas:
        raise HTTPException(status_code=422, detail="Nenhuma corrida válida encontrada no CSV")

    for c in corridas:
        doc = c.model_dump()
        await db["corridas_99"].update_one(
            {"id_corrida": c.id_corrida},
            {"$set": doc},
            upsert=True,
        )

    return {"importadas": len(corridas)}


# ─── Comparativo ─────────────────────────────────────────────────────────────

@router.get("/comparativo", response_model=ComparativoResponse)
async def comparativo(
    data: date = Query(..., description="Data a analisar (YYYY-MM-DD)"),
    motorista_nome: Optional[str] = Query(None, description="Filtrar por nome do motorista"),
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    """
    Compara o que o carro andou (jornada) com o que está nos relatórios Uber e 99.

    Para cada motorista retorna:
    - KM rodados na jornada vs km declarado nas corridas da 99
    - Faturamento declarado na jornada vs faturamento nos relatórios
    - Corridas fora do horário de jornada
    - Alertas automáticos de inconsistência
    """
    data_str = data.isoformat()

    # ── 1. Jornadas do dia ──
    filtro_jornada: dict = {"data": data_str}
    if motorista_nome:
        filtro_jornada["_id"] = {"$regex": motorista_nome, "$options": "i"}

    jornadas = await db["jornadas"].find(filtro_jornada).to_list(100)
    jornadas_por_motorista = {j["_id"].split("-")[0] + "-" + j["_id"].split("-")[1]: j
                               for j in jornadas}
    # Agrupa por nome do motorista (parte antes do 2o "-")
    jornadas_por_nome: dict = {}
    for j in jornadas:
        nome = j.get("_id", "").rsplit("-", 3)[0]  # nome pode ter hífens
        # extrai nome a partir do motorista_id
        jornadas_por_nome[nome] = j

    # Melhor: buscar via motorista_id e cruzar com user.nome
    jornadas_com_nome: list = []
    for j in jornadas:
        mid = j.get("motorista_id")
        user = await db["users"].find_one({"_id": mid})
        nome = user["nome"] if user else str(mid)
        jornadas_com_nome.append((nome, j))

    # ── 2. Corridas Uber do dia ──
    uber_docs = await db["corridas_uber"].find({
        "inicio": {
            "$gte": datetime.combine(data, time.min),
            "$lte": datetime.combine(data, time.max),
        }
    }).to_list(1000)
    uber_por_motorista: dict = defaultdict(list)
    for u in uber_docs:
        uber_por_motorista[u["nome_motorista"]].append(u)

    # ── 3. Corridas 99 do dia ──
    docs_99 = await db["corridas_99"].find({
        "solicitacao": {
            "$gte": datetime.combine(data, time.min),
            "$lte": datetime.combine(data, time.max),
        }
    }).to_list(1000)
    novenovepor_motorista: dict = defaultdict(list)
    for n in docs_99:
        novenovepor_motorista[n["nome_motorista"]].append(n)

    # ── 4. Todos os motoristas presentes em alguma fonte ──
    todos_nomes = set()
    for nome, _ in jornadas_com_nome:
        todos_nomes.add(nome)
    todos_nomes.update(uber_por_motorista.keys())
    todos_nomes.update(novenovepor_motorista.keys())

    if motorista_nome:
        todos_nomes = {n for n in todos_nomes if motorista_nome.lower() in n.lower()}

    # ── 5. Monta comparativo por motorista ──
    resultado: List[ComparativoMotorista] = []

    for nome in sorted(todos_nomes):
        jornada = next((j for n, j in jornadas_com_nome if n == nome), None)
        corridas_uber = uber_por_motorista.get(nome, [])
        corridas_99 = novenovepor_motorista.get(nome, [])

        comp = ComparativoMotorista(motorista_nome=nome, data=data)

        # KM
        if jornada:
            km_j = (jornada.get("km") or {})
            comp.jornada_km_rodados = km_j.get("rodados")

        comp.km_plataformas_99 = round(sum(c.get("distancia_km", 0) for c in corridas_99), 2)

        if comp.jornada_km_rodados is not None:
            comp.delta_km_99 = round(comp.jornada_km_rodados - comp.km_plataformas_99, 2)

        # Faturamento
        if jornada:
            fat = jornada.get("faturamento") or {}
            comp.faturamento_uber_declarado = fat.get("uber") or 0.0
            comp.faturamento_99_declarado = fat.get("noventa_nove") or 0.0

        # Uber: soma tarifa_base + gorjeta + ajuste (exclui pedágio que é pass-through)
        comp.faturamento_uber_relatorio = round(
            sum(
                (c.get("tarifa_base") or 0)
                + (c.get("gorjeta") or 0)
                + (c.get("ajuste_tarifa") or 0)
                for c in corridas_uber
            ),
            2,
        )
        # 99: soma valor_liquido
        comp.faturamento_99_relatorio = round(
            sum(c.get("valor_liquido", 0) for c in corridas_99), 2
        )

        comp.delta_uber = round(comp.faturamento_uber_relatorio - comp.faturamento_uber_declarado, 2)
        comp.delta_99 = round(comp.faturamento_99_relatorio - comp.faturamento_99_declarado, 2)
        comp.total_corridas_uber = len(corridas_uber)
        comp.total_corridas_99 = len(corridas_99)

        # Jornada CLT
        if jornada:
            comp.status_jornada = jornada.get("status")
            segundos = (jornada.get("horario") or {}).get("total_horas_segundos")
            if segundos:
                comp.horas_trabalhadas = round(segundos / 3600, 2)

        # Corridas fora da jornada
        fora: List[CorridaForaJornada] = []

        for c in corridas_uber:
            inicio_c = c.get("inicio")
            if not inicio_c:
                continue
            if isinstance(inicio_c, str):
                inicio_c = _dt(inicio_c)
            if not jornada:
                fora.append(CorridaForaJornada(
                    plataforma="UBER",
                    id_corrida=c.get("id_viagem", ""),
                    inicio=inicio_c,
                    fim=c.get("fim"),
                    origem=c.get("origem", ""),
                    destino=c.get("destino", ""),
                    valor=c.get("total_bruto") or c.get("tarifa_base", 0),
                    motivo="SEM_JORNADA",
                ))
            elif not _corrida_dentro_jornada(inicio_c, c.get("fim"), jornada):
                fora.append(CorridaForaJornada(
                    plataforma="UBER",
                    id_corrida=c.get("id_viagem", ""),
                    inicio=inicio_c,
                    fim=c.get("fim"),
                    origem=c.get("origem", ""),
                    destino=c.get("destino", ""),
                    valor=c.get("total_bruto") or c.get("tarifa_base", 0),
                    motivo="FORA_DO_HORARIO",
                ))

        for c in corridas_99:
            sol = c.get("solicitacao")
            if not sol:
                continue
            if isinstance(sol, str):
                sol = _dt(sol)
            if not jornada:
                fora.append(CorridaForaJornada(
                    plataforma="99",
                    id_corrida=c.get("id_corrida", ""),
                    inicio=sol,
                    origem=c.get("origem", ""),
                    destino=c.get("destino", ""),
                    valor=c.get("valor_liquido", 0),
                    motivo="SEM_JORNADA",
                ))
            elif not _corrida_dentro_jornada(sol, None, jornada):
                fora.append(CorridaForaJornada(
                    plataforma="99",
                    id_corrida=c.get("id_corrida", ""),
                    inicio=sol,
                    origem=c.get("origem", ""),
                    destino=c.get("destino", ""),
                    valor=c.get("valor_liquido", 0),
                    motivo="FORA_DO_HORARIO",
                ))

        comp.corridas_fora_jornada = fora

        # ── Alertas automáticos ──
        alertas = []

        if comp.delta_km_99 is not None and comp.km_plataformas_99 > 0:
            pct_km = abs(comp.delta_km_99) / comp.km_plataformas_99 * 100
            if pct_km > LIMIAR_ALERTA_KM_PCT:
                alertas.append(
                    f"KM: jornada={comp.jornada_km_rodados}km vs 99={comp.km_plataformas_99}km "
                    f"(delta {comp.delta_km_99}km / {pct_km:.1f}%)"
                )

        if comp.faturamento_uber_relatorio > 0:
            pct_uber = abs(comp.delta_uber) / comp.faturamento_uber_relatorio * 100
            if pct_uber > LIMIAR_ALERTA_FATURAMENTO_PCT:
                alertas.append(
                    f"Faturamento Uber: declarado=R${comp.faturamento_uber_declarado:.2f} "
                    f"vs relatório=R${comp.faturamento_uber_relatorio:.2f} "
                    f"(delta R${comp.delta_uber:.2f})"
                )

        if comp.faturamento_99_relatorio > 0:
            pct_99 = abs(comp.delta_99) / comp.faturamento_99_relatorio * 100
            if pct_99 > LIMIAR_ALERTA_FATURAMENTO_PCT:
                alertas.append(
                    f"Faturamento 99: declarado=R${comp.faturamento_99_declarado:.2f} "
                    f"vs relatório=R${comp.faturamento_99_relatorio:.2f} "
                    f"(delta R${comp.delta_99:.2f})"
                )

        if fora:
            alertas.append(
                f"{len(fora)} corrida(s) fora do horário de jornada registrada"
            )

        if not jornada and (corridas_uber or corridas_99):
            alertas.append("Corridas registradas sem jornada aberta no sistema")

        comp.alertas = alertas
        resultado.append(comp)

    return ComparativoResponse(
        data=data,
        total_motoristas=len(resultado),
        motoristas=resultado,
    )
