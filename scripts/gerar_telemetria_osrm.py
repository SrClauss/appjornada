import asyncio
from datetime import datetime, timezone, timedelta
import json
import httpx
import math
import random
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

try:
    from app.core.config import settings
except ImportError:
    pass

# Ler rides do json ou vamos re-gerar?
# As corridas ja estao no index.html, eu nao posso re-gerar as corridas se nao as do index.html vao ficar dessincronizadas!
# As corridas devem ser exatamente as mesmas do HTML.
# Mas as corridas estao perdidas em Python porque eu gerei on the fly!
