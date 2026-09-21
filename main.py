from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  
from app.routers import (
    auth,
    category,
    customer,
    payment,
    product,
    receipt,
    sale,
    sale_item,
    supplier,
    user,
)
from app.services.auth_service import bootstrap_admin
from database import Base, SessionLocal, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_admin(db)
    yield


app = FastAPI(title="POS API", version="2.0.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(category.router)
app.include_router(supplier.router)
app.include_router(customer.router)
app.include_router(product.router)
app.include_router(sale.router)
app.include_router(sale_item.router)
app.include_router(payment.router)
app.include_router(receipt.router)


@app.get("/")
def root():
    return {"message": "Welcome to POS API"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)