# Agent-Based API System

A modular, intent-driven API management system that handles complex workflows through specialized agents.

## Architecture Overview

```
┌─────────────────┐
│  Agent Manager  │ ← Orchestrates workflows & dependencies
└─────────────────┘
         │
    ┌────┼────┐
    │    │    │
┌───▼┐ ┌─▼─┐ ┌▼──┐
│City│ │Mat│ │...│ ← Specialized API Agents
└────┘ └───┘ └───┘
    │    │    │
┌───▼────▼────▼──┐
│   Base Agent   │ ← Common functionality
└────────────────┘
```

## Core Components

### 1. Base Agent (`base_agent.py`)
- **Purpose**: Common functionality for all agents
- **Features**: 
  - HTTP request handling with retry logic
  - Authentication (Basic Auth + Token)
  - Rate limiting & caching
  - Error handling & logging
  - Intent validation

### 2. Specialized Agents

#### City Agent (`city_agent.py`)
- **Purpose**: City data operations
- **Intents**: `LIST`, `SEARCH`, `READ`
- **Features**: MongoDB-style WHERE queries, name→ID resolution

#### Material Agent (`material_agent.py`) 
- **Purpose**: Material data operations
- **Intents**: `LIST`, `SEARCH`, `READ`
- **Features**: Regex search, fallback to default material ID

#### Trip Agent (`trip_agent.py`)
- **Purpose**: Trip management
- **Intents**: `CREATE`, `SEARCH`, `READ`, `LIST`
- **Features**: Route-based trip creation, dependency handling

#### Parcel Agent (`parcel_agent.py`)
- **Purpose**: Parcel lifecycle management
- **Intents**: `CREATE`, `READ`, `SEARCH`, `UPDATE`, `LIST`
- **Features**: Complex payload building, dependency integration

### 3. Agent Manager (`agent_manager.py`)
- **Purpose**: Workflow orchestration
- **Features**:
  - Intent routing
  - Dependency resolution
  - Multi-step workflows
  - Error recovery

## API Intents

### Basic Intents
- `CREATE` - Create new resource
- `READ` - Get specific resource by ID
- `SEARCH` - Search resources by criteria
- `UPDATE` - Update existing resource
- `DELETE` - Delete resource
- `LIST` - Get all resources
- `VALIDATE` - Validate data

### Workflow Intents
- `CREATE_PARCEL` - Complete parcel creation with dependencies
- `SEARCH_CITIES` - City search operations
- `SEARCH_MATERIALS` - Material search operations
- `FIND_TRIPS` - Trip search operations
- `GET_PARCEL_STATUS` - Parcel status checking
- `CREATE_TRIP` - Trip creation
- `RESOLVE_DEPENDENCIES` - Resolve IDs without actions

## Usage Examples

### Simple Agent Usage
```python
from agents.agent_manager import agent_manager
from agents.base_agent import APIIntent

# Search for a city
response = await agent_manager.execute_single_intent(
    "city", APIIntent.SEARCH, {"city_name": "Jaipur"}
)
```

### Complex Workflow Usage
```python
from agents.agent_manager import agent_manager, WorkflowIntent

# Create parcel with automatic dependency resolution
parcel_data = {
    "from_city": "Jaipur",
    "to_city": "Kolkata", 
    "material": "paint",
    "weight": 25,
    "sender_name": "Company A",
    "receiver_name": "Company B"
}

response = await agent_manager.execute_workflow(
    WorkflowIntent.CREATE_PARCEL, parcel_data
)
```

### Integration with Authentication
```python
# Set auth token for all agents
agent_manager.set_auth_token("Bearer your-token-here")

# Or use per-request authentication via environment variables
```

## Configuration

Set these environment variables:

```env
# Authentication
PARCEL_API_USERNAME=your_username
PARCEL_API_PASSWORD=your_password

# API URLs
GET_CITIES_API_URL=https://api.example.com/cities
GET_MATERIALS_API_URL=https://api.example.com/materials
TRIP_API_URL=https://api.example.com/trips
PARCEL_API_URL=https://api.example.com/parcels

# Default IDs
DEFAULT_MATERIAL_ID=61547b0b988da3862e52daaa
TRIP_ID=default_trip_id
CREATED_BY_ID=6257f1d75b42235a2ae4ab34
CREATED_BY_COMPANY_ID=62d66794e54f47829a886a1d
```

## Key Features

### 1. **Intent-Driven Design**
- Each agent handles specific intents
- Clear separation of concerns
- Easy to extend with new intents

### 2. **Smart Caching**
- Automatic caching for READ operations
- TTL-based cache expiration
- Cache-first approach for performance

### 3. **Dependency Resolution**
- Automatic city name → city ID resolution
- Material name → material ID resolution
- Trip creation/retrieval for parcels

### 4. **Error Handling**
- Comprehensive error handling
- Graceful fallbacks
- Detailed error reporting

### 5. **Rate Limiting**
- Configurable delays between requests
- Respects API timing requirements
- Prevents overwhelming external APIs

### 6. **Workflow Orchestration**
- Multi-step workflows
- Dependency coordination
- Transaction-like operations

## API Response Format

All agents return standardized responses:

```python
{
    "success": bool,
    "data": dict,           # Response data
    "error": str,           # Error message (if any)
    "status_code": int,     # HTTP status code
    "intent": str,          # The executed intent
    "agent_name": str,      # Which agent handled it
    "execution_time": float, # Time taken
    "sources": [str]        # API URLs called
}
```

## Workflow Response Format

Complex workflows provide additional details:

```python
{
    "success": bool,
    "data": {
        "workflow": "CREATE_PARCEL",
        "parcel_result": {...},
        "workflow_details": {
            "steps": ["✓ Step 1", "✓ Step 2"],
            "resolved_dependencies": {
                "from_city": {"name": "Jaipur", "id": "123"},
                "material": {"name": "paint", "id": "456"}
            }
        }
    }
}
```

## Testing

Run the example usage:
```bash
cd backend/agents
python example_usage.py
```

## Integration Points

### With FastAPI Backend
```python
from agents.agent_manager import agent_manager

@app.post("/create-parcel")
async def create_parcel_endpoint(data: dict):
    response = await agent_manager.execute_workflow(
        WorkflowIntent.CREATE_PARCEL, data
    )
    return response.dict()
```

### With LangChain Agents
The agent system can be integrated as tools in LangChain agents for natural language processing of API operations.

## Benefits

1. **Modularity**: Each agent handles one concern
2. **Scalability**: Easy to add new agents/intents
3. **Reliability**: Built-in error handling and retries
4. **Performance**: Smart caching and rate limiting
5. **Maintainability**: Clear separation of logic
6. **Testability**: Each component can be tested independently

## Extension Points

- Add new agents for other APIs
- Implement new intents for existing agents
- Create custom workflows in the agent manager
- Add middleware for logging, metrics, etc.
- Implement circuit breakers for failing APIs