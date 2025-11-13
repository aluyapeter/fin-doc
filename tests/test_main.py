import pytest
from httpx import AsyncClient
import stripe

@pytest.mark.asyncio
async def test_home(test_client):
    """Test the root endpoint"""
    response = await test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Wallet Service"}


@pytest.mark.asyncio
async def test_register_user(test_client):
    """Test user registration"""
    response = await test_client.post(
        "/register",
        json={
            "email": "test@example.com",
            "password": "securepassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(test_client):
    await test_client.post(
        "/register",
        json={
            "email": "duplicate@example.com",
            "password": "password123"
        }
    )
    
    response = await test_client.post(
        "/register",
        json={
            "email": "duplicate@example.com",
            "password": "differentpassword"
        }
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(test_client):
    await test_client.post(
        "/register",
        json={
            "email": "login@example.com",
            "password": "mypassword123"
        }
    )
    
    response = await test_client.post(
        "/login",
        data={
            "username": "login@example.com",
            "password": "mypassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(test_client):
    await test_client.post(
        "/register",
        json={
            "email": "user@example.com",
            "password": "correctpassword"
        }
    )
    
    response = await test_client.post(
        "/login",
        data={
            "username": "user@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(test_client):
    response = await test_client.post(
        "/login",
        data={
            "username": "nonexistent@example.com",
            "password": "somepassword"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_user_profile_authenticated(test_client):
    await test_client.post(
        "/register",
        json={
            "email": "profile@example.com",
            "password": "password123"
        }
    )
    
    login_response = await test_client.post(
        "/login",
        data={
            "username": "profile@example.com",
            "password": "password123"
        }
    )
    token = login_response.json()["access_token"]
    
    response = await test_client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_user_profile_unauthenticated(test_client):
    """Test that protected endpoint requires authentication"""
    response = await test_client.get("/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_product(test_client):
    """Test creating a product"""
    response = await test_client.post(
        "/products",
        json={
            "name": "Test Product",
            "price_in_pence": 1999
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Product"
    assert data["price_in_pence"] == 1999
    assert "id" in data


@pytest.mark.asyncio
async def test_create_transaction(test_client):
    """Test creating a transaction"""
    response = await test_client.post(
        "/transactions",
        json={
            "user_id": "test_user_123",
            "amount": "99.99",
            "description": "Test transaction"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user_123"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_transactions_for_user(test_client):
    user_id = "user_456"
    await test_client.post(
        "/transactions",
        json={
            "user_id": user_id,
            "amount": "50.00",
            "description": "Test transaction"
        }
    )
    

    response = await test_client.get(f"/transactions/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["user_id"] == user_id


@pytest.mark.asyncio
async def test_initiate_payment_success(test_client, mocker):
    """
    Test the /payments/initiate endpoint, mocking a successful
    Stripe PaymentIntent creation.
    """
    await test_client.post(
        "/register",
        json={"email": "payment_user@example.com", "password": "password123"}
    )
    
    login_response = await test_client.post(
        "/login",
        data={"username": "payment_user@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    product_response = await test_client.post(
        "/products",
        json={"name": "Test Payment Product", "price_in_pence": 1999}
    )
    product_id = product_response.json()["id"]

    
    fake_payment_intent = {
        "id": "pi_MOCK_SUCCESS_ID",
        "client_secret": "cs_MOCK_CLIENT_SECRET",
        "amount": 1999,
        "currency": "gbp"
    }
    mock_stripe_create = mocker.patch(
        "app.main.stripe.PaymentIntent.create",
        return_value=fake_payment_intent
    )

    response = await test_client.post(
        "/payments/initiate",
        headers=auth_headers,
        json={"product_id": product_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["payment_intent_id"] == "pi_MOCK_SUCCESS_ID"
    assert data["client_secret"] == "cs_MOCK_CLIENT_SECRET"
    
    mock_stripe_create.assert_called_once_with(
        amount=1999,
        currency="gbp",
        metadata={
            'user_id': '1',
            'product_id': str(product_id)
        }
    )


@pytest.mark.asyncio
async def test_initiate_payment_stripe_error(test_client, mocker):
    """
    Test the /payments/initiate endpoint, mocking a FAILED
    Stripe call (e.g., card declined).
    """
    await test_client.post(
        "/register",
        json={"email": "payment_fail_user@example.com", "password": "password123"}
    )
    
    login_response = await test_client.post(
        "/login",
        data={"username": "payment_fail_user@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    product_response = await test_client.post(
        "/products",
        json={"name": "Test Fail Product", "price_in_pence": 1999}
    )
    product_id = product_response.json()["id"]

    mock_stripe_create = mocker.patch(
        "app.main.stripe.PaymentIntent.create",
        side_effect=stripe.CardError(
            message="Your card was declined.",
            param="card_number",
            code="card_declined"
        )
    )

    response = await test_client.post(
        "/payments/initiate",
        headers=auth_headers,
        json={"product_id": product_id}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "Your card was declined" in data["detail"]
    
    mock_stripe_create.assert_called_once()