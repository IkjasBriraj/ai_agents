# File Operations Guide

## Overview

The Code Agent can now create, read, and write files in your specified workspace directory:
**`D:\learning\code\website`**

## Features

✅ Create files with any allowed extension
✅ Read existing files
✅ List directory contents
✅ Create complete project structures with multiple files
✅ Automatic directory creation
✅ Security checks (files only created in workspace)

## Allowed File Extensions

The agent can create files with these extensions:
- **Web**: `.html`, `.css`, `.scss`, `.js`, `.ts`, `.jsx`, `.tsx`, `.vue`, `.svelte`, `.php`
- **Programming**: `.py`, `.java`, `.c`, `.cpp`, `.h`, `.go`, `.rs`, `.rb`, `.swift`, `.kt`, `.dart`
- **Config**: `.json`, `.yaml`, `.yml`, `.xml`, `.toml`, `.ini`, `.env`
- **Documentation**: `.md`, `.txt`
- **Scripts**: `.sh`, `.bat`, `.ps1`
- **Database**: `.sql`
- **Other**: `.gitignore`

## Usage Examples

### 1. Create a Single File via API

```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create an index.html file with a welcome message",
    "stream": false
  }'
```

### 2. Create a Complete Website

```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a simple portfolio website with HTML, CSS, and JavaScript",
    "stream": false
  }'
```

The agent will automatically:
1. Create the project structure (folders and files)
2. Generate complete code for all files
3. Save everything to `D:\learning\code\website`
4. Provide the full paths where files were created

### 3. Create a Web Application

```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a todo list web app with HTML, CSS, and JavaScript. Include add, delete, and mark as complete features.",
    "stream": false
  }'
```

### 4. Read Existing Files

```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Read the index.html file and tell me what it contains",
    "stream": false
  }'
```

### 5. List Files in Workspace

```bash
curl -X POST http://localhost:8000/api/multi-agent/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "List all files in the workspace",
    "stream": false
  }'
```

## Example Prompts

### Simple Website
```
"Create a landing page for a coffee shop with HTML and CSS"
```

### Web Application
```
"Create a calculator web app with HTML, CSS, and JavaScript"
```

### Multi-Page Website
```
"Create a portfolio website with:
- Home page (index.html)
- About page (about.html)
- Projects page (projects.html)
- Contact page (contact.html)
- Shared CSS file (styles/main.css)
- Navigation JavaScript (scripts/nav.js)"
```

### React Application
```
"Create a React todo app with components for TodoList, TodoItem, and AddTodo"
```

### Python Project
```
"Create a Python Flask API with routes for users (CRUD operations)"
```

## File Structure Examples

### Simple Website
```
D:\learning\code\website\
├── index.html
├── styles/
│   └── main.css
└── scripts/
    └── app.js
```

### Complete Web App
```
D:\learning\code\website\
├── index.html
├── about.html
├── contact.html
├── styles/
│   ├── main.css
│   ├── responsive.css
│   └── animations.css
├── scripts/
│   ├── app.js
│   ├── utils.js
│   └── api.js
├── images/
│   └── .gitkeep
└── README.md
```

## Security Features

1. **Workspace Restriction**: Files can only be created in `D:\learning\code\website`
2. **Extension Validation**: Only allowed file extensions can be created
3. **Path Validation**: Prevents directory traversal attacks
4. **Size Limits**: Maximum file size for reading: 10MB

## Testing File Operations

### Quick Test
```bash
cd backend
python -c "from agents.tools import write_file_content; print(write_file_content('test.html', '<h1>Test</h1>'))"
```

### Verify Files
```bash
dir "D:\learning\code\website"
```

### Read a File
```bash
cd backend
python -c "from agents.tools import read_file_content; print(read_file_content('test.html'))"
```

## Tips for Best Results

1. **Be Specific**: Clearly describe what you want
   - ❌ "Create a website"
   - ✅ "Create a portfolio website with home, about, and contact pages"

2. **Mention File Structure**: If you want specific organization
   - "Create a website with separate folders for styles, scripts, and images"

3. **Request Complete Code**: The agent will provide full, working code
   - "Create a complete calculator app with all functionality"

4. **Ask for Documentation**: Request README files
   - "Include a README with setup instructions"

5. **Specify Technologies**: Mention frameworks or libraries
   - "Create a React app using hooks"
   - "Create a Flask API with SQLAlchemy"

## Common Use Cases

### 1. Landing Pages
```
"Create a modern landing page for a SaaS product with:
- Hero section
- Features section
- Pricing section
- Contact form
- Responsive design"
```

### 2. Web Applications
```
"Create a weather app that:
- Shows current weather
- Has a search feature
- Displays 5-day forecast
- Uses a clean, modern design"
```

### 3. Admin Dashboards
```
"Create an admin dashboard with:
- Sidebar navigation
- Dashboard cards with stats
- Data tables
- Charts section
- Responsive layout"
```

### 4. E-commerce Pages
```
"Create a product page with:
- Product images gallery
- Product details
- Add to cart button
- Related products section
- Reviews section"
```

## Troubleshooting

### Files Not Created
- Check if workspace directory exists: `D:\learning\code\website`
- Verify file extension is allowed
- Check backend logs for errors

### Permission Errors
- Ensure the directory is writable
- Run backend with appropriate permissions

### Path Issues
- Use relative paths (e.g., "index.html", "styles/main.css")
- Don't use absolute paths in prompts

## Advanced Usage

### Create Multiple Projects
The agent can create separate projects in subdirectories:
```
"Create a calculator app in the 'calculator' folder"
"Create a todo app in the 'todo-app' folder"
```

Result:
```
D:\learning\code\website\
├── calculator/
│   ├── index.html
│   ├── styles/
│   └── scripts/
└── todo-app/
    ├── index.html
    ├── styles/
    └── scripts/
```

### Modify Existing Files
```
"Read the index.html file and add a footer section"
```

### Code Review
```
"Read all files in the calculator folder and suggest improvements"
```

## Next Steps

1. Start the backend: `cd backend && python main.py`
2. Test file creation with a simple prompt
3. Open created files in your browser or editor
4. Iterate and improve with the agent's help

## Support

- **Documentation**: See [MULTI_AGENT_SYSTEM.md](./MULTI_AGENT_SYSTEM.md)
- **API Docs**: http://localhost:8000/docs
- **Quick Start**: [QUICK_START_MULTI_AGENT.md](./QUICK_START_MULTI_AGENT.md)

---

**Workspace Directory**: `D:\learning\code\website`
**Status**: ✅ Ready to create files!