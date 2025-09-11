"""
LangChain Tools for all specialized agents
Converts existing agents into LangChain tools for better AI integration
"""
from typing import Dict, Any, Optional, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json
import asyncio

# Import existing agents
from agents.agent_manager import agent_manager, WorkflowIntent
from agents.base_agent import APIIntent

# Utility function to safely run async code in LangChain tools
def run_async_safe(coro):
    """Safely run async code in sync context"""
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we're in a loop, we need to use a thread
        import concurrent.futures
        import threading
        
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except RuntimeError:
        # No event loop running, safe to run normally
        return asyncio.run(coro)

# === MATERIAL AGENT LANGCHAIN TOOL ===

class MaterialSearchInput(BaseModel):
    """Input for material search tool"""
    material_name: str = Field(description="Name of the material to search for")

class MaterialSearchTool(BaseTool):
    """LangChain tool for searching materials"""
    name: str = "material_search"
    description: str = """
    Search for materials in the logistics system. 
    Use this when users mention materials like steel, cement, rice, bamboo, etc.
    Returns material ID and details needed for parcel creation.
    """
    args_schema: type[BaseModel] = MaterialSearchInput
    
    def _run(self, material_name: str) -> str:
        """Search for material by name"""
        async def search_material():
            response = await agent_manager.execute_single_intent(
                "material", APIIntent.SEARCH, {"material_name": material_name}
            )
            
            if response.success and response.data:
                materials = response.data.get("materials", [])
                if materials:
                    material = materials[0]
                    return f"Found material: {material['name']} (ID: {material['id']}, State: {material.get('state', 'Unknown')})"
                else:
                    return f"No materials found matching '{material_name}'"
            else:
                return f"Material search failed: {response.error}"
        
        return run_async_safe(search_material())

# === CITY AGENT LANGCHAIN TOOL ===

class CitySearchInput(BaseModel):
    """Input for city search tool"""
    city_name: str = Field(description="Name of the city to search for")

class CitySearchTool(BaseTool):
    """LangChain tool for searching cities"""
    name: str = "city_search"
    description: str = """
    Search for cities in the logistics system.
    Use this when users mention cities like Mumbai, Delhi, Chennai, etc.
    Returns city ID and details needed for trip creation.
    """
    args_schema: type[BaseModel] = CitySearchInput
    
    def _run(self, city_name: str) -> str:
        """Search for city by name"""
        async def search_city():
            response = await agent_manager.execute_single_intent(
                "city", APIIntent.SEARCH, {"city_name": city_name}
            )
            
            if response.success and response.data:
                cities = response.data.get("cities", [])
                if cities:
                    city = cities[0]
                    return f"Found city: {city['name']} (ID: {city['id']}, State: {city.get('state', 'Unknown')})"
                else:
                    return f"No cities found matching '{city_name}'"
            else:
                return f"City search failed: {response.error}"
        
        return run_async_safe(search_city())

# === TRIP CREATION LANGCHAIN TOOL ===

class TripCreationInput(BaseModel):
    """Input for trip creation tool"""
    message: str = Field(description="User message describing the trip to create")
    user_id: str = Field(description="ID of the user creating the trip")
    from_city: Optional[str] = Field(default=None, description="Source city name")
    to_city: Optional[str] = Field(default=None, description="Destination city name")

