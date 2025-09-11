"""
Agent Manager - Orchestrates multiple specialized API agents
Handles intent routing, dependency resolution, and workflow coordination
"""
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import logging
from enum import Enum
import os
from dotenv import load_dotenv

from .base_agent import BaseAPIAgent, APIIntent, APIResponse
from .city_agent import CityAgent
from .material_agent import MaterialAgent
from .trip_agent import TripAgent
from .parcel_agent import ParcelAgent
from .auth_agent import AuthAgent

load_dotenv()
logger = logging.getLogger(__name__)

class WorkflowIntent(Enum):
    """High-level workflow intents that may involve multiple agents"""
    AUTHENTICATE_USER = "authenticate_user"
    CREATE_PARCEL = "create_parcel"
    SEARCH_CITIES = "search_cities"
    SEARCH_MATERIALS = "search_materials"
    FIND_TRIPS = "find_trips"
    GET_PARCEL_STATUS = "get_parcel_status"
    CREATE_TRIP = "create_trip"
    RESOLVE_DEPENDENCIES = "resolve_dependencies"

class AgentManager:
    """
    Central orchestrator for all API agents
    Routes intents, manages dependencies, and coordinates workflows
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAPIAgent] = {}
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Initialize all specialized agents with configuration"""
        # Get authentication config (will be updated after login)
        auth_config = {
            "username": os.getenv("PARCEL_API_USERNAME"),
            "password": os.getenv("PARCEL_API_PASSWORD"),
            "token": None  # Will be set after authentication
        }
        
        # Initialize Authentication Agent first
        auth_api_url = os.getenv("AUTH_API_URL", "https://35.244.19.78:8042")
        self.agents["auth"] = AuthAgent(base_url=auth_api_url)
        
        # Initialize City Agent
        cities_api_url = os.getenv("GET_CITIES_API_URL")
        if cities_api_url:
            self.agents["city"] = CityAgent(
                base_url=cities_api_url,
                auth_config=auth_config
            )
        
        # Initialize Material Agent
        materials_api_url = os.getenv("GET_MATERIALS_API_URL")
        if materials_api_url:
            self.agents["material"] = MaterialAgent(
                base_url=materials_api_url,
                auth_config=auth_config,
                default_material_id=os.getenv("DEFAULT_MATERIAL_ID")
            )
        
        # Initialize Trip Agent
        trips_api_url = os.getenv("TRIP_API_URL")
        if trips_api_url:
            self.agents["trip"] = TripAgent(
                base_url=trips_api_url,
                auth_config=auth_config,
                handled_by=os.getenv("CREATED_BY_ID"),
                created_by=os.getenv("CREATED_BY_ID"),
                created_by_company=os.getenv("CREATED_BY_COMPANY_ID"),
                default_trip_id=os.getenv("TRIP_ID")
            )
        
        # Initialize Parcel Agent
        parcels_api_url = os.getenv("PARCEL_API_URL")
        if parcels_api_url:
            self.agents["parcel"] = ParcelAgent(
                base_url=parcels_api_url,
                auth_config=auth_config,
                created_by=os.getenv("CREATED_BY_ID"),
                created_by_company=os.getenv("CREATED_BY_COMPANY_ID")
            )
        
        logger.info(f"AgentManager: Initialized {len(self.agents)} agents: {list(self.agents.keys())}")
    
    def set_auth_token(self, token: str):
        """Set authentication token for all agents (except auth agent)"""
        for name, agent in self.agents.items():
            if name != "auth":  # Skip auth agent
                agent.auth_config["token"] = token
        logger.info("AgentManager: Updated auth token for all agents")
    
    def set_basic_auth_for_all_agents(self, username: str, password: str):
        """Set basic auth credentials for all agents (except auth agent)"""
        for name, agent in self.agents.items():
            if name != "auth":  # Skip auth agent
                agent.auth_config["username"] = username
                agent.auth_config["password"] = password
        logger.info("AgentManager: Updated basic auth credentials for all agents")
    
    def get_agent(self, agent_name: str) -> Optional[BaseAPIAgent]:
        """Get specific agent by name"""
        return self.agents.get(agent_name)
    
    async def execute_single_intent(self, agent_name: str, intent: APIIntent, 
                                  data: Dict[str, Any]) -> APIResponse:
        """Execute a single intent on a specific agent"""
        agent = self.get_agent(agent_name)
        if not agent:
            return APIResponse(
                success=False,
                error=f"Agent '{agent_name}' not found or not configured",
                agent_name="AgentManager"
            )
        
        try:
            response = await agent.execute(intent, data)
            logger.info(f"AgentManager: {agent_name} {intent.value} - Success: {response.success}")
            return response
        except Exception as e:
            logger.error(f"AgentManager: Error executing {agent_name} {intent.value}: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name=agent_name,
                intent=intent.value
            )
    
    async def resolve_city_id(self, city_name: str) -> Optional[str]:
        """Resolve city name to city ID"""
        if "city" not in self.agents:
            return None
        
        response = await self.execute_single_intent(
            "city", APIIntent.SEARCH, {"city_name": city_name}
        )
        
        if response.success and response.data:
            cities = response.data.get("cities", [])
            if cities:
                return cities[0]["id"]
        
        return None
    
    async def resolve_material_id(self, material_name: str) -> Optional[str]:
        """Resolve material name to material ID"""
        if "material" not in self.agents:
            return None
        
        response = await self.execute_single_intent(
            "material", APIIntent.SEARCH, {"material_name": material_name}
        )
        
        if response.success and response.data:
            materials = response.data.get("materials", [])
            if materials:
                return materials[0]["id"]
        
        return None
    
    async def create_or_get_trip(self, from_city_id: str = None, to_city_id: str = None) -> Optional[str]:
        """Create a new trip or get existing trip for route"""
        if "trip" not in self.agents:
            return None
        
        trip_agent = self.agents["trip"]
        
        if from_city_id and to_city_id:
            # Try to get existing trip for route
            trip_id = await trip_agent.get_or_create_trip_for_route(from_city_id, to_city_id)
        else:
            # Create simple trip without route
            trip_id = await trip_agent.create_trip_simple()
        
        return trip_id
    
    async def execute_workflow(self, workflow: WorkflowIntent, 
                             data: Dict[str, Any]) -> APIResponse:
        """Execute complex workflows involving multiple agents"""
        
        if workflow == WorkflowIntent.AUTHENTICATE_USER:
            return await self._workflow_authenticate_user(data)
        elif workflow == WorkflowIntent.CREATE_PARCEL:
            return await self._workflow_create_parcel(data)
        elif workflow == WorkflowIntent.SEARCH_CITIES:
            return await self._workflow_search_cities(data)
        elif workflow == WorkflowIntent.SEARCH_MATERIALS:
            return await self._workflow_search_materials(data)
        elif workflow == WorkflowIntent.FIND_TRIPS:
            return await self._workflow_find_trips(data)
        elif workflow == WorkflowIntent.GET_PARCEL_STATUS:
            return await self._workflow_get_parcel_status(data)
        elif workflow == WorkflowIntent.CREATE_TRIP:
            return await self._workflow_create_trip(data)
        elif workflow == WorkflowIntent.RESOLVE_DEPENDENCIES:
            return await self._workflow_resolve_dependencies(data)
        else:
            return APIResponse(
                success=False,
                error=f"Workflow {workflow.value} not implemented",
                agent_name="AgentManager"
            )
    
    async def _workflow_create_parcel(self, data: Dict[str, Any]) -> APIResponse:
        """
        Complete parcel creation workflow with dependency resolution
        Steps:
        1. Resolve from/to cities to IDs
        2. Resolve material name to ID
        3. Create or get trip
        4. Create parcel
        """
        logger.info("AgentManager: Starting CREATE_PARCEL workflow")
        workflow_results = {
            "steps": [],
            "resolved_dependencies": {},
            "final_result": None
        }
        
        try:
            # Step 1: Resolve from city
            from_city_name = data.get("from_city")
            if from_city_name:
                from_city_id = await self.resolve_city_id(from_city_name)
                if from_city_id:
                    data["from_city_id"] = from_city_id
                    workflow_results["resolved_dependencies"]["from_city"] = {
                        "name": from_city_name,
                        "id": from_city_id
                    }
                    workflow_results["steps"].append(f"✓ Resolved from city: {from_city_name} → {from_city_id}")
                else:
                    workflow_results["steps"].append(f"⚠ Could not resolve from city: {from_city_name}")
            
            # Step 2: Resolve to city
            to_city_name = data.get("to_city")
            if to_city_name:
                to_city_id = await self.resolve_city_id(to_city_name)
                if to_city_id:
                    data["to_city_id"] = to_city_id
                    workflow_results["resolved_dependencies"]["to_city"] = {
                        "name": to_city_name,
                        "id": to_city_id
                    }
                    workflow_results["steps"].append(f"✓ Resolved to city: {to_city_name} → {to_city_id}")
                else:
                    workflow_results["steps"].append(f"⚠ Could not resolve to city: {to_city_name}")
            
            # Step 3: Resolve material
            material_name = data.get("material")
            if material_name:
                material_id = await self.resolve_material_id(material_name)
                if material_id:
                    data["material_id"] = material_id
                    workflow_results["resolved_dependencies"]["material"] = {
                        "name": material_name,
                        "id": material_id
                    }
                    workflow_results["steps"].append(f"✓ Resolved material: {material_name} → {material_id}")
                else:
                    workflow_results["steps"].append(f"⚠ Could not resolve material: {material_name}")
            
            # Step 4: Create or get trip
            trip_id = await self.create_or_get_trip(
                data.get("from_city_id"), 
                data.get("to_city_id")
            )
            if trip_id:
                data["trip_id"] = trip_id
                workflow_results["resolved_dependencies"]["trip"] = {"id": trip_id}
                workflow_results["steps"].append(f"✓ Created/retrieved trip: {trip_id}")
            else:
                workflow_results["steps"].append("⚠ Could not create/retrieve trip")
                return APIResponse(
                    success=False,
                    error="Failed to create or retrieve trip - required for parcel creation",
                    agent_name="AgentManager",
                    data=workflow_results
                )
            
            # Step 5: Create parcel
            parcel_response = await self.execute_single_intent(
                "parcel", APIIntent.CREATE, data
            )
            
            if parcel_response.success:
                workflow_results["steps"].append("✓ Parcel created successfully")
                workflow_results["final_result"] = parcel_response.data
                
                return APIResponse(
                    success=True,
                    data={
                        "workflow": "CREATE_PARCEL",
                        "parcel_result": parcel_response.data,
                        "workflow_details": workflow_results
                    },
                    agent_name="AgentManager"
                )
            else:
                workflow_results["steps"].append(f"✗ Parcel creation failed: {parcel_response.error}")
                return APIResponse(
                    success=False,
                    error=f"Parcel creation failed: {parcel_response.error}",
                    agent_name="AgentManager",
                    data=workflow_results
                )
        
        except Exception as e:
            logger.error(f"AgentManager: CREATE_PARCEL workflow error: {str(e)}")
            workflow_results["steps"].append(f"✗ Workflow error: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager",
                data=workflow_results
            )
    
    async def _workflow_search_cities(self, data: Dict[str, Any]) -> APIResponse:
        """Search for cities"""
        if "city_name" in data:
            return await self.execute_single_intent("city", APIIntent.SEARCH, data)
        else:
            return await self.execute_single_intent("city", APIIntent.LIST, data)
    
    async def _workflow_search_materials(self, data: Dict[str, Any]) -> APIResponse:
        """Search for materials"""
        if "material_name" in data:
            return await self.execute_single_intent("material", APIIntent.SEARCH, data)
        else:
            return await self.execute_single_intent("material", APIIntent.LIST, data)
    
    async def _workflow_find_trips(self, data: Dict[str, Any]) -> APIResponse:
        """Find trips by criteria"""
        return await self.execute_single_intent("trip", APIIntent.SEARCH, data)
    
    async def _workflow_get_parcel_status(self, data: Dict[str, Any]) -> APIResponse:
        """Get parcel status"""
        if "parcel_id" in data:
            return await self.execute_single_intent("parcel", APIIntent.READ, data)
        else:
            return await self.execute_single_intent("parcel", APIIntent.SEARCH, data)
    
    async def _workflow_create_trip(self, data: Dict[str, Any]) -> APIResponse:
        """Create a new trip"""
        return await self.execute_single_intent("trip", APIIntent.CREATE, data)
    
    async def _workflow_resolve_dependencies(self, data: Dict[str, Any]) -> APIResponse:
        """Resolve all dependencies without creating anything"""
        workflow_results = {
            "resolved_dependencies": {},
            "steps": []
        }
        
        # Resolve cities
        for city_field in ["from_city", "to_city", "city_name"]:
            if city_field in data:
                city_name = data[city_field]
                city_id = await self.resolve_city_id(city_name)
                if city_id:
                    workflow_results["resolved_dependencies"][city_field] = {
                        "name": city_name,
                        "id": city_id
                    }
                    workflow_results["steps"].append(f"✓ Resolved {city_field}: {city_name} → {city_id}")
        
        # Resolve materials
        if "material" in data or "material_name" in data:
            material_name = data.get("material") or data.get("material_name")
            material_id = await self.resolve_material_id(material_name)
            if material_id:
                workflow_results["resolved_dependencies"]["material"] = {
                    "name": material_name,
                    "id": material_id
                }
                workflow_results["steps"].append(f"✓ Resolved material: {material_name} → {material_id}")
        
        return APIResponse(
            success=True,
            data=workflow_results,
            agent_name="AgentManager"
        )
    
    async def initialize_cache(self):
        """Initialize cache for all agents"""
        logger.info("AgentManager: Initializing cache for all agents...")
        
        tasks = []
        for agent_name, agent in self.agents.items():
            if hasattr(agent, 'initialize_cache'):
                tasks.append(agent.initialize_cache())
            elif agent_name in ["city", "material"]:
                # For city and material agents, fetch initial data to populate cache
                tasks.append(agent.execute(APIIntent.LIST, {}))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"AgentManager: Cache initialization completed. {successful}/{len(tasks)} successful")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        status = {
            "total_agents": len(self.agents),
            "agents": {}
        }
        
        for name, agent in self.agents.items():
            status["agents"][name] = {
                "name": agent.name,
                "base_url": agent.base_url,
                "cache_size": len(agent.cache),
                "supported_intents": [intent.value for intent in agent.get_supported_intents()]
            }
        
        return status
    
    async def _workflow_authenticate_user(self, data: Dict[str, Any]) -> APIResponse:
        """
        Authentication workflow
        Steps:
        1. Authenticate user with auth agent
        2. Set auth credentials for all other agents
        3. Return authentication result
        """
        logger.info("AgentManager: Starting AUTHENTICATE_USER workflow")
        
        if "auth" not in self.agents:
            return APIResponse(
                success=False,
                error="Authentication agent not available",
                agent_name="AgentManager"
            )
        
        try:
            username = data.get("username")
            password = data.get("password")
            
            if not username or not password:
                return APIResponse(
                    success=False,
                    error="Username and password are required for authentication",
                    agent_name="AgentManager"
                )
            
            # Step 1: Authenticate user
            auth_response = await self.execute_single_intent(
                "auth", APIIntent.VALIDATE, {"username": username, "password": password}
            )
            
            if auth_response.success and auth_response.data:
                # Step 2: Set auth credentials for all other agents
                self.set_basic_auth_for_all_agents(username, password)
                
                # Also set token if available
                token = auth_response.data.get("token")
                if token:
                    self.set_auth_token(f"Bearer {token}")
                
                logger.info(f"AgentManager: User {username} authenticated successfully")
                
                return APIResponse(
                    success=True,
                    data={
                        "workflow": "AUTHENTICATE_USER",
                        "authentication_result": auth_response.data,
                        "message": "User authenticated and credentials set for all agents"
                    },
                    agent_name="AgentManager"
                )
            else:
                logger.error(f"AgentManager: Authentication failed for user {username}")
                return APIResponse(
                    success=False,
                    error=f"Authentication failed: {auth_response.error}",
                    agent_name="AgentManager"
                )
        
        except Exception as e:
            logger.error(f"AgentManager: AUTHENTICATE_USER workflow error: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )
    
    async def authenticate_user_and_setup(self, username: str, password: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Convenience method to authenticate user and setup all agents
        Returns: (success, user_info, error_message)
        """
        response = await self.execute_workflow(
            WorkflowIntent.AUTHENTICATE_USER, 
            {"username": username, "password": password}
        )
        
        if response.success and response.data:
            auth_result = response.data.get("authentication_result", {})
            user_info = {
                "user_id": auth_result.get("user_id"),
                "username": auth_result.get("username"),
                "name": auth_result.get("name"),
                "email": auth_result.get("email"),
                "token": auth_result.get("token"),
                "current_company": auth_result.get("current_company"),
                "user_type": auth_result.get("user_type"),
                "role_names": auth_result.get("role_names", [])
            }
            return True, user_info, None
        else:
            return False, None, response.error

# Global agent manager instance
agent_manager = AgentManager()