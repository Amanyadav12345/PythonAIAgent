"""
Parcel Agent - Handles parcel-related API operations
Purpose: Create, search, update, and manage parcel data
"""
from typing import Dict, Any, List, Optional
import json
import urllib.parse
from .base_agent import BaseAPIAgent, APIIntent, APIResponse

class ParcelAgent(BaseAPIAgent):
    """
    Specialized agent for parcel API operations
    
    Supported Operations:
    - CREATE: Create new parcel
    - READ: Get specific parcel by ID
    - SEARCH: Search parcels by criteria
    - UPDATE: Update existing parcel
    - LIST: Get all parcels
    """
    
    def __init__(self, base_url: str, auth_config: Dict[str, str],
                 created_by: str = None, created_by_company: str = None):
        super().__init__(name="ParcelAgent", base_url=base_url, auth_config=auth_config)
        self.rate_limit_delay = 1.0  # 1 second for parcel operations
        
        # Default values for parcel creation
        self.created_by = created_by or "6257f1d75b42235a2ae4ab34"
        self.created_by_company = created_by_company or "62d66794e54f47829a886a1d"
        
    def get_supported_intents(self) -> List[APIIntent]:
        return [APIIntent.CREATE, APIIntent.READ, APIIntent.SEARCH, APIIntent.UPDATE, APIIntent.LIST]
    
    def validate_payload(self, intent: APIIntent, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate payload for parcel operations"""
        if intent == APIIntent.CREATE:
            required_fields = ["trip_id", "material_id", "from_city_id", "to_city_id"]
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return False, f"Missing required fields: {missing_fields}"
        elif intent == APIIntent.READ:
            if "parcel_id" not in data:
                return False, "parcel_id is required for READ intent"
        elif intent == APIIntent.UPDATE:
            if "parcel_id" not in data:
                return False, "parcel_id is required for UPDATE intent"
        elif intent == APIIntent.SEARCH:
            if not any(key in data for key in ["sender", "receiver", "trip_id", "material_type", "status"]):
                return False, "At least one search criteria is required for SEARCH intent"
        # LIST intent doesn't require specific data
        return True, None
    
    async def handle_intent(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Handle parcel-specific intents"""
        
        if intent == APIIntent.CREATE:
            return await self._create_parcel(data)
        elif intent == APIIntent.READ:
            return await self._get_parcel_by_id(data["parcel_id"])
        elif intent == APIIntent.SEARCH:
            return await self._search_parcels(data)
        elif intent == APIIntent.UPDATE:
            return await self._update_parcel(data)
        elif intent == APIIntent.LIST:
            return await self._list_all_parcels()
        else:
            return APIResponse(
                success=False,
                error=f"Intent {intent.value} not implemented",
                agent_name=self.name
            )
    
    async def _create_parcel(self, data: Dict[str, Any]) -> APIResponse:
        """Create a new parcel using dynamic data"""
        # Build parcel payload using dynamic data
        parcel_payload = {
            "material_type": data.get('material_id', "619c925ee86624fb2a8f410e"),
            "quantity": data.get('weight', 22),
            "quantity_unit": data.get('quantity_unit', "TONNES"),
            "description": data.get('description', "Parcel created via AI Agent"),
            "cost": data.get('cost') or data.get('weight', 22),
            "part_load": data.get('part_load', False),
            "pickup_postal_address": {
                "address_line_1": data.get('pickup_address', "Default pickup address"),
                "address_line_2": data.get('pickup_address_2'),
                "pin": data.get('pickup_pin', "490026"),
                "city": data.get('from_city_id', "61421aa4de5cb316d9ba569e"),
                "no_entry_zone": data.get('pickup_no_entry_zone')
            },
            "unload_postal_address": {
                "address_line_1": data.get('delivery_address', "Default delivery address"),
                "address_line_2": data.get('delivery_address_2'),
                "pin": data.get('delivery_pin', "302013"),
                "city": data.get('to_city_id', "61421aa1de5cb316d9ba55c0"),
                "no_entry_zone": data.get('delivery_no_entry_zone')
            },
            "sender": {
                "sender_person": data.get('sender_person', "652eda4a8e7383db25404c9d"),
                "sender_company": data.get('sender_company', "66976a703eb59f3a8776b7ba"),
                "name": data.get('sender_name', "Default Sender"),
                "gstin": data.get('sender_gstin', "22AAACB7092E1Z1")
            },
            "receiver": {
                "receiver_person": data.get('receiver_person', "64ca11882b28dbd864e9e8b6"),
                "receiver_company": data.get('receiver_company', "654160760e415d44ff3e93ff"),
                "name": data.get('receiver_name', "Default Receiver"),
                "gstin": data.get('receiver_gstin', "08AABCR1634F1ZO")
            },
            "created_by": data.get('created_by', self.created_by),
            "trip_id": data['trip_id'],
            "verification": data.get('verification', "Verified"),
            "created_by_company": data.get('created_by_company', self.created_by_company)
        }
        
        response = await self._make_request("POST", "", payload=parcel_payload)
        
        if response.success and response.data:
            # Extract parcel_id from the API response
            result = response.data
            parcel_id = result.get('_id') or result.get('id') or result.get('parcel_id')
            
            if parcel_id:
                response.data = {
                    **response.data,
                    "extracted_parcel_id": parcel_id,
                    "creation_success": True,
                    "summary": {
                        "parcel_id": parcel_id,
                        "material_type": parcel_payload["material_type"],
                        "quantity": parcel_payload["quantity"],
                        "from_city": parcel_payload["pickup_postal_address"]["city"],
                        "to_city": parcel_payload["unload_postal_address"]["city"],
                        "trip_id": parcel_payload["trip_id"]
                    }
                }
        
        return response
    
    async def _get_parcel_by_id(self, parcel_id: str) -> APIResponse:
        """Get specific parcel by ID"""
        return await self._make_request("GET", f"/{parcel_id}")
    
    async def _search_parcels(self, data: Dict[str, Any]) -> APIResponse:
        """Search for parcels by various criteria"""
        where_conditions = {}
        
        # Build search conditions based on provided data
        if "sender" in data:
            where_conditions["sender.name"] = {"$regex": data["sender"], "$options": "i"}
        if "receiver" in data:
            where_conditions["receiver.name"] = {"$regex": data["receiver"], "$options": "i"}
        if "trip_id" in data:
            where_conditions["trip_id"] = data["trip_id"]
        if "material_type" in data:
            where_conditions["material_type"] = data["material_type"]
        if "status" in data:
            where_conditions["verification"] = data["status"]
        if "from_city" in data:
            where_conditions["pickup_postal_address.city"] = data["from_city"]
        if "to_city" in data:
            where_conditions["unload_postal_address.city"] = data["to_city"]
        
        if where_conditions:
            where_param = urllib.parse.quote(json.dumps(where_conditions))
            params = {"where": where_param}
        else:
            params = {}
        
        response = await self._make_request("GET", "", params=params)
        
        if response.success and response.data:
            # Process response to extract parcel information
            parcels_data = response.data
            processed_parcels = []
            
            if isinstance(parcels_data, dict) and "_items" in parcels_data:
                items = parcels_data["_items"]
                for parcel in items:
                    parcel_id = parcel.get('_id') or parcel.get('id', '')
                    if parcel_id:
                        processed_parcels.append({
                            "id": parcel_id,
                            "material_type": parcel.get("material_type"),
                            "quantity": parcel.get("quantity"),
                            "sender": parcel.get("sender", {}).get("name"),
                            "receiver": parcel.get("receiver", {}).get("name"),
                            "trip_id": parcel.get("trip_id"),
                            "verification": parcel.get("verification"),
                            "from_city": parcel.get("pickup_postal_address", {}).get("city"),
                            "to_city": parcel.get("unload_postal_address", {}).get("city")
                        })
                
                response.data = {
                    "parcels": processed_parcels,
                    "query": data,
                    "total_found": len(processed_parcels)
                }
        
        return response
    
    async def _update_parcel(self, data: Dict[str, Any]) -> APIResponse:
        """Update an existing parcel"""
        parcel_id = data.pop("parcel_id")
        
        # Remove None values and system fields
        update_payload = {k: v for k, v in data.items() 
                         if v is not None and k not in ["parcel_id", "_id", "created_by", "created_by_company"]}
        
        return await self._make_request("PUT", f"/{parcel_id}", payload=update_payload)
    
    async def _list_all_parcels(self) -> APIResponse:
        """Get all parcels from API"""
        return await self._make_request("GET", "", params=None)
    
    async def create_parcel_with_dependencies(self, parcel_info: Dict[str, Any], 
                                            trip_id: str) -> APIResponse:
        """Convenience method to create parcel with trip_id"""
        parcel_data = {**parcel_info, "trip_id": trip_id}
        return await self.execute(APIIntent.CREATE, parcel_data)
    
    def extract_parcel_summary(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key parcel information from API response"""
        if not response_data:
            return {}
        
        return {
            "parcel_id": response_data.get("extracted_parcel_id") or response_data.get("_id"),
            "material_type": response_data.get("material_type"),
            "quantity": response_data.get("quantity"),
            "sender": response_data.get("sender", {}).get("name"),
            "receiver": response_data.get("receiver", {}).get("name"),
            "trip_id": response_data.get("trip_id"),
            "verification": response_data.get("verification"),
            "pickup_city": response_data.get("pickup_postal_address", {}).get("city"),
            "delivery_city": response_data.get("unload_postal_address", {}).get("city")
        }