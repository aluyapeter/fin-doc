import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import sqlalchemy
from databases import Database
from app.main import app as fastapi_app
from app.db import metadata

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise ValueError("TEST_DATABASE_URL environment variable not set")

test_database = Database(TEST_DATABASE_URL)
test_engine = sqlalchemy.create_engine(TEST_DATABASE_URL)


@pytest_asyncio.fixture
async def test_client():
    import app.main
    import app.security
    
    original_database = app.main.database
    original_security_db = app.security.database
    
    app.main.database = test_database
    app.security.database = test_database
    
    await test_database.connect()
    
    metadata.create_all(test_engine)

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://testserver"
    ) as client:
        yield client

    metadata.drop_all(test_engine)
    await test_database.disconnect()
    
    app.main.database = original_database
    app.security.database = original_security_db 