# AI Guide Integration - AI_Agents_t-B

## ✅ Integration Complete!

The AI Guide has been successfully integrated into your AI_Agents_t-B project. This document explains what was added and how to use it.

## 📦 What Was Added

### Backend (Python/FastAPI)

**Files Added:**
```
backend/
└── ai_guide/
    ├── __init__.py       # Package exports
    ├── models.py         # Pydantic models
    ├── config.py         # Configuration
    └── api.py            # FastAPI router
```

**Changes Made:**
- ✅ Added AI Guide router to `backend/main.py`
- ✅ Configured context-aware prompts for SeniorAgent sections
- ✅ Added `litellm` to `requirements.txt`

### Frontend (React/TypeScript)

**Files Added:**
```
frontend/src/
├── ai-guide/
│   ├── types.ts          # Type definitions
│   ├── api-client.ts     # API communication
│   ├── ai-guide.ts       # Core functionality
│   └── index.ts          # Exports
└── components/
    └── AIGuide.tsx       # React component wrapper
```

## 🚀 How to Use

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install the new `litellm` dependency needed for AI Guide.

### 2. Start the Backend

```bash
cd backend
python main.py
```

The AI Guide API will be available at:
- Chat endpoint: `http://localhost:8000/api/guide/chat`
- Health check: `http://localhost:8000/api/guide/health`

### 3. Use in Your React Components

Import and use the AI Guide component in your app:

```tsx
import { AIGuide } from './components/AIGuide';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');

  return (
    <div>
      {/* Your app content */}
      <YourContent />
      
      {/* AI Guide - automatically adapts to current page */}
      <AIGuide context={currentPage} />
    </div>
  );
}
```

### 4. Update Context Based on Navigation

The AI Guide automatically adapts its responses based on the current page context:

```tsx
// Example: Update context when user navigates
function Navigation() {
  const [context, setContext] = useState('dashboard');

  return (
    <>
      <nav>
        <button onClick={() => setContext('dashboard')}>Dashboard</button>
        <button onClick={() => setContext('builder')}>Agent Builder</button>
        <button onClick={() => setContext('training')}>Training</button>
        <button onClick={() => setContext('leaderboard')}>Leaderboard</button>
        <button onClick={() => setContext('chat')}>Chat</button>
      </nav>
      
      <AIGuide context={context} />
    </>
  );
}
```

## 🎨 Customization

### Change Theme and Colors

```tsx
<AIGuide 
  context="dashboard"
  config={{
    theme: 'dark',
    primaryColor: '#3b82f6', // Your brand color
    position: 'bottom-right',
    autoOpen: true,
  }}
/>
```

### Custom Context Labels

Edit `backend/main.py` to customize the context labels:

```python
guide_config = AIGuideConfig(
    context_labels={
        "dashboard": "Dashboard Overview",
        "builder": "AI Agent Builder",
        "training": "Training Center",
        "leaderboard": "Performance Metrics",
        "chat": "Agent Chat Interface",
    }
)
```

### Custom System Prompts

Edit the `system_prompt_template` in `backend/main.py`:

```python
guide_config = AIGuideConfig(
    system_prompt_template="""You are an AI assistant for {context}.
    
    Your custom instructions here...
    """,
)
```

## 📍 Available Contexts

The AI Guide is configured with these contexts for your SeniorAgent app:

| Context | Description |
|---------|-------------|
| `dashboard` | Overview of all agents and performance metrics |
| `builder` | Create and configure new AI agents |
| `training` | Fine-tune agents with custom training data |
| `leaderboard` | Compare agent performance (TTFT, response time) |
| `chat` | Test and interact with agents |

## 🔧 Configuration Options

### Frontend Configuration

```tsx
interface AIGuideConfig {
  apiEndpoint: string;           // Backend API URL
  theme?: 'light' | 'dark' | 'auto';
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  primaryColor?: string;         // Hex color code
  autoOpen?: boolean;            // Auto-open on page change
  contextLabels?: Record<string, string>;
  enableSettings?: boolean;      // Show settings panel
  enableLocalStorage?: boolean;  // Save preferences
}
```

