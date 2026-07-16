from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Session, select
from typing import List, Optional
from datetime import datetime

from database.session import engine, get_session
from models.book import Book, BookCreate, BookUpdate

app = FastAPI(
    title="Bookstore Inventory API",
    version="1.0.0"
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




