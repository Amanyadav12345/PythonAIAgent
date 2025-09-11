#!/usr/bin/env python3
"""
Test script to show the actual consignor selection message
"""
import asyncio
import sys
import os
import io
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Set stdout to use UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_consignor_message():
    """Test to display the actual consignor message"""
    print("Testing consignor selection message display...")
    
    try:
        from agent_service import agent_service, ChatRequest
        
        test_message = "Create a trip from Mumbai to Delhi with steel"
        
        chat_request = ChatRequest(
            message=test_message,
            user_id="6257f1d75b42235a2ae4ab34"
        )
        
        chat_request.user_context = {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "username": "917340224449", 
            "name": "Aman yadav",
            "email": "yadavaman2282000@gmail.com",
            "current_company": "62d66794e54f47829a886a1d"
        }
        
        response = await agent_service.process_message(chat_request)
        
        print("\n" + "="*80)
        print("CONSIGNOR SELECTION WORKFLOW - FINAL RESULT")
        print("="*80)
        
        # Try to display the message with UTF-8 encoding
        try:
            print("\nFULL MESSAGE:")
            print("-" * 60)
            print(response.response)
            print("-" * 60)
        except UnicodeEncodeError:
            # Fallback: replace problematic characters
            cleaned_message = response.response.encode('ascii', 'replace').decode('ascii')
            print("\nFULL MESSAGE (cleaned):")
            print("-" * 60)
            print(cleaned_message)
            print("-" * 60)
        
        print(f"\nRESPONSE DATA:")
        if hasattr(response, 'data') and response.data:
            print(f"✅ requires_user_input: {response.data.get('requires_user_input')}")
            print(f"✅ input_type: {response.data.get('input_type')}")
            print(f"✅ trip_id: {response.data.get('trip_id')}")
            print(f"✅ parcel_id: {response.data.get('parcel_id')}")
            
            if response.data.get('consignor_selection'):
                consignor_data = response.data.get('consignor_selection')
                if isinstance(consignor_data, dict):
                    partners = consignor_data.get('partners', [])
                    print(f"✅ Found {len(partners)} preferred partners available for selection")
                    
                    if partners:
                        print("\n📋 PREFERRED PARTNERS:")
                        for i, partner in enumerate(partners[:3], 1):  # Show first 3
                            print(f"   {i}. {partner.get('name', 'Unknown')} ({partner.get('city', 'Unknown City')})")
                        if len(partners) > 3:
                            print(f"   ... and {len(partners) - 3} more partners")
        
        print(f"\n🎯 WORKFLOW STATUS: {'SUCCESS' if response.data and response.data.get('requires_user_input') else 'INCOMPLETE'}")
        print("="*80)
        
        if response.data and response.data.get('requires_user_input'):
            print("\n🚀 NEXT ACTIONS FOR USER:")
            print("1. Frontend should display the partner list")
            print("2. User selects a number (1-5), 'more', or 'skip'")
            print("3. Frontend calls agent_manager.handle_consignor_selection() with user's choice")
            print("4. System processes selection and completes the workflow")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_consignor_message())