from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from .base import PyObjectId

class AuditLog(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    user_email: str
    acao: str
    detalhes: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)
