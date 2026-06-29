# Multi-Agent System Documentation

## Overview

This project now includes a sophisticated multi-agent system built with LangGraph. The system features a main **Orchestrator Agent** that intelligently routes user requests to specialized agents based on the task requirements.

## Architecture

```
User Request
     ↓
Orchestrator Agent (LangGraph)
     ↓
  Analyzes Request
     ↓
Routes to Specialized Agent
     ↓
┌─────────────┬──────────────┬───────────────┐
│ Code Agent  │ Research     │ Analysis      │
│             │ Agent        │ Agent         │
└─────────────┴──────────────┴───────────────┘
     ↓
Returns Response to User
```

## Specialized Agents

### 1. Code Agent
**Purpose**: Software development and code generation

**Capabilities**:
- Generate code in multiple programming languages (Python, JavaScript, TypeScript, etc.)
- Execute Python code safely in a sandboxed environment
- Create complete applications from requirements
- Read and write files
- Analyze code for improvements
- Debug and fix code issues

**Tools**:
- `execute_code`: Execute Python code safely
- `generate_code`: Generate code based on requirements
- `file_operation`: Read, write, and list files
- `analyze_code`: Analyze code quality

**Example Usage**:
```
User: "Please make a Flask web app with user authentication"
→ Orchestrator routes to Code Agent
→ Code Agent generates complete app with all files
```

### 2. Research Agent
**Purpose**: Information gathering and research

**Capabilities**:
- Search and gather information
- Summarize complex documents
- Compare different approaches
- Provide well-researched recommendations
- Stay current with trends and technologies

**Tools**:
- `web_search`: Search for information (placeholder for API integration)
- `summarize_text`: Summarize long text content

**Example Usage**:
```
User: "Research the best practices for React state management"
→ Orchestrator routes to Research Agent
→ Research Agent provides comprehensive analysis
```

### 3. Analysis Agent
**Purpose**: Code and data analysis

**Capabilities**:
- Analyze code quality and performance
- Identify bugs and security vulnerabilities
- Suggest optimizations
- Review architecture and design patterns
- Analyze data patterns

**Tools**:
- `analyze_code`: Detailed code analysis
- `file_operation`: Read files for analysis

**Example Usage**:
```
User: "Analyze this code for security issues"
→ Orchestrator routes to Analysis Agent
→ Analysis Agent provides detailed security audit
```

## API Endpoints

### Multi-Agent Chat
**Endpoint**: `POST /api/multi-agent/agents/chat`

**Request**:
```json
{
  "prompt": "Please make a todo app",
  "context": {},
  "stream": false
}
```

**Response**:
```json
{
  "status": "success",
  "response": "**Agent Used:** CODE AGENT\n\n**Response:**\n[Generated code and instructions]",
  "agent_used": "code",
  "metadata": {
    "model": "llama3.2",
    "workflow_steps": 4
  }
}
```

### Get Available Agents
**Endpoint**: `GET /api/multi-agent/agents/available`

**Response**:
```json
{
  "status": "success",
  "agents": [
    {
      "name": "Code Agent",
      "type": "code",
      "tools": ["execute_code", "generate_code", "file_operation", "analyze_code"],
      "description": "You are a Code Agent specialized in software development..."
    }
  ],
  "count": 3
}
```

### Direct Agent Interaction
**Endpoint**: `POST /api/multi-agent/agents/direct/{agent_type}`

Bypass the orchestrator and interact directly with a specific agent.

**Request**:
```json
{
  "agent_type": "code",
  "task": "Generate a Python function to calculate fibonacci numbers",
  "context": {}
}
```

### Specialized Endpoints

#### Generate Application
**Endpoint**: `POST /api/multi-agent/agents/code/generate-app?requirements=...`

Directly use the Code Agent to generate a complete application.

#### Research Topic
**Endpoint**: `POST /api/multi-agent/agents/research/topic?topic=...`

Directly use the Research Agent to research a topic.

#### Analyze Code
**Endpoint**: `POST /api/multi-agent/agents/analysis/code?code=...&language=python`

Directly use the Analysis Agent to analyze code.

### Health Check
**Endpoint**: `GET /api/multi-agent/agents/health`

Check the health status of the multi-agent system.

## How It Works

### 1. Request Analysis
When a user sends a request, the Orchestrator Agent:
1. Receives the user's prompt
2. Analyzes the intent and requirements
3. Determines which specialized agent is best suited