class TripCreationTool(BaseTool):
    """LangChain tool for creating trips"""
    name: str = "create_trip"
    description: str = """
    Create a new trip in the logistics system.
    Use this when users want to create trips between cities.
    Requires user message, user_id, and optionally from/to cities.
    """
    args_schema: type[BaseModel] = TripCreationInput
    
    def _run(self, message: str, user_id: str, from_city: Optional[str] = None, to_city: Optional[str] = None) -> str:
        """Create a new trip"""
        import asyncio
        
        async def create_trip():
            workflow_data = {
                "message": message,
                "user_id": user_id,
                "current_company": "62d66794e54f47829a886a1d",  # Default company
                "username": "917340224449",
                "name": "User"
            }
            
            if from_city:
                workflow_data["from_city"] = from_city
            if to_city:
                workflow_data["to_city"] = to_city
            
            response = await agent_manager.execute_workflow(
                WorkflowIntent.CREATE_TRIP_ADVANCED, workflow_data
            )
            
            if response.success:
                trip_data = response.data.get("trip_result", {})
                trip_id = trip_data.get("trip_id")
                return f"Trip created successfully! Trip ID: {trip_id}"
            else:
                return f"Trip creation failed: {response.error}"
        
        return asyncio.run(create_trip())

# === PARCEL CREATION LANGCHAIN TOOL ===

class ParcelCreationInput(BaseModel):
    """Input for parcel creation tool"""
    trip_id: str = Field(description="ID of the trip for the parcel")
    user_id: str = Field(description="ID of the user creating the parcel")
    material_name: Optional[str] = Field(default=None, description="Name of the material being shipped")
    quantity: Optional[int] = Field(default=30, description="Quantity of material")
    quantity_unit: Optional[str] = Field(default="ton", description="Unit of quantity (kg, ton)")

class ParcelCreationTool(BaseTool):
    """LangChain tool for creating parcels"""
    name: str = "create_parcel"
    description: str = """
    Create a new parcel for an existing trip.
    Use this after creating a trip, to add cargo/material to it.
    Requires trip_id, user_id, and optionally material details.
    """
    args_schema: type[BaseModel] = ParcelCreationInput
    
    def _run(self, trip_id: str, user_id: str, material_name: Optional[str] = None, 
             quantity: int = 30, quantity_unit: str = "ton") -> str:
        """Create a new parcel"""
        import asyncio
        
        async def create_parcel():
            workflow_data = {
                "trip_id": trip_id,
                "user_id": user_id,
                "current_company": "62d66794e54f47829a886a1d",
                "username": "917340224449",
                "name": "User",
                "quantity": quantity,
                "quantity_unit": quantity_unit
            }
            
            if material_name:
                workflow_data["material"] = material_name
            
            response = await agent_manager.execute_workflow(
                WorkflowIntent.CREATE_PARCEL_FOR_TRIP, workflow_data
            )
            
            if response.success:
                parcel_data = response.data.get("parcel_result", {})
                parcel_id = parcel_data.get("parcel_id")
                
                # Check if consignor selection is triggered
                if response.data.get("requires_user_input"):
                    consignor_info = response.data.get("consignor_selection", {})
                    partners = consignor_info.get("partners", [])
                    if partners:
                        partner_list = ", ".join([f"{i+1}. {p['name']}" for i, p in enumerate(partners[:3])])
                        return f"Parcel created successfully! Parcel ID: {parcel_id}. Please select a consignor: {partner_list}"
                
                return f"Parcel created successfully! Parcel ID: {parcel_id}"
            else:
                return f"Parcel creation failed: {response.error}"
        
        return asyncio.run(create_parcel())

# === TRIP AND PARCEL COMBINED LANGCHAIN TOOL ===

class TripAndParcelInput(BaseModel):
    """Input for combined trip and parcel creation"""
    message: str = Field(description="User message describing the trip and cargo")
    user_id: str = Field(description="ID of the user")
    from_city: str = Field(description="Source city name")
    to_city: str = Field(description="Destination city name")
    material_name: Optional[str] = Field(default=None, description="Material to transport")

