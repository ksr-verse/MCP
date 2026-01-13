# SailPoint Support Bot

AI-powered L1 support automation using FastAPI backend with Groq LLM and MCP server for SailPoint IIQ integration.

## Overview

AI-powered L1 support automation that uses **Model Context Protocol (MCP)** to automatically resolve common access-related issues. The system understands user intent from chat messages, calls MCP tools, and triggers actions via SailPoint IIQ API.

## Use Case

**Problem:** Users report "My access request was approved but I didn't get access"

**Current Process:** L1 team manually checks SailPoint, runs Identity Refresh

**Solution:** AI bot automatically triggers Identity Refresh via MCP tools

**Result:** 80% of repetitive L1 tickets auto-resolved

## Prerequisites

- Python 3.8+
- Node.js 16+
- Groq API Key (Get from https://console.groq.com/keys`)

## Setup

**Note:** Make sure dependencies are installed first (see Manual Setup below).

### Manual Setup

If you prefer to run commands manually:

### Backend Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

**Dependencies:**
- `fastapi` - Web framework for building APIs
- `uvicorn` - ASGI server for running FastAPI
- `pydantic` - Data validation using Python type annotations
- `python-dotenv` - Load environment variables from .env file
- `groq` - Groq API client for LLM integration
- `requests` - HTTP library for API calls
- `python-multipart` - Support for form data
- `mcp` - Model Context Protocol SDK
- `anthropic` - Anthropic SDK (required by MCP)

2. **Configure environment variables:**

**Get GROQ_API_KEY:**
- Get it from https://console.groq.com/keys
- Find the `.env` file and copy the `GROQ_API_KEY` value

Create `.env` file in `backend/` directory:
```env

# OPTIONAL: Add when you have SailPoint instance
SAILPOINT_API_URL=your_sailpoint_url
SAILPOINT_CLIENT_ID=your_client_id
SAILPOINT_CLIENT_SECRET=your_client_secret

# APP SETTINGS (defaults)
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=True
```

3. **Run the backend server:**
```bash
uvicorn main:app --reload --port 8000
```

The backend will run at `http://localhost:8000`

### Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Run development server:**
```bash
npm run dev
```

The frontend will run at `http://localhost:3000`

**Note:** Make sure the backend is running at `http://localhost:8000` before starting the frontend.

## Architecture

### What is MCP (Model Context Protocol)?

MCP (Model Context Protocol) is an open protocol originally proposed by Anthropic that standardizes how LLMs receive external context and interact with tools and data sources.

### Our Implementation

We use **FastMCP** from the official MCP SDK combined with **Groq's Function Calling**:

```
User Message
    ↓
Groq LLM (with tool definitions)
    ↓
LLM decides which tool to call
    ↓
MCP Tool Execution (mcp_server.py)
    ↓
SailPoint IIQ API
    ↓
Return result to LLM
    ↓
LLM formats response for user
```

### MCP Components

1. **MCP Server** (`mcp_server.py`) - Uses FastMCP from official `mcp` package
2. **MCP Endpoint** - Mounted at `/mcp` using SSE transport
3. **MCP Tools** - Decorated with `@mcp.tool()` following MCP specification

## How It Works

### Example Flow

**User:** "User Aaron Nichols is unable to access application XYZ. Since this is a role-based access, he should receive access automatically."

**Step 1 - LLM Analysis:**
- LLM reads the message and identifies access issue
- LLM decides: Call `trigger_identity_refresh`
- LLM extracts: `user_id="Aaron.Nichols"`, `reason="Role-based access not provisioned"`

**Step 2 - MCP Tool Execution:**
```python
result = trigger_identity_refresh(
    user_id="Aaron.Nichols",
    reason="Role-based access not provisioned"
)
```

**Step 3 - SailPoint API:**
- OAuth 2.0 authentication
- Calls: `/identityiq/plugin/rest/RefreshIdentity/refreshIdentitySingleUser?userId=Aaron.Nichols`
- Returns actual SailPoint response

**Step 4 - Response:**
```
Identity Refresh Triggered

Task Status: Success

Please wait 2-3 minutes and try logging in again.

SailPoint IIQ API Response:
{actual data from API}
```

## API Endpoints

- `GET /` - Service info
- `POST /chat` - Main chat endpoint (processes user messages with LLM + MCP)
- `GET /health` - Health check
- `GET /mcp/status` - MCP server status

**Note:** The `/mcp` endpoint uses SSE transport for MCP protocol communication and is not accessible via browser.

## MCP Tools

Three tools exposed via the MCP protocol:

1. **trigger_identity_refresh** - Syncs user access from SailPoint (fully implemented)
   - **When to use:** Access approved but user can't login, colleagues have access but user doesn't, dynamic/role-based access not working
   - **Parameters:** `user_id`, `reason`

2. **check_request_status** - Checks access request status (dummy - no API URL available)
   - **Parameters:** `request_id`

3. **get_identity_info** - Retrieves identity details (dummy - no API URL available)
   - **Parameters:** `user_id`

## Project Structure

```
MCP/
├── backend/               # FastAPI + MCP Server
│   ├── main.py           # Main API with LLM integration
│   ├── mcp_server.py     # MCP tools
│   ├── sailpoint_api.py  # SailPoint integration
│   ├── config.py         # Configuration (reads from .env)
│   ├── requirements.txt  # Python dependencies
│   └── .env             # GROQ_API_KEY here
│
├── frontend/             # React UI
│   └── src/
│       └── App.jsx       # Chat interface
│
├── start-backend.bat     # Start backend (Windows)
├── start-frontend.bat    # Start frontend (Windows)
└── README.md            # This file
```

## Verification

### Verify Setup

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **MCP Status**: http://localhost:8000/mcp/status (Note: Not accessible via browser - uses different protocol. Use curl or API client)
- **Frontend**: http://localhost:3000

### Check Health:
```bash
curl http://localhost:8000/health


## View Logs

**Real-time logs:**
```powershell
Get-Content backend/sailpoint_bot.log -Wait
```

**Last 50 lines:**
```powershell
Get-Content backend/sailpoint_bot.log -Tail 50
```

**Linux/Mac:**
```bash
tail -f backend/sailpoint_bot.log
```

## Troubleshooting

### Backend won't start:
- Make sure Python 3.8+ is installed
- Check if GROQ_API_KEY is set in `.env`
- Try: `pip install --upgrade pip`
- Verify: `cd backend && pip install -r requirements.txt`

### "GROQ_API_KEY not found" error:
- Make sure `.env` file exists in `backend/` directory
- Verify the key is copied correctly from NL2MySQL project

### Frontend won't start:
- Make sure Node.js 16+ is installed
- Delete `node_modules` and run `npm install` again
- Check if port 3000 is available (or use port 3001 if 3000 is taken)

### Frontend can't connect to backend:
- Verify backend is running at port 8000
- Check CORS settings in `backend/main.py`
- Make sure no firewall is blocking
- Test backend directly: http://localhost:8000/health

## Why This is Real MCP

1. ✅ **Official SDK** - Uses `mcp` package from Anthropic
2. ✅ **FastMCP** - Official server implementation
3. ✅ **@mcp.tool() Decorator** - Follows MCP spec
4. ✅ **SSE Transport** - Mounted at `/mcp` endpoint
5. ✅ **Tool Discovery** - MCP protocol handles tool listing
6. ✅ **Protocol Compliant** - Follows modelcontextprotocol.io spec

## Tech Stack

- **Frontend:** React + Vite
- **Backend:** FastAPI + Python
- **MCP:** FastMCP (official SDK)
- **LLM:** Groq (Llama 3.3 70B)
- **Integration:** SailPoint IdentityIQ REST API with OAuth 2.0


## References

- MCP Specification: https://modelcontextprotocol.io
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Groq API: https://console.groq.com
