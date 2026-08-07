import asyncio
from app.db.database import get_db

async def fix():
    db = get_db()
    j_id = 'Clausemberg Rodrigues de Olvierira-TEST-1234-07082026150119'
    jornada = await db['jornadas'].find_one({'_id': j_id})
    if jornada:
        km = jornada.get('km', {})
        inicial = km.get('inicial', 1000.0) or 1000.0
        atual = km.get('atual', 1000.0) or 1000.0
        rodados = round(atual - inicial, 1)
        
        # Corrige null fields no dict KM
        if km.get('rodados') is None:
            km['rodados'] = rodados
        
        # Certifica-se que km['final'] não quebra
        if km.get('final') is None:
            km['final'] = atual
        
        update_doc = {'$set': {'km': km}}
        await db['jornadas'].update_one({'_id': j_id}, update_doc)
        print(f'Fixed KM schema: rodados={km["rodados"]}, final={km["final"]}')

asyncio.run(fix())
