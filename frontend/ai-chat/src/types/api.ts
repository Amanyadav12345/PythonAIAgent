export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token?: string;
  token_type?: string;
  // Direct auth API response fields
  data?: string;
  ok?: boolean;
  statusText?: string;
  token?: string;
  user_record?: UserRecord;
}

export interface UserRecord {
  _id: string;
  name: string;
  email: string;
  phone: {
    country_phone_code: string;
    number: string;
  };
  current_company: string;
  individual_user_type: string;
  user_type: string;
  role_names: string[];
  roles: Array<{ role: string }>;
  token: string;
  auth_field: string;
  _created: string;
  _updated: string;
  _version: number;
  record_status: string;
}

export interface User {
  username: string;
  email?: string;
  full_name?: string;
  // Extended fields from auth API
  user_id?: string;
  name?: string;
  phone?: string;
  current_company?: string;
  user_type?: string;
  role_names?: string[];
  token?: string;
}

export interface ChatRequest {
  message: string;
  user_id: string;
}

export interface PartnerButton {
  text: string;
  value: string;
  style: 'primary' | 'secondary' | 'outline';
  subtitle?: string;
  partner_data?: {
    id: string;
    name: string;
    city: string;
    display_number: number;
  };
  api_data?: {
    partner_id: string;
    partner_name: string;
    selection_type: string;
  };
}

export interface ActionButton {
  text: string;
  value: string;
  style: 'primary' | 'secondary' | 'outline';
  api_data?: {
    selection_type: string;
    action: string;
  };
}

export interface CompanyButton {
  text: string;
  value: string;
  style: 'primary' | 'secondary' | 'outline';
  subtitle?: string;
  company_data?: {
    id: string;
    name: string;
    gst?: string;
    city?: string;
  };
}

export interface AddressButton {
  text: string;
  value: string;
  style: 'primary' | 'secondary' | 'outline';
  subtitle?: string;
  address_data?: {
    id: string;
    address_line_1: string;
    city: string;
    pin?: string;
    location_type?: string;
  };
}

export interface ButtonData {
  buttons: PartnerButton[];
  action_buttons: ActionButton[];
  message: string;
  page?: number;
  total_partners?: number;
  has_more?: boolean;
}

export interface ChatResponse {
  response: string;
  sources: string[];
  tools_used: string[];
  button_data?: ButtonData;
  partner_buttons?: PartnerButton[];
  action_buttons?: ActionButton[];
  requires_user_input?: boolean;
  input_type?: 'consignor_selection' | 'company_selection';
  available_partners?: any[];
  current_page?: number;
}

export interface ApiError {
  detail: string;
}