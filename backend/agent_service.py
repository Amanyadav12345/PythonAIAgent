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

load_dotenv()

class ChatRequest(BaseModel):
    message: str
    user_id: str

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
        self.llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
        self.parser = PydanticOutputParser(pydantic_object=ResearchResponse)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a helpful AI assistant that can research information and answer questions.
            Use the available tools when necessary to provide accurate and up-to-date information.
            Format your response clearly and cite sources when applicable.
            """),
            ("placeholder", "{chat_history}"),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        self.tools = [search_tool, wiki_tool, save_tool]
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
    
    async def process_message(self, request: ChatRequest) -> ChatResponse:
        try:
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
        except Exception as e:
            return ChatResponse(
                response=f"I encountered an error: {str(e)}",
                sources=[],
                tools_used=[]
            )

# Global agent service instance
agent_service = AgentService()