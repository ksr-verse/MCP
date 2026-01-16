"""
Real MCP Server using FastMCP from official SDK
Exposes SailPoint IIQ operations as MCP tools
"""

import logging
from mcp.server.fastmcp import FastMCP
from typing import Optional

logger = logging.getLogger(__name__)

# MCP-safe SailPoint API client (set by backend, no credentials or token endpoint access)
# This is a wrapper that only exposes API methods - backend handles token retrieval
sailpoint_api: Optional[object] = None

# Create FastMCP server - This is REAL MCP!
mcp = FastMCP("SailPoint IIQ Server")


def set_sailpoint_api(api_client):
    """
    Set the MCP-safe SailPoint API client.
    Called by backend (main.py) after backend obtains token.
    
    This wrapper ensures:
    - MCP only receives token (already obtained by backend)
    - MCP only has access to API methods (trigger_refresh, get_request_status, get_identity)
    - MCP does NOT have access to:
      - Client ID / Secret
      - Token endpoint URL
      - Token retrieval methods
      - Any credential information
    
    Backend handles token retrieval separately - MCP is unaware of this process.
    """
    global sailpoint_api
    sailpoint_api = api_client
    logger.info("[MCP] MCP-safe API client set (no credentials or token endpoint exposed)")
    logger.info("[MCP] MCP can only call API methods - token retrieval handled by backend")


@mcp.tool()
def trigger_identity_refresh(user_id: str, reason: str = "User access issue") -> dict:
    """
    Trigger an identity refresh/aggregation task in SailPoint IIQ for a specific user.
    
    Use this when:
    - User mentions colleagues have access but they don't  
    - Dynamic access is not working
    - Access should have been automatically provisioned but wasn't
    
    The user_id should be extracted from the user's message. For example:
    - "User Ram can't access" -> user_id = "Ram" or "ram"
    - "Aaron.Nichols doesn't have access" -> user_id = "Aaron.Nichols"
    - "My colleague John Smith has issues" -> user_id = "John.Smith" or "john.smith"
    
    Args:
        user_id: The user ID/username who needs the identity refresh (e.g., "Aaron.Nichols", "Ram", "john.smith")
        reason: Brief reason why the refresh is needed
    
    Returns:
        Dictionary with the result from SailPoint IIQ including actual API response
    """
    if not sailpoint_api:
        logger.error("[MCP TOOL] SailPoint API not initialized - authentication required")
        return {
            "success": False,
            "message": "SailPoint API not authenticated. Please check backend configuration.",
            "error": "API instance not set"
        }
    
    logger.info(f"[MCP TOOL] trigger_identity_refresh called")
    logger.info(f"[MCP TOOL] User: {user_id}, Reason: {reason}")
    
    result = sailpoint_api.trigger_refresh(user_id)
    
    logger.info(f"[MCP TOOL] Result: {result.get('success', False)}")
    
    return result


@mcp.tool()
def check_request_status(request_id: str) -> dict:
    """
    Check the status of an access request in SailPoint IIQ.
    
    Args:
        request_id: The access request ID or user ID to check
    
    Returns:
        Dictionary with the request status from SailPoint IIQ
    """
    if not sailpoint_api:
        logger.error("[MCP TOOL] SailPoint API not initialized - authentication required")
        return {
            "success": False,
            "message": "SailPoint API not authenticated. Please check backend configuration.",
            "error": "API instance not set"
        }
    
    logger.info(f"[MCP TOOL] check_request_status called")
    logger.info(f"[MCP TOOL] Request ID: {request_id}")
    
    result = sailpoint_api.get_request_status(request_id)
    
    logger.info(f"[MCP TOOL] Status: {result.get('status', 'unknown')}")
    
    return result


@mcp.tool()
def get_identity_info(user_id: str) -> dict:
    """
    Get detailed identity information from SailPoint IIQ.
    
    Args:
        user_id: The user ID to get information about
    
    Returns:
        Dictionary with identity details from SailPoint IIQ
    """
    if not sailpoint_api:
        logger.error("[MCP TOOL] SailPoint API not initialized - authentication required")
        return {
            "success": False,
            "message": "SailPoint API not authenticated. Please check backend configuration.",
            "error": "API instance not set"
        }
    
    logger.info(f"[MCP TOOL] get_identity_info called")
    logger.info(f"[MCP TOOL] User ID: {user_id}")
    
    result = sailpoint_api.get_identity(user_id)
    
    logger.info(f"[MCP TOOL] Identity retrieved: {result.get('success', False)}")
    
    return result