class TripAndParcelTool(BaseTool):
    """LangChain tool for creating trip and parcel together"""
    name: str = "create_trip_and_parcel"
    description: str = """
    Create a complete logistics shipment: trip + parcel in one operation.
    Use this when users want to ship materials from one city to another.
    This is the most common logistics operation.
    """
    args_schema: type[BaseModel] = TripAndParcelInput
    
    def _run(self, message: str, user_id: str, from_city: str, to_city: str, 
             material_name: Optional[str] = None) -> str:
        """Create trip and parcel together"""
        import asyncio
        
        async def create_trip_and_parcel():
            # Use the enhanced Gemini service workflow
            from gemini_service import gemini_service
            
            user_context = {
                "user_id": user_id,
                "current_company": "62d66794e54f47829a886a1d",
                "username": "917340224449",
                "name": "User"
            }
            
            response = await gemini_service.enhanced_trip_and_parcel_creation(
                message, user_context
            )
            
            if response.get("success"):
                trip_id = response.get("trip_id")
                parcel_id = response.get("parcel_id")
                
                result = f"Successfully created trip ({trip_id}) and parcel"
                if parcel_id:
                    result += f" ({parcel_id})"
                result += f" from {from_city} to {to_city}"
                
                # Check for consignor selection
                if response.get("requires_user_input"):
                    result += ". Please select a consignor from the available preferred partners."
                
                return result
            else:
                return f"Failed to create trip and parcel: {response.get('error', 'Unknown error')}"
        
        return asyncio.run(create_trip_and_parcel())

# === CONSIGNOR SELECTION LANGCHAIN TOOL ===

class ConsignorSelectionInput(BaseModel):
    """Input for consignor selection tool"""
    company_id: Optional[str] = Field(default="62d66794e54f47829a886a1d", description="Company ID to search partners for")

class ConsignorSelectionTool(BaseTool):
    """LangChain tool for consignor selection"""
    name: str = "get_consignor_partners"
    description: str = """
    Get list of preferred partners for consignor selection.
    Use this when users need to select a consignor for their shipment.
    Shows available logistics partners.
    """
    args_schema: type[BaseModel] = ConsignorSelectionInput
    
    def _run(self, company_id: str = "62d66794e54f47829a886a1d") -> str:
        """Get preferred partners for consignor selection"""
        import asyncio
        
        async def get_partners():
            response = await agent_manager.execute_single_intent(
                "consignor_selector", APIIntent.SEARCH, {
                    "company_id": company_id,
                    "page": 0,
                    "page_size": 5
                }
            )
            
            if response.success and response.data:
                partners = response.data.get("partners", [])
                if partners:
                    partner_list = []
                    for i, partner in enumerate(partners, 1):
                        partner_list.append(f"{i}. {partner['name']} ({partner['city']})")
                    
                    result = "Available preferred partners:\n" + "\n".join(partner_list)
                    result += "\n\nPlease select a partner by number, or type 'more' for additional options."
                    return result
                else:
                    return "No preferred partners found for your company."
            else:
                return f"Failed to get preferred partners: {response.error}"
        
        return asyncio.run(get_partners())

# === COLLECT ALL TOOLS ===

def get_all_langchain_tools() -> List[BaseTool]:
    """Get all LangChain tools for the agent system"""
    return [
        MaterialSearchTool(),
        CitySearchTool(),
        TripCreationTool(),
        ParcelCreationTool(),
        TripAndParcelTool(),
        ConsignorSelectionTool()
    ]

# === TOOL DESCRIPTIONS FOR AI ===

TOOL_USAGE_GUIDE = """
Available Logistics Tools:

1. material_search: Search for materials by name (steel, cement, rice, etc.)
2. city_search: Search for cities by name (Mumbai, Delhi, Chennai, etc.)  
3. create_trip: Create a new trip between cities
4. create_parcel: Create a parcel for an existing trip
5. create_trip_and_parcel: Create complete shipment (most common - use this for "send X from Y to Z")
6. get_consignor_partners: Get list of preferred logistics partners

Most Common Workflows:
- "Ship steel from Mumbai to Delhi" → use create_trip_and_parcel
- "Find iron materials" → use material_search  
- "Create trip to Chennai" → use create_trip
- "Who are the logistics partners?" → use get_consignor_partners
"""