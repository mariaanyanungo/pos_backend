from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException

import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL","postgresql://postgres:postgres@localhost:5432/pos_db")

print(f"\n CRITICAL: FastAPI is connecting to database string: {DATABASE_URL}\n")


if not DATABASE_URL:
    raise ValueError("CRITICAL CONFIG ERROR: 'DATABASE_URL' is missing from your .env file!")


engine=create_engine(DATABASE_URL, echo=False, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
        
        
        
        







