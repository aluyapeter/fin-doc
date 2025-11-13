import os
from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DECIMAL

DATABASE_URL = os.environ.get("DATABASE_URL", "DATABASE_URL=postgresql://postgres:mysecretpassword@db:5432/db")

database = Database(DATABASE_URL)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(255), unique=True, index=True, nullable=False),
    Column("hashed_password", String(255), nullable=False),
)

transactions = Table(
    "transactions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", String(50)),
    Column("amount", DECIMAL(19, 2)),
    Column("description", String(255)),
)

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100)),
    Column("price_in_pence", Integer),
)

payments = Table(
    "payments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, index=True),
    Column("user_id", String(100), index=True),
    Column("stripe_payment_intent_id", String(255), unique=True),
    Column("status", String(50), index=True, default="pending"),
    Column("amount_in_pence", Integer),
)

engine = create_engine(DATABASE_URL)