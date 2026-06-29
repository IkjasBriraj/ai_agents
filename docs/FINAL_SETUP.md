# Final Setup - Multi-Agent System with gemma4:e4b

## Model Configuration

The system is now configured to use **gemma4:e4b** (Gemma 2 with 4-bit quantization).

### Why gemma4:e4b?
- **Smaller size**: 4-bit quantization reduces model size
- **Faster inference**: Quicker responses
- **Lower memory usage**: Works on systems with less RAM
- **Good performance**: Maintains quality while being efficient

## Setup Steps

### 1. Pull the Model
```powershell
ollama pull gemma4:e4b
```

### 2. Verify Model
```powershell
ollama list
```
You should see `gemma4:e4b` in the list.

### 3. Start Ollama
```powershell
ollama serve
```

### 4. Start Backend
```powershell
cd D:\learning\code\AI_Agents_t-B\backend
python main.py
```

### 5. Test the System
```powershell
cd D:\learning\code\AI_Agents_t-B\backend
python test_agent.py
```

## Files Updated

All files now use `gemma4:e4b` as the default model:

1. ✅ `backend/agents/specialized_agents.py`
2. ✅ `backend/agents/orchestrator.py`
3. ✅ `backend/agents/api.py`
4. ✅ `backend/main.py`

## Quick Test (PowerShell)

```powershell
# Create a simple HTML page
$body = @{
    prompt = "Create a simple HTML page called hello.html with a greeting"
    stream = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/chat" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

## Check Results

```powershell
# List created files
Get-ChildItem D:\learning\code\website

# View a file
Get-Content D:\learning\code\website\hello.html

# Open in browser
Start-Process D:\learning\code\website\hello.html
```

## Model Comparison

| Model | Size | Speed | Quality | Memory |
|-------|------|-------|---------|--------|
| gemma2 | ~9GB | Medium | High | High |
| **gemma4:e4b** | ~2.5GB | Fast | Good | Low |
| llama3.2 | ~2GB | Fast | Good | Low |

## Configuration

The model is set in multiple places. All have been updated to `gemma4:e4b`:

```python
# Default in all agent classes
model_name: str = "gemma4:e4b"

# In main.py
multi_agent_router = create_multi_agent_router(
    model_name="gemma4:e4b",
    ollama_base_url=OLLAMA_URL
)
```

## Switching Models

If you want to use a different model, you can:

### Option 1: Change Default (Permanent)
Edit the files and change `"gemma4:e4b"` to your preferred model.

### Option 2: Pass at Runtime (Temporary)
```python
# In your code
multi_agent_router = create_multi_agent_router(
    model_name="llama3.2",  # or any other model
    ollama_base_url="http://localhost:11434"
)
```

## Available Models

Popular Ollama models you can use:
- `gemma4:e4b` (current - 4-bit quantized)
- `gemma2` (full precision)
- `llama3.2`
- `llama3.1`
- `mistral`
- `phi3`
- `codellama`

To see all available models:
```powershell
ollama list
```

## Troubleshooting

### Model Not Found
```
Error: Model 'gemma4:e4b' not found
```
**Solution**:
```powershell
ollama pull gemma4:e4b
```

### Out of Memory
If you get memory errors, try a smaller model:
```powershell
ollama pull phi3
```
Then change the model in the code to `"phi3"`.

### Slow Performance
The e4b (4-bit) version should be fast. If it's still slow:
1. Check if Ollama is using GPU: `ollama ps`
2. Try an even smaller model like `phi3`
3. Close other applications to free up memory

## Performance Tips

### For Best Speed
```python
model_name="phi3"  # Smallest, fastest
```

### For Best Quality
```python
model_name="gemma2"  # Full precision, slower
```

### For Balance (Current)
```python
model_name="gemma4:e4b"  # 4-bit, good balance
```

## Testing Commands

### Test 1: Simple Page
```powershell
$body = @{prompt = "Create index.html"; stream = $false} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/chat" -Method Post -ContentType "application/json" -Body $body
```

### Test 2: Multi-File Project
```powershell
$body = @{prompt = "Create a todo app with HTML, CSS, and JavaScript"; stream = $false} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/chat" -Method Post -ContentType "application/json" -Body $body
```

### Test 3: Check Health
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/health" -Method Get
```

## What's Working

✅ File creation with gemma4:e4b model
✅ ReAct agent pattern for tool usage
✅ Python 3.14 compatibility
✅ PowerShell test scripts
✅ Complete documentation

## Summary

- **Model**: gemma4:e4b (4-bit quantized Gemma 2)
- **Benefits**: Faster, smaller, lower memory usage
- **Status**: All files updated and ready to use
- **Testing**: Use `python test_agent.py` or PowerShell commands

## Next Steps

1. ✅ Pull gemma4:e4b model
2. ✅ Start Ollama
3. ✅ Start backend
4. ✅ Run tests
5. ✅ Create your first project!

**The system is ready with gemma4:e4b!** 🚀