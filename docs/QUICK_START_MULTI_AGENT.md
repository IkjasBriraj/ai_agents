# Quick Start Guide - Multi-Agent System

## Prerequisites

1. **Ollama must be running**:
   ```bash
   ollama serve
   ```

2. **Pull the required model**:
   ```bash
   ollama pull llama3.2
   ```

3. **Install Python dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## Step 1: Start the Backend

```bash
cd backend
python main.py
```

The backend will start at `http://localhost:8000`

## Step 2: Test the Multi-Agent System

### Option A: Run the Test Suite

```bash
cd backend
python test_multi_agent.py
```

This will test:
- ✓ Available agents
- ✓ Code Agent
- ✓ Research Agent
- ✓ Analysis Agent
- ✓ Orchestrator routing
- ✓ Streaming responses

### Option B: Test via API

#### 1. Check Health
```bash
curl http://localhost:8000/api/multi-agent/agents/health
```

#### 2. Get Available Agents
```bash
curl http://localhost:8000/api/multi-agent/agents/available
```

#### 3. Chat with Orchestrator (Code Generation)
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Please make a simple calculator app in Python",
    "stream": false
  }'
```

#### 4. Chat with Orchestrator (Research)
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Research the best practices for REST API design",
    "stream": false
  }'
```

#### 5. Chat with Orchestrator (Analysis)
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze this code: def add(a,b): return a+b",
    "stream": false
  }'
```

#### 6. Direct Code Agent Interaction
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/direct/code \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "code",
    "task": "Generate a Python function to calculate fibonacci numbers"
  }'
```

#### 7. Generate Complete Application
```bash
curl -X POST "http://localhost:8000/api/multi-agent/agents/code/generate-app?requirements=A%20simple%20todo%20list%20CLI%20app"
```

#### 8. Research a Topic
```bash
curl -X POST "http://localhost:8000/api/multi-agent/agents/research/topic?topic=Machine%20Learning%20best%20practices"
```

#### 9. Analyze Code
```bash
curl -X POST "http://localhost:8000/api/multi-agent/agents/analysis/code" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def calculate_sum(numbers):\n    total = 0\n    for num in numbers:\n        total = total + num\n    return total",
    "language": "python"
  }'
```

## Step 3: View API Documentation

Open your browser and go to:
```
http://localhost:8000/docs
```

This will show the interactive Swagger UI with all available endpoints.

## Example Workflows

### Workflow 1: Build a Complete App

1. **User Request**: "Please make a Flask web app with user authentication"

2. **What Happens**:
   - Orchestrator analyzes the request
   - Routes to Code Agent
   - Code Agent generates:
     - Project structure
     - All code files
     - Requirements.txt
     - Setup instructions
     - Usage guide

3. **Test It**:
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Please make a Flask web app with user authentication",
    "stream": false
  }'
```

### Workflow 2: Research and Implement

1. **Research Phase**:
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Research the best database for a social media app",
    "stream": false
  }'
```

2. **Implementation Phase**:
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a database schema for a social media app with users, posts, and comments",
    "stream": false
  }'
```

### Workflow 3: Code Review

1. **Generate Code**:
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a user authentication function in Python",
    "stream": false
  }'
```

2. **Analyze Code**:
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze the security of this authentication code: [paste code here]",
    "stream": false
  }'
```

## Troubleshooting

### Issue: "Cannot connect to Ollama"
**Solution**: Make sure Ollama is running
```bash
ollama serve
```

### Issue: "Model not found"
**Solution**: Pull the model
```bash
ollama pull llama3.2
```

### Issue: "Import errors"
**Solution**: Install dependencies
```bash
pip install -r backend/requirements.txt
```

### Issue: "Agent not responding"
**Solution**: Check Ollama logs and ensure the model is loaded
```bash
ollama list
```

## Next Steps

1. **Explore the API**: Visit `http://localhost:8000/docs`
2. **Read Full Documentation**: See [MULTI_AGENT_SYSTEM.md](./MULTI_AGENT_SYSTEM.md)
3. **Customize Agents**: Modify agent prompts in `backend/agents/specialized_agents.py`
4. **Add New Tools**: Extend tools in `backend/agents/tools.py`
5. **Create New Agents**: Follow the pattern in specialized_agents.py

## Performance Tips

1. **Use Streaming**: Set `"stream": true` for better UX
2. **Cache Responses**: Implement caching for common requests
3. **Optimize Prompts**: Shorter, clearer prompts = faster responses
4. **Choose Right Model**: Balance between speed and quality

## Support

- **Documentation**: [MULTI_AGENT_SYSTEM.md](./MULTI_AGENT_SYSTEM.md)
- **API Docs**: http://localhost:8000/docs
- **Test Suite**: `python backend/test_multi_agent.py`

---

**Happy Building! 🚀**