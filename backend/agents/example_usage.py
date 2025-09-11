"""
Example Usage of Agent-Based API System
Demonstrates how to use the specialized agents for different API operations
"""
import asyncio
import json
from dotenv import load_dotenv

from agent_manager import agent_manager, WorkflowIntent
from base_agent import APIIntent

load_dotenv()

async def example_city_operations():
    """Example: City-related operations"""
    print("\n🏙️  CITY OPERATIONS EXAMPLES")
    print("=" * 50)
    
    # Search for a specific city
    print("1. Searching for city 'Jaipur':")
    response = await agent_manager.execute_single_intent(
        "city", APIIntent.SEARCH, {"city_name": "Jaipur"}
    )
    print(f"   Success: {response.success}")
    if response.success and response.data:
        cities = response.data.get("cities", [])
        for city in cities:
            print(f"   Found: {city['name']} (ID: {city['id']})")
    else:
        print(f"   Error: {response.error}")
    
    # List all cities (cached)
    print("\n2. Listing all cities:")
    response = await agent_manager.execute_single_intent(
        "city", APIIntent.LIST, {}
    )
    print(f"   Success: {response.success}")
    if response.success:
        print(f"   Execution time: {response.execution_time:.2f}s")

async def example_material_operations():
    """Example: Material-related operations"""
    print("\n🧱 MATERIAL OPERATIONS EXAMPLES")
    print("=" * 50)
    
    # Search for a specific material
    print("1. Searching for material 'paint':")
    response = await agent_manager.execute_single_intent(
        "material", APIIntent.SEARCH, {"material_name": "paint"}
    )
    print(f"   Success: {response.success}")
    if response.success and response.data:
        materials = response.data.get("materials", [])
        for material in materials:
            print(f"   Found: {material['name']} (ID: {material['id']})")
            if material.get("fallback"):
                print(f"   Note: Using fallback/default material")
    else:
        print(f"   Error: {response.error}")

async def example_trip_operations():
    """Example: Trip-related operations"""
    print("\n🚛 TRIP OPERATIONS EXAMPLES")
    print("=" * 50)
    
    # Create a simple trip
    print("1. Creating a new trip:")
    response = await agent_manager.execute_single_intent(
        "trip", APIIntent.CREATE, {}
    )
    print(f"   Success: {response.success}")
    if response.success and response.data:
        trip_id = response.data.get("extracted_trip_id")
        print(f"   Created trip ID: {trip_id}")
    else:
        print(f"   Error: {response.error}")

async def example_parcel_workflow():
    """Example: Complete parcel creation workflow"""
    print("\n📦 COMPLETE PARCEL CREATION WORKFLOW")
    print("=" * 50)
    
    # Complete parcel creation with dependency resolution
    parcel_data = {
        "from_city": "Jaipur",
        "to_city": "Kolkata", 
        "material": "paint",
        "weight": 25,
        "description": "Paint shipment from Jaipur to Kolkata",
        "sender_name": "Jaipur Paint Co.",
        "receiver_name": "Kolkata Distributors",
        "pickup_address": "Industrial Area, Jaipur",
        "delivery_address": "Salt Lake, Kolkata",
        "pickup_pin": "302013",
        "delivery_pin": "700091"
    }
    
    print("Creating parcel with automatic dependency resolution:")
    print(f"   From: {parcel_data['from_city']} to {parcel_data['to_city']}")
    print(f"   Material: {parcel_data['material']} ({parcel_data['weight']} tonnes)")
    
    response = await agent_manager.execute_workflow(
        WorkflowIntent.CREATE_PARCEL, parcel_data
    )
    
    print(f"\nWorkflow Result: {response.success}")
    
    if response.success and response.data:
        workflow_details = response.data.get("workflow_details", {})
        
        print("\nWorkflow Steps:")
        for step in workflow_details.get("steps", []):
            print(f"   {step}")
        
        print("\nResolved Dependencies:")
        dependencies = workflow_details.get("resolved_dependencies", {})
        for dep_type, dep_info in dependencies.items():
            if isinstance(dep_info, dict) and "name" in dep_info:
                print(f"   {dep_type}: {dep_info['name']} → {dep_info['id']}")
            else:
                print(f"   {dep_type}: {dep_info}")
        
        parcel_result = response.data.get("parcel_result", {})
        if parcel_result:
            parcel_id = parcel_result.get("extracted_parcel_id")
            print(f"\n✅ Parcel created successfully!")
            print(f"   Parcel ID: {parcel_id}")
            
            summary = parcel_result.get("summary", {})
            if summary:
                print("   Summary:")
                for key, value in summary.items():
                    print(f"     {key}: {value}")
    else:
        print(f"❌ Workflow failed: {response.error}")
        if response.data:
            steps = response.data.get("steps", [])
            print("\nWorkflow Steps:")
            for step in steps:
                print(f"   {step}")

async def example_dependency_resolution():
    """Example: Resolve dependencies without creating anything"""
    print("\n🔍 DEPENDENCY RESOLUTION EXAMPLE")
    print("=" * 50)
    
    test_data = {
        "from_city": "Mumbai",
        "to_city": "Delhi",
        "material": "steel"
    }
    
    print("Resolving dependencies for:")
    print(f"   Cities: {test_data['from_city']} → {test_data['to_city']}")
    print(f"   Material: {test_data['material']}")
    
    response = await agent_manager.execute_workflow(
        WorkflowIntent.RESOLVE_DEPENDENCIES, test_data
    )
    
    print(f"\nResolution Result: {response.success}")
    
    if response.success and response.data:
        dependencies = response.data.get("resolved_dependencies", {})
        steps = response.data.get("steps", [])
        
        print("\nResolution Steps:")
        for step in steps:
            print(f"   {step}")
        
        print("\nResolved Dependencies:")
        for dep_type, dep_info in dependencies.items():
            if isinstance(dep_info, dict):
                print(f"   {dep_type}: {dep_info.get('name')} → {dep_info.get('id')}")

async def example_agent_status():
    """Example: Get agent system status"""
    print("\n📊 AGENT SYSTEM STATUS")
    print("=" * 50)
    
    status = agent_manager.get_agent_status()
    
    print(f"Total Agents: {status['total_agents']}")
    print("\nAgent Details:")
    
    for agent_name, agent_info in status["agents"].items():
        print(f"\n🔧 {agent_info['name']}:")
        print(f"   URL: {agent_info['base_url']}")
        print(f"   Cache Size: {agent_info['cache_size']}")
        print(f"   Supported Intents: {', '.join(agent_info['supported_intents'])}")

async def main():
    """Run all examples"""
    print("🚀 AGENT-BASED API SYSTEM EXAMPLES")
    print("=" * 50)
    
    # Initialize agent cache
    print("Initializing agent cache...")
    await agent_manager.initialize_cache()
    print("Cache initialization completed.\n")
    
    # Run examples
    await example_agent_status()
    await example_city_operations()
    await example_material_operations()
    await example_trip_operations()
    await example_dependency_resolution()
    await example_parcel_workflow()
    
    print("\n✅ All examples completed!")

if __name__ == "__main__":
    asyncio.run(main())