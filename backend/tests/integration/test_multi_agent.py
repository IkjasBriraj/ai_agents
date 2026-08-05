"""
Test script for Multi-Agent System
Run this to test the orchestrator and specialized agents
"""

import os
import asyncio
import sys

# Ensure UTF-8 output encoding for consoles that do not support it by default
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agents.orchestrator import OrchestratorAgent
from agents.specialized_agents import create_specialized_agent
from agents.config import DEFAULT_MAIN_MODEL


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def test_orchestrator():
    """Test the orchestrator agent"""
    print_section("Testing Orchestrator Agent")
    
    try:
        # Initialize orchestrator
        orchestrator = OrchestratorAgent(
            model_name=DEFAULT_MAIN_MODEL,
            ollama_base_url="http://localhost:11434"
        )
        print("✓ Orchestrator initialized successfully")
        
        # Test cases
        test_cases = [
            {
                "name": "Code Generation Request",
                "prompt": "Please make a simple calculator app in Python",
                "expected_agent": "code"
            },
            {
                "name": "Research Request",
                "prompt": "Research the best practices for REST API design",
                "expected_agent": "research"
            },
            {
                "name": "Analysis Request",
                "prompt": "Analyze this code for potential bugs: def add(a,b): return a+b",
                "expected_agent": "analysis"
            },
            {
                "name": "Business Strategy & Spreadsheet Request",
                "prompt": "Create a 2026 financial forecast spreadsheet in CSV",
                "expected_agent": "business"
            },
            {
                "name": "General Request",
                "prompt": "Hello, how are you?",
                "expected_agent": "general"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case['name']}")
            print(f"Prompt: {test_case['prompt']}")
            
            result = orchestrator.process_request(test_case['prompt'])
            
            if result['status'] == 'success':
                print(f"✓ Status: {result['status']}")
                print(f"✓ Agent Used: {result['agent_used']}")
                print(f"✓ Response Preview: {result['response'][:100]}...")
                
                if result['agent_used'] == test_case['expected_agent']:
                    print(f"✓ Correct agent selected!")
                else:
                    print(f"⚠ Expected {test_case['expected_agent']}, got {result['agent_used']}")
            else:
                print(f"✗ Error: {result['response']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing orchestrator: {e}")
        return False


def test_code_agent():
    """Test the Code Agent directly"""
    print_section("Testing Code Agent")
    
    try:
        agent = create_specialized_agent("code")
        if not agent:
            print("✗ Failed to create Code Agent")
            return False
        
        print("✓ Code Agent created successfully")
        print(f"  Name: {agent.name}")
        print(f"  Type: {agent.agent_type}")
        print(f"  Tools: {[tool.name for tool in agent.tools]}")
        
        # Test code generation
        print("\nTesting code generation...")
        result = agent.process("Generate a Python function to calculate factorial")
        print(f"✓ Response: {result[:200]}...")
        
        # Test app generation
        print("\nTesting app generation...")
        app_result = agent.generate_app("A simple todo list CLI app")
        print(f"✓ Status: {app_result['status']}")
        print(f"✓ Type: {app_result['type']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing Code Agent: {e}")
        return False


def test_research_agent():
    """Test the Research Agent directly"""
    print_section("Testing Research Agent")
    
    try:
        agent = create_specialized_agent("research")
        if not agent:
            print("✗ Failed to create Research Agent")
            return False
        
        print("✓ Research Agent created successfully")
        print(f"  Name: {agent.name}")
        print(f"  Type: {agent.agent_type}")
        print(f"  Tools: {[tool.name for tool in agent.tools]}")
        
        # Test research
        print("\nTesting research...")
        result = agent.research_topic("Machine Learning best practices")
        print(f"✓ Status: {result['status']}")
        print(f"✓ Type: {result['type']}")
        print(f"✓ Response Preview: {result['result'][:200]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing Research Agent: {e}")
        return False


def test_analysis_agent():
    """Test the Analysis Agent directly"""
    print_section("Testing Analysis Agent")
    
    try:
        agent = create_specialized_agent("analysis")
        if not agent:
            print("✗ Failed to create Analysis Agent")
            return False
        
        print("✓ Analysis Agent created successfully")
        print(f"  Name: {agent.name}")
        print(f"  Type: {agent.agent_type}")
        print(f"  Tools: {[tool.name for tool in agent.tools]}")
        
        # Test code analysis
        print("\nTesting code analysis...")
        test_code = """
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total = total + num
    return total
"""
        result = agent.analyze_code(test_code, "python")
        print(f"✓ Status: {result['status']}")
        print(f"✓ Type: {result['type']}")
        print(f"✓ Response Preview: {result['result'][:200]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing Analysis Agent: {e}")
        return False


def test_business_agent():
    """Test the Business Agent directly"""
    print_section("Testing Business Agent")
    
    try:
        agent = create_specialized_agent("business")
        if not agent:
            print("✗ Failed to create Business Agent")
            return False
        
        print("✓ Business Agent created successfully")
        print(f"  Name: {agent.name}")
        print(f"  Type: {agent.agent_type}")
        print(f"  Tools: {[tool.name for tool in agent.tools]}")
        
        # Test business plan method
        print("\nTesting business plan generation struct...")
        bp_result = agent.generate_business_plan("SaaS subscription startup model")
        print(f"✓ Status: {bp_result['status']}")
        print(f"✓ Type: {bp_result['type']}")
        
        # Test financial model method
        print("\nTesting financial model generation struct...")
        fm_result = agent.create_financial_model("Monthly revenue forecast for Q1-Q4")
        print(f"✓ Status: {fm_result['status']}")
        print(f"✓ Type: {fm_result['type']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing Business Agent: {e}")
        return False


def test_csv_sheet_operation():
    """Test the csv_sheet_operation tool directly"""
    print_section("Testing CSV Sheet Operation Tool")
    
    try:
        from agents.tools import csv_sheet_operation
        import os
        
        test_path = "test_financials.csv"
        
        # Test write
        print("Testing CSV write operation...")
        header_and_data = [
            ["Quarter", "Revenue", "Expenses", "Profit"],
            ["Q1", "10000", "6000", "4000"],
            ["Q2", "15000", "7500", "7500"],
        ]
        write_res = csv_sheet_operation("write", test_path, header_and_data)
        print(f"✓ Write Result: {write_res}")
        if "[SUCCESS]" not in write_res:
            print("✗ CSV write failed")
            return False
            
        # Test append
        print("\nTesting CSV append operation...")
        append_data = [
            ["Q3", "20000", "9000", "11000"]
        ]
        append_res = csv_sheet_operation("append", test_path, append_data)
        print(f"✓ Append Result: {append_res}")
        if "[SUCCESS]" not in append_res:
            print("✗ CSV append failed")
            return False

        # Test read
        print("\nTesting CSV read operation...")
        read_res = csv_sheet_operation("read", test_path)
        print(f"✓ Read Result:\n{read_res}")
        if "test_financials.csv" not in read_res or "Quarter" not in read_res:
            print("✗ CSV read failed")
            return False
            
        # Clean up test file
        from agents.config import get_workspace_path
        abs_path = get_workspace_path(test_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
            print("✓ Cleaned up temporary test CSV file")

        return True

    except Exception as e:
        print(f"✗ Error testing CSV Sheet Operation tool: {e}")
        return False


def test_available_agents():
    """Test getting available agents"""
    print_section("Testing Available Agents")
    
    try:
        orchestrator = OrchestratorAgent()
        agents = orchestrator.get_available_agents()
        
        print(f"✓ Found {len(agents)} available agents:")
        for agent in agents:
            print(f"\n  Agent: {agent['name']}")
            print(f"  Type: {agent['type']}")
            print(f"  Tools: {', '.join(agent['tools'])}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error getting available agents: {e}")
        return False


import pytest


@pytest.mark.asyncio
async def test_streaming():
    """Test streaming response"""
    print_section("Testing Streaming Response")
    
    try:
        orchestrator = OrchestratorAgent()
        
        print("Streaming response for: 'Create a hello world function'")
        print("\nStream output:")
        print("-" * 60)
        
        async for chunk in orchestrator.process_request_stream(
            "Create a hello world function in Python"
        ):
            if chunk.get("type") == "agent_selection":
                print(f"\n[Agent Selected: {chunk.get('agent')}]")
            elif chunk.get("type") == "response":
                print(f"\n{chunk.get('content')}")
            elif chunk.get("type") == "error":
                print(f"\n[Error: {chunk.get('content')}]")
        
        print("-" * 60)
        return True
        
    except Exception as e:
        print(f"✗ Error testing streaming: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  MULTI-AGENT SYSTEM TEST SUITE")
    print("=" * 60)
    
    results = {
        "Available Agents": test_available_agents(),
        "Code Agent": test_code_agent(),
        "Research Agent": test_research_agent(),
        "Analysis Agent": test_analysis_agent(),
        "Business Agent": test_business_agent(),
        "CSV Sheet Tool": test_csv_sheet_operation(),
        "Orchestrator": test_orchestrator(),
    }
    
    # Test streaming separately
    print_section("Running Async Tests")
    try:
        asyncio.run(test_streaming())
        results["Streaming"] = True
    except Exception as e:
        print(f"✗ Streaming test failed: {e}")
        results["Streaming"] = False
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
