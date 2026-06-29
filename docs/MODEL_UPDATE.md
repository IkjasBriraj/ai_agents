# Model Update: llama3.2 → gemma2

## Changes Made

All references to `llama3.2` have been updated to `gemma2` in the AI Agents multi-agent system.

### Files Modified

1. **`backend/agents/specialized_agents.py`**
   - Updated default `model_name` parameter in `BaseSpecializedAgent.__init__()` from `"llama3.2"` to `"gemma2"`
   - Updated default `model_name` in `CodeAgent.__init__()` from `"llama3.2"` to `"gemma2"`
   - Updated default `model_name` in `ResearchAgent.__init__()` from `"llama3.2"` to `"gemma2"`
   - Updated default `model_name` in `AnalysisAgent.__init__()` from `"llama3.2"` to `"gemma2"`
   - Updated default `model_name` in `create_specialized_agent()` from `"llama3.2"` to `"gemma2"`

2. **`backend/agents/orchestrator.py`**
   - Updated default `model_name` parameter in `OrchestratorAgent.__init__()` from `"llama3.2"` to `"gemma2"`

3. **`backend/agents/api.py`**
   - Updated default `model_name` parameter in `create_multi_agent_router()` from `"llama3.2"` to `"gemma2"`

4. **`backend/main.py`**
   - Updated model initialization from `model_name="llama3.2"` to `model_name="gemma2"`

## Before Starting

### 1. Pull the gemma2 Model
Make sure you have the gemma2 model downloaded in Ollama:

```bash
ollama pull gemma2
```

### 2. Verify Model is Available
```bash
ollama list
```

You should see `gemma2` in the list of available models.

## Testing the Changes

### 1. Start Ollama
```bash
ollama serve
```

### 2. Start the Backend
```bash
cd D:\learning\code\AI_Agents_t-B\backend
python main.py
```

### 3. Test the Multi-Agent System
```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Create a simple HTML page\", \"stream\": false}"
```

### 4. Verify File Creation
Check that files are created in `D:\learning\code\website\`

## Model Comparison

### llama3.2
- Previous model
- Good for general tasks
- Smaller model size

### gemma2
- New model (Google's Gemma 2)
- Better performance on many tasks
- Improved reasoning capabilities
- Better tool usage

## Configuration

The model can be changed at runtime by passing a different `model_name` parameter:

```python
# In your code
multi_agent_router = create_multi_agent_router(
    model_name="gemma2",  # or any other Ollama model
    ollama_base_url="http://localhost:11434"
)
```

## Available Ollama Models

You can use any model available in Ollama. Popular options:
- `gemma2` (recommended)
- `llama3.2`
- `llama3.1`
- `mistral`
- `mixtral`
- `codellama`
- `phi3`

To see all available models:
```bash
ollama list
```

## Troubleshooting

### Model Not Found Error
```
Error: Model 'gemma2' not found
```
**Solution**: Pull the model first
```bash
ollama pull gemma2
```

### Ollama Not Running
```
Error: Cannot connect to Ollama
```
**Solution**: Start Ollama
```bash
ollama serve
```

### Performance Issues
If gemma2 is too slow on your hardware, you can switch back to a smaller model:
```python
model_name="llama3.2"  # or "phi3" for even faster performance
```

## Summary

✅ All files updated to use `gemma2` instead of `llama3.2`
✅ File creation functionality fixed (ReAct agent pattern)
✅ System ready to use with gemma2 model
✅ Backward compatible - can still use other models by changing the parameter

The multi-agent system is now configured to use Google's Gemma 2 model for better performance and reasoning capabilities!