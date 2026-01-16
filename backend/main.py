from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import json
import traceback
import os
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file FIRST (before importing config)
load_dotenv()

from mcp_server import mcp, set_sailpoint_api
from sailpoint_api import SailPointAPI, SailPointAPIClient
from config import (
    GROQ_API_KEY, GROQ_MODEL,
    ALLOWED_ORIGINS, LLM_TEMPERATURE, LLM_MAX_TOKENS
)

# Configure logging - write everything to file
import sys
from logging.config import dictConfig

# Get absolute path for log file (ensure it's always in backend directory)
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sailpoint_bot.log')

# Configure logging using dictConfig (uvicorn respects this)
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "simple": {
            "format": "%(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": log_file_path,
            "mode": "a",
            "encoding": "utf-8",
            "formatter": "default",
            "level": "INFO",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["file", "console"],
    },
    "loggers": {
        "uvicorn": {
            "level": "INFO",
            "handlers": ["file", "console"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["file", "console"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["file", "console"],
            "propagate": False,
        },
        "fastapi": {
            "level": "INFO",
            "handlers": ["file", "console"],
            "propagate": False,
        },
        "httpx": {
            "level": "INFO",
            "handlers": ["file", "console"],
            "propagate": False,
        },
    },
}

# Apply logging configuration
dictConfig(LOGGING_CONFIG)

# Get our app logger
logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info(f"LOGGING INITIALIZED - All logs writing to: {log_file_path}")
logger.info("=" * 80)

app = FastAPI(title="SailPoint Support Bot")

# Mount MCP Server - This is REAL MCP!
app.mount("/mcp", mcp.sse_app())

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and responses"""
    start_time = datetime.now()
    
    # Log incoming request
    logger.info("=" * 60)
    logger.info(f"[REQUEST] {request.method} {request.url.path}")
    logger.info(f"[REQUEST] Client: {request.client.host if request.client else 'unknown'}")
    
    try:
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"[RESPONSE] Status: {response.status_code}")
        logger.info(f"[RESPONSE] Time: {process_time:.3f}s")
        logger.info("=" * 60)
        
        return response
    except Exception as e:
        # Log exception
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error("=" * 60)
        logger.error(f"[ERROR] Exception in middleware")
        logger.error(f"[ERROR] Path: {request.method} {request.url.path}")
        logger.error(f"[ERROR] Error: {str(e)}")
        logger.error(f"[ERROR] Time: {process_time:.3f}s")
        logger.exception("Full traceback:")
        logger.error("=" * 60)
        raise

# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions"""
    logger.error("=" * 60)
    logger.error(f"[GLOBAL ERROR] Unhandled exception")
    logger.error(f"[GLOBAL ERROR] Path: {request.method} {request.url.path}")
    logger.error(f"[GLOBAL ERROR] Error type: {type(exc).__name__}")
    logger.error(f"[GLOBAL ERROR] Error message: {str(exc)}")
    logger.exception("Full traceback:")
    logger.error("=" * 60)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "error_type": type(exc).__name__
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning("=" * 60)
    logger.warning(f"[HTTP ERROR] {exc.status_code}: {exc.detail}")
    logger.warning(f"[HTTP ERROR] Path: {request.method} {request.url.path}")
    logger.warning("=" * 60)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning("=" * 60)
    logger.warning(f"[VALIDATION ERROR] Invalid request data")
    logger.warning(f"[VALIDATION ERROR] Path: {request.method} {request.url.path}")
    logger.warning(f"[VALIDATION ERROR] Errors: {exc.errors()}")
    logger.warning("=" * 60)
    
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )

# Initialize clients
groq_client = None
sailpoint_api = None


class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "anonymous"


