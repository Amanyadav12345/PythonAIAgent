"""
Authentication Agent - Handles login and authentication operations
Purpose: Authenticate users and provide tokens for other agents
"""
from typing import Dict, Any, List, Optional, Tuple
import json
import urllib.parse
import base64
from .base_agent import BaseAPIAgent, APIIntent, APIResponse

class AuthAgent(BaseAPIAgent):
    """
    Specialized agent for authentication operations
    
    Supported Operations:
    - VALIDATE: Authenticate user with username/password
    - READ: Get user details by token
    """
    
    def __init__(self, base_url: str):
        # Initialize without auth_config since this agent handles authentication
        super().__init__(name="AuthAgent", base_url=base_url, auth_config={})
        self.rate_limit_delay = 1.0  # 1 second for auth operations
        self.authenticated_users = {}  # Cache authenticated users
        
    def get_supported_intents(self) -> List[APIIntent]:
        return [APIIntent.VALIDATE, APIIntent.READ]
    
    def validate_payload(self, intent: APIIntent, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate payload for authentication operations"""
        if intent == APIIntent.VALIDATE:
            if "username" not in data:
                return False, "username is required for VALIDATE intent"
            if "password" not in data:
                return False, "password is required for VALIDATE intent"
            if not isinstance(data["username"], str) or not isinstance(data["password"], str):
                return False, "username and password must be strings"
        elif intent == APIIntent.READ:
            if "token" not in data and "user_id" not in data:
                return False, "token or user_id is required for READ intent"
        
        return True, None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Override: Auth agent doesn't use standard auth headers"""
        return {"Content-Type": "application/json"}
    
    async def handle_intent(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Handle authentication-specific intents"""
        
        if intent == APIIntent.VALIDATE:
            return await self._authenticate_user(data["username"], data["password"])
        elif intent == APIIntent.READ:
            return await self._get_user_details(data)
        else:
            return APIResponse(
                success=False,
                error=f"Intent {intent.value} not implemented",
                agent_name=self.name
            )
    
    async def _authenticate_user(self, username: str, password: str) -> APIResponse:
        """
        Authenticate user using the persons/authenticate API
        URL: /persons/authenticate?page=1&max_results=10&where={"$or":[{"username":"917340224449"},{"password":"12345"}]}
        """
        try:
            # Build the WHERE query as per API specification
            where_query = {
                "$or": [
                    {"username": username},
                    {"password": password}
                ]
            }
            
            # URL encode the JSON query
            where_param = urllib.parse.quote(json.dumps(where_query))
            
            # Build query parameters
            params = {
                "page": "1",
                "max_results": "10", 
                "where": where_param
            }
            
            # Create basic auth header using username:password
            credentials = f"{username}:{password}"
            credentials_b64 = base64.b64encode(credentials.encode()).decode()
            headers = {
                "Authorization": f"Basic {credentials_b64}",
                "Content-Type": "application/json"
            }
            
            # Make the authentication request
            import httpx
            import asyncio
            
            start_time = asyncio.get_event_loop().time()
            await self._enforce_rate_limit()
            
            url = f"{self.base_url.rstrip('/')}/persons/authenticate"
            
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                if response.status_code == 200:
                    auth_data = response.json()
                    
                    # Extract authentication details from response
                    if auth_data.get("ok") and auth_data.get("token"):
                        user_record = auth_data.get("user_record", {})
                        token = auth_data.get("token")
                        user_id = user_record.get("_id")
                        
                        # Cache the authenticated user
                        auth_info = {
                            "token": token,
                            "user_id": user_id,
                            "username": username,
                            "user_record": user_record,
                            "auth_header": f"Basic {credentials_b64}",
                            "credentials_b64": credentials_b64
                        }
                        
                        self.authenticated_users[username] = auth_info
                        self.authenticated_users[user_id] = auth_info
                        self.authenticated_users[token] = auth_info
                        
                        return APIResponse(
                            success=True,
                            data={
                                "authenticated": True,
                                "token": token,
                                "user_id": user_id,
                                "user_record": user_record,
                                "auth_header": f"Basic {credentials_b64}",
                                "credentials_b64": credentials_b64,
                                "username": username,
                                "name": user_record.get("name"),
                                "email": user_record.get("email"),
                                "phone": user_record.get("phone"),
                                "current_company": user_record.get("current_company"),
                                "role_names": user_record.get("role_names", []),
                                "user_type": user_record.get("user_type"),
                                "status_text": auth_data.get("statusText", "Successfully Logged In!")
                            },
                            status_code=response.status_code,
                            agent_name=self.name,
                            execution_time=execution_time,
                            sources=[url]
                        )
                    else:
                        return APIResponse(
                            success=False,
                            error="Authentication failed: Invalid response format",
                            status_code=response.status_code,
                            agent_name=self.name,
                            execution_time=execution_time,
                            sources=[url]
                        )
                else:
                    error_text = response.text if response.content else "Authentication failed"
                    return APIResponse(
                        success=False,
                        error=f"Authentication failed: HTTP {response.status_code} - {error_text}",
                        status_code=response.status_code,
                        agent_name=self.name,
                        execution_time=execution_time,
                        sources=[url]
                    )
                    
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Authentication error: {str(e)}",
                agent_name=self.name
            )
    
    async def _get_user_details(self, data: Dict[str, Any]) -> APIResponse:
        """Get user details from cached authentication data"""
        lookup_key = data.get("token") or data.get("user_id")
        
        if lookup_key in self.authenticated_users:
            auth_info = self.authenticated_users[lookup_key]
            return APIResponse(
                success=True,
                data={
                    "user_found": True,
                    "user_record": auth_info["user_record"],
                    "token": auth_info["token"],
                    "user_id": auth_info["user_id"],
                    "username": auth_info["username"],
                    "auth_header": auth_info["auth_header"]
                },
                agent_name=self.name
            )
        else:
            return APIResponse(
                success=False,
                error="User not found in authenticated users cache",
                agent_name=self.name
            )
    
    def get_auth_token_for_user(self, username: str) -> Optional[str]:
        """Get auth token for a specific user"""
        if username in self.authenticated_users:
            return self.authenticated_users[username]["token"]
        return None
    
    def get_basic_auth_header_for_user(self, username: str) -> Optional[str]:
        """Get Basic Auth header for a specific user"""
        if username in self.authenticated_users:
            return self.authenticated_users[username]["auth_header"]
        return None
    
    def get_credentials_b64_for_user(self, username: str) -> Optional[str]:
        """Get base64 encoded credentials for a specific user"""
        if username in self.authenticated_users:
            return self.authenticated_users[username]["credentials_b64"]
        return None
    
    def is_user_authenticated(self, username: str) -> bool:
        """Check if user is authenticated"""
        return username in self.authenticated_users
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get complete user information"""
        if username in self.authenticated_users:
            return self.authenticated_users[username]
        return None
    
    def logout_user(self, username: str) -> bool:
        """Remove user from authenticated users cache"""
        if username in self.authenticated_users:
            auth_info = self.authenticated_users[username]
            
            # Remove all references to this user
            keys_to_remove = [
                username,
                auth_info.get("user_id"),
                auth_info.get("token")
            ]
            
            for key in keys_to_remove:
                if key and key in self.authenticated_users:
                    del self.authenticated_users[key]
            
            return True
        return False
    
    def clear_all_auth_cache(self):
        """Clear all authenticated users cache"""
        self.authenticated_users.clear()
    
    async def authenticate_and_get_auth_header(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Convenience method to authenticate and return auth header
        Returns: (success, auth_header, user_info)
        """
        response = await self.execute(APIIntent.VALIDATE, {
            "username": username,
            "password": password
        })
        
        if response.success and response.data:
            auth_header = response.data.get("auth_header")
            user_info = {
                "user_id": response.data.get("user_id"),
                "token": response.data.get("token"),
                "name": response.data.get("name"),
                "email": response.data.get("email"),
                "current_company": response.data.get("current_company"),
                "user_record": response.data.get("user_record")
            }
            return True, auth_header, user_info
        else:
            return False, None, None