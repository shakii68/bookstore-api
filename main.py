from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordRequestForm

from sqlmodel import SQLModel, Session, select
from typing import List, Optional
from datetime import datetime

from database.session import engine, get_session
from models.book import Book, BookCreate, BookUpdate
from models.supplier import Supplier, SupplierCreate
from models.user import User, UserCreate, UserResponse
from models.blacklist import TokenBlacklist
from models.patients import Patient

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    oauth2_scheme,
    get_current_user,
    get_current_active_user,
    get_current_admin,
)

app = FastAPI(
    title="Bookstore Inventory API",
    version="1.0.0"
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "status_code": exc.status_code,
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "status_code": 422,
            "message": "Validation Error",
            "errors": exc.errors(),
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "status_code": 500,
            "message": "Internal Server Error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.post("/register", response_model=UserResponse, status_code=201)
def register_user(
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    existing_username = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=409,
            detail="Username already exists"
        )

    existing_email = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user

@app.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = session.exec(
        select(User).where(User.username == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})

    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/logout")
def logout_user(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    payload = decode_access_token(token)
    
    exp = payload.get("exp") if isinstance(payload, dict) else None
    expires_at = datetime.utcfromtimestamp(exp) if exp else datetime.utcnow()

    blacklisted_token = TokenBlacklist(token=token, expires_at=expires_at)
    session.add(blacklisted_token)
    session.commit()

    return {"message": f"Successfully logged out {current_user.username}"}

@app.get("/users/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 10,
    role: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    
    return session.exec(query.offset(skip).limit(limit)).all()

@app.post("/books", response_model=Book, status_code=201)
def create_book(book: BookCreate, session: Session = Depends(get_session)):
    existing = session.exec(
        select(Book).where(Book.isbn == book.isbn)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="ISBN already exists")

    if book.supplier_id is not None:
        supplier = session.get(Supplier, book.supplier_id)

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found"
            )

    db_book = Book(**book.model_dump())

    session.add(db_book)
    session.commit()
    session.refresh(db_book)

    return db_book

@app.get("/books", response_model=List[Book])
def list_books(
    skip: int = 0,
    limit: int = 10,
    author: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    available: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    query = select(Book)

    if author:
        query = query.where(Book.author.contains(author))

    if min_price is not None:
        query = query.where(Book.price >= min_price)

    if max_price is not None:
        query = query.where(Book.price <= max_price)

    if available is not None:
        query = query.where(Book.available == available)

    return session.exec(query.offset(skip).limit(limit)).all()

@app.get("/books/search", response_model=List[Book])
def search_books(q: str, session: Session = Depends(get_session)):
    query = select(Book).where(
        (Book.title.contains(q)) |
        (Book.author.contains(q))
    )

    return session.exec(query).all()

@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return book

@app.patch("/books/update-prices")
def bulk_price_update(
    category: str,
    percentage: float,
    session: Session = Depends(get_session)
):
    books = session.exec(
        select(Book).where(Book.category == category)
    ).all()

    if not books:
        raise HTTPException(
            status_code=404,
            detail="No books found in this category"
        )

    for book in books:
        book.price += book.price * (percentage / 100)
        session.add(book)

    session.commit()

    return {
        "message": f"{len(books)} book(s) updated successfully"
    }

@app.patch("/books/{book_id}", response_model=Book)
def update_book(
    book_id: int,
    book_update: BookUpdate,
    session: Session = Depends(get_session)
):
    book = session.get(Book, book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    for key, value in book_update.model_dump(exclude_unset=True).items():
        setattr(book, key, value)

    book.updated_at = datetime.utcnow()

    session.add(book)
    session.commit()
    session.refresh(book)

    return book

@app.delete("/books/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    session: Session = Depends(get_session)
):
    book = session.get(Book, book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    session.delete(book)
    session.commit()

    return None

@app.post("/suppliers", response_model=Supplier)
def create_supplier(
    supplier: SupplierCreate,
    session: Session = Depends(get_session)
):
    existing = session.exec(
        select(Supplier).where(Supplier.email == supplier.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Supplier email already exists"
        )

    db_supplier = Supplier(**supplier.model_dump())

    session.add(db_supplier)
    session.commit()
    session.refresh(db_supplier)

    return db_supplier

@app.get("/suppliers", response_model=List[Supplier])
def list_suppliers(session: Session = Depends(get_session)):
    return session.exec(select(Supplier)).all()

@app.patch("/books/{book_id}/stock")
def update_stock(
    book_id: int,
    quantity: int,
    session: Session = Depends(get_session)
):
    book = session.get(Book, book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.stock += quantity

    if book.stock < 0:
        raise HTTPException(status_code=400, detail="Stock cannot be negative")

    session.add(book)
    session.commit()
    session.refresh(book)

    return book

from uuid import uuid4

# Temporary in-memory storage for reset tokens
password_reset_tokens = {}


@app.post("/forgot-password")
def forgot_password(email: str, session: Session = Depends(get_session)):
  

    user = session.exec(
        select(User).where(User.email == email)
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    reset_token = str(uuid4())

    password_reset_tokens[reset_token] = user.id

    return {
        "message": "Password reset token generated.",
        "reset_token": reset_token
    }


@app.post("/reset-password")
def reset_password(
    token: str,
    new_password: str,
    session: Session = Depends(get_session)
):
   

    if token not in password_reset_tokens:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )

    user_id = password_reset_tokens[token]

    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.hashed_password = hash_password(new_password)

    session.add(user)
    session.commit()

    del password_reset_tokens[token]

    return {
        "message": "Password reset successful."
    }