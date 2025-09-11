"""
Material Agent - Handles material-related API operations
Purpose: Search, list, and manage material data
"""
from typing import Dict, Any, List, Optional
import json
import urllib.parse
from .base_agent import BaseAPIAgent, APIIntent, APIResponse

class MaterialAgent(BaseAPIAgent):
    """
    Specialized agent for material API operations
    
    Supported Operations:
    - LIST: Get all materials
    - SEARCH: Search materials by name or criteria
    - READ: Get specific material by ID
    """
    
    def __init__(self, base_url: str, auth_config: Dict[str, str], default_material_id: str = None):
        super().__init__(name="MaterialAgent", base_url=base_url, auth_config=auth_config)
        self.rate_limit_delay = 5.0  # 5 seconds as per original code
        self.default_material_id = default_material_id
        
    def get_supported_intents(self) -> List[APIIntent]:
        return [APIIntent.LIST, APIIntent.SEARCH, APIIntent.READ]
    
    def validate_payload(self, intent: APIIntent, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate payload for material operations"""
        if intent == APIIntent.SEARCH:
            if "material_name" not in data:
                return False, "material_name is required for SEARCH intent"
            if not isinstance(data["material_name"], str):
                return False, "material_name must be a string"
        elif intent == APIIntent.READ:
            if "material_id" not in data:
                return False, "material_id is required for READ intent"
        # LIST intent doesn't require specific data
        return True, None
    
    async def handle_intent(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Handle material-specific intents"""
        
        if intent == APIIntent.LIST:
            return await self._list_all_materials()
        elif intent == APIIntent.SEARCH:
            return await self._search_material_by_name(data["material_name"])
        elif intent == APIIntent.READ:
            return await self._get_material_by_id(data["material_id"])
        else:
            return APIResponse(
                success=False,
                error=f"Intent {intent.value} not implemented",
                agent_name=self.name
            )
    
    async def _list_all_materials(self) -> APIResponse:
        """Get all materials from API"""
        return await self._make_request("GET", "", params=None)
    
    async def _search_material_by_name(self, material_name: str) -> APIResponse:
        """Search for materials by name using MongoDB-style regex WHERE clause"""
        # Use MongoDB-style WHERE clause with regex as per original code
        where_query = {
            "$or": [
                {
                    "name": {
                        "$regex": f"^{material_name}",
                        "$options": "-i"  # case insensitive with -i flag
                    }
                }
            ]
        }
        
        # URL encode the JSON query
        where_param = urllib.parse.quote(json.dumps(where_query))
        params = {"where": where_param}
        
        response = await self._make_request("GET", "", params=params)
        
        if response.success and response.data:
            # Process response to extract material information
            materials_data = response.data
            processed_materials = []
            
            if isinstance(materials_data, dict) and "_items" in materials_data:
                items = materials_data["_items"]
                for material in items:
                    material_name_from_api = material.get('name', '').strip()
                    material_id_from_api = material.get('_id', '')
                    
                    # Check for exact match (case insensitive)
                    if material_name_from_api.lower() == material_name.lower():
                        processed_materials.append({
                            "id": material_id_from_api,
                            "name": material_name_from_api,
                            "matched": True
                        })
                        break
                
                # If no exact match found, use default material ID if available
                if not processed_materials and self.default_material_id:
                    processed_materials.append({
                        "id": self.default_material_id,
                        "name": f"Default Material (for {material_name})",
                        "matched": False,
                        "fallback": True
                    })
                
                response.data = {
                    "materials": processed_materials,
                    "query": material_name,
                    "total_found": len(processed_materials)
                }
        
        return response
    
    async def _get_material_by_id(self, material_id: str) -> APIResponse:
        """Get specific material by ID"""
        return await self._make_request("GET", f"/{material_id}")
    
    def extract_material_mapping(self, response_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract name -> id mapping from API response"""
        mapping = {}
        
        if isinstance(response_data, list):
            for material in response_data:
                material_name = material.get('name', '').strip()
                material_id = material.get('id') or material.get('_id', '')
                if material_name and material_id:
                    mapping[material_name.lower().strip()] = str(material_id)
        
        elif isinstance(response_data, dict):
            if "_items" in response_data:
                for material in response_data["_items"]:
                    material_name = material.get('name', '').strip()
                    material_id = material.get('_id') or material.get('id', '')
                    if material_name and material_id:
                        mapping[material_name.lower().strip()] = str(material_id)
            else:
                for key, value in response_data.items():
                    if isinstance(value, dict):
                        material_name = value.get('name') or key
                        material_id = value.get('id') or value.get('_id', key)
                        if material_name and material_id:
                            mapping[material_name.lower().strip()] = str(material_id)
        
        return mapping
    
    async def get_material_id_by_name(self, material_name: str) -> Optional[str]:
        """Convenience method to get material ID by name"""
        response = await self.execute(APIIntent.SEARCH, {"material_name": material_name})
        
        if response.success and response.data:
            materials = response.data.get("materials", [])
            if materials and len(materials) > 0:
                return materials[0]["id"]
        
        # Return default material ID if no match found
        return self.default_material_id