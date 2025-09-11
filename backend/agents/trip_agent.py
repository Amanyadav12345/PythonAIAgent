"""
Trip Agent - Handles trip-related API operations
Purpose: Create, search, and manage trip data
"""
from typing import Dict, Any, List, Optional
import json
import urllib.parse
from .base_agent import BaseAPIAgent, APIIntent, APIResponse

class TripAgent(BaseAPIAgent):
    """
    Specialized agent for trip API operations
    
    Supported Operations:
    - CREATE: Create new trip
    - SEARCH: Search trips by route/criteria
    - READ: Get specific trip by ID
    - LIST: Get all trips
    """
    
    def __init__(self, base_url: str, auth_config: Dict[str, str], 
                 handled_by: str = None, created_by: str = None, 
                 created_by_company: str = None, default_trip_id: str = None):
        super().__init__(name="TripAgent", base_url=base_url, auth_config=auth_config)
        self.rate_limit_delay = 1.0  # 1 second for trip operations
        
        # Default values for trip creation
        self.handled_by = handled_by or "61421a01de5cb316d9ba4b16"
        self.created_by = created_by or "6257f1d75b42235a2ae4ab34"
        self.created_by_company = created_by_company or "62d66794e54f47829a886a1d"
        self.default_trip_id = default_trip_id
        
    def get_supported_intents(self) -> List[APIIntent]:
        return [APIIntent.CREATE, APIIntent.SEARCH, APIIntent.READ, APIIntent.LIST]
    
    def validate_payload(self, intent: APIIntent, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate payload for trip operations"""
        if intent == APIIntent.CREATE:
            # CREATE doesn't require specific data - uses defaults
            pass
        elif intent == APIIntent.SEARCH:
            if not any(key in data for key in ["from_city_id", "to_city_id", "route"]):
                return False, "from_city_id, to_city_id, or route is required for SEARCH intent"
        elif intent == APIIntent.READ:
            if "trip_id" not in data:
                return False, "trip_id is required for READ intent"
        # LIST intent doesn't require specific data
        return True, None
    
    async def handle_intent(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Handle trip-specific intents"""
        
        if intent == APIIntent.CREATE:
            return await self._create_trip(data)
        elif intent == APIIntent.SEARCH:
            return await self._search_trips_by_route(data)
        elif intent == APIIntent.READ:
            return await self._get_trip_by_id(data["trip_id"])
        elif intent == APIIntent.LIST:
            return await self._list_all_trips()
        else:
            return APIResponse(
                success=False,
                error=f"Intent {intent.value} not implemented",
                agent_name=self.name
            )
    
    async def _create_trip(self, data: Dict[str, Any]) -> APIResponse:
        """Create a new trip using the exact API payload format"""
        # Use the exact payload format as per original code
        trip_payload = {
            "specific_vehicle_requirements": {
                "number_of_wheels": data.get("wheels"),
                "vehicle_body_type": data.get("body_type"),
                "axle_type": data.get("axle_type"),
                "expected_price": data.get("expected_price")
            },
            "handled_by": data.get("handled_by", self.handled_by),
            "created_by": data.get("created_by", self.created_by),
            "created_by_company": data.get("created_by_company", self.created_by_company)
        }
        
        # Add route information if provided
        if "from_city_id" in data and "to_city_id" in data:
            trip_payload["pickup_postal_address"] = {"city": data["from_city_id"]}
            trip_payload["unload_postal_address"] = {"city": data["to_city_id"]}
        
        response = await self._make_request("POST", "", payload=trip_payload)
        
        if response.success and response.data:
            # Extract trip_id from the API response
            result = response.data
            trip_id = result.get('_id') or result.get('id') or result.get('trip_id')
            
            if not trip_id:
                # Try to find any field that might contain the trip ID
                for field, value in result.items():
                    if 'id' in field.lower() and isinstance(value, str) and len(value) > 10:
                        trip_id = value
                        break
            
            if trip_id:
                response.data = {
                    **response.data,
                    "extracted_trip_id": trip_id,
                    "creation_success": True
                }
            else:
                response.success = False
                response.error = "Trip created but could not extract trip_id from response"
        
        return response
    
    async def _search_trips_by_route(self, data: Dict[str, Any]) -> APIResponse:
        """Search for trips by route"""
        params = {}
        
        if "from_city_id" in data and "to_city_id" in data:
            where_query = {
                "pickup_postal_address.city": data["from_city_id"],
                "unload_postal_address.city": data["to_city_id"]
            }
            params["where"] = urllib.parse.quote(json.dumps(where_query))
        elif "route" in data:
            # Generic route search
            params["search"] = data["route"]
        
        response = await self._make_request("GET", "", params=params)
        
        if response.success and response.data:
            # Process response to extract trip information
            trips_data = response.data
            processed_trips = []
            
            if isinstance(trips_data, dict) and "_items" in trips_data:
                items = trips_data["_items"]
                for trip in items:
                    trip_id = trip.get('_id') or trip.get('id', '')
                    if trip_id:
                        processed_trips.append({
                            "id": trip_id,
                            "pickup_city": trip.get("pickup_postal_address", {}).get("city"),
                            "unload_city": trip.get("unload_postal_address", {}).get("city"),
                            "created_by": trip.get("created_by"),
                            "handled_by": trip.get("handled_by")
                        })
                
                response.data = {
                    "trips": processed_trips,
                    "query": data,
                    "total_found": len(processed_trips)
                }
        
        return response
    
    async def _get_trip_by_id(self, trip_id: str) -> APIResponse:
        """Get specific trip by ID"""
        return await self._make_request("GET", f"/{trip_id}")
    
    async def _list_all_trips(self) -> APIResponse:
        """Get all trips from API"""
        return await self._make_request("GET", "", params=None)
    
    async def get_or_create_trip_for_route(self, from_city_id: str, to_city_id: str) -> Optional[str]:
        """Get existing trip or create new one for the given route"""
        # First try to search for existing trips
        search_response = await self.execute(APIIntent.SEARCH, {
            "from_city_id": from_city_id,
            "to_city_id": to_city_id
        })
        
        if search_response.success and search_response.data:
            trips = search_response.data.get("trips", [])
            if trips:
                return trips[0]["id"]
        
        # If no existing trip found, create a new one
        create_response = await self.execute(APIIntent.CREATE, {
            "from_city_id": from_city_id,
            "to_city_id": to_city_id
        })
        
        if create_response.success and create_response.data:
            return create_response.data.get("extracted_trip_id")
        
        # Fallback to default trip ID if available
        return self.default_trip_id
    
    async def create_trip_simple(self) -> Optional[str]:
        """Create a simple trip without route requirements"""
        response = await self.execute(APIIntent.CREATE, {})
        
        if response.success and response.data:
            return response.data.get("extracted_trip_id")
        
        return self.default_trip_id