class ChatResponse(BaseModel):
    response: str
    action_taken: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize Groq client and SailPoint API on startup"""
    global groq_client, sailpoint_api
    # Force write to log file on startup
    logger.info("=" * 60)
    logger.info("Starting SailPoint Support Bot Backend")
    logger.info(f"Log file location: {log_file_path}")
    logger.info("=" * 60)
    # Ensure log is flushed
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.flush()
    
    # Initialize Groq client
    if not GROQ_API_KEY:
        logger.warning("[WARNING] GROQ_API_KEY not found in environment variables")
        logger.warning("Please set GROQ_API_KEY in .env file")
    else:
        try:
            groq_client = Groq(api_key=GROQ_API_KEY)
            logger.info("[OK] Groq client initialized successfully")
            logger.info(f"Using model: {GROQ_MODEL}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Groq client: {str(e)}")
    
    # Initialize SailPoint API (authentication happens here with secrets)
    try:
        # Backend handles token retrieval with client_id and secret
        sailpoint_api = SailPointAPI()
        logger.info("[OK] SailPoint API authenticated successfully")
        logger.info("[OK] Token obtained and stored in memory by backend")
        
        # Create MCP-safe wrapper (only token and API methods, no credentials or token endpoint)
        mcp_client = SailPointAPIClient(sailpoint_api)
        logger.info("[OK] MCP-safe client created (token + API endpoints only)")
        
        # Pass wrapper to MCP server (MCP never sees credentials or token endpoint)
        set_sailpoint_api(mcp_client)
        logger.info("[OK] MCP client passed to MCP server (no credentials or token endpoint exposed)")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize SailPoint API: {str(e)}")
        logger.warning("[WARNING] MCP tools will not work without SailPoint API authentication")
    
    logger.info("MCP Server mounted at /mcp endpoint")
    logger.info("MCP Tools: trigger_identity_refresh, check_request_status, get_identity_info")
    logger.info("Backend ready to accept requests")


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "status": "active",
        "service": "SailPoint Support Bot",
        "version": "1.0.0"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Main chat endpoint that processes user messages with LLM + MCP tools
    """
    logger.info("=" * 60)
    logger.info(f"[MSG] New chat message received")
    logger.info(f"User ID: {message.user_id}")
    logger.info(f"Message: {message.message}")
    logger.info("=" * 60)
    
    if not groq_client:
        logger.error("[ERROR] Groq client not initialized")
        raise HTTPException(status_code=500, detail="LLM client not initialized")
    
    try:
        logger.info("[LLM] Processing message with Groq Function Calling (MCP pattern)...")
        
        # Get MCP tool definitions - these are from the REAL MCP server
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "trigger_identity_refresh",
                    "description": "Trigger identity refresh in SailPoint IIQ when user can't access after approval, colleagues have access but they don't, or dynamic access not working. Extract the username from the user's message.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "The username/user_id extracted from the message (e.g., 'Ram', 'Aaron.Nichols', 'John.Smith'). Look for names mentioned in the message."
                            },
                            "reason": {
                                "type": "string",
                                "description": "Brief reason why refresh is needed (e.g., 'Dynamic access not provisioned', 'Approved but can't access')"
                            }
                        },
                        "required": ["user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_request_status",
                    "description": "Check access request status in SailPoint IIQ",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "request_id": {"type": "string", "description": "Request ID or user ID"}
                        },
                        "required": ["request_id"]
                    }
                }
            }
        ]
        
        logger.info(f"[MCP] Loaded {len(tools)} tools from MCP server")
        
        system_prompt = """You are a SailPoint IIQ L1 support assistant.

When users report access issues:
1. EXTRACT the username/user_id from the message (e.g., "User Ram", "Aaron.Nichols", "John Smith")
2. Decide if identity refresh is needed
3. Call trigger_identity_refresh with the extracted user_id

Examples:
- "User Ram can't login" -> Extract: user_id="Ram"
- "Aaron.Nichols doesn't have access" -> Extract: user_id="Aaron.Nichols"  
- "My colleague John Smith" -> Extract: user_id="John.Smith"

Common scenarios needing identity_refresh:
- Colleagues have access but this user doesn't
- Dynamic access not working
- Should have auto-provisioned but didn't
- Role based access not working

Be direct and helpful."""

        logger.info("Calling Groq API with function calling...")
        
        # First LLM call - let it decide if tool is needed
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message.message}
            ],
            tools=tools,
            tool_choice="auto",
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS
        )
        
        assistant_message = response.choices[0].message
        llm_response = ""
        action_taken = None
        
        # Check if LLM wants to call a tool
        if assistant_message.tool_calls:
            logger.info(f"[TOOL] LLM decided to call tool: {assistant_message.tool_calls[0].function.name}")
            
            tool_call = assistant_message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            logger.info(f"[TOOL] Function: {function_name}")
            logger.info(f"[TOOL] Arguments: {function_args}")
            
            # Execute the MCP tool via the actual MCP server
            logger.info(f"[MCP] Calling MCP server tool: {function_name}")
            
            # Use user_id from function args if provided, otherwise from message
            tool_user_id = function_args.get("user_id", message.user_id)
            
            # Call the actual MCP tool function
            if function_name == "trigger_identity_refresh":
                from mcp_server import trigger_identity_refresh
                action_result = trigger_identity_refresh(
                    user_id=tool_user_id,
                    reason=function_args.get("reason", "User access issue")
                )
                action_taken = "identity_refresh_triggered"
                
                # Format response with SailPoint data
                sailpoint_data = action_result.get('sailpoint_response', {})
                task_status = action_result.get('task_status', sailpoint_data.get('taskStatus', 'Unknown'))
                sailpoint_message = action_result.get('message', sailpoint_data.get('message', 'Identity refresh triggered'))
                
                # Use actual SailPoint response message
                llm_response = f"""{sailpoint_message}

Task Status: {task_status}

Please wait 2-3 minutes and try accessing the application again.

SailPoint IIQ API Response:
{json.dumps(sailpoint_data, indent=2)}"""
                
            elif function_name == "check_request_status":
                from mcp_server import check_request_status
                action_result = check_request_status(request_id=tool_user_id)
                action_taken = "status_check"
                
                sailpoint_data = action_result.get('sailpoint_response', {})
                sailpoint_json = json.dumps(sailpoint_data, indent=2)
                llm_response = f"Request Status: {action_result.get('status', 'unknown')}\n\nSailPoint IIQ API Response:\n\n{sailpoint_json}"
                
            elif function_name == "get_identity_info":
                from mcp_server import get_identity_info
                action_result = get_identity_info(user_id=tool_user_id)
                action_taken = "identity_info"
                
                sailpoint_data = action_result.get('sailpoint_response', {})
                sailpoint_json = json.dumps(sailpoint_data, indent=2)
                llm_response = f"Identity Information:\n\nSailPoint IIQ API Response:\n\n{sailpoint_json}"
                
            else:
                action_result = {"error": "Unknown tool"}
                action_taken = None
                llm_response = f"Tool '{function_name}' not recognized"
        
        else:
            # No tool needed - LLM provided direct response
            logger.info("[LLM] No tool call needed - using LLM response")
            llm_response = assistant_message.content
            action_taken = None
        
        logger.info("=" * 60)
        logger.info(f"[RESPONSE] Sending response to user")
        logger.info(f"Action taken: {action_taken or 'None'}")
        logger.info(f"Response length: {len(llm_response)} chars")
        logger.info("=" * 60)
        
        return ChatResponse(
            response=llm_response,
            action_taken=action_taken
        )
        
    except Exception as e:
        # Ensure error is logged to file
        logger.error("=" * 60)
        logger.error(f"[ERROR] Error processing chat request")
        logger.error(f"[ERROR] Error type: {type(e).__name__}")
        logger.error(f"[ERROR] Error message: {str(e)}")
        logger.exception("Full traceback:")
        logger.error("=" * 60)
        
        # Force flush log file
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
        
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check endpoint accessed")
    
    groq_status = "active" if groq_client else "inactive"
    logger.info(f"Groq client status: {groq_status}")
    
    return {
        "status": "healthy",
        "mcp_server": "active",
        "mcp_endpoint": "/mcp",
        "mcp_note": "MCP endpoint uses SSE transport - not accessible via browser",
        "groq_client": groq_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/mcp/status")
async def mcp_status():
    """MCP server status endpoint (for verification)"""
    logger.info("MCP status endpoint accessed")
    
    return {
        "mcp_server": "active",
        "endpoint": "/mcp",
        "transport": "SSE (Server-Sent Events)",
        "tools": [
            "trigger_identity_refresh",
            "check_request_status",
            "get_identity_info"
        ],
        "note": "The /mcp endpoint is for MCP protocol communication, not direct browser access"
    }
