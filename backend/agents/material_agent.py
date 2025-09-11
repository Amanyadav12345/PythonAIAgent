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
        # Note: endpoint is included in base_url like CityAgent
        
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
        params = {
            "max_results": "1000"
        }
        return await self._make_request("GET", "", params=params)
    
    async def _search_material_by_name(self, material_name: str) -> APIResponse:
        """Search for materials by name with exact matching and suggestions"""
        print(f"MaterialAgent: Searching for material: '{material_name}'")
        
        # Clean and prepare the search term
        search_term = material_name.strip()
        
        # Use MongoDB-style WHERE clause with regex - search for materials starting with the input
        where_query = {
            "$or": [
                {
                    "name": {
                        "$regex": f"^{search_term}",
                        "$options": "-i"  # case insensitive
                    }
                },
                {
                    "name": {
                        "$regex": f"{search_term}",
                        "$options": "-i"  # also search for materials containing the term
                    }
                }
            ]
        }
        
        # Use params like CityAgent - let the base agent handle URL encoding
        params = {
            "where": json.dumps(where_query),
            "max_results": "50"
        }
        
        response = await self._make_request("GET", "", params=params)
        
        if response.success and response.data:
            materials_data = response.data
            exact_match = None
            partial_matches = []
            
            if isinstance(materials_data, dict) and "_items" in materials_data:
                items = materials_data["_items"]
                print(f"MaterialAgent: Found {len(items)} materials from API")
                
                # Process all materials to find exact match and collect partial matches
                for material in items:
                    material_name_from_api = material.get('name', '').strip()
                    material_id_from_api = material.get('_id', '')
                    
                    # Check for exact match (case insensitive)
                    if material_name_from_api.lower() == search_term.lower():
                        exact_match = {
                            "id": material_id_from_api,
                            "name": material_name_from_api,
                            "matched": True,
                            "match_type": "exact",
                            "state": material.get("state", "Unknown"),
                            "hazard": material.get("hazard", "Unknown")
                        }
                        print(f"MaterialAgent: Found exact match: {material_name_from_api}")
                        break
                    # Check for partial matches (contains search term)
                    elif search_term.lower() in material_name_from_api.lower():
                        partial_matches.append({
                            "id": material_id_from_api,
                            "name": material_name_from_api,
                            "matched": False,
                            "match_type": "partial",
                            "state": material.get("state", "Unknown"),
                            "hazard": material.get("hazard", "Unknown"),
                            "similarity": self._calculate_similarity(search_term.lower(), material_name_from_api.lower())
                        })
                
                # Sort partial matches by similarity
                partial_matches.sort(key=lambda x: x.get("similarity", 0), reverse=True)
                
                # Prepare response
                if exact_match:
                    # Return exact match
                    response.data = {
                        "success": True,
                        "match_type": "exact",
                        "materials": [exact_match],
                        "query": search_term,
                        "total_found": 1,
                        "message": f"Found exact match for '{search_term}': {exact_match['name']}"
                    }
                elif partial_matches:
                    # Return partial matches as suggestions
                    top_suggestions = partial_matches[:5]  # Top 5 suggestions
                    response.data = {
                        "success": False,
                        "match_type": "partial",
                        "materials": top_suggestions,
                        "query": search_term,
                        "total_found": len(partial_matches),
                        "message": f"No exact match found for '{search_term}'. Did you mean one of these?",
                        "suggestions": top_suggestions,
                        "confirmation_needed": True
                    }
                else:
                    # No matches found
                    response.data = {
                        "success": False,
                        "match_type": "none",
                        "materials": [],
                        "query": search_term,
                        "total_found": 0,
                        "message": f"No materials found matching '{search_term}'. Please check spelling and try again.",
                        "suggestions": []
                    }
            else:
                response.data = {
                    "success": False,
                    "error": "Invalid API response format",
                    "materials": [],
                    "query": search_term
                }
        else:
            print(f"MaterialAgent: API request failed: {response.error if response else 'Unknown error'}")
        
        return response
    
    async def _get_material_by_id(self, material_id: str) -> APIResponse:
        """Get specific material by ID"""
        return await self._make_request("GET", f"/{material_id}")
    
    def _calculate_similarity(self, search_term: str, material_name: str) -> float:
        """Calculate similarity between search term and material name"""
        # Simple similarity calculation based on:
        # 1. Exact substring match
        # 2. Word matching
        # 3. Character overlap
        
        search_lower = search_term.lower()
        name_lower = material_name.lower()
        
        # Exact substring match gets highest score
        if search_lower == name_lower:
            return 1.0
        
        # Check if search term is contained in material name
        if search_lower in name_lower:
            return 0.8 + (len(search_lower) / len(name_lower)) * 0.2
        
        # Check if material name starts with search term
        if name_lower.startswith(search_lower):
            return 0.7 + (len(search_lower) / len(name_lower)) * 0.3
        
        # Word-based matching
        search_words = set(search_lower.split())
        name_words = set(name_lower.split())
        
        if search_words.intersection(name_words):
            word_overlap = len(search_words.intersection(name_words)) / len(search_words.union(name_words))
            return word_overlap * 0.6
        
        # Character overlap as fallback
        search_chars = set(search_lower)
        name_chars = set(name_lower)
        char_overlap = len(search_chars.intersection(name_chars)) / len(search_chars.union(name_chars))
        
        return char_overlap * 0.3
    
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
    
    async def confirm_material_choice(self, material_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Confirm user's material choice and return the material information
        
        Args:
            material_data: The material object that user confirmed
            
        Returns:
            Dict with confirmed material details
        """
        try:
            if material_data and "id" in material_data:
                return {
                    "success": True,
                    "material": {
                        "id": material_data["id"],
                        "name": material_data["name"],
                        "state": material_data.get("state", "Unknown"),
                        "hazard": material_data.get("hazard", "Unknown")
                    },
                    "match_type": "confirmed",
                    "confirmation_needed": False
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid material selection",
                    "confirmation_needed": False
                }
        except Exception as e:
            print(f"MaterialAgent: Error confirming material choice: {str(e)}")
            return {
                "success": False,
                "error": f"Material confirmation failed: {str(e)}",
                "confirmation_needed": False
            }