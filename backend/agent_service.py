from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
import sys
import os

# Add parent directory to path to import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import search_tool, wiki_tool, save_tool
from truck_tools import calculate_rolling_radius, calculate_truck_load_distribution, estimate_fuel_consumption
from agents.agent_manager import agent_manager, WorkflowIntent

load_dotenv()

class ChatRequest(BaseModel):
    message: str
    user_id: str
    user_context: dict = {}

class ChatResponse(BaseModel):
    response: str
    sources: list[str] = []
    tools_used: list[str] = []

class ResearchResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]

class AgentService:
    def __init__(self):
        # Check if Anthropic API key is available
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
            self.llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
            self.has_llm = True
        else:
            self.llm = None
            self.has_llm = False
            print("Warning: ANTHROPIC_API_KEY not set. Using specialized agents only.")
        
        self.parser = PydanticOutputParser(pydantic_object=ResearchResponse)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a specialized logistics and transportation assistant focused on truck operations, rolling radius calculations, and parcel management.
            
            You help with:
            - Creating and managing parcels for truck transportation
            - Route optimization and trip planning
            - Rolling radius calculations for different tire sizes
            - Material transport specifications and requirements
            - Truck load optimization and vehicle selection
            - Logistics cost calculations and delivery estimates
            
            Use the available tools when necessary to provide accurate transportation and logistics information.
            Always format responses clearly and focus on practical trucking and logistics solutions.
            """),
            ("placeholder", "{chat_history}"),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        self.tools = [
            search_tool, wiki_tool, save_tool,
            calculate_rolling_radius, calculate_truck_load_distribution, estimate_fuel_consumption
        ]
        
        if self.has_llm:
            self.agent = create_tool_calling_agent(
                llm=self.llm,
                prompt=self.prompt,
                tools=self.tools
            )
            
            self.agent_executor = AgentExecutor(
                agent=self.agent, 
                tools=self.tools, 
                verbose=True,
                return_intermediate_steps=True
            )
        else:
            self.agent = None
            self.agent_executor = None
    
    async def process_message(self, request: ChatRequest) -> ChatResponse:
        try:
            # Check if this is a trip or parcel creation request
            message_lower = request.message.lower()
            
            # Detect combined trip and parcel creation intent first (more specific)
            if self._is_combined_trip_parcel_request(message_lower):
                return await self._handle_trip_and_parcel_creation(request)
            
            # Detect trip creation intent
            elif self._is_trip_creation_request(message_lower):
                return await self._handle_trip_creation(request)
            
            # Detect parcel creation intent
            elif self._is_parcel_creation_request(message_lower):
                return await self._handle_parcel_creation(request)
            
            # Default to existing langchain agent executor if available
            if self.has_llm and self.agent_executor:
                result = self.agent_executor.invoke({"query": request.message})
                
                # Extract tools used and sources from intermediate steps
                tools_used = []
                sources = []
                
                if "intermediate_steps" in result:
                    for step in result["intermediate_steps"]:
                        if hasattr(step[0], 'tool'):
                            tools_used.append(step[0].tool)
                        # Extract sources from tool outputs if available
                        if "http" in str(step[1]):
                            sources.extend([url for url in str(step[1]).split() if url.startswith("http")])
                
                return ChatResponse(
                    response=result["output"],
                    sources=list(set(sources)),
                    tools_used=list(set(tools_used))
                )
            else:
                # Fallback response when no LLM is available
                return ChatResponse(
                    response="I can help you create trips and parcels! Try saying something like:\n"
                             "• 'Create a new trip for truck transport'\n"
                             "• 'Make trip and parcel 25kg from Mumbai to Delhi'\n"
                             "• 'Create delivery with 2 tonnes steel'\n\n"
                             "For other queries, please set up the ANTHROPIC_API_KEY in your .env file.",
                    sources=[],
                    tools_used=["FallbackResponse"]
                )
        except Exception as e:
            return ChatResponse(
                response=f"I encountered an error: {str(e)}",
                sources=[],
                tools_used=[]
            )
    
    def _is_trip_creation_request(self, message: str) -> bool:
        """Check if message is requesting trip creation"""
        trip_keywords = ["create trip", "new trip", "make trip", "start trip", "trip for"]
        return any(keyword in message for keyword in trip_keywords)
    
    def _is_parcel_creation_request(self, message: str) -> bool:
        """Check if message is requesting parcel creation"""
        parcel_keywords = ["create parcel", "new parcel", "make parcel", "send parcel", "ship package"]
        return any(keyword in message for keyword in parcel_keywords)
    
    def _is_combined_trip_parcel_request(self, message: str) -> bool:
        """Check if message is requesting both trip and parcel creation"""
        has_trip = any(word in message for word in ["trip", "delivery", "transport"])
        has_parcel = any(word in message for word in ["parcel", "package", "shipment"])
        has_create = any(word in message for word in ["create", "make", "new", "send"])
        
        # Also check for the specific pattern: "from [city] to [city]" which indicates trip+parcel
        has_route = "from" in message and "to" in message
        
        return (has_trip and has_parcel and has_create) or has_route
    
    async def _handle_trip_creation(self, request: ChatRequest) -> ChatResponse:
        """Handle trip creation requests"""
        try:
            # Merge user context with message data
            workflow_data = {
                "message": request.message,
                "user_id": request.user_id,
                **request.user_context
            }
            
            response = await agent_manager.execute_workflow(
                WorkflowIntent.CREATE_TRIP_ADVANCED,
                workflow_data
            )
            
            if response.success:
                trip_data = response.data.get("trip_result", {})
                return ChatResponse(
                    response=response.data.get("message", "Trip created successfully!"),
                    sources=[],
                    tools_used=["TripCreationAgent"]
                )
            else:
                return ChatResponse(
                    response=f"Failed to create trip 1: {response.error}",
                    sources=[],
                    tools_used=["TripCreationAgent"]
                )
                
        except Exception as e:
            return ChatResponse(
                response=f"Trip creation error: {str(e)}",
                sources=[],
                tools_used=[]
            )
    
    async def _handle_parcel_creation(self, request: ChatRequest) -> ChatResponse:
        """Handle parcel creation requests"""
        try:
            # For parcel creation, we need a trip_id
            # This is a simplified version - in reality, you might need to extract trip_id from context
            workflow_data = {
                "message": request.message,
                "user_id": request.user_id,
                "trip_id": None,  # Would need to be provided or extracted
                **request.user_context
            }
            
            response = await agent_manager.execute_workflow(
                WorkflowIntent.CREATE_PARCEL_FOR_TRIP,
                workflow_data
            )
            
            if response.success:
                return ChatResponse(
                    response=response.data.get("message", "Parcel created successfully!"),
                    sources=[],
                    tools_used=["ParcelCreationAgent"]
                )
            else:
                return ChatResponse(
                    response=f"Failed to create parcel: {response.error}",
                    sources=[],
                    tools_used=["ParcelCreationAgent"]
                )
                
        except Exception as e:
            return ChatResponse(
                response=f"Parcel creation error: {str(e)}",
                sources=[],
                tools_used=[]
            )
    
    async def _handle_trip_and_parcel_creation(self, request: ChatRequest) -> ChatResponse:
        """Handle combined trip and parcel creation requests using enhanced Gemini workflow"""
        try:
            # Use the enhanced Gemini service for intelligent city lookup and workflow
            from gemini_service import gemini_service
            
            # Use the full user context from authenticated user
            user_context = request.user_context or {
                "user_id": request.user_id
            }
            
            response = await gemini_service.enhanced_trip_and_parcel_creation(
                request.message, 
                user_context
            )
            
            if response.get("success"):
                return ChatResponse(
                    response=response.get("message", "Trip and parcel created successfully!"),
                    sources=[],
                    tools_used=["GeminiService", "TripCreationAgent", "ParcelCreationAgent", "CityLookupAPI"]
                )
            else:
                error_message = response.get("error", "Unknown error occurred")
                
                # If there are city suggestions, include them in the response
                if "suggestions" in response:
                    suggestions = response["suggestions"]
                    suggestion_text = ""
                    
                    if suggestions.get("from_city"):
                        suggestion_text += f"\n\nFor source city, did you mean: {', '.join([s['name'] for s in suggestions['from_city'][:3]])}"
                    
                    if suggestions.get("to_city"):
                        suggestion_text += f"\n\nFor destination city, did you mean: {', '.join([s['name'] for s in suggestions['to_city'][:3]])}"
                    
                    error_message += suggestion_text
                
                return ChatResponse(
                    response=error_message,
                    sources=[],
                    tools_used=["GeminiService", "CityLookupAPI"]
                )
                
        except Exception as e:
            # Fallback to original workflow if enhanced workflow fails
            try:
                workflow_data = {
                    "message": request.message,
                    "user_id": request.user_id,
                    **request.user_context
                }
                
                response = await agent_manager.execute_workflow(
                    WorkflowIntent.CREATE_TRIP_AND_PARCEL,
                    workflow_data
                )
                
                if response.success:
                    return ChatResponse(
                        response=response.data.get("message", "Trip and parcel created successfully!"),
                        sources=[],
                        tools_used=["TripCreationAgent", "ParcelCreationAgent"]
                    )
                else:
                    return ChatResponse(
                        response=f"Failed to create trip 11 and parcel: {response.error}",
                        sources=[],
                        tools_used=["TripCreationAgent", "ParcelCreationAgent"]
                    )
            except Exception as fallback_error:
                return ChatResponse(
                    response=f"Trip and parcel creation error: {str(e)}. Fallback also failed: {str(fallback_error)}",
                    sources=[],
                    tools_used=[]
                )

# Global agent service instance
agent_service = AgentService()