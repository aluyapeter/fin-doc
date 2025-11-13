# tests/test_security.py
import pytest
from app.security import hash_password, verify_password

@pytest.fixture(autouse=True)
def mock_env_vars(mocker):
    mocker.patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "postgresql://test:test@db/test_db",
            "JWT_SECRET_KEY": "test_secret_key",
            "JWT_ALGORITHM": "HS256",
            "STRIPE_SECRET_KEY": "sk_test_123",
            "STRIPE_WEBHOOK_SECRET": "whsec_test_123"
        },
        clear=True
    )


def test_hash_password():
    plain_password = "mysecretpassword123"

    hashed_password = hash_password(plain_password)

    assert hashed_password is not None
    assert isinstance(hashed_password, str)
    assert hashed_password != plain_password

def test_verify_password_correct():
    plain_password = "SupaStr0ng!£123"

    hashed_password = hash_password(plain_password)

    is_correct = verify_password(plain_password, hashed_password)

    assert is_correct is True

def test_verify_password_incorrect():
    plain_password = "SupaStr0ng!£123"
    wrong_password = "wrong_password"

    hashed_password = hash_password(plain_password)

    is_correct = verify_password(wrong_password, hashed_password)
    assert is_correct is False