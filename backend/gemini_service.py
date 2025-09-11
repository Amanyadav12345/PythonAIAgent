"""
Gemini AI Service for intelligent identification of cities and materials from user input
"""
import google.generativeai as genai
import json
import os
import httpx
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
import logging
import asyncio
from difflib import SequenceMatcher

load_dotenv()
logger = logging.getLogger(__name__)

class GeminiIdentificationService:
    def __init__(self):
        # Configure Gemini AI
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. City/material identification may not work.")
            self.model = None
            return
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # City API configuration
        self.city_api_base = "https://35.244.19.78:8042"
        
    def _get_api_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        username = os.getenv("PARCEL_API_USERNAME")
        password = os.getenv("PARCEL_API_PASSWORD")
        headers = {"Content-Type": "application/json"}
        
        if username and password:
            import base64
            credentials = f"{username}:{password}"
            credentials_b64 = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {credentials_b64}"
        
        return headers
    
    async def identify_cities_and_materials(self, 
                                          user_message: str, 
                                          available_cities: List[Dict] = None, 
                                          available_materials: List[Dict] = None) -> Dict[str, Any]:
        """
        Use Gemini AI to identify cities and materials from user message
        
        Args:
            user_message: User's natural language input
            available_cities: List of available cities with id and name (optional - will fetch if not provided)
            available_materials: List of available materials with id and name (optional - will fetch if not provided)
            
        Returns:
            Dict with identified cities and materials
        """
        if not self.model:
            return {"error": "Gemini AI not configured"}
        
        # Get cities and materials from agents if not provided
        if available_cities is None:
            available_cities = await self._get_cities_from_agent()
        
        if available_materials is None:
            available_materials = await self._get_materials_from_agent()
        
        # Create context for Gemini
        cities_context = self._create_cities_context(available_cities)
        materials_context = self._create_materials_context(available_materials)
        
        prompt = f"""
You are an expert logistics assistant. Analyze the user's message and identify:

1. FROM CITY (pickup location)
2. TO CITY (delivery location) 
3. MATERIAL TYPE being transported
4. QUANTITY and UNIT (convert to either KILOGRAMS or TONNES)

AVAILABLE CITIES:
{cities_context}

AVAILABLE MATERIALS:
{materials_context}

USER MESSAGE: "{user_message}"

QUANTITY UNIT CONVERSION RULES:
- "kg", "kilo", "kilogram", "kilograms" → KILOGRAMS
- "ton", "tonne", "tons", "tonnes", "metric ton" → TONNES

INSTRUCTIONS:
- Match city names intelligently (handle variations, abbreviations, common names)
- Match material types based on context and synonyms
- Extract quantity and convert units as specified
- If multiple cities/materials are mentioned, pick the most relevant ones
- Return ONLY valid JSON format

REQUIRED JSON RESPONSE FORMAT:
{{
    "from_city": {{
        "id": "city_id_here",
        "name": "matched_city_name",
        "confidence": 0.95
    }},
    "to_city": {{
        "id": "city_id_here", 
        "name": "matched_city_name",
        "confidence": 0.95
    }},
    "material": {{
        "id": "material_id_here",
        "name": "matched_material_name",
        "confidence": 0.95
    }},
    "quantity": {{
        "value": 25,
        "unit": "KILOGRAMS",
        "original_text": "25 kg"
    }},
    "parsing_notes": "Brief explanation of what was identified"
}}

If something cannot be identified, set the field to null but keep the structure.
"""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean the response to extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON response
            parsed_result = json.loads(result_text)
            
            logger.info(f"Gemini identification successful: {parsed_result.get('parsing_notes', 'No notes')}")
            return parsed_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Raw response: {result_text}")
            return {"error": f"JSON parsing failed: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Gemini AI identification failed: {str(e)}")
            return {"error": f"Gemini AI failed: {str(e)}"}
    
    def _create_cities_context(self, cities: List[Dict]) -> str:
        """Create a concise context string for cities"""
        if not cities:
            return "No cities available"
        
        # Take first 50 cities to avoid token limits
        cities_subset = cities[:50]
        context_items = []
        
        for city in cities_subset:
            city_info = f"ID: {city.get('_id', city.get('id'))}, Name: {city.get('name', 'Unknown')}"
            if city.get('state'):
                city_info += f", State: {city.get('state')}"
            context_items.append(city_info)
        
        return "\n".join(context_items)
    
    def _create_materials_context(self, materials: List[Dict]) -> str:
        """Create a concise context string for materials"""
        if not materials:
            return "No materials available"
        
        # Take first 30 materials to avoid token limits
        materials_subset = materials[:30]
        context_items = []
        
        for material in materials_subset:
            material_info = f"ID: {material.get('_id', material.get('id'))}, Name: {material.get('name', 'Unknown')}"
            if material.get('category'):
                material_info += f", Category: {material.get('category')}"
            context_items.append(material_info)
        
        return "\n".join(context_items)
    
    def parse_quantity_unit(self, text: str) -> Tuple[Optional[float], str]:
        """
        Parse quantity and unit from text
        Returns: (quantity_value, standardized_unit)
        """
        import re
        
        text_lower = text.lower()
        
        # Find numeric quantities
        quantity_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:kg|kilo|kilogram|kilograms)',
            r'(\d+(?:\.\d+)?)\s*(?:ton|tonne|tons|tonnes|metric\s*ton)',
            r'(\d+(?:\.\d+)?)\s*(?:quintal|quintals)',
            r'(\d+(?:\.\d+)?)\s*(?:pound|pounds|lbs?)'
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, text_lower)
            if match:
                quantity = float(match.group(1))
                
                # Determine unit
                unit_text = text_lower[match.start():match.end()]
                if any(u in unit_text for u in ['kg', 'kilo', 'kilogram']):
                    return quantity, "KILOGRAMS"
                elif any(u in unit_text for u in ['ton', 'tonne', 'metric']):
                    return quantity, "TONNES"
                elif any(u in unit_text for u in ['quintal']):
                    return quantity * 100, "KILOGRAMS"  # 1 quintal = 100kg
                elif any(u in unit_text for u in ['pound', 'lbs', 'lb']):
                    return quantity * 0.453592, "KILOGRAMS"  # Convert to kg
        
        return None, "KILOGRAMS"  # Default unit
    
    def get_fallback_identification(self, user_message: str) -> Dict[str, Any]:
        """
        Fallback identification without Gemini AI (basic regex/keyword matching)
        """
        message_lower = user_message.lower()
        
        # Basic city extraction patterns
        from_patterns = ['from', 'pickup', 'origin', 'source']
        to_patterns = ['to', 'delivery', 'destination', 'drop']
        
        # Basic quantity extraction
        quantity, unit = self.parse_quantity_unit(user_message)
        
        result = {
            "from_city": None,
            "to_city": None,
            "material": None,
            "quantity": {
                "value": quantity,
                "unit": unit,
                "original_text": user_message if quantity else None
            } if quantity else None,
            "parsing_notes": "Fallback parsing used (Gemini AI not available)",
            "fallback_mode": True
        }
        
        return result
    
    async def _get_cities_from_agent(self) -> List[Dict]:
        """Get cities list using CityAgent through agent_manager"""
        try:
            from agents.agent_manager import agent_manager
            from agents.base_agent import APIIntent
            response = await agent_manager.execute_single_intent("city", APIIntent.LIST, {})
            
            if response.success and response.data:
                return response.data.get("cities", [])
        except Exception as e:
            logger.error(f"Error getting cities from agent: {str(e)}")
        
        return []
    
    async def _get_materials_from_agent(self) -> List[Dict]:
        """Get materials list using MaterialAgent through agent_manager"""
        try:
            from agents.agent_manager import agent_manager
            from agents.base_agent import APIIntent
            response = await agent_manager.execute_single_intent("material", APIIntent.LIST, {})
            
            if response.success and response.data:
                return response.data.get("materials", [])
        except Exception as e:
            logger.error(f"Error getting materials from agent: {str(e)}")
        
        return []
    
    async def lookup_material_by_name(self, material_name: str) -> Dict[str, Any]:
        """
        Lookup material by name using MaterialAgent through agent_manager
        
        Args:
            material_name: The material name to search for
            
        Returns:
            Dict with material details or error
        """
        try:
            from agents.agent_manager import agent_manager
            from agents.base_agent import APIIntent
            
            # Use MaterialAgent to search for material
            response = await agent_manager.execute_single_intent(
                "material", APIIntent.SEARCH, {"material_name": material_name}
            )
            
            if response.success and response.data:
                materials = response.data.get("materials", [])
                
                if materials and len(materials) > 0:
                    # Return first match
                    material = materials[0]
                    return {
                        "success": True,
                        "material": {
                            "id": material.get("id"),
                            "name": material.get("name"),
                            "matched": material.get("matched", False)
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"No materials found matching '{material_name}'"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Material search failed: {response.error if response else 'Unknown error'}"
                }
                    
        except Exception as e:
            logger.error(f"Error looking up material '{material_name}': {str(e)}")
            return {
                "success": False,
                "error": f"Material lookup failed: {str(e)}"
            }
    
    async def lookup_city_by_name(self, city_name: str) -> Dict[str, Any]:
        """
        Lookup city by name using CityAgent with confirmation flow
        
        Args:
            city_name: The city name to search for
            
        Returns:
            Dict with city details, confirmation requirements, or suggestions
        """
        try:
            from agents.agent_manager import agent_manager
            from agents.city_agent import CityAgent
            
            # Get the city agent from agent manager
            city_agent = agent_manager.agents.get("city")
            if not city_agent or not isinstance(city_agent, CityAgent):
                return {
                    "success": False,
                    "error": "CityAgent not available"
                }
            
            # Use the new confirmation check method
            result = await city_agent.get_city_with_confirmation_check(city_name)
            
            if result["success"]:
                if result["match_type"] == "exact":
                    # Exact match found
                    exact_match = result["exact_match"]
                    return {
                        "success": True,
                        "city": {
                            "id": exact_match["id"],
                            "name": exact_match["name"],
                            "state": exact_match.get("state", "Unknown"),
                            "district": exact_match.get("district", "Unknown")
                        },
                        "match_type": "exact",
                        "confirmation_needed": False
                    }
                elif result["confirmation_needed"]:
                    # Partial matches - need user confirmation
                    suggestions = result["suggestions"]
                    suggested_city = result["suggested_city"]
                    
                    return {
                        "success": False,
                        "confirmation_needed": True,
                        "match_type": "partial",
                        "error": result["confirmation_message"],
                        "suggestions": [
                            {
                                "id": city["id"],
                                "name": city["name"],
                                "state": city.get("state", "Unknown"),
                                "district": city.get("district", "Unknown")
                            } for city in suggestions
                        ],
                        "suggested_city": {
                            "id": suggested_city["id"],
                            "name": suggested_city["name"],
                            "state": suggested_city.get("state", "Unknown"),
                            "district": suggested_city.get("district", "Unknown")
                        } if suggested_city else None,
                        "confirmation_prompt": f"Did you mean '{suggested_city['name']}' in {suggested_city.get('state', 'Unknown')}?" if suggested_city else None
                    }
                else:
                    # No matches found
                    return {
                        "success": False,
                        "error": f"No cities found matching '{city_name}'. Please check the spelling and try again.",
                        "confirmation_needed": False
                    }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "City lookup failed"),
                    "confirmation_needed": False
                }
                    
        except Exception as e:
            logger.error(f"Error looking up city '{city_name}': {str(e)}")
            return {
                "success": False,
                "error": f"City lookup failed: {str(e)}",
                "confirmation_needed": False
            }
    
    async def confirm_city_choice(self, suggested_city: Dict[str, Any]) -> Dict[str, Any]:
        """
        Confirm user's city choice and return the city information
        
        Args:
            suggested_city: The city object that user confirmed
            
        Returns:
            Dict with confirmed city details
        """
        try:
            if suggested_city and "id" in suggested_city:
                return {
                    "success": True,
                    "city": {
                        "id": suggested_city["id"],
                        "name": suggested_city["name"],
                        "state": suggested_city.get("state", "Unknown"),
                        "district": suggested_city.get("district", "Unknown")
                    },
                    "match_type": "confirmed",
                    "confirmation_needed": False
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid city selection",
                    "confirmation_needed": False
                }
        except Exception as e:
            logger.error(f"Error confirming city choice: {str(e)}")
            return {
                "success": False,
                "error": f"City confirmation failed: {str(e)}",
                "confirmation_needed": False
            }
    
    async def _fuzzy_city_search(self, city_name: str) -> Dict[str, Any]:
        """
        Perform fuzzy search for cities when exact/partial matches fail
        """
        try:
            # Get a broader list of cities for fuzzy matching
            url = f"{self.city_api_base}/cities"
            params = {
                "max_results": "100",
                "embedded": json.dumps({
                    "district": 1,
                    "district.state": 1
                })
            }
            
            headers = self._get_api_headers()
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    cities = data.get("_items", [])
                    
                    # Calculate similarity scores
                    similarities = []
                    for city in cities:
                        city_name_api = city.get("name", "").lower()
                        similarity = SequenceMatcher(None, city_name, city_name_api).ratio()
                        if similarity > 0.6:  # Threshold for suggestions
                            similarities.append({
                                "city": city,
                                "similarity": similarity
                            })
                    
                    # Sort by similarity
                    similarities.sort(key=lambda x: x["similarity"], reverse=True)
                    
                    if similarities:
                        suggestions = []
                        for sim in similarities[:5]:  # Top 5 suggestions
                            city = sim["city"]
                            suggestions.append({
                                "id": city["_id"],
                                "name": city["name"],
                                "state": city.get("district", {}).get("state", {}).get("name", "Unknown"),
                                "similarity": round(sim["similarity"] * 100, 1)
                            })
                        
                        return {
                            "success": False,
                            "error": f"No exact match found for '{city_name}'",
                            "suggestions": suggestions,
                            "suggestion_message": f"Did you mean one of these cities?"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"No cities found matching '{city_name}'. Please check the spelling and try again."
                        }
                else:
                    return {
                        "success": False,
                        "error": "Failed to fetch cities for fuzzy search"
                    }
                    
        except Exception as e:
            logger.error(f"Fuzzy search failed for '{city_name}': {str(e)}")
            return {
                "success": False,
                "error": f"Fuzzy search failed: {str(e)}"
            }
    
    async def enhanced_trip_and_parcel_creation(self, user_message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced workflow for creating trips and parcels with proper city lookup and Gemini context understanding
        
        Args:
            user_message: User's natural language request
            user_context: User context including user_id, etc.
            
        Returns:
            Complete workflow result with trip and parcel creation
        """
        # Extract user_id from user_context
        user_id = user_context.get("user_id")
        if not user_id:
            return {
                "success": False,
                "error": "User ID is required for trip and parcel creation"
            }
        try:
            # Step 1: Use Gemini to parse the user message for city names, material, quantity, etc.
            if self.model:
                parsing_result = await self._parse_trip_parcel_request_with_gemini(user_message)
            else:
                parsing_result = self._parse_trip_parcel_request_basic(user_message)
            
            if "error" in parsing_result:
                return parsing_result
            
            # Step 2: Lookup cities using the city API
            from_city_name = parsing_result.get("from_city")
            to_city_name = parsing_result.get("to_city")
            
            if not from_city_name or not to_city_name:
                return {
                    "success": False,
                    "error": "Could not identify both source and destination cities from your message. Please specify 'from [city]' and 'to [city]'."
                }
            
            # Lookup both cities
            from_city_result = await self.lookup_city_by_name(from_city_name)
            to_city_result = await self.lookup_city_by_name(to_city_name)
            
            # Handle city lookup results
            city_errors = []
            if not from_city_result.get("success"):
                if "suggestions" in from_city_result:
                    city_errors.append(f"Source city '{from_city_name}' not found. {from_city_result['suggestion_message']}: {', '.join([s['name'] for s in from_city_result['suggestions'][:3]])}")
                else:
                    city_errors.append(f"Source city '{from_city_name}' not found: {from_city_result.get('error', 'Unknown error')}")
            
            if not to_city_result.get("success"):
                if "suggestions" in to_city_result:
                    city_errors.append(f"Destination city '{to_city_name}' not found. {to_city_result['suggestion_message']}: {', '.join([s['name'] for s in to_city_result['suggestions'][:3]])}")
                else:
                    city_errors.append(f"Destination city '{to_city_name}' not found: {to_city_result.get('error', 'Unknown error')}")
            
            if city_errors:
                return {
                    "success": False,
                    "error": ". ".join(city_errors),
                    "suggestions": {
                        "from_city": from_city_result.get("suggestions", []),
                        "to_city": to_city_result.get("suggestions", [])
                    }
                }
            
            # Step 3: Create trip using agent manager
            from agents.agent_manager import agent_manager
            from agents.agent_manager import WorkflowIntent
            
            # Prepare trip creation data with user context
            trip_creation_data = {
                "message": user_message,
                "user_id": user_id,
                **user_context  # Pass the full user context including current_company
            }
            
            print(f"GeminiService: Passing data to trip creation workflow: {trip_creation_data}")
            print(f"GeminiService: current_company in data: {trip_creation_data.get('current_company')}")
            
            trip_response = await agent_manager.execute_workflow(
                WorkflowIntent.CREATE_TRIP_ADVANCED,
                trip_creation_data
            )
            
            if not trip_response.success:
                return {
                    "success": False,
                    "error": f"Failed to create 44: {trip_response.error}"
                }
            
            # Extract trip ID from nested response structure
            trip_id = None
            if trip_response.data:
                # Try to get trip_id from the nested trip_result
                trip_result = trip_response.data.get("trip_result", {})
                trip_id = trip_result.get("trip_id")
                
                # Fallback to direct access
                if not trip_id:
                    trip_id = trip_response.data.get("trip_id")
            
            if not trip_id:
                logger.error(f"Trip ID extraction failed. Response structure: {trip_response.data}")
                return {
                    "success": False,
                    "error": f"Trip was created but no trip ID was returned. Response: {trip_response.data}"
                }
            
            # Step 4: Create parcel with city IDs and parsed details  
            
            parcel_creation_data = {
                "message": user_message,
                "user_id": user_id,
                "trip_id": trip_id,
                "from_city_id": from_city_result["city"]["id"],
                "to_city_id": to_city_result["city"]["id"],
                "material_type": parsing_result.get("material_type"),
                "quantity": parsing_result.get("quantity", 30),
                "quantity_unit": parsing_result.get("quantity_unit", "ton"),
                "cost": parsing_result.get("cost", 200000),  # Default from your example
                **user_context  # Pass the full user context including current_company
            }
            
            parcel_response = await agent_manager.execute_workflow(
                WorkflowIntent.CREATE_PARCEL_FOR_TRIP,
                parcel_creation_data
            )
            
            if not parcel_response.success:
                return {
                    "success": False,
                    "error": f"Trip created successfully (ID: {trip_id}) but parcel creation failed: {parcel_response.error}"
                }
            
            # Step 5: Return success response
            return {
                "success": True,
                "trip_id": trip_id,
                "parcel_id": parcel_response.data.get("parcel_id"),
                "from_city": from_city_result["city"],
                "to_city": to_city_result["city"],
                "parsing_details": parsing_result,
                "message": f"Successfully created trip ({trip_id}) and parcel from {from_city_result['city']['name']} to {to_city_result['city']['name']}"
            }
            
        except Exception as e:
            logger.error(f"Enhanced trip and parcel creation failed: {str(e)}")
            return {
                "success": False,
                "error": f"Workflow failed: {str(e)}"
            }
    
    async def _parse_trip_parcel_request_with_gemini(self, user_message: str) -> Dict[str, Any]:
        """Parse trip/parcel request using Gemini AI"""
        prompt = f"""
        You are a logistics expert. Parse this user request for creating a trip and parcel:
        
        USER MESSAGE: "{user_message}"
        
        Extract the following information:
        1. FROM CITY (source/pickup location)
        2. TO CITY (destination/delivery location)  
        3. MATERIAL TYPE (what is being transported)
        4. QUANTITY (amount with unit)
        5. COST (if mentioned, otherwise null)
        
        QUANTITY UNIT CONVERSION:
        - Convert to either "KILOGRAMS" or "TONNES"
        - "kg", "kilo", "kilogram" → KILOGRAMS
        - "ton", "tonne", "metric ton" → TONNES
        
        Return ONLY valid JSON:
        {{
            "from_city": "city_name",
            "to_city": "city_name", 
            "material_type": "material_name",
            "quantity": 30,
            "quantity_unit": "TONNES",
            "cost": 200000
        }}
        
        If something cannot be identified, set it to null.
        """
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean JSON response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Gemini parsing failed: {str(e)}")
            return self._parse_trip_parcel_request_basic(user_message)
    
    def _parse_trip_parcel_request_basic(self, user_message: str) -> Dict[str, Any]:
        """Basic parsing without Gemini AI"""
        import re
        
        message_lower = user_message.lower()
        
        # Extract city names (basic patterns)
        from_match = re.search(r'from\s+([a-zA-Z\s]+?)(?:\s+to|\s+\d|\s*$)', message_lower)
        to_match = re.search(r'to\s+([a-zA-Z\s]+?)(?:\s+|$|\s+\d)', message_lower)
        
        # Extract quantity
        quantity_match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|kilo|kilogram|ton|tonne|tonnes)', message_lower)
        
        # Extract cost
        cost_match = re.search(r'(?:cost|price|rate|rs|₹)\s*(\d+(?:,\d{3})*)', message_lower)
        
        result = {
            "from_city": from_match.group(1).strip() if from_match else None,
            "to_city": to_match.group(1).strip() if to_match else None,
            "material_type": "general_goods",  # Default
            "quantity": float(quantity_match.group(1)) if quantity_match else 30,
            "quantity_unit": "TONNES" if quantity_match and "ton" in quantity_match.group(2) else "KILOGRAMS",
            "cost": int(cost_match.group(1).replace(',', '')) if cost_match else None
        }
        
        return result

# Global service instance
gemini_service = GeminiIdentificationService()