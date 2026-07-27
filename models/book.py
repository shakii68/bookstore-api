from sqlmodel import SQLModel, Field
from pydantic import field_validator
from datetime import datetime
from typing import Optional
import re



class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    title: str = Field(index=True, min_length=1)
    author: str = Field(index=True, min_length=1)
    category: str = Field(index=True)
    isbn: str = Field(unique=True, index=True)

    published_year: int = Field(ge=1000, le=datetime.now().year)

    price: float = Field(gt=0)
    stock: int = Field(default=0, ge=0)

    available: bool = Field(default=True)

    supplier_id: Optional[int] = Field(default=None, foreign_key="supplier.id")


    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BookCreate(SQLModel):
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    category: str
    isbn: str

    published_year: int = Field(ge=1000, le=datetime.now().year)

    price: float = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    available: bool = True

    supplier_id: Optional[int] = None



    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if not v[0].isupper():
            raise ValueError("Title must start with a capital letter")

        if re.search(r'[^a-zA-Z0-9\s]', v):
            raise ValueError("Title cannot contain special characters")

        return v


    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v < 1:
            raise ValueError("Price must be at least 1")

        return round(v, 2)


    @field_validator("stock")
    @classmethod
    def validate_stock(cls, v):
        if v < 0:
            raise ValueError("Stock cannot be negative")

        return v
    


class BookUpdate(SQLModel):
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    isbn: Optional[str] = None

    published_year: Optional[int] = Field(
        default=None,
        ge=1000,
        le=datetime.now().year
    )

    price: Optional[float] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    available: Optional[bool] = None

    supplier_id: Optional[int] = None



  