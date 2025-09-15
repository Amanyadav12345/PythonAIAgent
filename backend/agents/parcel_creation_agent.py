from typing import Dict, Any, Optional, List
import httpx
import json
import asyncio
import os
import logging
from dotenv import load_dotenv
from .base_agent import BaseAPIAgent, APIResponse, APIIntent
from pydantic import BaseModel

load_dotenv()
logger = logging.getLogger(__name__)

class AddressModel(BaseModel):
    address_line_1: str
    address_line_2: Optional[str] = None
    pin: str
    city: str  # City ID
    no_entry_zone: Optional[str] = None

class SenderModel(BaseModel):
    sender_person: str
    sender_company: str
    name: str
    gstin: str

class ReceiverModel(BaseModel):
    receiver_person: str
    receiver_company: str
    name: str
    gstin: str

class ParcelRequest(BaseModel):
    material_type: str
    quantity: float
    quantity_unit: str  # KILOGRAMS or TONNES
    description: Optional[str] = None
    cost: float
    part_load: bool = False
    pickup_postal_address: AddressModel
    unload_postal_address: AddressModel
    sender: SenderModel
    receiver: ReceiverModel
    created_by: str
    trip_id: str
    verification: str = "Verified"
    created_by_company: str

class ParcelCreationAgent(BaseAPIAgent):
    def __init__(self):
        auth_config = {
            "username": os.getenv("PARCEL_API_USERNAME"),
            "password": os.getenv("PARCEL_API_PASSWORD")
        }
        super().__init__(
            name="ParcelCreationAgent",
            base_url="https://35.244.19.78:8042",
            auth_config=auth_config
        )
        self.endpoint = "/parcels"
        self.material_types_endpoint = "/material_types"
        
        # Default GSTIN values (these are standard defaults, not user-specific)
        self.default_gstin = {
            "sender": "08AABCR1634F1ZO",
            "receiver": "08AABCN7953M1ZV"
        }
        
        # Default receiver values (these should ideally come from configuration)
        self.default_receiver = {
            "person": "63341980ef1172ca37b9b02d",
            "company": "65b0e0a7ff9d5050d247022c",
            "name": "Default Receiver"
        }
    
    async def search_material_by_name(self, material_name: str) -> Optional[Dict[str, Any]]:
        """Search for material by name using the external API and return exact match"""
        try:
            # Build the query using URL encoding format like your working example
            where_query = {
                "$or": [
                    {"name": {"$regex": f"^{material_name}", "$options": "-i"}}
                ]
            }
            
            # Use the direct URL format that works
            import urllib.parse
            where_encoded = urllib.parse.quote(json.dumps(where_query))
            full_url = f"{self.base_url}{self.material_types_endpoint}?where={where_encoded}"
            
            print(f"Material search URL: {full_url}")
            
            response = await self._make_request(
                method="GET",
                endpoint=f"{self.material_types_endpoint}?where={where_encoded}&max_results=10"
            )
            
            if response.success and response.data:
                items = response.data.get("_items", [])
                print(f"Found {len(items)} materials for search: {material_name}")
                
                # Find exact match (case-insensitive)
                for item in items:
                    item_name = item.get("name", "").lower().strip()
                    search_name = material_name.lower().strip()
                    
                    print(f"Comparing: '{item_name}' with '{search_name}'")
                    
                    if item_name == search_name:
                        print(f"Exact match found: {item.get('name')} -> {item.get('_id')}")
                        return {
                            "id": item.get("_id"),
                            "name": item.get("name"),
                            "state": item.get("state"),
                            "hazard": item.get("hazard")
                        }
                
                # If no exact match, look for partial matches
                for item in items:
                    item_name = item.get("name", "").lower().strip()
                    search_name = material_name.lower().strip()
                    
                    if search_name in item_name or item_name in search_name:
                        print(f"Partial match found: {item.get('name')} -> {item.get('_id')}")
                        return {
                            "id": item.get("_id"),
                            "name": item.get("name"),
                            "state": item.get("state"),
                            "hazard": item.get("hazard")
                        }
            
            print(f"No material found for '{material_name}'")
            return None
            
        except Exception as e:
            print(f"Error searching material '{material_name}': {str(e)}")
            return None
    
    async def create_parcel(self, parcel_payload: Dict[str, Any]) -> APIResponse:
        """Create a new parcel with complete payload structure"""
        
        response = await self._make_request(
            method="POST",
            endpoint=self.endpoint,
            payload=parcel_payload
        )
        response.intent = APIIntent.CREATE.value
        return response
    
    async def handle_parcel_creation_request(self, 
                                           user_message: str, 
                                           user_context: Dict[str, Any],
                                           trip_id: Optional[str] = None,
                                           cities_data: Optional[List[Dict]] = None,
                                           materials_data: Optional[List[Dict]] = None,
                                           from_city_id: Optional[str] = None,
                                           to_city_id: Optional[str] = None,
                                           material_type: Optional[str] = None,
                                           quantity: Optional[float] = None,
                                           quantity_unit: Optional[str] = None,
                                           cost: Optional[float] = None) -> APIResponse:
        """Handle natural language parcel creation requests with AI-powered identification"""
        
        # If no trip_id provided, we need one
        if not trip_id:
            return APIResponse(
                success=False,
                error="A trip ID is required to create a parcel. Please create a trip first or provide a trip ID.",
                intent=APIIntent.CREATE,
                agent_name=self.name
            )
        
        try:
            # If city IDs are already provided (from enhanced workflow), use them directly
            if from_city_id and to_city_id:
                # Use MaterialAgent to get proper material ID
                material_result = await self._lookup_material_with_agent(material_type)
                
                if not material_result["success"]:
                    return APIResponse(
                        success=False,
                        error=f"Material identification failed: {material_result['error']}",
                        data={"suggestions": material_result.get("suggestions", [])},
                        agent_name=self.name
                    )
                
                material_info = material_result["material"]
                identification_result = {
                    "from_city": {"id": from_city_id},
                    "to_city": {"id": to_city_id}, 
                    "material": material_info,
                    "quantity": {
                        "value": quantity or 30.0,
                        "unit": quantity_unit or "TONNES"
                    },
                    "parsing_notes": f"Enhanced Gemini workflow provided city IDs directly, using material ID: {material_info['id']} ({material_info['name']})"
                }
            else:
                # Use GeminiService approach for robust city lookup and parsing
                identification_result = await self._handle_parcel_creation_with_gemini_approach(
                    user_message, user_context
                )
                
                if "error" in identification_result:
                    return APIResponse(
                        success=False,
                        error=identification_result["error"],
                        intent=APIIntent.CREATE,
                        agent_name=self.name,
                        data=identification_result.get("data", {})
                    )
            
            # Step 2: Build complete parcel payload
            parcel_payload = await self._build_parcel_payload(
                identification_result=identification_result,
                user_message=user_message,
                user_context=user_context,
                trip_id=trip_id,
                override_cost=cost
            )
            
            if "error" in parcel_payload:
                return APIResponse(
                    success=False,
                    error=parcel_payload["error"],
                    intent=APIIntent.CREATE,
                    agent_name=self.name
                )
            
            # Step 3: Create the parcel
            response = await self.create_parcel(parcel_payload)
            
            if response.success:
                parcel_data = response.data
                parcel_id = parcel_data.get('_id')
                parcel_etag = parcel_data.get('_etag')  # Extract _etag from parcel creation response

                return APIResponse(
                    success=True,
                    data={
                        "parcel_id": parcel_id,
                        "parcel_etag": parcel_etag,  # Include _etag for subsequent PATCH operations
                        "trip_id": trip_id,
                        "parcel_details": parcel_data,
                        "identification_result": identification_result,
                        "message": f"📦 Parcel created successfully! Parcel ID: {parcel_id}",
                        "summary": self._generate_advanced_parcel_summary(identification_result, parcel_id, trip_id)
                    },
                    intent=APIIntent.CREATE,
                    agent_name=self.name
                )
            else:
                return APIResponse(
                    success=False,
                    error=f"Failed to create parcel: {response.error}",
                    intent=APIIntent.CREATE,
                    agent_name=self.name
                )
                
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Parcel creation failed: {str(e)}",
                intent=APIIntent.CREATE,
                agent_name=self.name
            )
    
    async def _handle_parcel_creation_with_gemini_approach(self, user_message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle parcel creation using GeminiService approach for robust city lookup and parsing
        Similar to gemini_service.enhanced_trip_and_parcel_creation but focused on parcel creation
        """
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from gemini_service import gemini_service
            
            # Step 1: Parse the user message with Gemini AI or fallback
            if gemini_service.model:
                parsing_result = await gemini_service._parse_trip_parcel_request_with_gemini(user_message)
            else:
                parsing_result = gemini_service._parse_trip_parcel_request_basic(user_message)
            
            if "error" in parsing_result:
                return {"error": parsing_result["error"]}
            
            # Step 2: Lookup cities using GeminiService approach
            from_city_name = parsing_result.get("from_city")
            to_city_name = parsing_result.get("to_city")
            
            if not from_city_name or not to_city_name:
                return {
                    "error": "Could not identify both source and destination cities from your message. Please specify 'from [city]' and 'to [city]'."
                }
            
            # Lookup both cities using GeminiService methods
            from_city_result = await gemini_service.lookup_city_by_name(from_city_name)
            to_city_result = await gemini_service.lookup_city_by_name(to_city_name)
            
            # Handle city lookup results
            city_errors = []
            suggestions_data = {}
            
            if not from_city_result.get("success"):
                if "suggestions" in from_city_result:
                    city_errors.append(f"Source city '{from_city_name}' not found. {from_city_result.get('suggestion_message', 'Suggestions available')}: {', '.join([s['name'] for s in from_city_result['suggestions'][:3]])}")
                    suggestions_data["from_city"] = from_city_result["suggestions"]
                else:
                    city_errors.append(f"Source city '{from_city_name}' not found: {from_city_result.get('error', 'Unknown error')}")
            
            if not to_city_result.get("success"):
                if "suggestions" in to_city_result:
                    city_errors.append(f"Destination city '{to_city_name}' not found. {to_city_result.get('suggestion_message', 'Suggestions available')}: {', '.join([s['name'] for s in to_city_result['suggestions'][:3]])}")
                    suggestions_data["to_city"] = to_city_result["suggestions"]
                else:
                    city_errors.append(f"Destination city '{to_city_name}' not found: {to_city_result.get('error', 'Unknown error')}")
            
            if city_errors:
                return {
                    "error": ". ".join(city_errors),
                    "data": {"suggestions": suggestions_data}
                }
            
            # Step 3: Material lookup using MaterialAgent
            material_type_name = parsing_result.get("material_type")
            material_result = await self._lookup_material_with_agent(material_type_name)
            
            if not material_result["success"]:
                return {
                    "error": material_result["error"],
                    "suggestions": material_result.get("suggestions", [])
                }
            
            effective_material_id = material_result["material"]["id"] 
            material_name = material_result["material"]["name"]
            
            # Build identification result in the expected format
            return {
                "from_city": from_city_result["city"],
                "to_city": to_city_result["city"], 
                "material": {"id": effective_material_id, "name": material_name},
                "quantity": {
                    "value": parsing_result.get("quantity", 30.0),
                    "unit": parsing_result.get("quantity_unit", "TONNES")
                },
                "parsing_notes": f"Parsed using GeminiService approach: {from_city_name} → {to_city_name}, {material_name}"
            }
            
        except Exception as e:
            logger.error(f"Error in GeminiService approach for parcel creation: {str(e)}")
            return {
                "error": f"Parcel creation parsing failed: {str(e)}"
            }
    
    async def _build_parcel_payload(self, 
                                   identification_result: Dict[str, Any],
                                   user_message: str,
                                   user_context: Dict[str, Any],
                                   trip_id: str,
                                   override_cost: Optional[float] = None) -> Dict[str, Any]:
        """Build the complete parcel payload using identification results"""
        
        try:
            # Extract identified data
            from_city = identification_result.get('from_city', {})
            to_city = identification_result.get('to_city', {})
            material = identification_result.get('material', {})
            quantity_info = identification_result.get('quantity', {})
            
            # Validate required fields
            if not from_city or not from_city.get('id'):
                return {"error": "Could not identify pickup city from your message"}
            
            if not to_city or not to_city.get('id'):
                return {"error": "Could not identify delivery city from your message"}
            
            # Search for material using the external API if not already identified
            if not material or not material.get('id'):
                # Try to extract material name from the message if not provided
                material_name = self._extract_material_name_from_message(user_message)
                if material_name:
                    print(f"Searching for material: {material_name}")
                    searched_material = await self.search_material_by_name(material_name)
                    if searched_material:
                        material = searched_material
                        print(f"Found material: {material['name']} with ID: {material['id']}")
                    else:
                        # Use MaterialAgent to search for a default material
                        print(f"No material found for '{material_name}', searching for general goods")
                        material_result = await self._lookup_material_with_agent("general goods")
                        if material_result["success"]:
                            material = material_result["material"]
                        else:
                            # Final fallback
                            material = {"id": "61d938b2abfc80dadb54b107", "name": "Aata"}
                else:
                    print("No material name extracted, using MaterialAgent for default lookup")
                    material_result = await self._lookup_material_with_agent("general goods")
                    if material_result["success"]:
                        material = material_result["material"]
                    else:
                        # Final fallback
                        material = {"id": "61d938b2abfc80dadb54b107", "name": "Aata"}
            
            if not quantity_info or not quantity_info.get('value'):
                return {"error": "Could not identify quantity from your message"}
            
            # Parse additional details from message
            cost = override_cost if override_cost is not None else self._extract_cost(user_message)
            part_load = self._determine_part_load(user_message)
            description = self._extract_description(user_message)
            
            # Get addresses (simplified - in real app, would be more sophisticated)
            pickup_address = self._build_address(from_city, "pickup", user_message)
            delivery_address = self._build_address(to_city, "delivery", user_message)
            
            # Helper function to format ObjectId for MongoDB API
            def format_objectid(oid_str):
                """Format ObjectId string for MongoDB API"""
                if oid_str and isinstance(oid_str, str) and len(oid_str) == 24:
                    # Try both formats - some APIs expect {"$oid": "..."} format
                    return oid_str  # Start with string format
                return oid_str
            
            # Get ObjectId values from user context (localStorage user data)
            # This user_id comes from frontend localStorage (user_record._id from auth API)
            user_id = user_context.get("user_id")
            company_id = user_context.get("current_company", "62d66794e54f47829a886a1d")
            
            # Extract user details from user_record if available
            user_record = user_context.get("user_record", {})
            user_name = user_context.get("name") or user_record.get("name", "User")
            
            # Validate that we have the required ObjectId for user_id (from localStorage)
            if not user_id:
                raise ValueError("ParcelCreationAgent: user_id is required from localStorage user data")
            
            if isinstance(user_id, str) and len(user_id) != 24:
                raise ValueError(f"ParcelCreationAgent: Invalid ObjectId format for user_id: '{user_id}' (must be 24 characters)")
            
            # Ensure company_id is always set
            if not company_id:
                company_id = "62d66794e54f47829a886a1d"
                
            if isinstance(company_id, str) and len(company_id) != 24:
                raise ValueError(f"ParcelCreationAgent: Invalid ObjectId format for company_id: '{company_id}' (must be 24 characters)")
                
            print(f"ParcelCreationAgent: Using localStorage user_id: {user_id}")
            print(f"ParcelCreationAgent: Using localStorage company_id: {company_id}")
            print(f"ParcelCreationAgent: Using user name: {user_name}")
            
            # Format ObjectIds for API
            definitive_user_id = format_objectid(user_id)
            definitive_company_id = format_objectid(company_id)
            
            # Build complete payload
            payload = {
                "material_type": material["id"],
                "quantity": quantity_info["value"],
                "quantity_unit": quantity_info["unit"],
                "description": description,
                "cost": cost,
                "part_load": part_load,
                "pickup_postal_address": pickup_address,
                "unload_postal_address": delivery_address,
                "sender": {
                    "sender_person": definitive_user_id,  # User from localStorage (_id field)
                    "sender_company": definitive_company_id,  # Company from localStorage
                    "name": user_name,  # User name from localStorage
                    "gstin": self.default_gstin["sender"]
                },
                "receiver": {
                    "receiver_person": format_objectid(self.default_receiver["person"]),
                    "receiver_company": format_objectid(self.default_receiver["company"]),
                    "name": self.default_receiver["name"],
                    "gstin": self.default_gstin["receiver"]
                },
                "created_by": definitive_user_id,  # User from localStorage (_id field)
                "trip_id": trip_id,
                "verification": "Verified",
                "created_by_company": definitive_company_id  # Company from localStorage
            }
            
            print(f"ParcelCreationAgent: Final payload created_by: {payload['created_by']}")
            print(f"ParcelCreationAgent: Final payload sender_person: {payload['sender']['sender_person']}")
            
            return payload
            
        except Exception as e:
            return {"error": f"Failed to build parcel payload: {str(e)}"}
    
    async def _lookup_material_with_agent(self, material_name: Optional[str]) -> Dict[str, Any]:
        """
        Use MaterialAgent to lookup material by name with smart handling
        
        Args:
            material_name: The material name to search for
            
        Returns:
            Dict with material details or error/suggestions
        """
        if not material_name or material_name.strip() == "":
            # If no material name provided, default to general goods
            material_name = "general goods"
        
        try:
            # Import agent manager to use MaterialAgent
            from agents.agent_manager import agent_manager
            from agents.base_agent import APIIntent
            
            print(f"ParcelCreationAgent: Looking up material '{material_name}' using MaterialAgent")
            
            # Use MaterialAgent to search for the material
            response = await agent_manager.execute_single_intent(
                "material", APIIntent.SEARCH, {"material_name": material_name}
            )
            
            if response.success and response.data:
                data = response.data
                match_type = data.get("match_type")
                materials = data.get("materials", [])
                
                if match_type == "exact" and materials:
                    # Exact match found
                    material = materials[0]
                    print(f"ParcelCreationAgent: Found exact match: {material['name']} (ID: {material['id']})")
                    return {
                        "success": True,
                        "material": {
                            "id": material["id"],
                            "name": material["name"]
                        },
                        "match_type": "exact"
                    }
                    
                elif match_type == "partial" and materials:
                    # Partial matches - use the best match automatically or return suggestions
                    best_match = materials[0]  # MaterialAgent sorts by similarity
                    similarity = best_match.get("similarity", 0)
                    
                    if similarity > 0.8:  # Use high similarity matches automatically
                        print(f"ParcelCreationAgent: Using best match: {best_match['name']} (ID: {best_match['id']}) - {similarity:.1%} match")
                        return {
                            "success": True,
                            "material": {
                                "id": best_match["id"],
                                "name": best_match["name"]
                            },
                            "match_type": "partial_auto"
                        }
                    else:
                        # Lower similarity - return suggestions for user confirmation
                        print(f"ParcelCreationAgent: Material '{material_name}' needs user confirmation")
                        return {
                            "success": False,
                            "error": f"Material '{material_name}' not found exactly. Please choose from suggestions or try a different name.",
                            "suggestions": [
                                {
                                    "id": mat["id"],
                                    "name": mat["name"],
                                    "similarity": mat.get("similarity", 0)
                                } for mat in materials[:3]  # Top 3 suggestions
                            ],
                            "match_type": "partial_suggestions"
                        }
                        
                else:
                    # No matches found - fallback to default
                    print(f"ParcelCreationAgent: No matches for '{material_name}', using fallback")
                    return {
                        "success": False,
                        "error": f"Material '{material_name}' not found. Using default material.",
                        "suggestions": []
                    }
            else:
                # MaterialAgent search failed - fallback to default  
                print(f"ParcelCreationAgent: MaterialAgent search failed for '{material_name}'")
                return {
                    "success": False,
                    "error": f"Material search failed for '{material_name}'. Using default material.",
                    "suggestions": []
                }
                
        except Exception as e:
            print(f"ParcelCreationAgent: Exception during material lookup: {str(e)}")
            return {
                "success": False,
                "error": f"Material lookup failed: {str(e)}",
                "suggestions": []
            }

    def _extract_material_name_from_message(self, message: str) -> Optional[str]:
        """Extract material name from user message"""
        message_lower = message.lower()
        
        # Common material keywords to look for
        material_keywords = [
            "cement", "steel", "iron", "sand", "gravel", "brick", "concrete",
            "aata", "wheat", "rice", "sugar", "salt", "flour", "grain",
            "coal", "wood", "timber", "plastic", "rubber", "glass",
            "chemicals", "oil", "fuel", "fertilizer", "marble", "granite"
        ]
        
        # Look for material keywords in the message
        for keyword in material_keywords:
            if keyword in message_lower:
                return keyword.title()  # Return with proper capitalization
        
        # Try to extract material from common patterns
        import re
        
        # Pattern: "transport/ship/move [quantity] [material]"
        patterns = [
            r'(?:transport|ship|move|send|carry|deliver)\s+(?:\d+\s*(?:kg|ton|tonne|mt|liter|litre)?s?\s+)?(\w+)',
            r'(\w+)\s+(?:from|to)',
            r'load\s+of\s+(\w+)',
            r'cargo\s+of\s+(\w+)',
            r'shipment\s+of\s+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                potential_material = match.group(1).strip()
                # Filter out common non-material words
                non_material_words = ['the', 'and', 'from', 'to', 'with', 'for', 'truck', 'trip', 'parcel']
                if potential_material not in non_material_words and len(potential_material) > 2:
                    return potential_material.title()
        
        return None
    
    def _extract_cost(self, message: str) -> float:
        """Extract cost from user message"""
        import re
        cost_match = re.search(r'(?:cost|price|rate).*?(\d+(?:,\d{3})*(?:\.\d{2})?)', message.lower())
        if cost_match:
            try:
                return float(cost_match.group(1).replace(',', ''))
            except ValueError:
                pass
        return 121.0  # Default cost
    
    def _determine_part_load(self, message: str) -> bool:
        """Determine if this is a part load based on message"""
        part_load_indicators = ["part load", "partial", "shared", "ltl", "less than truck"]
        full_load_indicators = ["full load", "complete", "ftl", "full truck"]
        
        message_lower = message.lower()
        
        if any(indicator in message_lower for indicator in part_load_indicators):
            return True
        elif any(indicator in message_lower for indicator in full_load_indicators):
            return False
        else:
            return False  # Default to full load
    
    def _extract_description(self, message: str) -> Optional[str]:
        """Extract description from user message (max 100 chars)"""
        # Extract material and quantity info for description
        words = message.lower().split()
        description_parts = []
        
        # Look for material keywords
        material_keywords = ["wall putty", "cement", "steel", "iron", "sand", "gravel", "brick"]
        for keyword in material_keywords:
            if keyword in message.lower():
                description_parts.append(keyword.title())
                break
        
        # Look for quantity
        import re
        qty_match = re.search(r'(\d+)\s*(ton|kg|liter|litre|mt)', message.lower())
        if qty_match:
            description_parts.append(f"{qty_match.group(1)} {qty_match.group(2)}")
        
        # Create concise description under 100 chars
        if description_parts:
            description = " ".join(description_parts)
            return description[:95] + "..." if len(description) > 100 else description
        else:
            return "Parcel shipment"[:100]
    
    def _build_address(self, city_info: Dict, address_type: str, user_message: str) -> Dict[str, Any]:
        """Build address object for pickup/delivery"""
        
        # Extract PIN code if mentioned
        import re
        pin_match = re.search(r'\b(\d{6})\b', user_message)
        pin_code = pin_match.group(1) if pin_match else "000000"
        
        # Generate address line based on city and type
        if address_type == "pickup":
            address_line = f"Pickup location in {city_info.get('name', 'Unknown City')}"
        else:
            address_line = f"Delivery location in {city_info.get('name', 'Unknown City')}"
        
        # Look for specific address in message
        address_keywords = ["address", "location", "at", "near"]
        for keyword in address_keywords:
            if keyword in user_message.lower():
                # Try to extract address context
                keyword_idx = user_message.lower().find(keyword)
                surrounding_text = user_message[max(0, keyword_idx-20):keyword_idx+100]
                if len(surrounding_text.strip()) > len(keyword):
                    address_line = surrounding_text.strip()
                break
        
        return {
            "address_line_1": address_line,
            "address_line_2": None,
            "pin": int(pin_code) if pin_code.isdigit() else 000000,  # Convert to integer for API
            "city": city_info["id"],
            "no_entry_zone": None
        }
    
    def _generate_advanced_parcel_summary(self, identification_result: Dict, parcel_id: str, trip_id: str) -> str:
        """Generate a comprehensive human-readable summary"""
        summary_parts = [f"Parcel {parcel_id} created for trip {trip_id}"]
        
        from_city = identification_result.get('from_city', {})
        to_city = identification_result.get('to_city', {})
        material = identification_result.get('material', {})
        quantity = identification_result.get('quantity', {})
        
        if from_city.get('name') and to_city.get('name'):
            summary_parts.append(f"Route: {from_city['name']} → {to_city['name']}")
        
        if material.get('name'):
            summary_parts.append(f"Material: {material['name']}")
        
        if quantity.get('value') and quantity.get('unit'):
            summary_parts.append(f"Quantity: {quantity['value']} {quantity['unit']}")
        
        parsing_notes = identification_result.get('parsing_notes', '')
        if parsing_notes and 'Gemini' in parsing_notes:
            summary_parts.append("🤖 AI-powered identification used")
        
        return " | ".join(summary_parts)
    
    def _parse_parcel_details(self, message: str) -> Dict[str, Any]:
        """Parse parcel details from user message"""
        details = {}
        message_lower = message.lower()
        
        # Parse sender information
        if "from" in message_lower:
            # Simple extraction - in real app, use NLP
            import re
            from_match = re.search(r'from\s+([^,\n]+?)(?:\s+to|\s+$)', message_lower)
            if from_match:
                sender_info = from_match.group(1).strip()
                details["sender_name"] = sender_info
                details["sender_address"] = sender_info
        
        # Parse receiver information
        if "to" in message_lower:
            to_match = re.search(r'to\s+([^,\n]+?)(?:\s+|$)', message_lower)
            if to_match:
                receiver_info = to_match.group(1).strip()
                details["receiver_name"] = receiver_info
                details["receiver_address"] = receiver_info
        
        # Parse weight
        import re
        weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|kilograms?|pounds?|lbs?)', message_lower)
        if weight_match:
            try:
                weight = float(weight_match.group(1))
                # Convert pounds to kg if needed
                if any(unit in weight_match.group(0) for unit in ['pounds', 'lbs', 'lb']):
                    weight = weight * 0.453592
                details["weight"] = weight
            except ValueError:
                pass
        
        # Parse dimensions
        dimension_match = re.search(r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)', message_lower)
        if dimension_match:
            try:
                length = float(dimension_match.group(1))
                width = float(dimension_match.group(2))
                height = float(dimension_match.group(3))
                details["dimensions"] = {
                    "length": length,
                    "width": width,
                    "height": height
                }
            except ValueError:
                pass
        
        # Parse fragile
        if any(word in message_lower for word in ["fragile", "delicate", "breakable", "careful"]):
            details["fragile"] = True
        
        # Parse priority
        if any(word in message_lower for word in ["urgent", "rush", "emergency", "asap"]):
            details["priority"] = "high"
        elif any(word in message_lower for word in ["low priority", "non-urgent", "when possible"]):
            details["priority"] = "low"
        
        # Parse description
        desc_keywords = ["package", "parcel", "item", "goods", "cargo", "shipment"]
        for keyword in desc_keywords:
            if keyword in message_lower:
                # Extract surrounding context as description
                start_idx = message_lower.find(keyword)
                surrounding = message[max(0, start_idx-20):start_idx+50]
                details["parcel_description"] = surrounding.strip()
                break
        
        return details
    
    def _generate_parcel_summary(self, details: Dict, parcel_id: str, trip_id: str) -> str:
        """Generate a human-readable summary of the parcel"""
        summary = [f"Parcel {parcel_id} created for trip {trip_id}"]
        
        if details.get("sender_name"):
            summary.append(f"From: {details['sender_name']}")
        
        if details.get("receiver_name"):
            summary.append(f"To: {details['receiver_name']}")
        
        if details.get("weight"):
            summary.append(f"Weight: {details['weight']:.2f} kg")
        
        if details.get("dimensions"):
            dims = details["dimensions"]
            summary.append(f"Dimensions: {dims.get('length', '?')} x {dims.get('width', '?')} x {dims.get('height', '?')}")
        
        if details.get("fragile"):
            summary.append("⚠️ FRAGILE ITEM")
        
        if details.get("priority") and details["priority"] != "normal":
            summary.append(f"Priority: {details['priority'].upper()}")
        
        return " | ".join(summary)
    
    def get_supported_intents(self) -> list[APIIntent]:
        """Return the list of supported API intents"""
        return [APIIntent.CREATE]
    
    def can_handle_intent(self, intent: APIIntent, context: str = "") -> bool:
        """Check if this agent can handle the given intent"""
        parcel_keywords = ["parcel", "package", "shipment", "cargo", "goods", "item"]
        create_keywords = ["create", "make", "new", "add", "send", "ship"]
        
        if intent == APIIntent.CREATE:
            return any(keyword in context.lower() for keyword in parcel_keywords) and \
                   any(keyword in context.lower() for keyword in create_keywords)
        
        return False
    
    def get_help_text(self) -> str:
        """Return help text for this agent"""
        return """
📦 **Parcel Creation Agent**

I can help you create parcels for existing trips.

**Examples:**
- "Create a parcel from Mumbai to Delhi, weight 25kg"
- "Add a fragile package 30x20x15 cm for trip ABC123"
- "Send urgent shipment from John Smith to ABC Company"
- "Make a parcel 50kg from warehouse to customer"

**Supported Details:**
- Sender and receiver information
- Weight (kg, pounds)
- Dimensions (length x width x height)
- Fragile/delicate items
- Priority levels (normal, high, low)
- Custom descriptions

**Requirements:**
- Must have a valid trip ID (create a trip first)

**Usage:**
Describe the parcel you want to create and I'll extract the details!
        """
    
    async def handle_intent(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Handle specific intent - implementation of abstract method"""
        if intent == APIIntent.CREATE:
            # Require user_context from localStorage - no defaults
            user_id = data.get("user_id")
            if not user_id:
                return APIResponse(
                    success=False,
                    error="user_id is required from localStorage authentication data",
                    intent=intent.value,
                    agent_name=self.name
                )
            
            user_context = {
                "user_id": user_id,
                "current_company": data.get("current_company"),
                "name": data.get("name"),
                "email": data.get("email"),
                "user_record": data.get("user_record"),
                "username": data.get("username")
            }
            return await self.handle_parcel_creation_request(
                user_message=data.get("message", ""),
                user_context=user_context,
                trip_id=data.get("trip_id"),
                cities_data=data.get("cities_data", []),
                materials_data=data.get("materials_data", []),
                from_city_id=data.get("from_city_id"),
                to_city_id=data.get("to_city_id"),
                material_type=data.get("material_type"),
                quantity=data.get("quantity"),
                quantity_unit=data.get("quantity_unit"),
                cost=data.get("cost")
            )
        else:
            return APIResponse(
                success=False,
                error=f"Intent {intent.value} not supported by {self.name}",
                intent=intent.value,
                agent_name=self.name
            )
    
    def validate_payload(self, intent: APIIntent, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate payload for specific intent - implementation of abstract method"""
        if intent == APIIntent.CREATE:
            # Basic validation for parcel creation
            required_fields = ["message"]
            if "trip_id" not in data:
                return False, "Missing required field: trip_id"
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
            return True, None
        else:
            return False, f"Intent {intent.value} not supported"