from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from sqlmodel import SQLModel, Session, select
from typing import List, Optional
from datetime import datetime

from database.session import engine, get_session
from models.book import Book, BookCreate, BookUpdate
from models.supplier import Supplier, SupplierCreate



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




