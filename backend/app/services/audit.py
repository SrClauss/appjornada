from typing import Dict, Any, List


def calcular_score_auditoria(jornada_doc: Dict[str, Any], limite_km_morta_pct: float = 20.0) -> Dict[str, Any]:
    score_risco = 0
    motivos: List[str] = []

    km_data = jornada_doc.get("km", {}) or {}
    if not isinstance(km_data, dict):
        km_data = {}

    km_inicial = km_data.get("inicial") or jornada_doc.get("km_inicial") or 0.0
    km_final = km_data.get("final") or jornada_doc.get("km_final") or 0.0
    km_rodados = km_data.get("rodados") or (km_final - km_inicial if km_final > km_inicial else 0.0)
    km_morta = km_data.get("morta") or 0.0

    # 1. Checa contestação manual de hodômetro
    if km_data.get("inicial_contestado") or km_data.get("final_contestado"):
        score_risco += 40
        motivos.append("Leitura do hodômetro foi ajustada manualmente pelo motorista")

    # 2. Checa razão de KM morta
    razao_km_morta_pct = 0.0
    if km_rodados > 0:
        razao_km_morta_pct = round((km_morta / km_rodados) * 100.0, 1)
        if razao_km_morta_pct > limite_km_morta_pct:
            score_risco += 30
            motivos.append(f"Razão KM Morta ({razao_km_morta_pct}%) excedeu o limite do gestor ({limite_km_morta_pct}%)")

    # 3. Checa faturamento declarado vs comprovantes processados
    fat_data = jornada_doc.get("faturamento", {}) or {}
    if not isinstance(fat_data, dict):
        fat_data = {}

    comp_list = fat_data.get("comprovantes_processados", []) or []
    if comp_list:
        total_declarado = (fat_data.get("uber") or 0.0) + (fat_data.get("noventa_nove") or 0.0)
        total_comprovantes = sum(c.get("valor", 0.0) for c in comp_list if isinstance(c, dict))
        if total_declarado > 0 and abs(total_declarado - total_comprovantes) > 5.0:
            score_risco += 30
            motivos.append(f"Divergência entre faturamento informado (R$ {total_declarado:.2f}) e comprovantes lidos (R$ {total_comprovantes:.2f})")

    # Define nível de risco
    if score_risco <= 20:
        nivel_risco = "VERDE"
    elif score_risco <= 50:
        nivel_risco = "AMARELO"
    else:
        nivel_risco = "VERMELHO"

    return {
        "score_risco": min(score_risco, 100),
        "nivel_risco": nivel_risco,
        "motivos_risco": motivos,
        "razao_km_morta_pct": razao_km_morta_pct,
        "limite_km_morta_pct": limite_km_morta_pct,
    }
