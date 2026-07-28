from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    doctor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    medical_history: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    