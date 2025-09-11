#!/usr/bin/env python3
"""
ConsignorSelectionAgent - Handles selection of consignors from preferred partners
Triggers after successful parcel creation to show available preferred partners
"""
import json
from typing import Dict, List, Any, Optional
from .base_agent import BaseAPIAgent, APIIntent, APIResponse

class ConsignorSelectionAgent(BaseAPIAgent):
    """Agent for selecting consignors from preferred partners API"""
    
    def __init__(self):
        auth_config = {
            "username": "917340224449",
            "password": "12345",
            "token": None
        }
        super().__init__(
            name="consignor_selection",
            base_url="https://35.244.19.78:8042/preferred_partners",
            auth_config=auth_config
        )
    
    async def execute(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Execute consignor selection based on intent"""
        try:
            if intent == APIIntent.SEARCH:
                return await self._get_preferred_partners(data)
            elif intent == APIIntent.UPDATE:
                return await self._select_consignor(data)
            else:
                return APIResponse(
                    success=False,
                    error=f"Unsupported intent: {intent}",
                    agent_name=self.name
                )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"ConsignorSelectionAgent error: {str(e)}",
                agent_name=self.name
            )
    
    async def _get_preferred_partners(self, data: Dict[str, Any]) -> APIResponse:
        """Get preferred partners for consignor selection"""
        try:
            company_id = data.get("company_id", "62d66794e54f47829a886a1d")
            page = data.get("page", 0)
            page_size = data.get("page_size", 5)
            
            # Build embedded query for partner details
            embedded_query = {
                "user_preferred_partner": 1,
                "user_preferred_partner.postal_addresses.city": 1,
                "company_preferred_partner": 1
            }
            
            # Build where query for company filter
            where_query = {
                "user_company": company_id
            }
            
            # Build request parameters
            params = {
                "embedded": json.dumps(embedded_query),
                "where": json.dumps(where_query),
                "max_results": str(page_size + 10),  # Get extra for pagination
                "skip": str(page * page_size)
            }
            
            print(f"ConsignorSelectionAgent: Searching for company_id: {company_id}")
            print(f"ConsignorSelectionAgent: API URL: {self.base_url}")
            print(f"ConsignorSelectionAgent: embedded query: {json.dumps(embedded_query)}")
            print(f"ConsignorSelectionAgent: where query: {json.dumps(where_query)}")
            
            response = await self._make_request("GET", "", params=params)
            
            print(f"ConsignorSelectionAgent: API response success: {response.success}")
            if response.data:
                items = response.data.get("_items", [])
                print(f"ConsignorSelectionAgent: Found {len(items)} items in API response")
            
            if not response.success:
                return APIResponse(
                    success=False,
                    error=f"API request failed: {response.error or 'Unknown error'}",
                    agent_name=self.name
                )
            
            items = response.data.get("_items", []) if response.data else []
            
            if not items:
                return APIResponse(
                    success=True,
                    data={
                        "partners": [],
                        "message": "No preferred partners found for your company",
                        "has_more": False,
                        "page": page
                    },
                    agent_name=self.name
                )
            
            # Process partners for display (5 at a time)
            partners = []
            start_idx = 0
            end_idx = min(page_size, len(items))
            
            for item in items[start_idx:end_idx]:
                partner_info = self._extract_partner_info(item)
                if partner_info:
                    partners.append(partner_info)
            
            has_more = len(items) > end_idx
            
            return APIResponse(
                success=True,
                data={
                    "partners": partners,
                    "message": f"Found {len(partners)} preferred partners",
                    "has_more": has_more,
                    "page": page,
                    "total_available": len(items)
                },
                agent_name=self.name
            )
            
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Error getting preferred partners: {str(e)}",
                agent_name=self.name
            )
    
    def _extract_partner_info(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract partner information for display"""
        try:
            # Get user_preferred_partner data
            user_partner = item.get("user_preferred_partner")
            if not user_partner:
                return None
            
            partner_name = user_partner.get("name", "Unknown Partner")
            partner_id = user_partner.get("_id", "")
            
            # Get city information if available
            postal_addresses = user_partner.get("postal_addresses", [])
            city_name = "Unknown City"
            if postal_addresses and len(postal_addresses) > 0:
                city_info = postal_addresses[0].get("city", {})
                if isinstance(city_info, dict):
                    city_name = city_info.get("name", "Unknown City")
                elif isinstance(city_info, str):
                    city_name = city_info
            
            # Get company_preferred_partner data if available
            company_partner = item.get("company_preferred_partner")
            company_info = ""
            if company_partner:
                company_info = company_partner.get("name", "")
            
            return {
                "id": partner_id,
                "name": partner_name,
                "city": city_name,
                "company_info": company_info,
                "display_text": f"{partner_name} ({city_name})"
            }
            
        except Exception as e:
            print(f"Error extracting partner info: {str(e)}")
            return None
    
    async def _select_consignor(self, data: Dict[str, Any]) -> APIResponse:
        """Handle consignor selection"""
        try:
            selected_partner_id = data.get("partner_id")
            partner_name = data.get("partner_name", "Selected Partner")
            
            if not selected_partner_id:
                return APIResponse(
                    success=False,
                    error="Partner ID is required for selection",
                    agent_name=self.name
                )
            
            # For now, just confirm selection
            # In future, this could update the parcel with consignor info
            return APIResponse(
                success=True,
                data={
                    "selected_partner_id": selected_partner_id,
                    "selected_partner_name": partner_name,
                    "message": f"Successfully selected {partner_name} as consignor",
                    "action": "consignor_selected"
                },
                agent_name=self.name
            )
            
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Error selecting consignor: {str(e)}",
                agent_name=self.name
            )
    
    def format_partners_for_chat(self, partners: List[Dict[str, Any]], page: int = 0) -> str:
        """Format partners list for chat display"""
        if not partners:
            return "No preferred partners available for selection."
        
        message = f"**Available Preferred Partners (Page {page + 1}):**\n\n"
        
        for i, partner in enumerate(partners, 1):
            display_num = (page * 5) + i
            message += f"{display_num}. **{partner['name']}**\n"
            message += f"   Location: {partner['city']}\n"
            if partner.get('company_info'):
                message += f"   Company: {partner['company_info']}\n"
            message += "\n"
        
        message += "Please select a partner by typing the number (e.g., '1', '2', '3')\n"
        message += "Type 'more' to see more partners or 'skip' to continue without selecting."
        
        return message
    
    def get_supported_intents(self) -> List[APIIntent]:
        """Return list of supported intents"""
        return [APIIntent.SEARCH, APIIntent.UPDATE]
    
    async def handle_intent(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Handle intent - delegates to execute method"""
        return await self.execute(intent, data)
    
    def validate_payload(self, intent: APIIntent, data: Dict[str, Any]) -> Optional[str]:
        """Validate payload for specific intent"""
        if intent == APIIntent.SEARCH:
            company_id = data.get("company_id")
            if not company_id:
                return "company_id is required for searching preferred partners"
        elif intent == APIIntent.UPDATE:
            partner_id = data.get("partner_id")
            if not partner_id:
                return "partner_id is required for selecting consignor"
        return None