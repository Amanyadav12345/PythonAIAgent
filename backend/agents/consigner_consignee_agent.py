#!/usr/bin/env python3
"""
ConsignerConsigneeAgent - Enhanced agent for handling both consigner and consignee selection
Supports shared partner lists, data storage, and API integration
"""
import json
from typing import Dict, List, Any, Optional
from .base_agent import BaseAPIAgent, APIIntent, APIResponse

class ConsignerConsigneeAgent(BaseAPIAgent):
    """Enhanced agent for selecting both consigners and consignees with shared data"""
    
    def __init__(self):
        auth_config = {
            "username": "917340224449",
            "password": "12345",
            "token": None
        }
        super().__init__(
            name="consigner_consignee",
            base_url="https://35.244.19.78:8042/preferred_partners",
            auth_config=auth_config
        )
        
        # Data storage for selected details
        self.selection_data = {
            "consigner": None,
            "consignee": None,
            "shared_partners": [],
            "current_step": "consigner",  # 'consigner' or 'consignee'
            "trip_id": None,
            "parcel_id": None,
            "user_context": {}
        }
    
    async def execute(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Execute consigner/consignee selection based on intent"""
        try:
            if intent == APIIntent.SEARCH:
                return await self._get_preferred_partners(data)
            elif intent == APIIntent.UPDATE:
                return await self._handle_selection(data)
            elif intent == APIIntent.CREATE:
                return await self._initialize_selection_process(data)
            else:
                return APIResponse(
                    success=False,
                    error=f"Unsupported intent: {intent}",
                    agent_name=self.name
                )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"ConsignerConsigneeAgent error: {str(e)}",
                agent_name=self.name
            )
    
    async def _initialize_selection_process(self, data: Dict[str, Any]) -> APIResponse:
        """Initialize the consigner/consignee selection process"""
        try:
            # Store context for the selection process
            self.selection_data["trip_id"] = data.get("trip_id")
            self.selection_data["parcel_id"] = data.get("parcel_id")
            self.selection_data["user_context"] = data.get("user_context", {})
            self.selection_data["current_step"] = "consigner"
            
            # Fetch preferred partners
            company_id = data.get("company_id", "62d66794e54f47829a886a1d")
            partners_response = await self._get_preferred_partners({
                "company_id": company_id,
                "page": 0,
                "page_size": 10  # Get more partners initially
            })
            
            if partners_response.success:
                self.selection_data["shared_partners"] = partners_response.data.get("partners", [])
                
                # Format initial consigner selection message
                partners_to_show = self.selection_data["shared_partners"][:5]  # Show first 5
                formatted_message = self.format_consigner_selection_message(partners_to_show)
                button_data = self.format_partners_as_buttons(partners_to_show, "consigner", 0)
                
                return APIResponse(
                    success=True,
                    data={
                        "message": formatted_message,
                        "current_step": "consigner",
                        "partners": partners_to_show,
                        "button_data": button_data,
                        "total_partners": len(self.selection_data["shared_partners"]),
                        "selection_data": self.get_selection_summary(),
                        "requires_user_input": True,
                        "input_type": "consigner_selection"
                    },
                    agent_name=self.name
                )
            else:
                return partners_response
                
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Error initializing selection process: {str(e)}",
                agent_name=self.name
            )
    
    async def _get_preferred_partners(self, data: Dict[str, Any]) -> APIResponse:
        """Get preferred partners for selection"""
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
                "max_results": str(page_size + 10),
                "skip": str(page * page_size)
            }
            
            print(f"ConsignerConsigneeAgent: Searching for company_id: {company_id}")
            
            response = await self._make_request("GET", "", params=params)
            
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
            
            # Process partners for display
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
            user_partner = item.get("user_preferred_partner")
            if not user_partner:
                return None
            
            partner_name = user_partner.get("name", "Unknown Partner")
            partner_id = user_partner.get("_id", "")
            
            # Get city information
            postal_addresses = user_partner.get("postal_addresses", [])
            city_name = "Unknown City"
            if postal_addresses and len(postal_addresses) > 0:
                city_info = postal_addresses[0].get("city", {})
                if isinstance(city_info, dict):
                    city_name = city_info.get("name", "Unknown City")
                elif isinstance(city_info, str):
                    city_name = city_info
            
            # Get company info
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
    
    async def _handle_selection(self, data: Dict[str, Any]) -> APIResponse:
        """Handle partner selection for consigner or consignee"""
        try:
            selection_type = data.get("selection_type", self.selection_data["current_step"])
            partner_id = data.get("partner_id")
            partner_name = data.get("partner_name")
            
            if not partner_id or not partner_name:
                return APIResponse(
                    success=False,
                    error="Partner ID and name are required for selection",
                    agent_name=self.name
                )
            
            # Validate sequential flow - consigner must be selected first
            if selection_type == "consignee" and self.selection_data["current_step"] != "consignee":
                return APIResponse(
                    success=False,
                    error="Please select a consigner first before selecting a consignee",
                    agent_name=self.name
                )
            
            if selection_type == "consigner" and self.selection_data["current_step"] != "consigner":
                return APIResponse(
                    success=False,
                    error="Consigner has already been selected. Please select a consignee or restart the process",
                    agent_name=self.name
                )
            
            # Find the selected partner from stored data
            selected_partner = None
            for partner in self.selection_data["shared_partners"]:
                if partner["id"] == partner_id:
                    selected_partner = partner
                    break
            
            if not selected_partner:
                return APIResponse(
                    success=False,
                    error="Selected partner not found in available partners",
                    agent_name=self.name
                )
            
            # Store the selection
            if selection_type == "consigner":
                self.selection_data["consigner"] = selected_partner
                self.selection_data["current_step"] = "consignee"
                
                # Format consignee selection message
                partners_to_show = self.selection_data["shared_partners"][:5]  # Show same list
                formatted_message = self.format_consignee_selection_message(selected_partner, partners_to_show)
                button_data = self.format_partners_as_buttons(partners_to_show, "consignee", 0)
                
                return APIResponse(
                    success=True,
                    data={
                        "action": "consigner_selected",
                        "selected_consigner": selected_partner,
                        "message": formatted_message,
                        "current_step": "consignee",
                        "partners": partners_to_show,
                        "button_data": button_data,
                        "selection_data": self.get_selection_summary(),
                        "requires_user_input": True,
                        "input_type": "consignee_selection"
                    },
                    agent_name=self.name
                )
                
            elif selection_type == "consignee":
                self.selection_data["consignee"] = selected_partner
                self.selection_data["current_step"] = "completed"
                
                # Get complete company details for both consigner and consignee
                print(f"ConsignerConsigneeAgent: Getting complete details for API update...")
                consigner_details_enhanced = await self._enhance_partner_details(self.selection_data["consigner"])
                consignee_details_enhanced = await self._enhance_partner_details(selected_partner)
                
                # Update stored details with enhanced information
                self.selection_data["consigner"] = consigner_details_enhanced
                self.selection_data["consignee"] = consignee_details_enhanced
                
                # Both selections complete - prepare final data with enhanced details
                final_data = self.prepare_final_data()
                
                return APIResponse(
                    success=True,
                    data={
                        "action": "consignee_selected",
                        "selected_consignee": consignee_details_enhanced,
                        "message": self.format_completion_message(),
                        "current_step": "completed", 
                        "final_data": final_data,
                        "selection_data": self.get_selection_summary(),
                        "requires_user_input": False,
                        "ready_for_api": True,
                        "auto_patch_ready": True
                    },
                    agent_name=self.name
                )
            
            else:
                return APIResponse(
                    success=False,
                    error=f"Invalid selection type: {selection_type}",
                    agent_name=self.name
                )
                
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Error handling selection: {str(e)}",
                agent_name=self.name
            )
    
    def get_selection_summary(self) -> Dict[str, Any]:
        """Get current selection summary"""
        return {
            "consigner": self.selection_data["consigner"],
            "consignee": self.selection_data["consignee"],
            "current_step": self.selection_data["current_step"],
            "trip_id": self.selection_data["trip_id"],
            "parcel_id": self.selection_data["parcel_id"],
            "completion_status": {
                "consigner_selected": self.selection_data["consigner"] is not None,
                "consignee_selected": self.selection_data["consignee"] is not None,
                "process_complete": self.selection_data["current_step"] == "completed"
            }
        }
    
    def prepare_final_data(self) -> Dict[str, Any]:
        """Prepare final data structure for API integration"""
        consigner = self.selection_data["consigner"]
        consignee = self.selection_data["consignee"]
        
        return {
            "trip_id": self.selection_data["trip_id"],
            "parcel_id": self.selection_data["parcel_id"],
            "consigner_details": {
                "id": consigner["id"] if consigner else None,
                "name": consigner["name"] if consigner else None,
                "city": consigner["city"] if consigner else None,
                "company_info": consigner.get("company_info", "") if consigner else None
            },
            "consignee_details": {
                "id": consignee["id"] if consignee else None,
                "name": consignee["name"] if consignee else None,
                "city": consignee["city"] if consignee else None,
                "company_info": consignee.get("company_info", "") if consignee else None
            },
            "user_context": self.selection_data["user_context"],
            "api_payload": self.build_api_payload()
        }
    
    def build_api_payload(self) -> Dict[str, Any]:
        """Build the API payload for final submission"""
        consigner = self.selection_data["consigner"]
        consignee = self.selection_data["consignee"]
        
        payload = {
            "trip_id": self.selection_data["trip_id"],
            "parcel_id": self.selection_data["parcel_id"],
            "consigner_id": consigner["id"] if consigner else None,
            "consignee_id": consignee["id"] if consignee else None,
            "user_id": self.selection_data["user_context"].get("user_id"),
            "company_id": self.selection_data["user_context"].get("current_company"),
            "metadata": {
                "consigner_name": consigner["name"] if consigner else None,
                "consigner_city": consigner["city"] if consigner else None,
                "consignee_name": consignee["name"] if consignee else None,
                "consignee_city": consignee["city"] if consignee else None,
                "selection_timestamp": self._get_current_timestamp()
            }
        }
        
        return payload
    
    def format_completion_message(self) -> str:
        """Format the completion message"""
        consigner = self.selection_data["consigner"]
        consignee = self.selection_data["consignee"]
        
        message = "🎉 **Selection Complete!**\n\n"
        message += "**CONSIGNER DETAILS:**\n"
        message += f"• Name: {consigner['name']}\n"
        message += f"• Location: {consigner['city']}\n"
        message += f"• ID: {consigner['id']}\n\n"
        
        message += "**CONSIGNEE DETAILS:**\n"
        message += f"• Name: {consignee['name']}\n"
        message += f"• Location: {consignee['city']}\n"
        message += f"• ID: {consignee['id']}\n\n"
        
        if self.selection_data["trip_id"]:
            message += f"🚛 **Trip ID:** {self.selection_data['trip_id']}\n"
        if self.selection_data["parcel_id"]:
            message += f"📦 **Parcel ID:** {self.selection_data['parcel_id']}\n"
        
        message += "\n✅ All information is ready for API submission!"
        
        return message
    
    def format_consigner_selection_message(self, partners: List[Dict[str, Any]], page: int = 0) -> str:
        """Format message specifically for consigner selection"""
        if not partners:
            return "No preferred partners available for consigner selection."
        
        message = "📋 **STEP 1: Select a CONSIGNER (Sender)**\n\n"
        message += "Choose who will be sending the parcel:\n\n"
        
        # Show available partners
        for i, partner in enumerate(partners, 1):
            partner_name = partner['name']
            city = partner['city'] if partner['city'] != 'Unknown City' else 'Unknown City'
            
            message += f"🔵 `{i}. {partner_name}`\n"
            message += f"   📍 {city}"
            if partner.get('company_info'):
                message += f" • {partner['company_info']}"
            message += "\n\n"
        
        # Action buttons
        message += f"🔵 `Show More Partners`     🔵 `Skip Selection`\n\n"
        message += "💡 **Click on any partner number to select them as CONSIGNER.**"
        
        return message
    
    def format_consignee_selection_message(self, selected_consigner: Dict[str, Any], 
                                         partners: List[Dict[str, Any]], page: int = 0) -> str:
        """Format message specifically for consignee selection after consigner is selected"""
        if not partners:
            return f"✅ Consigner selected: {selected_consigner['name']}\n\nNo partners available for consignee selection."
        
        message = f"✅ **CONSIGNER SELECTED:** {selected_consigner['name']} ({selected_consigner['city']})\n\n"
        message += "📋 **STEP 2: Select a CONSIGNEE (Receiver)**\n\n"
        message += "Choose who will be receiving the parcel:\n\n"
        
        # Show available partners (same list, but different purpose)
        for i, partner in enumerate(partners, 1):
            partner_name = partner['name']
            city = partner['city'] if partner['city'] != 'Unknown City' else 'Unknown City'
            
            # Highlight if it's the same as consigner
            if partner['id'] == selected_consigner['id']:
                message += f"🔵 `{i}. {partner_name}` *(Same as Consigner)*\n"
            else:
                message += f"🔵 `{i}. {partner_name}`\n"
            
            message += f"   📍 {city}"
            if partner.get('company_info'):
                message += f" • {partner['company_info']}"
            message += "\n\n"
        
        # Action buttons
        message += f"🔵 `Show More Partners`     🔵 `Skip Selection`\n\n"
        message += "💡 **Click on any partner number to select them as CONSIGNEE.**"
        
        return message

    def format_partners_for_display(self, partners: List[Dict[str, Any]], 
                                  selection_type: str, page: int = 0) -> str:
        """Format partners list for display"""
        if not partners:
            return f"No preferred partners available for {selection_type} selection."
        
        current_step = selection_type.title()
        message = f"**Select a {current_step}:**\n\n"
        
        # Show current selection status
        if self.selection_data["consigner"]:
            consigner = self.selection_data["consigner"]
            message += f"✅ **Consigner:** {consigner['name']} ({consigner['city']})\n\n"
        
        # Show available partners
        for i, partner in enumerate(partners, 1):
            partner_name = partner['name']
            city = partner['city'] if partner['city'] != 'Unknown City' else 'Unknown City'
            
            message += f"🔵 `{i}. {partner_name}`\n"
            message += f"   📍 {city}"
            if partner.get('company_info'):
                message += f" • {partner['company_info']}"
            message += "\n\n"
        
        # Action buttons
        message += f"🔵 `Show More Partners`     🔵 `Skip Selection`\n\n"
        message += f"💡 **Click on any partner number to select them as {selection_type}.**"
        
        return message
    
    def format_partners_as_buttons(self, partners: List[Dict[str, Any]], 
                                 selection_type: str, page: int = 0) -> Dict[str, Any]:
        """Format partners as button data for frontend"""
        if not partners:
            return {
                "buttons": [],
                "message": f"No preferred partners available for {selection_type} selection.",
                "has_action_buttons": True,
                "action_buttons": [
                    {"text": f"Skip {selection_type.title()} Selection", "value": "skip", "style": "secondary"}
                ]
            }
        
        # Create partner selection buttons
        partner_buttons = []
        for i, partner in enumerate(partners, 1):
            partner_name = partner['name']
            city = partner['city']
            
            button_text = f"{i}. {partner_name}"
            if len(button_text) > 35:
                button_text = f"{i}. {partner_name[:30]}..."
            
            partner_buttons.append({
                "text": button_text,
                "value": f"{selection_type}_{partner['id']}",
                "style": "primary",
                "subtitle": f"📍 {city}",
                "partner_data": {
                    "id": partner['id'],
                    "name": partner['name'],
                    "city": partner['city'],
                    "selection_type": selection_type,
                    "display_number": i
                },
                "api_data": {
                    "partner_id": partner['id'],
                    "partner_name": partner['name'],
                    "selection_type": selection_type
                }
            })
        
        # Create action buttons
        action_buttons = [
            {
                "text": "Show More Partners", 
                "value": "show_more", 
                "style": "secondary",
                "api_data": {
                    "selection_type": "more",
                    "action": "show_more"
                }
            },
            {
                "text": f"Skip {selection_type.title()}", 
                "value": f"skip_{selection_type}", 
                "style": "outline",
                "api_data": {
                    "selection_type": "skip",
                    "action": f"skip_{selection_type}"
                }
            }
        ]
        
        return {
            "buttons": partner_buttons,
            "action_buttons": action_buttons,
            "message": f"Select a {selection_type} from the options below:",
            "page": page,
            "total_partners": len(partners),
            "selection_type": selection_type
        }
    
    def reset_selection_data(self):
        """Reset selection data for new process"""
        self.selection_data = {
            "consigner": None,
            "consignee": None,
            "shared_partners": [],
            "current_step": "consigner",
            "trip_id": None,
            "parcel_id": None,
            "user_context": {}
        }
    
    async def _enhance_partner_details(self, partner: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance partner details with company information for API"""
        if not partner or not partner.get("id"):
            return partner
        
        try:
            # Get company details for this partner
            company_info = await self._get_partner_companies(partner["id"])
            
            enhanced_partner = partner.copy()
            
            if company_info.get("success") and company_info.get("companies"):
                companies = company_info["companies"]
                primary_company = companies[0] if companies else {}
                
                # Add company information to partner details
                enhanced_partner["company_id"] = primary_company.get("_id", "")
                enhanced_partner["company_name"] = primary_company.get("name", "")
                enhanced_partner["gstin"] = primary_company.get("gstin", "")
                enhanced_partner["companies"] = companies
                enhanced_partner["total_companies"] = len(companies)
                
                print(f"ConsignerConsigneeAgent: Enhanced {partner['name']} with {len(companies)} company details")
            else:
                print(f"ConsignerConsigneeAgent: Could not get company details for {partner['name']}")
                # Set empty defaults
                enhanced_partner["company_id"] = ""
                enhanced_partner["company_name"] = ""
                enhanced_partner["gstin"] = ""
                enhanced_partner["companies"] = []
                enhanced_partner["total_companies"] = 0
            
            return enhanced_partner
            
        except Exception as e:
            print(f"ConsignerConsigneeAgent: Error enhancing partner details: {str(e)}")
            return partner
    
    async def _get_partner_companies(self, partner_id: str) -> Dict[str, Any]:
        """Get company details for a partner using getUserCompany API"""
        if not partner_id:
            return {"success": False, "error": "No partner ID provided"}
        
        try:
            import httpx
            
            # Build the API URL
            api_url = f"https://35.244.19.78:8042/get_user_companies"
            params = {"user_id": partner_id}
            
            print(f"ConsignerConsigneeAgent: Getting company details for partner: {partner_id}")
            
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                # Use Basic Auth
                auth = (self.auth_config["username"], self.auth_config["password"])
                
                response = await client.get(api_url, params=params, auth=auth)
                
                if response.status_code == 200:
                    data = response.json()
                    companies = data.get("companies", []) if isinstance(data, dict) else []
                    
                    print(f"ConsignerConsigneeAgent: Found {len(companies)} companies for partner {partner_id}")
                    
                    return {
                        "success": True,
                        "companies": companies,
                        "total": len(companies)
                    }
                else:
                    print(f"ConsignerConsigneeAgent: Failed to get companies for partner {partner_id}: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API call failed with status {response.status_code}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            print(f"ConsignerConsigneeAgent: Exception getting company details for partner {partner_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Exception: {str(e)}"
            }

    def _get_current_timestamp(self) -> str:
        """Get current timestamp for metadata"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_supported_intents(self) -> List[APIIntent]:
        """Return list of supported intents"""
        return [APIIntent.SEARCH, APIIntent.UPDATE, APIIntent.CREATE]
    
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
                return "partner_id is required for selection"
        elif intent == APIIntent.CREATE:
            # For initialization, basic validation
            pass
        return None