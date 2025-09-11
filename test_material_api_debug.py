#!/usr/bin/env python3
"""
Debug material API queries to understand the correct format
"""
import asyncio
import httpx
import json
import urllib.parse
import base64
import os
from dotenv import load_dotenv

load_dotenv()

async def test_material_api_formats():
    """Test different query formats against the materials API"""
    
    base_url = "https://35.244.19.78:8042"
    endpoint = "/material_types"
    
    # Get authentication headers
    username = os.getenv("PARCEL_API_USERNAME", "917340224449")
    password = os.getenv("PARCEL_API_PASSWORD", "12345")
    
    credentials = f"{username}:{password}"
    credentials_b64 = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials_b64}",
        "Content-Type": "application/json"
    }
    
    print("Testing different material API query formats...")
    print(f"Base URL: {base_url}{endpoint}")
    print(f"Auth: {username}:***")
    
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        
        # Test 1: Simple GET without parameters
        print(f"\n=== Test 1: Simple GET ===")
        try:
            response = await client.get(f"{base_url}{endpoint}", headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                total = len(data.get("_items", []))
                print(f"Success: Got {total} materials")
                # Show a few material names
                for i, item in enumerate(data.get("_items", [])[:3]):
                    print(f"   {i+1}. {item.get('name', 'Unknown')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")
        
        # Test 2: Query for materials containing "iron" 
        print(f"\n=== Test 2: Search for materials containing 'iron' ===")
        try:
            # Try the format you showed me
            where_query = {
                "$or": [
                    {
                        "name": {
                            "$regex": "iron",
                            "$options": "-i"
                        }
                    }
                ]
            }
            
            where_encoded = urllib.parse.quote(json.dumps(where_query))
            url = f"{base_url}{endpoint}?where={where_encoded}"
            print(f"URL: {url}")
            
            response = await client.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                materials = data.get("_items", [])
                print(f"Success: Found {len(materials)} materials with 'iron'")
                for material in materials:
                    print(f"   - {material.get('name', 'Unknown')} (ID: {material.get('_id')})")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")
            
        # Test 3: Simple regex without $or
        print(f"\n=== Test 3: Simple regex for 'bamboo' ===")
        try:
            where_query = {
                "name": {
                    "$regex": "bamboo",
                    "$options": "-i"
                }
            }
            
            where_encoded = urllib.parse.quote(json.dumps(where_query))
            url = f"{base_url}{endpoint}?where={where_encoded}"
            print(f"URL: {url}")
            
            response = await client.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                materials = data.get("_items", [])
                print(f"Success: Found {len(materials)} materials with 'bamboo'")
                for material in materials:
                    print(f"   - {material.get('name', 'Unknown')} (ID: {material.get('_id')})")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")
            
        # Test 4: Test the exact format from your example
        print(f"\n=== Test 4: Your exact URL format ===")
        try:
            # Your example: https://35.244.19.78:8042/material_types?where={%22$or%22:%20[{%22name%22:%20{%22$regex%22:%20%22^[object%20Object]%22,%22$options%22:%22-i%22}}]}
            # Let's try with "iron" instead of "[object Object]"
            test_url = f"{base_url}{endpoint}?where=" + urllib.parse.quote('{"$or": [{"name": {"$regex": "^iron", "$options": "-i"}}]}')
            print(f"URL: {test_url}")
            
            response = await client.get(test_url, headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                materials = data.get("_items", [])
                print(f"Success: Found {len(materials)} materials starting with 'iron'")
                for material in materials:
                    print(f"   - {material.get('name', 'Unknown')} (ID: {material.get('_id')})")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_material_api_formats())