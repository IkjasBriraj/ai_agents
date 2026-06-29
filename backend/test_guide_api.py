"""
Test script for AI Guide API
"""
import asyncio
import httpx

async def test_health():
    """Test the health endpoint"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/api/guide/health")
            print(f"Health Check Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False

async def test_chat():
    """Test the chat endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            payload = {
                "messages": [
                    {"role": "user", "content": "Hello, what can you help me with?"}
                ],
                "page_context": "arena"
            }
            
            print("\nSending chat request...")
            async with client.stream("POST", "http://localhost:8000/api/guide/chat", json=payload) as response:
                print(f"Chat Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("\nStreaming response:")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            print(line[6:])  # Remove "data: " prefix
                else:
                    print(f"Error: {await response.aread()}")
                    
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

async def main():
    print("=" * 50)
    print("AI Guide API Test")
    print("=" * 50)
    
    print("\n1. Testing Health Endpoint...")
    health_ok = await test_health()
    
    if health_ok:
        print("\n2. Testing Chat Endpoint...")
        await test_chat()
    else:
        print("\n❌ Health check failed. Make sure the backend server is running.")
        print("   Run: python main.py")

if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
