"""
SailPoint IIQ API Integration with OAuth 2.0
"""

import requests
import logging
import base64
from typing import Dict, Any
from datetime import datetime
from config import SAILPOINT_API_URL, SAILPOINT_CLIENT_ID, SAILPOINT_CLIENT_SECRET

logger = logging.getLogger(__name__)


class SailPointAPI:
    """SailPoint IdentityIQ API Client with OAuth 2.0"""
    
    def __init__(self):
        logger.info("Initializing SailPoint API client...")
        self.base_url = SAILPOINT_API_URL
        self.client_id = SAILPOINT_CLIENT_ID
        self.client_secret = SAILPOINT_CLIENT_SECRET
        self.access_token = None
        
        logger.info(f"SailPoint API URL: {self.base_url}")
        if self.client_id:
            logger.info(f"Client ID: {self.client_id[:10]}...")
        
        # Get OAuth token
        self._get_oauth_token()
        logger.info("SailPoint API client initialized")
    
    def _get_oauth_token(self):
        """Get OAuth 2.0 access token"""
        logger.info("Getting OAuth token...")
        
        token_url = f"{self.base_url}/identityiq/oauth2/token?grant_type=client_credentials"
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded}'
        }
        
        try:
            response = requests.post(token_url, headers=headers, data="")
            if response.status_code == 200:
                self.access_token = response.json().get('access_token')
                logger.info("[OK] OAuth token obtained")
            else:
                logger.error(f"[ERROR] Token failed: {response.status_code}")
                self.access_token = None
        except Exception as e:
            logger.error(f"[ERROR] Token exception: {str(e)}")
            self.access_token = None
    
    def _get_headers(self):
        """Get API headers"""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Check request status - placeholder (dummy implementation, no API URL available)"""
        logger.info(f"[API] get_request_status: {request_id} (placeholder)")
        
        return {
            "success": False,
            "message": "This is a placeholder - API endpoint not yet configured",
            "request_id": request_id,
            "note": "check_request_status is a dummy tool - no SailPoint API URL available"
        }
    
    def trigger_refresh(self, user_id: str) -> Dict[str, Any]:
        """Trigger identity refresh for a specific user using REAL SailPoint endpoint"""
        logger.info(f"[API] trigger_refresh: {user_id}")
        
        if not self.access_token:
            logger.info("[API] Getting fresh OAuth token...")
            self._get_oauth_token()
        
        try:
            # REAL SailPoint Identity Refresh Endpoint
            url = f"{self.base_url}/identityiq/plugin/rest/RefreshIdentity/refreshIdentitySingleUser?userId={user_id}"
            logger.info(f"Calling SailPoint Identity Refresh API: {url}")
            logger.info(f"Refreshing identity for user: {user_id}")
            
            response = requests.get(url, headers=self._get_headers())
            logger.info(f"SailPoint API response status: {response.status_code}")
            
            if response.status_code == 200:
                # Get ACTUAL response from SailPoint
                sailpoint_data = response.json()
                logger.info(f"SailPoint returned data: {sailpoint_data}")
                
                # Use actual SailPoint response structure
                # Expected format: {"message": "...", "userId": "...", "taskStatus": "...", "status": "..."}
                return {
                    "success": sailpoint_data.get("status") == "success",
                    "user_id": sailpoint_data.get("userId", user_id),
                    "message": sailpoint_data.get("message", f"Identity refresh triggered for {user_id}"),
                    "task_status": sailpoint_data.get("taskStatus", "Unknown"),
                    "sailpoint_response": sailpoint_data,  # ACTUAL API RESPONSE
                    "api_endpoint": url,
                    "timestamp": datetime.now().isoformat()
                }
            elif response.status_code == 401:
                # Token expired - get new one and retry
                logger.warning("[WARNING] 401 Unauthorized - refreshing token and retrying...")
                self._get_oauth_token()
                
                response = requests.get(url, headers=self._get_headers())
                if response.status_code == 200:
                    sailpoint_data = response.json()
                    logger.info(f"SailPoint returned data (retry): {sailpoint_data}")
                    
                    # Use actual SailPoint response structure
                    return {
                        "success": sailpoint_data.get("status") == "success",
                        "user_id": sailpoint_data.get("userId", user_id),
                        "message": sailpoint_data.get("message", f"Identity refresh triggered for {user_id}"),
                        "task_status": sailpoint_data.get("taskStatus", "Unknown"),
                        "sailpoint_response": sailpoint_data,  # ACTUAL API RESPONSE
                        "api_endpoint": url,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Retry failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "user_id": user_id,
                        "message": f"Authentication failed: {response.status_code}",
                        "error_details": response.text,
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                logger.error(f"SailPoint API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "user_id": user_id,
                    "message": f"API error: {response.status_code}",
                    "error_details": response.text,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Exception calling SailPoint: {str(e)}")
            return {
                "success": False,
                "user_id": user_id,
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_identity(self, user_id: str) -> Dict[str, Any]:
        """Get identity info - placeholder (dummy implementation, no API URL available)"""
        logger.info(f"[API] get_identity: {user_id} (placeholder)")
        
        return {
            "success": False,
            "message": "This is a placeholder - API endpoint not yet configured",
            "user_id": user_id,
            "note": "get_identity_info is a dummy tool - no SailPoint API URL available"
        }


class SailPointAPIClient:
    """
    MCP-safe wrapper for SailPoint API.
    Only exposes API methods - NO credentials, token endpoint, or token retrieval methods.
    This class is what gets passed to MCP server.
    MCP is unaware that token retrieval exists or how tokens are obtained.
    """
    
    def __init__(self, sailpoint_api_instance: SailPointAPI):
        """
        Initialize with authenticated SailPointAPI instance.
        MCP receives only API methods - no credentials or token endpoint access.
        
        Args:
            sailpoint_api_instance: Fully authenticated SailPointAPI instance (with token already obtained by backend)
        """
        self._api = sailpoint_api_instance  # Private reference - MCP cannot access internal methods
        self.base_url = sailpoint_api_instance.base_url  # Only base URL, NOT token endpoint
        
        logger.info("[MCP Client] SailPointAPIClient initialized")
        logger.info("[MCP Client] MCP has access to: API methods only")
        logger.info("[MCP Client] MCP does NOT have access to: credentials, token endpoint, or token retrieval methods")
    
    def trigger_refresh(self, user_id: str) -> Dict[str, Any]:
        """
        Trigger identity refresh - MCP-safe method.
        Token refresh happens internally in SailPointAPI if needed.
        MCP is unaware of token retrieval process.
        """
        return self._api.trigger_refresh(user_id)
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """
        Check request status - MCP-safe method.
        Token refresh happens internally in SailPointAPI if needed.
        """
        return self._api.get_request_status(request_id)
    
    def get_identity(self, user_id: str) -> Dict[str, Any]:
        """
        Get identity info - MCP-safe method.
        Token refresh happens internally in SailPointAPI if needed.
        """
        return self._api.get_identity(user_id)
