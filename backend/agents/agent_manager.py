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
from .trip_creation_agent import TripCreationAgent
from .parcel_creation_agent import ParcelCreationAgent
from .consignor_selection_agent import ConsignorSelectionAgent
from .consigner_consignee_agent import ConsignerConsigneeAgent
from .parcel_update_agent import ParcelUpdateAgent

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
    CREATE_TRIP_ADVANCED = "create_trip_advanced"
    CREATE_PARCEL_FOR_TRIP = "create_parcel_for_trip"
    CREATE_TRIP_AND_PARCEL = "create_trip_and_parcel"
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
        
        # Initialize new specialized agents for trip and parcel creation
        self.agents["trip_creator"] = TripCreationAgent()
        self.agents["parcel_creator"] = ParcelCreationAgent()
        self.agents["consignor_selector"] = ConsignorSelectionAgent()
        self.agents["consigner_consignee"] = ConsignerConsigneeAgent()
        self.agents["parcel_updater"] = ParcelUpdateAgent()
        
        # Initialize cache for cities and materials data
        self._cached_cities = []
        self._cached_materials = []
        
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
        elif workflow == WorkflowIntent.CREATE_TRIP_ADVANCED:
            return await self._workflow_create_trip_advanced(data)
        elif workflow == WorkflowIntent.CREATE_PARCEL_FOR_TRIP:
            return await self._workflow_create_parcel_for_trip(data)
        elif workflow == WorkflowIntent.CREATE_TRIP_AND_PARCEL:
            return await self._workflow_create_trip_and_parcel(data)
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
    
    async def _workflow_create_trip_advanced(self, data: Dict[str, Any]) -> APIResponse:
        """
        Advanced trip creation workflow using the new TripCreationAgent
        This uses the external API at https://35.244.19.78:8042/trips
        """
        logger.info("AgentManager: Starting CREATE_TRIP_ADVANCED workflow")
        
        if "trip_creator" not in self.agents:
            return APIResponse(
                success=False,
                error="Trip creation agent not available",
                agent_name="AgentManager"
            )
        
        try:
            trip_creator = self.agents["trip_creator"]
            
            # Extract user context for trip creation from localStorage data
            user_id = data.get("user_id")
            # Use static current_company or fall back to data
            current_company = data.get("current_company", "62d66794e54f47829a886a1d")
            
            if not user_id:
                return APIResponse(
                    success=False,
                    error="user_id is required from localStorage authentication data for trip creation",
                    agent_name="AgentManager"
                )
            
            # Ensure current_company is always set
            if not current_company:
                current_company = "62d66794e54f47829a886a1d"
            
            user_context = {
                "user_id": user_id,
                "current_company": current_company,
                "name": data.get("name", "User"),
                "email": data.get("email", ""),
                "username": data.get("username", ""),
                "user_record": data.get("user_record"),
                # Legacy field mappings
                "company_id": current_company,
                "handled_by": user_id  # handled_by is same as created_by (user_id)
            }
            
            print(f"AgentManager: user_context for trip creation: {user_context}")
            
            # Use natural language processing to create trip
            response = await trip_creator.handle_trip_creation_request(
                user_message=data.get("message", "Create a new trip"),
                user_context=user_context
            )
            
            if response.success:
                logger.info(f"AgentManager: Trip created successfully with ID: {response.data.get('trip_id')}")
                return APIResponse(
                    success=True,
                    data={
                        "workflow": "CREATE_TRIP_ADVANCED",
                        "trip_result": response.data,
                        "message": response.data.get("message")
                    },
                    agent_name="AgentManager"
                )
            else:
                logger.error(f"AgentManager: Trip creation failed: {response.error}")
                return APIResponse(
                    success=False,
                    error=f"Trip creation failed: {response.error}",
                    agent_name="AgentManager"
                )
                
        except Exception as e:
            logger.error(f"AgentManager: CREATE_TRIP_ADVANCED workflow error: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )
    
    async def _workflow_create_parcel_for_trip(self, data: Dict[str, Any]) -> APIResponse:
        """
        Create parcel for existing trip workflow using ParcelCreationAgent
        """
        logger.info("AgentManager: Starting CREATE_PARCEL_FOR_TRIP workflow")
        
        if "parcel_creator" not in self.agents:
            return APIResponse(
                success=False,
                error="Parcel creation agent not available",
                agent_name="AgentManager"
            )
        
        trip_id = data.get("trip_id")
        if not trip_id:
            return APIResponse(
                success=False,
                error="trip_id is required for parcel creation",
                agent_name="AgentManager"
            )
        
        try:
            parcel_creator = self.agents["parcel_creator"]
            
            # Pass through all user context data from the workflow
            # Ensure we have the required user_id from localStorage
            user_id = data.get("user_id")
            if not user_id:
                return APIResponse(
                    success=False,
                    error="user_id is required from localStorage authentication data",
                    agent_name="AgentManager"
                )
            
            # Use static current_company or fall back to data
            current_company = data.get("current_company", "62d66794e54f47829a886a1d")
            if not current_company:
                current_company = "62d66794e54f47829a886a1d"
            
            user_context = {
                "user_id": user_id,
                "username": data.get("username", ""),
                "name": data.get("name", "User"),
                "email": data.get("email", ""),
                "current_company": current_company,
                "user_record": data.get("user_record"),
                # Legacy fallbacks for older code
                "company_id": current_company,
                "user_name": data.get("name", "User")
            }
            
            print(f"AgentManager: user_context for parcel creation: {user_context}")
            
            # Get cached cities and materials data, or fetch if not available
            cities_data = getattr(self, '_cached_cities', [])
            materials_data = getattr(self, '_cached_materials', [])
            
            # If no cached data, try to fetch it synchronously
            if not cities_data and "city" in self.agents:
                cities_response = await self.execute_single_intent("city", APIIntent.LIST, {})
                if cities_response.success and cities_response.data:
                    cities_data = cities_response.data.get('cities', [])
                    self._cached_cities = cities_data
            
            if not materials_data and "material" in self.agents:
                materials_response = await self.execute_single_intent("material", APIIntent.LIST, {})
                if materials_response.success and materials_response.data:
                    materials_data = materials_response.data.get('materials', [])
                    self._cached_materials = materials_data
            
            response = await parcel_creator.handle_parcel_creation_request(
                user_message=data.get("message", "Create a parcel"),
                user_context=user_context,
                trip_id=trip_id,
                cities_data=cities_data,
                materials_data=materials_data,
                from_city_id=data.get("from_city_id"),
                to_city_id=data.get("to_city_id"),
                material_type=data.get("material_type"),
                quantity=data.get("quantity"),
                quantity_unit=data.get("quantity_unit"),
                cost=data.get("cost")
            )
            
            if response.success:
                logger.info(f"AgentManager: Parcel created successfully with ID: {response.data.get('parcel_id')}")
                
                # Trigger NEW consigner/consignee selection after successful parcel creation
                parcel_id = response.data.get('parcel_id')
                consigner_response = await self._trigger_consigner_consignee_flow(data, trip_id, parcel_id)
                
                if consigner_response.success:
                    logger.info("AgentManager: Consigner/Consignee selection initiated")
                    
                    # Get the formatted message with partner options and button data
                    formatted_partners = consigner_response.data.get("message", "")
                    button_data = consigner_response.data.get("button_data", {})
                    
                    # Create comprehensive message with parcel success + consigner selection
                    full_message = f"{response.data.get('message')}\n\n{formatted_partners}"
                    
                    return APIResponse(
                        success=True,
                        data={
                            "workflow": "CREATE_PARCEL_FOR_TRIP",
                            "parcel_result": response.data,
                            "consigner_selection": consigner_response.data,
                            "message": full_message,
                            "button_data": button_data,
                            "available_partners": consigner_response.data.get("partners", []),
                            "current_page": 0,
                            "requires_user_input": True,
                            "input_type": "consigner_selection",
                            "partner_buttons": button_data.get("buttons", []),
                            "action_buttons": button_data.get("action_buttons", [])
                        },
                        agent_name="AgentManager"
                    )
                else:
                    logger.warning(f"AgentManager: Consigner selection failed: {consigner_response.error}")
                    # Still return success for parcel creation even if consigner selection fails
                    return APIResponse(
                        success=True,
                        data={
                            "workflow": "CREATE_PARCEL_FOR_TRIP",
                            "parcel_result": response.data,
                            "message": f"{response.data.get('message')} (Consigner selection unavailable)"
                        },
                        agent_name="AgentManager"
                    )
            else:
                logger.error(f"AgentManager: Parcel creation failed: {response.error}")
                return APIResponse(
                    success=False,
                    error=f"Parcel creation failed: {response.error}",
                    agent_name="AgentManager"
                )
                
        except Exception as e:
            logger.error(f"AgentManager: CREATE_PARCEL_FOR_TRIP workflow error: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )
    
    async def _workflow_create_trip_and_parcel(self, data: Dict[str, Any]) -> APIResponse:
        """
        Complete workflow: Create trip first, then create parcel for that trip
        """
        logger.info("AgentManager: Starting CREATE_TRIP_AND_PARCEL workflow")
        
        workflow_results = {
            "steps": [],
            "trip_result": None,
            "parcel_result": None
        }
        
        try:
            # Step 1: Create trip
            trip_response = await self._workflow_create_trip_advanced(data)
            
            if not trip_response.success:
                workflow_results["steps"].append(f"✗ Trip creation failed: {trip_response.error}")
                return APIResponse(
                    success=False,
                    error=f"Trip creation failed: {trip_response.error}",
                    agent_name="AgentManager",
                    data=workflow_results
                )
            
            trip_id = trip_response.data.get("trip_result", {}).get("trip_id")
            if not trip_id:
                workflow_results["steps"].append("✗ Trip created but no trip ID returned")
                return APIResponse(
                    success=False,
                    error="Trip created but no trip ID returned",
                    agent_name="AgentManager",
                    data=workflow_results
                )
            
            workflow_results["steps"].append(f"✓ Trip created successfully: {trip_id}")
            workflow_results["trip_result"] = trip_response.data.get("trip_result")
            
            # Step 2: Create parcel for the trip
            parcel_data = data.copy()
            parcel_data["trip_id"] = trip_id
            
            parcel_response = await self._workflow_create_parcel_for_trip(parcel_data)
            
            if parcel_response.success:
                workflow_results["steps"].append("✓ Parcel created successfully")
                workflow_results["parcel_result"] = parcel_response.data.get("parcel_result")
                
                # Step 3: Trigger NEW consigner/consignee selection after successful parcel creation
                parcel_id = workflow_results["parcel_result"].get("parcel_id")
                consigner_response = await self._trigger_consigner_consignee_flow(data, trip_id, parcel_id)
                
                if consigner_response.success:
                    workflow_results["steps"].append("✓ Consigner selection initiated")
                    workflow_results["consigner_selection"] = consigner_response.data
                    
                    # Get the formatted message and button data
                    formatted_partners = consigner_response.data.get("message", "")
                    button_data = consigner_response.data.get("button_data", {})
                    success_message = f"Successfully created trip ({trip_id}) and parcel ({parcel_id}).\n\n{formatted_partners}"
                    
                    return APIResponse(
                        success=True,
                        data={
                            "workflow": "CREATE_TRIP_AND_PARCEL",
                            "trip_id": trip_id,
                            "parcel_id": parcel_id,
                            "workflow_details": workflow_results,
                            "consigner_selection": workflow_results.get("consigner_selection"),
                            "message": success_message,
                            "button_data": button_data,
                            "available_partners": consigner_response.data.get("partners", []),
                            "current_page": 0,
                            "company_id": data.get("current_company"),
                            "requires_user_input": True,
                            "input_type": "consigner_selection",
                            "partner_buttons": button_data.get("buttons", []),
                            "action_buttons": button_data.get("action_buttons", [])
                        },
                        agent_name="AgentManager"
                    )
                else:
                    workflow_results["steps"].append(f"⚠ Consigner selection failed: {consigner_response.error}")
                    
                    return APIResponse(
                        success=True,
                        data={
                            "workflow": "CREATE_TRIP_AND_PARCEL",
                            "trip_id": trip_id,
                            "parcel_id": parcel_id,
                            "workflow_details": workflow_results,
                            "message": f"Successfully created trip ({trip_id}) and parcel ({parcel_id}). (Consigner selection unavailable)",
                            "requires_user_input": False
                        },
                        agent_name="AgentManager"
                    )
            else:
                workflow_results["steps"].append(f"✗ Parcel creation failed: {parcel_response.error}")
                return APIResponse(
                    success=False,
                    error=f"Parcel creation failed after successful trip creation: {parcel_response.error}",
                    agent_name="AgentManager",
                    data=workflow_results
                )
                
        except Exception as e:
            logger.error(f"AgentManager: CREATE_TRIP_AND_PARCEL workflow error: {str(e)}")
            workflow_results["steps"].append(f"✗ Workflow error: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager",
                data=workflow_results
            )
    
    async def _trigger_consigner_consignee_flow(self, data: Dict[str, Any], trip_id: str, parcel_id: str) -> APIResponse:
        """
        Trigger the NEW consigner/consignee selection flow (shows ONLY consigner first)
        """
        logger.info("AgentManager: Triggering NEW consigner/consignee selection flow")
        
        if "consigner_consignee" not in self.agents:
            return APIResponse(
                success=False,
                error="ConsignerConsigneeAgent not available",
                agent_name="AgentManager"
            )
        
        try:
            # Get company ID from user context
            company_id = (
                data.get("current_company") or 
                data.get("company_id") or 
                data.get("created_by_company") or
                "62d66794e54f47829a886a1d"
            )
            
            print(f"AgentManager: Starting consigner/consignee flow for company: {company_id}")
            print(f"AgentManager: Trip ID: {trip_id}, Parcel ID: {parcel_id}")
            
            # Initialize the NEW consigner/consignee selection process
            flow_data = {
                "company_id": company_id,
                "trip_id": trip_id,
                "parcel_id": parcel_id,
                "user_context": {
                    "user_id": data.get("user_id"),
                    "current_company": company_id,
                    "username": data.get("username"),
                    "name": data.get("name"),
                    "email": data.get("email")
                }
            }
            
            # Start the flow - this will show ONLY consigner options
            response = await self.start_consigner_consignee_flow(flow_data)
            
            if response.success:
                logger.info("AgentManager: NEW consigner selection initiated (consigner only)")
                return response
            else:
                logger.error(f"AgentManager: Failed to start consigner/consignee flow: {response.error}")
                return response
                
        except Exception as e:
            logger.error(f"AgentManager: Error triggering NEW consigner/consignee flow: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )

    async def _trigger_consignor_selection(self, data: Dict[str, Any], trip_id: str, parcel_id: str) -> APIResponse:
        """
        Trigger consignor selection after successful parcel creation
        """
        logger.info("AgentManager: Triggering consignor selection workflow")
        
        if "consignor_selector" not in self.agents:
            return APIResponse(
                success=False,
                error="Consignor selection agent not available",
                agent_name="AgentManager"
            )
        
        try:
            consignor_agent = self.agents["consignor_selector"]
            
            # Get company ID from user context - try multiple fields
            company_id = (
                data.get("current_company") or 
                data.get("company_id") or 
                data.get("created_by_company") or
                "62d66794e54f47829a886a1d"
            )
            
            print(f"AgentManager: Triggering consignor selection for company: {company_id}")
            print(f"AgentManager: Available user context keys: {list(data.keys())}")
            
            # Get preferred partners (first page, 5 items)
            consignor_data = {
                "company_id": company_id,
                "page": 0,
                "page_size": 5,
                "trip_id": trip_id,
                "parcel_id": parcel_id
            }
            
            response = await consignor_agent.execute(APIIntent.SEARCH, consignor_data)
            
            if response.success and response.data:
                partners = response.data.get("partners", [])
                
                if partners:
                    # Format partners for display with button format
                    formatted_message = consignor_agent.format_partners_for_chat(
                        partners, 
                        response.data.get("page", 0)
                    )
                    
                    # Create button data for frontend
                    button_data = consignor_agent.format_partners_as_buttons(
                        partners,
                        response.data.get("page", 0)
                    )
                    button_data["has_more"] = response.data.get("has_more", False)
                    
                    return APIResponse(
                        success=True,
                        data={
                            "partners": partners,
                            "available_partners": partners,  # Store for selection handling
                            "formatted_message": formatted_message,
                            "button_data": button_data,
                            "has_more": response.data.get("has_more", False),
                            "current_page": response.data.get("page", 0),
                            "total_available": response.data.get("total_available", 0),
                            "trip_id": trip_id,
                            "parcel_id": parcel_id,
                            "requires_user_input": True,
                            "input_type": "partner_selection"
                        },
                        agent_name="AgentManager"
                    )
                else:
                    return APIResponse(
                        success=True,
                        data={
                            "partners": [],
                            "formatted_message": "No preferred partners found for your company. You can continue without selecting a consignor.",
                            "has_more": False,
                            "page": 0,
                            "total_available": 0,
                            "trip_id": trip_id,
                            "parcel_id": parcel_id
                        },
                        agent_name="AgentManager"
                    )
            else:
                return APIResponse(
                    success=False,
                    error=f"Failed to fetch preferred partners: {response.error}",
                    agent_name="AgentManager"
                )
                
        except Exception as e:
            logger.error(f"AgentManager: Error triggering consignor selection: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )

    async def handle_consignor_selection(self, data: Dict[str, Any]) -> APIResponse:
        """
        Handle user's consignor selection from preferred partners
        """
        logger.info("AgentManager: Handling consignor selection")
        
        if "consignor_selector" not in self.agents:
            return APIResponse(
                success=False,
                error="Consignor selection agent not available",
                agent_name="AgentManager"
            )
        
        try:
            consignor_agent = self.agents["consignor_selector"]
            
            # Check if user wants to see more partners
            user_input = data.get("selection", "").lower().strip()
            
            if user_input == "more":
                # Get next page of partners
                page = data.get("current_page", 0) + 1
                company_id = data.get("company_id", "62d66794e54f47829a886a1d")
                
                consignor_data = {
                    "company_id": company_id,
                    "page": page,
                    "page_size": 5
                }
                
                response = await consignor_agent.execute(APIIntent.SEARCH, consignor_data)
                
                if response.success and response.data:
                    partners = response.data.get("partners", [])
                    formatted_message = consignor_agent.format_partners_for_chat(partners, page)
                    
                    return APIResponse(
                        success=True,
                        data={
                            "action": "show_more_partners",
                            "partners": partners,
                            "formatted_message": formatted_message,
                            "has_more": response.data.get("has_more", False),
                            "page": page
                        },
                        agent_name="AgentManager"
                    )
                    
            elif user_input == "skip":
                # User chose to skip consignor selection
                return APIResponse(
                    success=True,
                    data={
                        "action": "skip_consignor",
                        "message": "Consignor selection skipped. Your trip and parcel are ready!"
                    },
                    agent_name="AgentManager"
                )
                
            elif user_input.isdigit() or self._is_button_selection(user_input, data.get("available_partners", [])) or self._is_partner_name_selection(user_input, data.get("available_partners", [])):
                # User selected a partner by number, button text, or direct name
                available_partners = data.get("available_partners", [])
                selected_partner = None
                
                if user_input.isdigit():
                    selection_number = int(user_input)
                    if 1 <= selection_number <= len(available_partners):
                        selected_partner = available_partners[selection_number - 1]
                elif self._is_button_selection(user_input, available_partners):
                    # Extract number from button text like "1. Partner Name"
                    selection_number = self._extract_number_from_button_text(user_input)
                    if selection_number and 1 <= selection_number <= len(available_partners):
                        selected_partner = available_partners[selection_number - 1]
                else:
                    # Direct partner name selection
                    selected_partner = self._find_partner_by_name(user_input, available_partners)
                
                if selected_partner:
                    partner_name = selected_partner["name"]
                    partner_id = selected_partner.get("id")
                    partner_city = selected_partner.get("city", "Unknown City")
                    
                    # Call getUserCompany API for the selected partner
                    user_companies_response = await self._call_get_user_companies_api(partner_id)
                    
                    trip_id = data.get("trip_id", "")
                    parcel_id = data.get("parcel_id", "")
                    
                    if user_companies_response.get("success"):
                        companies_data = user_companies_response.get("companies", [])
                        
                        # Check if partner has multiple companies - if so, show company selection
                        if len(companies_data) > 1:
                            # Multiple companies - user needs to select one
                            if "user_company" in self.agents:
                                user_company_agent = self.agents["user_company"]
                                formatted_companies = user_company_agent.format_companies_for_selection(companies_data)
                                company_buttons = user_company_agent.format_companies_as_buttons(companies_data)
                                
                                return APIResponse(
                                    success=True,
                                    data={
                                        "action": "company_selection_required",
                                        "step": "company_selection",
                                        "selected_partner": {
                                            "id": partner_id,
                                            "name": partner_name,
                                            "city": partner_city
                                        },
                                        "companies": companies_data,
                                        "formatted_message": f"**Partner Selected:** {partner_name}\n\n{formatted_companies}",
                                        "button_data": company_buttons,
                                        "trip_id": trip_id,
                                        "parcel_id": parcel_id,
                                        "requires_user_input": True,
                                        "input_type": "company_selection"
                                    },
                                    agent_name="AgentManager"
                                )
                        
                        # Single company or no companies - proceed with selection
                        selected_company = companies_data[0] if companies_data else None
                        companies_info = f"\n**Partner Company:** {selected_company.get('name', 'N/A')}" if selected_company else "\n**Partner Companies:** No companies found"
                    else:
                        companies_data = []
                        selected_company = None
                        companies_info = f"\n**Partner Companies:** Error fetching companies - {user_companies_response.get('error', 'Unknown error')}"
                    
                    # Create confirmation message
                    confirmation_message = f"✅ **Partner Selected Successfully**\n\n"
                    confirmation_message += f"**Selected Partner:** {partner_name}\n"
                    confirmation_message += f"**Location:** {partner_city}\n"
                    confirmation_message += f"**Partner ID:** {partner_id}\n"
                    confirmation_message += companies_info
                    
                    if parcel_id:
                        confirmation_message += f"\n\n📦 **Parcel ID:** {parcel_id}"
                    if trip_id:
                        confirmation_message += f"\n🚛 **Trip ID:** {trip_id}"
                    
                    confirmation_message += f"\n\n🎉 Your parcel is now linked with {partner_name}!"
                    
                    # Update consignor selection
                    response = await consignor_agent.execute(APIIntent.UPDATE, {
                        "partner_id": partner_id,
                        "partner_name": partner_name
                    })
                    
                    return APIResponse(
                        success=True,
                        data={
                            "action": "consignor_selected",
                            "selected_partner": {
                                "id": partner_id,
                                "name": partner_name,
                                "city": partner_city,
                                "companies": companies_data,
                                "selected_company": selected_company
                            },
                            "message": confirmation_message,
                            "trip_id": trip_id,
                            "parcel_id": parcel_id,
                            "user_companies_response": user_companies_response
                        },
                        agent_name="AgentManager"
                    )
                else:
                    return APIResponse(
                        success=False,
                        error=f"Invalid selection. Please enter a number between 1 and {len(available_partners)}, 'more' for more options, or 'skip' to continue.",
                        agent_name="AgentManager"
                    )
            else:
                return APIResponse(
                    success=False,
                    error="Invalid input. Please enter a number (1-5), 'more' for more options, or 'skip' to continue.",
                    agent_name="AgentManager"
                )
                
        except Exception as e:
            logger.error(f"AgentManager: Error handling consignor selection: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )
    
    async def _call_get_user_companies_api(self, user_id: str) -> Dict[str, Any]:
        """
        Call the getUserCompany API for the selected partner
        """
        try:
            import httpx
            
            # Build the API URL
            api_url = f"https://35.244.19.78:8042/get_user_companies"
            params = {"user_id": user_id}
            
            print(f"AgentManager: Calling getUserCompany API for user_id: {user_id}")
            print(f"AgentManager: API URL: {api_url}")
            
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                # Use Basic Auth
                auth = (self.agents["consignor_selector"].auth_config["username"], 
                       self.agents["consignor_selector"].auth_config["password"])
                
                response = await client.get(api_url, params=params, auth=auth)
                
                print(f"AgentManager: getUserCompany API status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"AgentManager: getUserCompany API success: found companies")
                    
                    return {
                        "success": True,
                        "companies": data.get("companies", []),
                        "total": data.get("_meta", {}).get("total", 0) if isinstance(data, dict) else 0,
                        "raw_response": data
                    }
                else:
                    error_text = response.text
                    print(f"AgentManager: getUserCompany API error: {error_text}")
                    
                    return {
                        "success": False,
                        "error": f"API call failed with status {response.status_code}: {error_text}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            print(f"AgentManager: Exception calling getUserCompany API: {str(e)}")
            return {
                "success": False,
                "error": f"Exception calling getUserCompany API: {str(e)}"
            }

    def _is_button_selection(self, user_input: str, available_partners: List[Dict]) -> bool:
        """Check if user input matches a button text format"""
        # Check if it matches pattern like "1. Partner Name"
        import re
        pattern = r'^\d+\.\s'
        if re.match(pattern, user_input):
            return True
        
        # Check if it matches any partner button text
        for i, partner in enumerate(available_partners, 1):
            button_text = f"{i}. {partner['name']}"
            if user_input.strip() == button_text.strip():
                return True
        
        return False

    def _extract_number_from_button_text(self, button_text: str) -> int:
        """Extract number from button text like '1. Partner Name'"""
        import re
        match = re.match(r'^(\d+)\.', button_text.strip())
        if match:
            return int(match.group(1))
        
        # Fallback: check against available partners
        # This is handled in the calling method
        return 0

    def _is_partner_name_selection(self, user_input: str, available_partners: List[Dict]) -> bool:
        """Check if user input matches a partner name"""
        user_input_clean = user_input.strip().lower()
        
        for partner in available_partners:
            partner_name = partner.get('name', '').strip().lower()
            if user_input_clean == partner_name:
                return True
        
        return False

    def _find_partner_by_name(self, user_input: str, available_partners: List[Dict]) -> Dict:
        """Find partner by exact name match"""
        user_input_clean = user_input.strip().lower()
        
        for partner in available_partners:
            partner_name = partner.get('name', '').strip().lower()
            if user_input_clean == partner_name:
                return partner
        
        return None
    
    async def start_consigner_consignee_flow(self, data: Dict[str, Any]) -> APIResponse:
        """
        Start the enhanced consigner/consignee selection flow
        """
        logger.info("AgentManager: Starting consigner/consignee selection flow")
        
        if "consigner_consignee" not in self.agents:
            return APIResponse(
                success=False,
                error="ConsignerConsigneeAgent not available",
                agent_name="AgentManager"
            )
        
        try:
            consigner_consignee_agent = self.agents["consigner_consignee"]
            
            # Get company ID from user context
            company_id = (
                data.get("current_company") or 
                data.get("company_id") or 
                "62d66794e54f47829a886a1d"
            )
            
            # Initialize the selection process
            init_data = {
                "company_id": company_id,
                "trip_id": data.get("trip_id"),
                "parcel_id": data.get("parcel_id"),
                "user_context": {
                    "user_id": data.get("user_id"),
                    "current_company": company_id,
                    "username": data.get("username"),
                    "name": data.get("name"),
                    "email": data.get("email")
                }
            }
            
            response = await consigner_consignee_agent.execute(APIIntent.CREATE, init_data)
            
            if response.success:
                # The response already contains formatted message and button data from initialization
                return APIResponse(
                    success=True,
                    data={
                        "workflow": "CONSIGNER_CONSIGNEE_SELECTION",
                        "message": response.data.get("message"),
                        "button_data": response.data.get("button_data"),
                        "partners": response.data.get("partners"),
                        "current_step": response.data.get("current_step"),
                        "selection_data": response.data.get("selection_data"),
                        "requires_user_input": True,
                        "input_type": "consigner_selection"
                    },
                    agent_name="AgentManager"
                )
            else:
                return response
                
        except Exception as e:
            logger.error(f"AgentManager: Error starting consigner/consignee flow: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )
    
    async def handle_consigner_consignee_selection(self, data: Dict[str, Any]) -> APIResponse:
        """
        Handle selection in the consigner/consignee flow
        """
        logger.info("AgentManager: Handling consigner/consignee selection")
        
        if "consigner_consignee" not in self.agents:
            return APIResponse(
                success=False,
                error="ConsignerConsigneeAgent not available",
                agent_name="AgentManager"
            )
        
        try:
            consigner_consignee_agent = self.agents["consigner_consignee"]
            
            # Handle the selection
            response = await consigner_consignee_agent.execute(APIIntent.UPDATE, data)
            
            if response.success:
                action = response.data.get("action")
                
                if action == "consigner_selected":
                    # Consigner selected, response already contains formatted consignee selection message
                    return APIResponse(
                        success=True,
                        data={
                            "action": "consigner_selected",
                            "message": response.data.get("message"),
                            "button_data": response.data.get("button_data"),
                            "partners": response.data.get("partners"),
                            "current_step": response.data.get("current_step"),
                            "selection_data": response.data.get("selection_data"),
                            "selected_consigner": response.data.get("selected_consigner"),
                            "requires_user_input": True,
                            "input_type": "consignee_selection"
                        },
                        agent_name="AgentManager"
                    )
                
                elif action == "consignee_selected":
                    # Both selections complete - now update the parcel
                    final_data = response.data.get("final_data")
                    parcel_id = final_data.get("parcel_id")
                    
                    if parcel_id and "parcel_updater" in self.agents:
                        # Automatically update the parcel with consigner/consignee details
                        update_response = await self._update_parcel_with_selections(final_data, data)
                        
                        if update_response.success:
                            return APIResponse(
                                success=True,
                                data={
                                    "action": "selection_complete_and_parcel_updated",
                                    "message": update_response.data.get("message"),
                                    "final_data": final_data,
                                    "update_result": update_response.data,
                                    "parcel_id": parcel_id,
                                    "selection_data": response.data.get("selection_data"),
                                    "requires_user_input": False,
                                    "workflow_complete": True
                                },
                                agent_name="AgentManager"
                            )
                        else:
                            # Selection complete but parcel update failed
                            return APIResponse(
                                success=True,
                                data={
                                    "action": "selection_complete_update_failed",
                                    "message": f"{response.data.get('message')}\n\n⚠️ **Warning:** Parcel update failed: {update_response.error}",
                                    "final_data": final_data,
                                    "api_payload": final_data.get("api_payload"),
                                    "selection_data": response.data.get("selection_data"),
                                    "update_error": update_response.error,
                                    "requires_user_input": False,
                                    "ready_for_manual_api": True
                                },
                                agent_name="AgentManager"
                            )
                    else:
                        # No parcel ID or parcel updater not available
                        return APIResponse(
                            success=True,
                            data={
                                "action": "selection_complete",
                                "message": response.data.get("message"),
                                "final_data": final_data,
                                "api_payload": final_data.get("api_payload"),
                                "selection_data": response.data.get("selection_data"),
                                "requires_user_input": False,
                                "ready_for_api": True
                            },
                            agent_name="AgentManager"
                        )
            
            return response
            
        except Exception as e:
            logger.error(f"AgentManager: Error handling consigner/consignee selection: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )
    
    async def _update_parcel_with_selections(self, final_data: Dict[str, Any], 
                                           original_data: Dict[str, Any]) -> APIResponse:
        """
        Update parcel with consigner/consignee selections using PATCH API
        """
        logger.info("AgentManager: Updating parcel with consigner/consignee selections")
        
        try:
            parcel_updater = self.agents["parcel_updater"]
            parcel_id = final_data.get("parcel_id")
            
            if not parcel_id:
                return APIResponse(
                    success=False,
                    error="No parcel_id found in final_data for update",
                    agent_name="AgentManager"
                )
            
            # Prepare data for parcel update
            update_data = {
                "parcel_id": parcel_id,
                "final_data": final_data,
                "trip_id": final_data.get("trip_id"),
                "user_context": final_data.get("user_context", {})
            }
            
            # Add any additional context from original data
            if original_data:
                for key in ["_etag", "company_id", "current_company"]:
                    if key in original_data:
                        update_data[key] = original_data[key]
            
            print(f"AgentManager: ========================================")
            print(f"AgentManager: AUTOMATIC CHAIN EXECUTION")
            print(f"AgentManager: ConsignerConsigneeAgent → ParcelUpdateAgent")
            print(f"AgentManager: ========================================")
            print(f"AgentManager: ConsignerConsigneeAgent completed successfully")
            print(f"AgentManager: → Consigner selected: {final_data.get('consigner_details', {}).get('name')}")
            print(f"AgentManager: → Consignee selected: {final_data.get('consignee_details', {}).get('name')}")
            print(f"AgentManager: → Parcel ID: {parcel_id}")
            print(f"AgentManager: → Trip ID: {final_data.get('trip_id')}")
            print(f"AgentManager: Now executing ParcelUpdateAgent with PATCH API...")
            
            # Execute the parcel update via ParcelUpdateAgent
            response = await parcel_updater.execute(APIIntent.CREATE, update_data)
            
            if response.success:
                print(f"AgentManager: ✅ ParcelUpdateAgent execution SUCCESS!")
                print(f"AgentManager: → PATCH API completed successfully")
                print(f"AgentManager: → Parcel {parcel_id} updated with all consigner/consignee details")
                print(f"AgentManager: ========================================")
                logger.info(f"AgentManager: CHAIN COMPLETE: ConsignerConsigneeAgent → ParcelUpdateAgent → SUCCESS")
                return response
            else:
                print(f"AgentManager: ❌ ParcelUpdateAgent execution FAILED!")
                print(f"AgentManager: → Error: {response.error}")
                print(f"AgentManager: ========================================")
                logger.error(f"AgentManager: CHAIN FAILED: ConsignerConsigneeAgent → ParcelUpdateAgent → ERROR: {response.error}")
                return response
                
        except Exception as e:
            logger.error(f"AgentManager: Error updating parcel with selections: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )
    
    async def update_parcel_directly(self, data: Dict[str, Any]) -> APIResponse:
        """
        Direct method to update a parcel via PATCH API
        """
        logger.info("AgentManager: Direct parcel update requested")
        
        if "parcel_updater" not in self.agents:
            return APIResponse(
                success=False,
                error="ParcelUpdateAgent not available",
                agent_name="AgentManager"
            )
        
        try:
            parcel_updater = self.agents["parcel_updater"]
            
            # Determine the intent based on data structure
            if "update_payload" in data:
                # Direct update with payload
                return await parcel_updater.execute(APIIntent.UPDATE, data)
            elif "final_data" in data:
                # Update with consigner/consignee data
                return await parcel_updater.execute(APIIntent.CREATE, data)
            else:
                # Get parcel details
                return await parcel_updater.execute(APIIntent.READ, data)
                
        except Exception as e:
            logger.error(f"AgentManager: Error in direct parcel update: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )

    async def handle_company_selection(self, data: Dict[str, Any]) -> APIResponse:
        """
        Handle user's company selection after partner selection
        Called when a partner has multiple companies and user needs to choose one
        """
        logger.info("AgentManager: Handling company selection")
        
        try:
            # Get the selected partner info
            selected_partner = data.get("selected_partner", {})
            companies = data.get("companies", [])
            user_selection = data.get("selection", "").strip()
            trip_id = data.get("trip_id", "")
            parcel_id = data.get("parcel_id", "")
            
            if not selected_partner or not companies:
                return APIResponse(
                    success=False,
                    error="Missing partner or company information for selection",
                    agent_name="AgentManager"
                )
            
            # Find the selected company
            selected_company = None
            
            # Try to match by company name
            for company in companies:
                if user_selection.lower() == company.get("name", "").lower():
                    selected_company = company
                    break
            
            # If not found by name, try by index if it's a number
            if not selected_company and user_selection.isdigit():
                selection_index = int(user_selection) - 1
                if 0 <= selection_index < len(companies):
                    selected_company = companies[selection_index]
            
            if not selected_company:
                return APIResponse(
                    success=False,
                    error=f"Invalid company selection. Please choose from the available companies.",
                    agent_name="AgentManager"
                )
            
            # Complete the consignor selection with the chosen company
            partner_name = selected_partner.get("name")
            partner_id = selected_partner.get("id")
            partner_city = selected_partner.get("city", "Unknown City")
            company_name = selected_company.get("name")
            
            # Create final confirmation message
            confirmation_message = f"✅ **Selection Complete**\n\n"
            confirmation_message += f"**Selected Partner:** {partner_name}\n"
            confirmation_message += f"**Location:** {partner_city}\n"
            confirmation_message += f"**Partner ID:** {partner_id}\n"
            confirmation_message += f"**Selected Company:** {company_name}\n"
            
            if parcel_id:
                confirmation_message += f"\n📦 **Parcel ID:** {parcel_id}"
            if trip_id:
                confirmation_message += f"\n🚛 **Trip ID:** {trip_id}"
            
            confirmation_message += f"\n\n🎉 Your parcel is now linked with {partner_name} ({company_name})!"
            
            # Update consignor selection
            if "consignor_selector" in self.agents:
                consignor_agent = self.agents["consignor_selector"]
                await consignor_agent.execute(APIIntent.UPDATE, {
                    "partner_id": partner_id,
                    "partner_name": partner_name
                })
            
            return APIResponse(
                success=True,
                data={
                    "action": "consignor_and_company_selected",
                    "selected_partner": {
                        "id": partner_id,
                        "name": partner_name,
                        "city": partner_city,
                        "selected_company": selected_company
                    },
                    "message": confirmation_message,
                    "trip_id": trip_id,
                    "parcel_id": parcel_id
                },
                agent_name="AgentManager"
            )
            
        except Exception as e:
            logger.error(f"AgentManager: Error handling company selection: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                agent_name="AgentManager"
            )

# Global agent manager instance
agent_manager = AgentManager()