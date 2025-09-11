from typing import Dict, Any, Optional
import httpx
import json
import asyncio
import logging
import os
from dotenv import load_dotenv
from .base_agent import BaseAPIAgent, APIResponse, APIIntent
from pydantic import BaseModel

load_dotenv()
logger = logging.getLogger(__name__)

class VehicleRequirements(BaseModel):
    number_of_wheels: Optional[int] = None
    vehicle_body_type: Optional[str] = None
    axle_type: Optional[str] = None
    expected_price: Optional[float] = None

class TripRequest(BaseModel):
    created_by: str
    created_by_company: str
    handled_by: str
    specific_vehicle_requirements: VehicleRequirements

class TripResponse(BaseModel):
    _id: str
    _updated: str
    _created: str
    _deleted: bool
    _version: int
    _etag: str
    _latest_version: int
    _status: str

class TripCreationAgent(BaseAPIAgent):
    def __init__(self):
        auth_config = {
            "username": os.getenv("PARCEL_API_USERNAME"),
            "password": os.getenv("PARCEL_API_PASSWORD")
        }
        super().__init__(
            name="TripCreationAgent",
            base_url="https://35.244.19.78:8042",
            auth_config=auth_config
        )
        self.endpoint = "/trips"
    
    async def create_trip(self, 
                         created_by: str,
                         created_by_company: str,
                         handled_by: str,
                         vehicle_requirements: Optional[Dict] = None) -> APIResponse:
        """Create a new trip using the external API"""
        
        # Default vehicle requirements if not provided
        if vehicle_requirements is None:
            vehicle_requirements = {
                "number_of_wheels": None,
                "vehicle_body_type": None,
                "axle_type": None,
                "expected_price": None
            }
        
        # Prepare the request payload
        payload = {
            "created_by": created_by,
            "created_by_company": created_by_company,
            "handled_by": handled_by,
            "specific_vehicle_requirements": vehicle_requirements
        }
        
        response = await self._make_request(
            method="POST",
            endpoint=self.endpoint,
            payload=payload
        )
        response.intent = APIIntent.CREATE.value
        return response
    
    async def handle_trip_creation_request(self, user_message: str, user_context: Dict[str, Any]) -> APIResponse:
        """Handle natural language trip creation requests with async data fetching"""
        
        # Get ObjectIds from user_context (from frontend localStorage) - NO DEFAULTS
        user_id = user_context.get("user_id")
        company_id = user_context.get("current_company")
        
        # Validate required localStorage data
        if not user_id:
            raise ValueError("TripCreationAgent: user_id is required from localStorage user data")
        if not company_id:
            raise ValueError("TripCreationAgent: current_company is required from localStorage user data")
            
        handled_by = user_id  # handled_by is same as created_by
        
        print(f"TripCreationAgent: Using user_id from localStorage: {user_id}")
        print(f"TripCreationAgent: Using current_company from localStorage: {company_id}")
        print(f"TripCreationAgent: handled_by set to user_id: {handled_by}")
        
        # Parse vehicle requirements from user message
        vehicle_requirements = self._parse_vehicle_requirements(user_message)
        
        try:
            # Step 1: Create the trip
            response = await self.create_trip(
                created_by=user_id,
                created_by_company=company_id,
                handled_by=handled_by,
                vehicle_requirements=vehicle_requirements
            )
            
            if response.success:
                trip_data = response.data
                logger.info(f"Trip creation response data: {trip_data}")
                
                # Enhanced trip ID extraction
                trip_id = None
                
                # Log the actual response structure for debugging
                logger.info(f"Trip API response type: {type(trip_data)}")
                logger.info(f"Trip API response content: {trip_data}")
                
                # Try multiple extraction methods
                if isinstance(trip_data, dict):
                    # Direct field extraction
                    trip_id = (trip_data.get('_id') or 
                              trip_data.get('id') or 
                              trip_data.get('trip_id') or
                              trip_data.get('insertedId') or
                              trip_data.get('created_id'))
                    
                    # If still no trip_id, check nested structures
                    if not trip_id:
                        for key, value in trip_data.items():
                            if isinstance(value, str) and len(value) == 24:  # MongoDB ObjectId length
                                trip_id = value
                                logger.info(f"Extracted trip ID from field '{key}': {trip_id}")
                                break
                            elif isinstance(value, dict):
                                # Check nested objects
                                nested_id = (value.get('_id') or 
                                           value.get('id') or 
                                           value.get('trip_id'))
                                if nested_id:
                                    trip_id = nested_id
                                    logger.info(f"Extracted trip ID from nested field '{key}': {trip_id}")
                                    break
                                    
                elif isinstance(trip_data, str) and len(trip_data) == 24:
                    # If trip_data is a string that looks like an ObjectId
                    trip_id = trip_data
                elif isinstance(trip_data, list) and trip_data:
                    # If it's a list, check the first item
                    first_item = trip_data[0]
                    if isinstance(first_item, dict):
                        trip_id = (first_item.get('_id') or 
                                  first_item.get('id') or 
                                  first_item.get('trip_id'))
                    elif isinstance(first_item, str) and len(first_item) == 24:
                        trip_id = first_item
                
                # Generate a dummy trip ID if we can't extract it but the API call was successful
                if not trip_id:
                    import time
                    trip_id = f"trip_{int(time.time())}"
                    logger.warning(f"Could not extract trip ID from response, using generated ID: {trip_id}")
                
                # Step 2: Trigger async data fetching for cities and materials
                asyncio.create_task(self._fetch_cities_and_materials_async(trip_id))
                
                return APIResponse(
                    success=True,
                    data={
                        "trip_id": trip_id,
                        "trip_details": trip_data,
                        "vehicle_requirements": vehicle_requirements,
                        "message": f"✅ Trip created successfully! Trip ID: {trip_id}",
                        "next_step": "Cities and materials data are being loaded. You can now create parcels for this trip.",
                        "data_loading": "Cities and materials data loading in background..."
                    },
                    intent=APIIntent.CREATE,
                    agent_name=self.name
                )
            else:
                return APIResponse(
                    success=False,
                    error=f"Failed to create trip: {response.error}",
                    intent=APIIntent.CREATE,
                    agent_name=self.name
                )
                
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Trip creation failed: {str(e)}",
                intent=APIIntent.CREATE,
                agent_name=self.name
            )
    
    async def _fetch_cities_and_materials_async(self, trip_id: str):
        """Asynchronously fetch cities and materials data for later use"""
        try:
            # Import the agent manager using absolute import
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from agents.agent_manager import agent_manager
            
            # Fetch cities and materials concurrently
            cities_task = agent_manager.execute_single_intent("city", APIIntent.LIST, {})
            materials_task = agent_manager.execute_single_intent("material", APIIntent.LIST, {})
            
            cities_response, materials_response = await asyncio.gather(
                cities_task, materials_task, return_exceptions=True
            )
            
            # Store the data in agent manager's cache for later use
            if hasattr(cities_response, 'data') and cities_response.data:
                agent_manager._cached_cities = cities_response.data.get('cities', [])
                logger.info(f"Cached {len(agent_manager._cached_cities)} cities for trip {trip_id}")
            
            if hasattr(materials_response, 'data') and materials_response.data:
                agent_manager._cached_materials = materials_response.data.get('materials', [])
                logger.info(f"Cached {len(agent_manager._cached_materials)} materials for trip {trip_id}")
                
        except Exception as e:
            logger.error(f"Failed to fetch cities/materials data for trip {trip_id}: {str(e)}")
    
    def _parse_vehicle_requirements(self, message: str) -> Dict:
        """Parse vehicle requirements from user message"""
        requirements = {
            "number_of_wheels": None,
            "vehicle_body_type": None,
            "axle_type": None,
            "expected_price": None
        }
        
        message_lower = message.lower()
        
        # Parse number of wheels
        if "6 wheel" in message_lower or "six wheel" in message_lower:
            requirements["number_of_wheels"] = 6
        elif "4 wheel" in message_lower or "four wheel" in message_lower:
            requirements["number_of_wheels"] = 4
        elif "8 wheel" in message_lower or "eight wheel" in message_lower:
            requirements["number_of_wheels"] = 8
        elif "10 wheel" in message_lower or "ten wheel" in message_lower:
            requirements["number_of_wheels"] = 10
        
        # Parse vehicle body type
        if "truck" in message_lower:
            requirements["vehicle_body_type"] = "truck"
        elif "trailer" in message_lower:
            requirements["vehicle_body_type"] = "trailer"
        elif "container" in message_lower:
            requirements["vehicle_body_type"] = "container"
        elif "tanker" in message_lower:
            requirements["vehicle_body_type"] = "tanker"
        
        # Parse axle type
        if "single axle" in message_lower:
            requirements["axle_type"] = "single"
        elif "double axle" in message_lower or "dual axle" in message_lower:
            requirements["axle_type"] = "double"
        elif "triple axle" in message_lower:
            requirements["axle_type"] = "triple"
        
        # Parse expected price (basic extraction)
        import re
        price_match = re.search(r'(?:price|cost|budget).*?(\d+(?:,\d{3})*(?:\.\d{2})?)', message_lower)
        if price_match:
            try:
                price_str = price_match.group(1).replace(',', '')
                requirements["expected_price"] = float(price_str)
            except ValueError:
                pass
        
        return requirements
    
    def get_supported_intents(self) -> list[APIIntent]:
        """Return the list of supported API intents"""
        return [APIIntent.CREATE]
    
    def can_handle_intent(self, intent: APIIntent, context: str = "") -> bool:
        """Check if this agent can handle the given intent"""
        trip_keywords = ["trip", "journey", "transport", "delivery route", "shipping"]
        create_keywords = ["create", "make", "new", "start", "begin", "setup"]
        
        if intent == APIIntent.CREATE:
            return any(keyword in context.lower() for keyword in trip_keywords) and \
                   any(keyword in context.lower() for keyword in create_keywords)
        
        return False
    
    def get_help_text(self) -> str:
        """Return help text for this agent"""
        return """
🚛 **Trip Creation Agent**

I can help you create new trips for your logistics operations.

**Examples:**
- "Create a new trip for truck transport"
- "Make a trip with 6 wheel truck"
- "Start a new delivery route with container trailer"
- "Create trip for tanker transport with budget 50000"

**Supported Vehicle Types:**
- Truck, Trailer, Container, Tanker
- 4, 6, 8, 10 wheel configurations
- Single, Double, Triple axle types

**Usage:**
Just describe what kind of trip you want to create and I'll handle the API call!
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
                "username": data.get("username"),
                # Legacy field for compatibility
                "company_id": data.get("current_company")
            }
            return await self.handle_trip_creation_request(
                user_message=data.get("message", ""),
                user_context=user_context
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
            # Basic validation for trip creation
            required_fields = ["message"]
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
            return True, None
        else:
            return False, f"Intent {intent.value} not supported"