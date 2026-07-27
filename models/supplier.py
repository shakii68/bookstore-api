from sqlmodel import SQLModel, Field
from pydantic import EmailStr, field_validator
from typing import Optional
import re


class Supplier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(unique=True)
    contact_person: str
    email: EmailStr = Field(unique=True)
    phone: str
    is_active: bool = True


class SupplierCreate(SQLModel):
    name: str
    contact_person: str
    email: EmailStr
    phone: str
    is_active: bool = True

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not re.fullmatch(r"^(\+254|0)\d{9}$", v):
            raise ValueError("Invalid Kenyan phone number")
        return v