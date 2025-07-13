import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register a new user
    username = "testuser_login"
    email = "testuser_login@example.com"
    password = "a_very_secure_password"

    registration_data = {
        "username": username,
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User"
    }

    # Use the correct registration endpoint
    response = await client.post("/api/v1/auth/register", json=registration_data)

    # Check if registration was successful or if user already exists
    if response.status_code == 400 and "already exists" in response.text:
        print(f"User {username} or email {email} already exists. Proceeding to login.")
    else:
        assert response.status_code == 201, f"Failed to register user: {response.text}"
        user_data = response.json()
        assert user_data["username"] == username

    # Now, log in with the new user
    login_data = {
        "username": username,
        "password": password
    }

    login_response = await client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200, f"Failed to log in: {login_response.text}"

    token_data = login_response.json()
    assert "access_token" in token_data
    assert "user_id" in token_data

    print(f"Successfully logged in user: {username}")
    print(f"Access Token: {token_data['access_token']}")
    print(f"User ID: {token_data['user_id']}")
