#!/usr/bin/env python3
"""
Debug the CityAgent API request
"""
import asyncio
import os
import sys
import json
import httpx
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def debug_city_request():
    """Debug the exact request being made by CityAgent"""
    
    # Test the exact parameters that CityAgent would create
    city_name = "jaipur"
    city_name_clean = city_name.strip().lower()
    
    where_query = {
        "name": {
            "$regex": f"^{city_name_clean}",
            "$options": "i"
        }
    }
    
    embedded_query = {
        "district": 1,
        "district.state": 1
    }
    
    params = {
        "where": json.dumps(where_query),
        "embedded": json.dumps(embedded_query),
        "projection": json.dumps({})
    }
    
    print("Parameters that CityAgent would send:")
    print(f"where: {params['where']}")
    print(f"embedded: {params['embedded']}")
    print(f"projection: {params['projection']}")
    print()
    
    # Test the request
    base_url = "https://35.244.19.78:8042/cities"
    username = os.getenv("PARCEL_API_USERNAME", "")
    password = os.getenv("PARCEL_API_PASSWORD", "")
    
    headers = {"Content-Type": "application/json"}
    if username and password:
        import base64
        credentials = f"{username}:{password}"
        credentials_b64 = base64.b64encode(credentials.encode()).decode()
        headers["Authorization"] = f"Basic {credentials_b64}"
    
    print("Making request with httpx...")
    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.get(base_url, headers=headers, params=params)
            print(f"Status Code: {response.status_code}")
            print(f"Request URL: {response.url}")
            print(f"Response: {response.text[:500]}...")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(debug_city_request())