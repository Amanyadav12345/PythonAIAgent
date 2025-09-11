"""
Base Agent Class for API Operations
Provides common functionality for all specialized API agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import httpx
import asyncio
import logging
import json
import base64
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

class APIIntent(Enum):
    """Define different API operation intents"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    LIST = "list"
    VALIDATE = "validate"

class APIResponse(BaseModel):
    """Standardized API response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    intent: Optional[str] = None
    agent_name: Optional[str] = None
    execution_time: Optional[float] = None
    sources: List[str] = []

class BaseAPIAgent(ABC):
    """
    Base class for all API agents
    Each agent handles specific API endpoints with defined intents
    """
    
    def __init__(self, name: str, base_url: str, auth_config: Dict[str, str]):
        self.name = name
        self.base_url = base_url
        self.auth_config = auth_config
        self.cache = {}
        self.rate_limit_delay = 1.0  # Default 1 second between calls
        self.last_request_time = 0
        
    def get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers"""
        if self.auth_config.get("token"):
            return {
                "Authorization": self.auth_config["token"],
                "Content-Type": "application/json"
            }
        elif self.auth_config.get("username") and self.auth_config.get("password"):
            credentials = f"{self.auth_config['username']}:{self.auth_config['password']}"
            credentials_b64 = base64.b64encode(credentials.encode()).decode()
            return {
                "Authorization": f"Basic {credentials_b64}",
                "Content-Type": "application/json"
            }
        else:
            return {"Content-Type": "application/json"}
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting between API calls"""
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _make_request(self, method: str, endpoint: str, payload: Optional[Dict] = None, 
                          params: Optional[Dict] = None) -> APIResponse:
        """Make HTTP request with error handling and timing"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self._enforce_rate_limit()
            
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            headers = self.get_auth_headers()
            
            logger.info(f"{self.name}: {method} {url}")
            if payload:
                logger.debug(f"{self.name}: Payload: {json.dumps(payload, indent=2)}")
            
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=payload)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=payload)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                logger.info(f"{self.name}: Response status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    data = response.json() if response.content else {}
                    return APIResponse(
                        success=True,
                        data=data,
                        status_code=response.status_code,
                        agent_name=self.name,
                        execution_time=execution_time,
                        sources=[url]
                    )
                else:
                    logger.error(f"{self.name}: API Error {response.status_code}: {response.text}")
                    return APIResponse(
                        success=False,
                        error=f"HTTP {response.status_code}: {response.text}",
                        status_code=response.status_code,
                        agent_name=self.name,
                        execution_time=execution_time,
                        sources=[url]
                    )
                    
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"{self.name}: Request failed: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name=self.name,
                execution_time=execution_time
            )
    
    @abstractmethod
    async def handle_intent(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Handle specific intent - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_supported_intents(self) -> List[APIIntent]:
        """Return list of supported intents for this agent"""
        pass
    
    @abstractmethod
    def validate_payload(self, intent: APIIntent, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate payload for specific intent"""
        pass
    
    def get_cache_key(self, intent: APIIntent, data: Dict[str, Any]) -> str:
        """Generate cache key for request"""
        return f"{self.name}:{intent.value}:{hash(str(sorted(data.items())))}"
    
    def cache_response(self, key: str, response: APIResponse, ttl: int = 300):
        """Cache API response for given TTL (seconds)"""
        import time
        self.cache[key] = {
            "response": response,
            "expires": time.time() + ttl
        }
    
    def get_cached_response(self, key: str) -> Optional[APIResponse]:
        """Get cached response if still valid"""
        import time
        if key in self.cache:
            cached = self.cache[key]
            if time.time() < cached["expires"]:
                logger.info(f"{self.name}: Using cached response")
                return cached["response"]
            else:
                del self.cache[key]
        return None
    
    async def execute(self, intent: APIIntent, data: Dict[str, Any], use_cache: bool = True) -> APIResponse:
        """Execute agent with given intent and data"""
        # Check if intent is supported
        if intent not in self.get_supported_intents():
            return APIResponse(
                success=False,
                error=f"Intent {intent.value} not supported by {self.name}",
                agent_name=self.name,
                intent=intent.value
            )
        
        # Validate payload
        is_valid, error_msg = self.validate_payload(intent, data)
        if not is_valid:
            return APIResponse(
                success=False,
                error=f"Invalid payload: {error_msg}",
                agent_name=self.name,
                intent=intent.value
            )
        
        # Check cache for READ operations
        if use_cache and intent in [APIIntent.READ, APIIntent.SEARCH, APIIntent.LIST]:
            cache_key = self.get_cache_key(intent, data)
            cached_response = self.get_cached_response(cache_key)
            if cached_response:
                cached_response.intent = intent.value
                return cached_response
        
        # Execute the intent
        response = await self.handle_intent(intent, data)
        response.intent = intent.value
        
        # Cache successful READ operations
        if (use_cache and response.success and 
            intent in [APIIntent.READ, APIIntent.SEARCH, APIIntent.LIST]):
            cache_key = self.get_cache_key(intent, data)
            self.cache_response(cache_key, response)
        
        return response