# Quick Start Guide - Multi-Agent System

## Prerequisites

1. ✅ Python 3.14 installed
2. ✅ Ollama installed and running
3. ✅ gemma2 model downloaded

## Setup (One-Time)

### 1. Install gemma2 Model
```powershell
ollama pull gemma2
```

### 2. Verify Installation
```powershell
ollama list
```
You should see `gemma2` in the list.

### 3. Install Python Dependencies
```powershell
cd D:\learning\code\AI_Agents_t-B\backend
pip install -r requirements.txt
```

## Running the System

### Step 1: Start Ollama (Terminal 1)
```powershell
ollama serve
```
Keep this terminal open.

### Step 2: Start Backend (Terminal 2)
```powershell
cd D:\learning\code\AI_Agents_t-B\backend
python main.py
```
Keep this terminal open. You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Testing the System

### Option 1: Use Python Test Script (Recommended)
```powershell
cd D:\learning\code\AI_Agents_t-B\backend
python test_agent.py
```

This will run all tests automatically and show results.

### Option 2: Use PowerShell Test Script
```powershell
cd D:\learning\code\AI_Agents_t-B\backend
.\test_agent.ps1
```

### Option 3: Manual PowerShell Commands

#### Test 1: Create Simple HTML Page
```powershell
$body = @{
    prompt = "Create a simple HTML page called hello.html"
    stream = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

#### Test 2: Check Available Agents
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/available" `
    -Method Get
```

#### Test 3: Health Check
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/health" `
    -Method Get
```

#### Test 4: Create Todo App
```powershell
$body = @{
    prompt = "Create a complete todo app with HTML, CSS, and JavaScript"
    stream = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### Option 4: Use Python Requests (Interactive)
```python
import requests

# Create HTML page
response = requests.post(
    "http://localhost:8000/api/multi-agent/agents/chat",
    json={
        "prompt": "Create a simple HTML page",
        "stream": False
    }
)
print(response.json())
```

## Checking Results

### View Created Files
```powershell
# List files in website directory
Get-ChildItem D:\learning\code\website

# View a specific file
Get-Content D:\learning\code\website\hello.html
```

### Open in Browser
```powershell
# Open the created HTML file
Start-Process D:\learning\code\website\hello.html
```

## Common Issues & Solutions

### Issue 1: "curl: command not found" or PowerShell curl errors
**Problem**: PowerShell's `curl` is an alias for `Invoke-WebRequest` with different syntax.

**Solution**: Use one of these methods:
1. Use the Python test script: `python test_agent.py`
2. Use the PowerShell test script: `.\test_agent.ps1`
3. Use `Invoke-RestMethod` (see examples above)

### Issue 2: "Model 'gemma2' not found"
**Solution**:
```powershell
ollama pull gemma2
```

### Issue 3: "Cannot connect to Ollama"
**Solution**: Start Ollama in a separate terminal:
```powershell
ollama serve
```

### Issue 4: "Port 8000 already in use"
**Solution**: Kill the process using port 8000:
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Issue 5: Import errors
**Solution**: Reinstall dependencies:
```powershell
cd D:\learning\code\AI_Agents_t-B\backend
pip install -r requirements.txt --force-reinstall
```

## Example Workflows

### Workflow 1: Create a Landing Page
```powershell
$body = @{
    prompt = "Create a modern landing page with a hero section, features section, and contact form. Use modern CSS with gradients and animations."
    stream = $false
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

Write-Host $response.response
```

### Workflow 2: Create a Calculator App
```powershell
$body = @{
    prompt = "Create a calculator app with HTML, CSS, and JavaScript. Include basic operations: +, -, *, /"
    stream = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### Workflow 3: Create a Dashboard
```powershell
$body = @{
    prompt = "Create a dashboard with charts and statistics. Use HTML, CSS, and JavaScript. Include sample data."
    stream = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

## API Endpoints Reference

### 1. Multi-Agent Chat
- **URL**: `POST /api/multi-agent/agents/chat`
- **Body**: `{"prompt": "your request", "stream": false}`
- **Response**: Agent's response with created files

### 2. Get Available Agents
- **URL**: `GET /api/multi-agent/agents/available`
- **Response**: List of available agents and their capabilities

### 3. Health Check
- **URL**: `GET /api/multi-agent/agents/health`
- **Response**: System health status

### 4. Direct Agent Interaction
- **URL**: `POST /api/multi-agent/agents/direct/{agent_type}`
- **Agent Types**: `code`, `research`, `analysis`
- **Body**: `{"task": "your task", "context": {}}`

## Tips for Best Results

### 1. Be Specific
❌ Bad: "Create a website"
✅ Good: "Create a landing page with a hero section, features list, and contact form"

### 2. Specify File Names
❌ Bad: "Create an HTML page"
✅ Good: "Create an HTML page called index.html"

### 3. Request Complete Projects
✅ "Create a todo app with HTML, CSS, and JavaScript files"

### 4. Check Verbose Output
The agent shows its reasoning process. Check the backend terminal to see:
- What the agent is thinking
- Which tools it's using
- File creation confirmations

## File Locations

All files are created in:
```
D:\learning\code\website\
```

Example structure after creating a todo app:
```
D:\learning\code\website\
├── index.html
├── styles.css
├── script.js
└── README.md
```

## Next Steps

1. ✅ Run the test scripts to verify everything works
2. ✅ Try creating simple HTML pages
3. ✅ Try creating multi-file projects
4. ✅ Experiment with different prompts
5. ✅ Check the created files in the website directory

## Getting Help

- Check `COMPLETE_SOLUTION.md` for detailed technical information
- Check `FIX_SUMMARY.md` for the fix explanation
- Check `MODEL_UPDATE.md` for model configuration details
- Check backend terminal for verbose agent output

## Success Indicators

✅ Ollama is running (terminal shows "Ollama is running")
✅ Backend is running (shows "Uvicorn running on http://0.0.0.0:8000")
✅ Test scripts run without errors
✅ Files appear in `D:\learning\code\website\`
✅ Agent shows reasoning in verbose output

**You're ready to use the multi-agent system!** 🎉