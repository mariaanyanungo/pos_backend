from fastapi import FastAPI
from database import Base, engine, get_db
from app.routers  import product, customer,category,supplier,user,sale, sale_item,receipt, payment


app=FastAPI(title="POS API", version="1.0.0")

Base.metadata.create_all(bind=engine)

app.include_router(product.router)
app.include_router(customer.router)
app.include_router(category.router)
app.include_router(supplier.router)
app.include_router(user.router)
app.include_router(sale.router)
app.include_router(sale_item.router)
app.include_router(receipt.router)
app.include_router(payment.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    
@app.get("/")  
def root():
    return{"message":"Welcome to POS API"}