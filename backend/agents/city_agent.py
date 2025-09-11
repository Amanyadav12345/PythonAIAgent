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
        """Get all cities from API with embedded district/state data"""
        params = {
            "max_results": "1000",
            "embedded": json.dumps({
                "district": 1,
                "district.state": 1
            })
        }
        
        response = await self._make_request("GET", "", params=params)
        
        if response.success and response.data:
            cities_data = response.data
            processed_cities = []
            
            if isinstance(cities_data, dict) and "_items" in cities_data:
                items = cities_data["_items"]
                for city in items:
                    processed_cities.append({
                        "id": city.get('_id', ''),
                        "name": city.get('name', ''),
                        "state": city.get('district', {}).get('state', {}).get('name', 'Unknown') if isinstance(city.get('district'), dict) else 'Unknown',
                        "district": city.get('district', {}).get('name', 'Unknown') if isinstance(city.get('district'), dict) else 'Unknown'
                    })
                
                response.data = {
                    "cities": processed_cities,
                    "total_count": len(processed_cities)
                }
        
        return response
    
    async def _search_city_by_name(self, city_name: str) -> APIResponse:
        """Search for cities by name using MongoDB regex query"""
        city_name_clean = city_name.strip().lower()
        
        # Create MongoDB regex query for case-insensitive search starting with city name
        where_query = {
            "name": {
                "$regex": f"^{city_name_clean}",
                "$options": "i"
            }
        }
        
        embedded_query = {
            "district": 1,
            "district.state": 1
        }
        
        # URL encode the parameters as shown in the API example
        params = {
            "where": json.dumps(where_query),
            "embedded": json.dumps(embedded_query),
            "projection": json.dumps({})
        }
        
        response = await self._make_request("GET", "", params=params)
        
        if response.success and response.data:
            cities_data = response.data
            processed_cities = []
            
            if isinstance(cities_data, dict) and "_items" in cities_data:
                items = cities_data["_items"]
                
                # Process all matching cities from regex search
                for city in items:
                    city_name_from_api = city.get('name', '').strip()
                    city_id_from_api = city.get('_id', '')
                    
                    if city_name_from_api and city_id_from_api:
                        # Check if it's an exact match
                        is_exact_match = city_name_from_api.lower() == city_name_clean
                        
                        processed_cities.append({
                            "id": city_id_from_api,
                            "name": city_name_from_api,
                            "matched": is_exact_match,
                            "state": self._extract_state_name(city),
                            "district": self._extract_district_name(city)
                        })
                
                # Sort by exact match first, then alphabetically
                processed_cities.sort(key=lambda x: (not x["matched"], x["name"]))
                
                # Check if we have exact matches
                exact_matches = [city for city in processed_cities if city.get("matched", False)]
                partial_matches = [city for city in processed_cities if not city.get("matched", False)]
                
                if exact_matches:
                    # Exact match found
                    response.data = {
                        "cities": processed_cities,
                        "query": city_name,
                        "total_found": len(processed_cities),
                        "match_type": "exact",
                        "exact_match": exact_matches[0],
                        "confirmation_needed": False
                    }
                elif partial_matches:
                    # Only partial matches found - need user confirmation
                    response.data = {
                        "cities": processed_cities,
                        "query": city_name,
                        "total_found": len(processed_cities),
                        "match_type": "partial",
                        "suggestions": partial_matches[:3],  # Top 3 suggestions
                        "confirmation_needed": True,
                        "confirmation_message": f"No exact match found for '{city_name}'. Did you mean one of these cities?",
                        "suggested_city": partial_matches[0] if partial_matches else None
                    }
                else:
                    # No matches
                    response.data = {
                        "cities": [],
                        "query": city_name,
                        "total_found": 0,
                        "match_type": "none",
                        "confirmation_needed": False,
                        "error_message": f"No cities found matching '{city_name}'"
                    }
            else:
                # No results found
                response.data = {
                    "cities": [],
                    "query": city_name,
                    "total_found": 0
                }
        
        return response
    
    async def _get_city_by_id(self, city_id: str) -> APIResponse:
        """Get specific city by ID"""
        return await self._make_request("GET", f"/{city_id}")
    
    def _extract_state_name(self, city_data: Dict[str, Any]) -> str:
        """Extract state name from city data"""
        try:
            district = city_data.get('district', {})
            if isinstance(district, dict):
                state = district.get('state', {})
                if isinstance(state, dict):
                    return state.get('name', 'Unknown')
            return 'Unknown'
        except Exception:
            return 'Unknown'
    
    def _extract_district_name(self, city_data: Dict[str, Any]) -> str:
        """Extract district name from city data"""
        try:
            district = city_data.get('district', {})
            if isinstance(district, dict):
                return district.get('name', 'Unknown')
            return 'Unknown'
        except Exception:
            return 'Unknown'
    
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
        """Convenience method to get city ID by name with exact match priority"""
        response = await self.execute(APIIntent.SEARCH, {"city_name": city_name})
        
        if response.success and response.data:
            # Check if exact match found
            if response.data.get("match_type") == "exact":
                exact_match = response.data.get("exact_match")
                if exact_match:
                    return exact_match["id"]
            
            # If only partial matches, return None to indicate confirmation needed
            elif response.data.get("confirmation_needed", False):
                return None
                
            # Fallback for backward compatibility
            cities = response.data.get("cities", [])
            if cities and len(cities) > 0:
                return cities[0]["id"]
        
        return None
    
    async def get_city_with_confirmation_check(self, city_name: str) -> Dict[str, Any]:
        """
        Get city information with confirmation logic
        Returns structured response indicating if confirmation is needed
        """
        response = await self.execute(APIIntent.SEARCH, {"city_name": city_name})
        
        if response.success and response.data:
            return {
                "success": True,
                "match_type": response.data.get("match_type", "unknown"),
                "confirmation_needed": response.data.get("confirmation_needed", False),
                "exact_match": response.data.get("exact_match"),
                "suggestions": response.data.get("suggestions", []),
                "confirmation_message": response.data.get("confirmation_message", ""),
                "suggested_city": response.data.get("suggested_city"),
                "total_found": response.data.get("total_found", 0)
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_needed": False
            }
    
    def confirm_city_selection(self, suggested_city: Dict[str, Any]) -> str:
        """
        Confirm city selection and return the city ID
        This method is called after user confirms they want the suggested city
        """
        if suggested_city and "id" in suggested_city:
            return suggested_city["id"]
        return None