### Backend Configuration

The backend is already configured in `main.py`. You can modify:

```python
guide_config = AIGuideConfig(
    model_provider="ollama",       # LLM provider
    model_name="llama3",           # Model to use
    api_base=OLLAMA_URL,           # Ollama URL
    temperature=0.7,               # Response creativity
    max_tokens=2000,               # Max response length
)
```

## 🎯 Features

- ✅ **Context-Aware**: Automatically adapts to current page
- ✅ **Streaming Responses**: Real-time ChatGPT-like experience
- ✅ **Persistent Settings**: Saves user preferences
- ✅ **Auto-Open**: Opens automatically on page changes (can be disabled)
- ✅ **Customizable**: Theme, colors, position, and prompts
- ✅ **Lightweight**: Minimal impact on app performance

## 🐛 Troubleshooting

### AI Guide doesn't appear

1. Check that backend is running: `http://localhost:8000/api/guide/health`
2. Verify Ollama is running: `ollama list`
3. Check browser console for errors

### No responses from AI

1. Ensure Ollama is running with llama3 model
2. Check backend logs for errors
3. Verify API endpoint URL is correct

### CORS errors

The backend is already configured to allow all origins. If you still see CORS errors:
1. Check that CORS middleware is enabled in `main.py`
2. Verify the frontend is making requests to the correct URL

## 📚 Additional Resources

- **AI Guide Documentation**: See `ai-guide-standalone/docs/` in the neural-tool-router project
- **Integration Guide**: `ai-guide-standalone/docs/AI_GUIDE_INTEGRATION_GUIDE.md`
- **Architecture**: `ai-guide-standalone/docs/AI_GUIDE_ARCHITECTURE.md`

## 🎉 Example Usage

Here's a complete example of integrating AI Guide into your main App component:

```tsx
// src/App.tsx
import { useState } from 'react';
import { AIGuide } from './components/AIGuide';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Navigation */}
      <nav className="bg-gray-800 p-4">
        <div className="flex gap-4">
          <button 
            onClick={() => setCurrentPage('dashboard')}
            className="px-4 py-2 rounded hover:bg-gray-700"
          >
            Dashboard
          </button>
          <button 
            onClick={() => setCurrentPage('builder')}
            className="px-4 py-2 rounded hover:bg-gray-700"
          >
            Agent Builder
          </button>
          <button 
            onClick={() => setCurrentPage('training')}
            className="px-4 py-2 rounded hover:bg-gray-700"
          >
            Training
          </button>
          <button 
            onClick={() => setCurrentPage('leaderboard')}
            className="px-4 py-2 rounded hover:bg-gray-700"
          >
            Leaderboard
          </button>
          <button 
            onClick={() => setCurrentPage('chat')}
            className="px-4 py-2 rounded hover:bg-gray-700"
          >
            Chat
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="p-8">
        <h1 className="text-3xl font-bold mb-4">
          {currentPage.charAt(0).toUpperCase() + currentPage.slice(1)}
        </h1>
        <p>Your content here...</p>
      </main>

      {/* AI Guide - Floating assistant */}
      <AIGuide 
        context={currentPage}
        config={{
          theme: 'dark',
          primaryColor: '#3b82f6',
          autoOpen: true,
        }}
      />
    </div>
  );
}

export default App;
```

## 💡 Tips

1. **Start with defaults** - The AI Guide works great out of the box
2. **Customize gradually** - Add custom prompts and styling as needed
3. **Monitor usage** - Check backend logs to see what users ask
4. **Iterate on prompts** - Refine system prompts based on user feedback
5. **Test contexts** - Make sure each page context provides helpful responses

---

**Need Help?** Check the comprehensive documentation in the `ai-guide-standalone` package or review the example files.

**Integration Date**: 2026-05-16  
**AI Guide Version**: 1.0.0