"""
City Agent - Handles city-related API operations
Purpose: Search, list, and manage city data
"""
from typing import Dict, Any, List, Optional
import json
import urllib.parse
from .base_agent import BaseAPIAgent, APIIntent, APIResponse

class CityAgent(BaseAPIAgent):
    """
    Specialized agent for city API operations
    
    Supported Operations:
    - LIST: Get all cities
    - SEARCH: Search cities by name or criteria
    - READ: Get specific city by ID
    """
    
    def __init__(self, base_url: str, auth_config: Dict[str, str]):
        super().__init__(name="CityAgent", base_url=base_url, auth_config=auth_config)
        self.rate_limit_delay = 5.0  # 5 seconds as per original code
        
    def get_supported_intents(self) -> List[APIIntent]:
        return [APIIntent.LIST, APIIntent.SEARCH, APIIntent.READ]
    
    def validate_payload(self, intent: APIIntent, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate payload for city operations"""
        if intent == APIIntent.SEARCH:
            if "city_name" not in data:
                return False, "city_name is required for SEARCH intent"
            if not isinstance(data["city_name"], str):
                return False, "city_name must be a string"
        elif intent == APIIntent.READ:
            if "city_id" not in data:
                return False, "city_id is required for READ intent"
        # LIST intent doesn't require specific data
        return True, None
    
    async def handle_intent(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Handle city-specific intents"""
        
        if intent == APIIntent.LIST:
            return await self._list_all_cities()
        elif intent == APIIntent.SEARCH:
            return await self._search_city_by_name(data["city_name"])
        elif intent == APIIntent.READ:
            return await self._get_city_by_id(data["city_id"])
        else:
            return APIResponse(
                success=False,
                error=f"Intent {intent.value} not implemented",
                agent_name=self.name
            )
    
    async def _list_all_cities(self) -> APIResponse:
        """Get all cities from API"""
        return await self._make_request("GET", "", params=None)
    
    async def _search_city_by_name(self, city_name: str) -> APIResponse:
        """Search for cities by name using MongoDB-style WHERE clause"""
        # Create WHERE query for exact name matching
        where_query = {
            "name": city_name.title()  # Try title case first
        }
        
        # URL encode the JSON query
        where_param = urllib.parse.quote(json.dumps(where_query))
        params = {"where": where_param}
        
        response = await self._make_request("GET", "", params=params)
        
        if response.success and response.data:
            # Process response to extract city information
            cities_data = response.data
            processed_cities = []
            
            if isinstance(cities_data, dict) and "_items" in cities_data:
                items = cities_data["_items"]
                for city in items:
                    city_name_from_api = city.get('name', '').strip()
                    city_id_from_api = city.get('_id', '')
                    
                    if city_name_from_api.lower() == city_name.lower():
                        processed_cities.append({
                            "id": city_id_from_api,
                            "name": city_name_from_api,
                            "matched": True
                        })
                        break
                
                response.data = {
                    "cities": processed_cities,
                    "query": city_name,
                    "total_found": len(processed_cities)
                }
        
        return response
    
    async def _get_city_by_id(self, city_id: str) -> APIResponse:
        """Get specific city by ID"""
        return await self._make_request("GET", f"/{city_id}")
    
    def extract_city_mapping(self, response_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract name -> id mapping from API response"""
        mapping = {}
        
        if isinstance(response_data, list):
            for city in response_data:
                city_name = city.get('name', '').strip()
                city_id = city.get('id') or city.get('_id', '')
                if city_name and city_id:
                    mapping[city_name.lower().strip()] = str(city_id)
        
        elif isinstance(response_data, dict):
            if "_items" in response_data:
                for city in response_data["_items"]:
                    city_name = city.get('name', '').strip()
                    city_id = city.get('_id') or city.get('id', '')
                    if city_name and city_id:
                        mapping[city_name.lower().strip()] = str(city_id)
            else:
                for key, value in response_data.items():
                    if isinstance(value, dict):
                        city_name = value.get('name') or key
                        city_id = value.get('id') or value.get('_id', key)
                        if city_name and city_id:
                            mapping[city_name.lower().strip()] = str(city_id)
        
        return mapping
    
    async def get_city_id_by_name(self, city_name: str) -> Optional[str]:
        """Convenience method to get city ID by name"""
        response = await self.execute(APIIntent.SEARCH, {"city_name": city_name})
        
        if response.success and response.data:
            cities = response.data.get("cities", [])
            if cities and len(cities) > 0:
                return cities[0]["id"]
        
        return None