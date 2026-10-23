import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database.db import init_db

async def run_auth_tests():
    print("Initializing DB...")
    await init_db()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test database status
        print("Testing GET /api/database/status...")
        db_res = await client.get("/api/database/status")
        assert db_res.status_code == 200, f"Expected 200, got {db_res.status_code}: {db_res.text}"
        db_data = db_res.json()
        print("Database status response:", db_data)
        assert "connected" in db_data
        assert "status" in db_data

        # 2. Test registration
        test_username = f"testuser_{os.urandom(4).hex()}"
        test_email = f"{test_username}@example.com"
        print(f"Testing POST /api/auth/register with {test_username}...")
        reg_res = await client.post("/api/auth/register", json={
            "username": test_username,
            "email": test_email,
            "password": "Password123!",
            "full_name": "Test User Account"
        })
        assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
        reg_data = reg_res.json()
        assert reg_data["status"] == "success"
        token = reg_data["token"]
        assert token is not None
        assert reg_data["user"]["username"] == test_username
        print("Registration successful!")

        # 3. Test duplicate registration rejection
        dup_res = await client.post("/api/auth/register", json={
            "username": test_username,
            "email": f"diff_{test_email}",
            "password": "Password123!"
        })
        assert dup_res.status_code == 400
        print("Duplicate username correctly rejected!")

        # 4. Test login with valid credentials
        print("Testing POST /api/auth/login...")
        login_res = await client.post("/api/auth/login", json={
            "username_or_email": test_username,
            "password": "Password123!"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        login_data = login_res.json()
        assert login_data["token"] is not None
        print("Login with username successful!")

        # 5. Test login with email
        login_email_res = await client.post("/api/auth/login", json={
            "username_or_email": test_email,
            "password": "Password123!"
        })
        assert login_email_res.status_code == 200
        print("Login with email successful!")

        # 6. Test login with invalid password
        bad_login = await client.post("/api/auth/login", json={
            "username_or_email": test_username,
            "password": "WrongPassword!"
        })
        assert bad_login.status_code == 401
        print("Bad password correctly rejected!")

        # 7. Test /api/auth/me with Bearer token
        print("Testing GET /api/auth/me...")
        me_res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200, f"Get me failed: {me_res.text}"
        me_data = me_res.json()
        assert me_data["username"] == test_username
        print("Me endpoint verified successfully!")

        # 8. Test Demo login
        print("Testing POST /api/auth/demo...")
        demo_res = await client.post("/api/auth/demo")
        assert demo_res.status_code == 200, f"Demo login failed: {demo_res.text}"
        demo_data = demo_res.json()
        assert demo_data["user"]["username"] == "guest_researcher"
        assert demo_data["token"] is not None
        print("Demo login verified successfully!")

        # 9. Test /health includes MongoDB
        print("Testing GET /health...")
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        h_data = health_res.json()
        assert "mongodb" in h_data["components"]
        print("Health check includes mongodb component:", h_data["components"]["mongodb"])

    print("\nALL BACKEND AUTH & MONGO TESTS PASSED SUCCESSFULLY! 🎉\n")

if __name__ == "__main__":
    asyncio.run(run_auth_tests())
