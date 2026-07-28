from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class TokenBlacklist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    invalidated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    