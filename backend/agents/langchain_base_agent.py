"""
LangChain Base Agent - Hybrid approach combining existing agents with LangChain
Allows existing agents to work both standalone and as LangChain tools
"""
from typing import Dict, Any, Optional, List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import asyncio
from abc import ABC, abstractmethod

from .base_agent import BaseAPIAgent, APIIntent, APIResponse

class LangChainCompatibleAgent(BaseAPIAgent, ABC):
    """
    Base class for agents that work both standalone and as LangChain tools
    """
    
    def __init__(self, name: str, base_url: str, auth_config: Dict[str, str]):
        super().__init__(name, base_url, auth_config)
    
    @abstractmethod
    def get_tool_description(self) -> str:
        """Get description for use as LangChain tool"""
        pass
    
    @abstractmethod 
    def get_tool_input_schema(self) -> Type[BaseModel]:
        """Get pydantic schema for tool inputs"""
        pass
    
    @abstractmethod
    async def execute_as_tool(self, **kwargs) -> str:
        """Execute agent as LangChain tool and return string result"""
        pass
    
    def to_langchain_tool(self) -> BaseTool:
        """Convert this agent to a LangChain tool"""
        agent_instance = self
        
        class AgentTool(BaseTool):
            name: str = agent_instance.name.lower().replace('agent', '').replace('_', '_')
            description: str = agent_instance.get_tool_description()
            args_schema = agent_instance.get_tool_input_schema()
            
            def _run(self, **kwargs) -> str:
                """Run the agent as a tool"""
                return asyncio.run(agent_instance.execute_as_tool(**kwargs))
        
        return AgentTool()

# Example of how to update MaterialAgent to be LangChain compatible
class LangChainMaterialAgentMixin:
    """Mixin to add LangChain compatibility to MaterialAgent"""
    
    def get_tool_description(self) -> str:
        return """
        Search for materials in the logistics system by name.
        Use this when users mention materials like steel, cement, rice, bamboo, iron, etc.
        Returns material ID, name, state, and hazard information needed for parcel creation.
        """
    
    def get_tool_input_schema(self) -> Type[BaseModel]:
        class MaterialSearchInput(BaseModel):
            material_name: str = Field(description="Name of the material to search for")
        
        return MaterialSearchInput
    
    async def execute_as_tool(self, material_name: str) -> str:
        """Execute material search as LangChain tool"""
        response = await self.execute(APIIntent.SEARCH, {"material_name": material_name})
        
        if response.success and response.data:
            materials = response.data.get("materials", [])
            if materials and response.data.get("match_type") == "exact":
                material = materials[0]
                return f"Found exact match: {material['name']} (ID: {material['id']}, State: {material.get('state', 'Unknown')}, Hazard: {material.get('hazard', 'Unknown')})"
            elif materials and response.data.get("match_type") == "partial":
                suggestions = [f"{m['name']} ({m.get('similarity', 0):.1%} match)" for m in materials[:3]]
                return f"No exact match found for '{material_name}'. Suggestions: {', '.join(suggestions)}"
            else:
                return f"No materials found matching '{material_name}'"
        else:
            return f"Material search failed: {response.error}"

# Example of how to update CityAgent to be LangChain compatible  
class LangChainCityAgentMixin:
    """Mixin to add LangChain compatibility to CityAgent"""
    
    def get_tool_description(self) -> str:
        return """
        Search for cities in the logistics system by name.
        Use this when users mention cities like Mumbai, Delhi, Chennai, Kolkata, Bangalore, etc.
        Returns city ID, name, state information needed for trip creation.
        """
    
    def get_tool_input_schema(self) -> Type[BaseModel]:
        class CitySearchInput(BaseModel):
            city_name: str = Field(description="Name of the city to search for")
        
        return CitySearchInput
    
    async def execute_as_tool(self, city_name: str) -> str:
        """Execute city search as LangChain tool"""
        response = await self.execute(APIIntent.SEARCH, {"city_name": city_name})
        
        if response.success and response.data:
            cities = response.data.get("cities", [])
            if cities:
                city = cities[0]
                return f"Found city: {city['name']} (ID: {city['id']}, State: {city.get('state', 'Unknown')})"
            else:
                return f"No cities found matching '{city_name}'"
        else:
            return f"City search failed: {response.error}"

# Example of how to update ConsignorSelectionAgent
class LangChainConsignorAgentMixin:
    """Mixin to add LangChain compatibility to ConsignorSelectionAgent"""
    
    def get_tool_description(self) -> str:
        return """
        Get list of preferred logistics partners for consignor selection.
        Use this when users need to select a consignor or logistics partner for their shipment.
        Shows available partners with their locations.
        """
    
    def get_tool_input_schema(self) -> Type[BaseModel]:
        class ConsignorSearchInput(BaseModel):
            company_id: Optional[str] = Field(default="62d66794e54f47829a886a1d", description="Company ID to search partners for")
            page: Optional[int] = Field(default=0, description="Page number for pagination")
        
        return ConsignorSearchInput
    
    async def execute_as_tool(self, company_id: str = "62d66794e54f47829a886a1d", page: int = 0) -> str:
        """Execute consignor search as LangChain tool"""
        response = await self.execute(APIIntent.SEARCH, {
            "company_id": company_id,
            "page": page,
            "page_size": 5
        })
        
        if response.success and response.data:
            partners = response.data.get("partners", [])
            if partners:
                partner_list = []
                for i, partner in enumerate(partners, 1):
                    partner_list.append(f"{i}. {partner['name']} - {partner['city']}")
                
                result = f"Available preferred partners:\n" + "\n".join(partner_list)
                if response.data.get("has_more"):
                    result += f"\n\nThere are more partners available. Use page={page + 1} to see more."
                result += "\n\nUser can select a partner by number or request more options."
                return result
            else:
                return "No preferred partners found for this company."
        else:
            return f"Failed to get preferred partners: {response.error}"

def create_langchain_tool_from_agent(agent_instance, tool_name: str, description: str, 
                                   input_schema: Type[BaseModel], execute_func) -> BaseTool:
    """Utility function to create LangChain tools from existing agents"""
    
    class DynamicAgentTool(BaseTool):
        name: str = tool_name
        description: str = description
        args_schema = input_schema
        
        def _run(self, **kwargs) -> str:
            return asyncio.run(execute_func(**kwargs))
    
    return DynamicAgentTool()

# Usage guide for integrating existing agents with LangChain
INTEGRATION_GUIDE = """
To make existing agents LangChain compatible:

1. Add the appropriate mixin to your agent class:
   class MaterialAgent(BaseAPIAgent, LangChainMaterialAgentMixin):

2. Or create tools dynamically:
   tool = create_langchain_tool_from_agent(
       agent_instance, 
       "material_search", 
       "Search materials",
       MaterialSearchInput,
       agent_instance.execute_as_tool
   )

3. The agent can now work both ways:
   - Standalone: await agent.execute(APIIntent.SEARCH, {...})
   - LangChain: tool._run(material_name="steel")
"""