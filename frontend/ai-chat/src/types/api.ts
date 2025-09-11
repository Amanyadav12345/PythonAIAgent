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

export interface ChatResponse {
  response: string;
  sources: string[];
  tools_used: string[];
}

export interface ApiError {
  detail: string;
}