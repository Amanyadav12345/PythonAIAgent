# Python AI Agent Framework

## Overview

This project is a **multi-agent AI framework** designed for natural language processing and task automation. The current implementation serves as a foundation for building complex AI agent systems that can handle parcel creation, task delegation, and API orchestration through natural language interfaces.

## Current Architecture

### Core Components

#### 1. Main Agent System (`main.py`)
- **LLM Integration**: Uses Claude 3.5 Sonnet via LangChain Anthropic API
- **Structured Output**: Implements Pydantic models for consistent response formatting
- **Agent Executor**: LangChain-based agent with tool-calling capabilities
- **Research Pipeline**: Configured for research assistant functionality

#### 2. Tool System (`tools.py`)
- **Web Search**: DuckDuckGo integration for real-time information retrieval
- **Knowledge Base**: Wikipedia API wrapper for factual data
- **File Operations**: Text file saving with timestamp metadata
- **Extensible Design**: Tool-based architecture for easy expansion

#### 3. Data Models
```python
class ResearchResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]
```

## Technology Stack

### AI & Language Models
- **LangChain**: Framework for LLM application development
- **Anthropic Claude**: Primary language model (claude-3-5-sonnet-20241022)
- **OpenAI Support**: Ready for GPT model integration
- **Pydantic**: Data validation and structured outputs

### APIs & Integrations
| API/Service | Purpose | Usage Pattern | Configuration |
|-------------|---------|---------------|---------------|
| **Anthropic Claude API** | Primary LLM | `ChatAnthropic(model="claude-3-5-sonnet-20241022")` | `ANTHROPIC_API_KEY` |
| **OpenAI API** | Alternative LLM | `ChatOpenAI()` (configured but not active) | `OPENAI_API_KEY` |
| **DuckDuckGo Search** | Web search | `DuckDuckGoSearchRun()` | No API key required |
| **Wikipedia API** | Knowledge retrieval | `WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100)` | No API key required |

### Dependencies
```txt
langchain                 # Core LLM framework
wikipedia                 # Wikipedia API client
langchain-community       # Community tools and utilities
langchain-openai          # OpenAI integration
langchain-anthropic       # Anthropic integration
python-dotenv            # Environment variable management
pydantic                 # Data validation and modeling
duckduckgo-search        # Web search functionality
```

## Current API Architecture

### Agent Workflow
1. **Input Processing**: Natural language query input
2. **Tool Selection**: Agent determines appropriate tools based on query
3. **Execution**: Tools are called with structured parameters
4. **Response Formatting**: Output structured via Pydantic models
5. **Result Storage**: Optional file saving with timestamps

### Tool API Patterns
- **Search Tool**: `search.run(query: str) -> str`
- **Wiki Tool**: `wiki_tool.run(query: str) -> str`  
- **Save Tool**: `save_to_txt(data: str, filename: str) -> str`

## Future Vision: Multi-Agent Parcel System

### Planned Architecture Expansion

#### 1. Agent Specialization
```
├── ParcelCreationAgent/
│   ├── PackagingAgent      # Handles packaging requirements
│   ├── RoutingAgent        # Manages delivery routes
│   └── PricingAgent        # Calculates costs
├── APIOrchestrationAgent/
│   ├── ShippingProviders   # FedEx, UPS, DHL integrations
│   ├── TrackingServices    # Real-time status updates
│   └── PaymentProcessing   # Transaction handling
└── TaskCoordinationAgent/
    ├── WorkflowManager     # Multi-step task orchestration
    ├── ErrorRecovery       # Failure handling and retries
    └── AuditLogger         # Complete API usage tracking
```

#### 2. API Integration Strategy
- **Shipping Providers**: FedEx, UPS, DHL, USPS APIs
- **Geolocation Services**: Google Maps, Mapbox for routing
- **Payment Gateways**: Stripe, PayPal for transactions
- **Database Systems**: PostgreSQL/MongoDB for parcel tracking
- **Message Queues**: Redis/RabbitMQ for async processing

#### 3. Natural Language Interface
```python
# Example future usage:
query = "Create a parcel from New York to Los Angeles, 2kg, express delivery, insured for $500"
# System automatically:
# 1. Extracts: origin, destination, weight, service level, insurance
# 2. Calculates best routes and pricing
# 3. Creates parcel in system
# 4. Returns tracking number and estimated delivery
```

## API Usage Tracking

### Current Monitoring
- Basic console output via `verbose=True` in AgentExecutor
- File-based logging for research outputs
- Exception handling for parsing errors

### Future API Management
```python
class APIUsageTracker:
    def track_api_call(self, service: str, endpoint: str, cost: float, tokens: int):
        # Log all API interactions
        # Track costs across services  
        # Monitor rate limits
        # Generate usage reports
```

## Getting Started

### Prerequisites
```bash
pip install -r requirements.txt
```

### Environment Setup
```bash
cp sample.env .env
# Add your API keys:
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here (optional)
```

### Running the Agent
```bash
python main.py
```

## Development Roadmap

### Phase 1: Foundation (Current)
- ✅ Basic agent framework
- ✅ Tool system architecture  
- ✅ Structured output handling
- ✅ Environment configuration

### Phase 2: Multi-Agent System
- 🔄 Agent specialization and delegation
- 🔄 Inter-agent communication protocols
- 🔄 Centralized task coordination
- 🔄 Error handling and recovery

### Phase 3: Parcel Management
- ⏳ Shipping provider integrations
- ⏳ Real-time tracking system
- ⏳ Cost optimization algorithms
- ⏳ Payment processing workflows

### Phase 4: Advanced Features
- ⏳ Machine learning for route optimization
- ⏳ Predictive delivery analytics
- ⏳ Custom business logic integration
- ⏳ Multi-tenant support

## API Allocation Strategy

All API integrations are designed with the following principles:
- **Rate Limit Management**: Automatic throttling and queuing
- **Cost Optimization**: Smart caching and request batching
- **Fault Tolerance**: Failover between providers
- **Usage Analytics**: Detailed logging for future allocation decisions
- **Security**: API key rotation and secure credential storage

This foundation provides a scalable architecture for building sophisticated AI-powered logistics and automation systems.