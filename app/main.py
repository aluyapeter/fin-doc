from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
import stripe
from stripe import Webhook
from decimal import Decimal
from typing import Dict, List, Optional
import os
from contextlib import asynccontextmanager
from .db import database, transactions, engine, metadata, products, payments, users
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
    )

try:
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
except KeyError:
    print("!!! STRIPE_SECRET_KEY environment variable not set. !!!")

try:
    STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]
except KeyError:
    print("!!! STRIPE_WEBHOOK_SECRET environment variable not set. !!!")
    STRIPE_WEBHOOK_SECRET = ""

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOutput(BaseModel):
    id: int
    email: EmailStr

class TransactionInput(BaseModel):
    user_id: str
    amount: Decimal
    description: str

class TransactionOutput(TransactionInput):
    id: int

class ProductInput(BaseModel):
    name: str
    price_in_pence: int

class ProductOutput(ProductInput):
    id: int

class PaymentIntentRequest(BaseModel):
    product_id: int
    # user_id: str

class PaymentIntentResponse(BaseModel):
    client_secret: Optional[str] 
    payment_intent_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Connecting to database...")
    await database.connect()
    print("Database connection established.")
    
    yield

    print("Disconnecting from database...")
    await database.disconnect()
    print("Database connection closed.")

app = FastAPI(title="Fintech Service", lifespan=lifespan)


@app.get("/")
def read_root() -> Dict[str, str]:
    return {"message": "Welcome to the Wallet Service"}

#----- user authentication----------------
@app.post("/register", response_model=UserOutput, tags=["Authentication"])
async def register_user(user_in: UserCreate):
    hashed_pass = hash_password(user_in.password)

    query = users.insert().values(
        email=user_in.email,
        hashed_password=hashed_pass
    )

    try:
        last_record_id = await database.execute(query)
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(
            status_code=400, 
            detail="Email already registered."
        )
    return UserOutput(id=last_record_id, email=user_in.email)

@app.post("/login", response_model=Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    query = users.select().where(users.c.email == form_data.username)
    db_user = await database.fetch_one(query)

    if not db_user or not verify_password(form_data.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {"sub": str(db_user["id"])} 

    access_token = create_access_token(data_to_encode=token_data)

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserOutput, tags=["Users"])
async def get_my_profile(current_user: UserOutput = Depends(get_current_user)):
    return current_user


@app.post("/products", response_model=ProductOutput, tags=["Products"])
async def create_product(product_in: ProductInput) -> ProductOutput:
    query = products.insert().values(
        name=product_in.name,
        price_in_pence=product_in.price_in_pence
    )
    last_record_id = await database.execute(query)
    
    return ProductOutput(id=last_record_id, **product_in.model_dump())


@app.post("/payments/initiate", response_model=PaymentIntentResponse, tags=["Payments"])
async def initiate_payment(intent_request: PaymentIntentRequest, current_user: UserOutput = Depends(get_current_user)) -> PaymentIntentResponse:
    query = products.select().where(products.c.id == intent_request.product_id)
    product = await database.fetch_one(query)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    amount = product["price_in_pence"] 

    user_id_from_token = current_user.id
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="gbp",
            metadata={
                "user_id": str(user_id_from_token),
                "product_id": str(intent_request.product_id)
            }
        )

    except stripe.CardError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.StripeError as e: # Catch other Stripe errors
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    
    insert_query = payments.insert().values(
        product_id=intent_request.product_id,
        user_id=str(user_id_from_token),
        stripe_payment_intent_id=payment_intent['id'],
        status="pending",
        amount_in_pence=amount
    )
    await database.execute(insert_query)

    return PaymentIntentResponse(
        client_secret=payment_intent['client_secret'],
        payment_intent_id=payment_intent['id']
    )

@app.post("/transactions", response_model=TransactionOutput)
async def create_transaction(txn_in: TransactionInput) -> TransactionOutput:
    query = transactions.insert().values(
        user_id=txn_in.user_id,
        amount=txn_in.amount,
        description=txn_in.description
    )
    last_record_id = await database.execute(query)

    return TransactionOutput(id=last_record_id, **txn_in.model_dump())

@app.get("/transactions/{user_id}", response_model=List[TransactionOutput])
async def get_transactions_for_user(user_id: str) -> List[TransactionOutput]:
    query = transactions.select().where(transactions.c.user_id == user_id)

    results = await database.fetch_all(query)
    
    return [TransactionOutput(**row._mapping) for row in results]

##---- webhook config----

@app.post("/webhooks/stripe", tags=["Webhooks"])
async def stripe_webhook(request: Request):
    """
    Handles incoming webhooks from Stripe.
    1. Verifies the signature.
    2. Updates the payment status in our database.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    if not STRIPE_WEBHOOK_SECRET:
         raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    except stripe.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]

        stripe_pi_id = payment_intent["id"]

        update_query = (
            payments.update()
            .where(payments.c.stripe_payment_intent_id == stripe_pi_id)
            .values(status="succeeded")
        )

        rows_updated = await database.execute(update_query)

        if rows_updated == 0:
            print(f"!!! WARNING: Received successful webhook for unknown payment intent: {stripe_pi_id} !!!")
        else:
            print(f"Payment {stripe_pi_id} updated to 'succeeded'")

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        stripe_pi_id = payment_intent["id"]

        update_query = (
            payments.update()
            .where(payments.c.stripe_payment_intent_id == stripe_pi_id)
            .values(status="failed")
        )
        await database.execute(update_query)
        print(f"Payment {stripe_pi_id} updated to 'failed'")

    else:
        print(f"Unhandled event type {event['type']}")

    return {"status": "success"}