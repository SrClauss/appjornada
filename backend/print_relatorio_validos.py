#!/usr/bin/env python3
import json

json_path = '/home/claus/src/app_jornada/backend/analise_triplicada_resultados.json'
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

validos = {k: v for k, v in data.items() if any(r.get('sucesso') for r in v.get('rodadas', []))}

print("=" * 105)
print(f"RELATÓRIO DE PRECISÃO E REPETIBILIDADE - APENAS VÍDEOS VÁLIDOS ({len(validos)} ARQUIVOS)")
print("=" * 105)
print(f"{'Vídeo':<38} | {'Rodada 1':>16} | {'Rodada 2':>16} | {'Rodada 3':>16} | {'Status / Variação':>20}")
print("─" * 105)

tot_perfeito = 0
diferencas = []

for v_name, res in validos.items():
    rds = res['rodadas']
    str_rds = []
    fats = []
    for r in rds:
        if r.get('sucesso'):
            str_rds.append(f"{r['qtd_corridas']}c R${r['faturamento']:.2f}")
            fats.append(r['faturamento'])
        else:
            str_rds.append("FALHA")
    
    if len(fats) == 3:
        diff = max(fats) - min(fats)
        diferencas.append(diff)
        if diff < 0.01 and rds[0]['qtd_corridas'] == rds[1]['qtd_corridas'] == rds[2]['qtd_corridas']:
            tot_perfeito += 1
            status_str = "🟢 PERFEITO (100%)"
        elif diff < 1.0:
            status_str = f"🟢 Δ R$ {diff:.2f}"
        elif diff < 20.0:
            status_str = f"🟡 Δ R$ {diff:.2f}"
        else:
            status_str = f"🟠 Δ R$ {diff:.2f}"
    else:
        status_str = "INCOMPLETO"
        
    print(f"{v_name:<38} | {str_rds[0]:>16} | {str_rds[1]:>16} | {str_rds[2]:>16} | {status_str:>20}")

print("─" * 105)
media_diff = sum(diferencas) / len(diferencas) if diferencas else 0
max_diff = max(diferencas) if diferencas else 0
min_diff = min(diferencas) if diferencas else 0

print(f"🎯 Concordância 100% Idêntica (Zero Diferença): {tot_perfeito}/{len(validos)} ({(tot_perfeito/len(validos))*100:.1f}%)")
print(f"📊 Variação Média de Faturamento entre as 3 rodadas: R$ {media_diff:.2f}")
print(f"📉 Menor Variação: R$ {min_diff:.2f} | 📈 Maior Variação: R$ {max_diff:.2f}")
print("=" * 105)
