import asyncio
from app.db.database import get_db

async def fix():
    db = get_db()
    j_id = 'Clausemberg Rodrigues de Olvierira-TEST-1234-07082026150119'
    jornada = await db['jornadas'].find_one({'_id': j_id})
    if jornada:
        pausas = jornada.get('pausas', [])
        
        # Encontra a ultima pausa e conserta a localizacao
        if pausas:
            ultima_pausa = pausas[-1]
            localizacao_correta = {
                "lat": -18.7214,
                "lon": -39.8551
            }
            ultima_pausa["localizacao_inicio"] = localizacao_correta
            ultima_pausa["localizacao_fim"] = localizacao_correta
        
        update_doc = {'$set': {
            'pausas': pausas,
            'localizacao_atual': localizacao_correta
        }}
        await db['jornadas'].update_one({'_id': j_id}, update_doc)
        print('Fixed Localizacao schema!')

asyncio.run(fix())