### 2. Agent Selection
The orchestrator uses an LLM to intelligently classify requests:
- **Code-related**: "make an app", "generate code", "create a function" → Code Agent
- **Research-related**: "research", "find information", "compare" → Research Agent
- **Analysis-related**: "analyze", "review", "check for bugs" → Analysis Agent
- **General**: Conversational queries → Handled directly by orchestrator

### 3. Task Execution
The selected agent:
1. Receives the task with context
2. Uses its specialized tools if needed
3. Processes the request using its LLM
4. Returns the result

### 4. Response Formatting
The orchestrator formats the response to include:
- Which agent was used
- The agent's response
- Metadata about the processing

## LangGraph Workflow

The orchestrator uses LangGraph to manage the workflow:

```python
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("analyze_request", analyze_request)
workflow.add_node("route_to_agent", route_to_agent)
workflow.add_node("generate_response", generate_response)

# Edges
workflow.set_entry_point("analyze_request")
workflow.add_edge("analyze_request", "route_to_agent")
workflow.add_edge("route_to_agent", "generate_response")
workflow.add_edge("generate_response", END)
```

## Configuration

### Model Configuration
Default model: `llama3.2`
Ollama URL: `http://localhost:11434`

You can customize these in `backend/main.py`:
```python
multi_agent_router = create_multi_agent_router(
    model_name="llama3.2",  # Change model here
    ollama_base_url=OLLAMA_URL
)
```

### Adding New Agents

1. **Create Agent Class** in `backend/agents/specialized_agents.py`:
```python
class NewAgent(BaseSpecializedAgent):
    def __init__(self, model_name, ollama_base_url):
        system_prompt = "Your specialized prompt..."
        super().__init__(
            name="New Agent",
            agent_type="new",
            system_prompt=system_prompt,
            model_name=model_name,
            ollama_base_url=ollama_base_url
        )
```

2. **Add Tools** in `backend/agents/tools.py`:
```python
def get_new_agent_tools() -> List[Tool]:
    return [
        Tool(name="tool_name", func=tool_function, description="...")
    ]

AGENT_TOOLS["new"] = get_new_agent_tools
```

3. **Register Agent** in `specialized_agents.py`:
```python
SPECIALIZED_AGENTS["new"] = NewAgent
```

## Testing

### Test the System
```bash
# Start the backend
cd backend
python main.py

# Test multi-agent chat
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Please make a calculator app", "stream": false}'

# Get available agents
curl http://localhost:8000/api/multi-agent/agents/available

# Health check
curl http://localhost:8000/api/multi-agent/agents/health
```

### Example Requests

**Generate an App**:
```bash
curl -X POST "http://localhost:8000/api/multi-agent/agents/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a Python Flask API with CRUD operations for a todo list",
    "stream": false
  }'
```

**Research a Topic**:
```bash
curl -X POST "http://localhost:8000/api/multi-agent/agents/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Research the best practices for microservices architecture",
    "stream": false
  }'
```

**Analyze Code**:
```bash
curl -X POST "http://localhost:8000/api/multi-agent/agents/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze this code for security vulnerabilities: [code here]",
    "stream": false
  }'
```

## Dependencies

Make sure all dependencies are installed:
```bash
pip install -r backend/requirements.txt
```

Required packages:
- `fastapi`
- `uvicorn`
- `langchain`
- `langchain-community`
- `langgraph`
- `pydantic`
- `httpx`

## Future Enhancements

1. **Tool Integration**:
   - Integrate real web search APIs
   - Add code execution sandboxing
   - Implement file system operations with safety checks

2. **More Agents**:
   - Database Agent (SQL queries, schema design)
   - DevOps Agent (deployment, CI/CD)
   - Testing Agent (generate tests, run tests)
   - Documentation Agent (generate docs)

3. **Advanced Features**:
   - Agent collaboration (multiple agents working together)
   - Memory and context persistence
   - Learning from user feedback
   - Custom agent creation via UI

4. **Performance**:
   - Caching for common requests
   - Parallel agent execution
   - Response streaming for better UX

## Troubleshooting

### Ollama Connection Issues
```
Error: Cannot connect to Ollama
Solution: Ensure Ollama is running: ollama serve
```

### Model Not Found
```
Error: Model 'llama3.2' not found
Solution: Pull the model: ollama pull llama3.2
```

### Import Errors
```
Error: Module not found
Solution: Install dependencies: pip install -r backend/requirements.txt
```

## Contributing

To add new features or agents:
1. Follow the existing agent structure
2. Add comprehensive docstrings
3. Test thoroughly
4. Update this documentation

---

**Built with LangGraph** 🦜🔗