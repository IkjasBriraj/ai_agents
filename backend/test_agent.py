"""
Test script for Multi-Agent System
Run this after starting the backend with: python main.py
"""

import requests
import json
import os
import sys
from pathlib import Path

# Ensure UTF-8 output encoding for consoles that do not support it by default
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000"
WEBSITE_DIR = Path(r"D:\learning\code\website")

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def test_create_html_page():
    """Test 1: Create a simple HTML page"""
    print_header("Test 1: Create Simple HTML Page")
    
    payload = {
        "prompt": "Create a simple HTML page called hello.html with a greeting message",
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/multi-agent/agents/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"\nAgent Used: {result.get('agent_used', 'Unknown')}")
            print(f"\nResponse:\n{result.get('response', 'No response')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")

def test_check_files():
    """Test 2: Check if files were created"""
    print_header("Test 2: Check Created Files")
    
    if WEBSITE_DIR.exists():
        files = list(WEBSITE_DIR.glob("*"))
        if files:
            print(f"✅ Files found in {WEBSITE_DIR}:")
            for file in files:
                size = file.stat().st_size if file.is_file() else 0
                print(f"  - {file.name} ({size} bytes)")
        else:
            print(f"⚠️  No files in {WEBSITE_DIR}")
    else:
        print(f"❌ Directory not found: {WEBSITE_DIR}")

def test_get_agents():
    """Test 3: Get available agents"""
    print_header("Test 3: Get Available Agents")
    
    try:
        response = requests.get(f"{BASE_URL}/api/multi-agent/agents/available")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Found {result.get('count', 0)} agents:")
            for agent in result.get('agents', []):
                print(f"\n  Agent: {agent.get('name')}")
                print(f"  Type: {agent.get('type')}")
                print(f"  Tools: {', '.join(agent.get('tools', []))}")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health():
    """Test 4: Health check"""
    print_header("Test 4: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/api/multi-agent/agents/health")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ System Status: {result.get('status', 'Unknown')}")
            print(f"   Model: {result.get('model', 'Unknown')}")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_create_todo_app():
    """Test 5: Create a complete todo app"""
    print_header("Test 5: Create Todo App (Multi-file)")
    
    payload = {
        "prompt": "Create a complete todo app with HTML, CSS, and JavaScript. Include add, delete, and mark as complete functionality.",
        "stream": False
    }
    
    try:
        print("⏳ This may take a moment...")
        response = requests.post(
            f"{BASE_URL}/api/multi-agent/agents/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=130
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"\nAgent Used: {result.get('agent_used', 'Unknown')}")
            print(f"\nResponse:\n{result.get('response', 'No response')[:500]}...")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("\n" + "="*60)
    print("  Multi-Agent System Test Suite")
    print("="*60)
    print("\nMake sure the backend is running: python main.py")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Run tests
        test_health()
        test_get_agents()
        test_create_html_page()
        test_check_files()
        
        # Ask if user wants to run the complex test
        print("\n" + "="*60)
        response = input("\nRun complex test (Create Todo App)? This may take 30-60 seconds. (y/n): ")
        if response.lower() == 'y':
            test_create_todo_app()
            test_check_files()
        
        print("\n" + "="*60)
        print("  All Tests Complete!")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()

# Made with Bob
