from datetime import timedelta
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
from auth import (
    authenticate_user, create_access_token, verify_token, get_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, Token, User
)
from agent_service import agent_service, ChatRequest, ChatResponse
from agents.agent_manager import agent_manager, WorkflowIntent

app = FastAPI(title="🚛 Truck & Rolling Radius Management API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev server
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "User-Agent"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class LoginRequest(BaseModel):
    username: str
    password: str

async def get_current_user(request: Request):
    """Authentication handler that supports both Basic Auth and Bearer tokens"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    authorization = request.headers.get("authorization", "")
    print(f"Auth debug: Authorization header: '{authorization[:50]}{'...' if len(authorization) > 50 else ''}'")
    
    if not authorization:
        print("Auth debug: No authorization header found")
        raise credentials_exception
    
    # Handle Basic Auth (from external API)
    if authorization.startswith("Basic "):
        try:
            basic_token = authorization.replace("Basic ", "")
            decoded = base64.b64decode(basic_token).decode('utf-8')
            username, password = decoded.split(':', 1)
            
            # For basic auth, create a simple user object
            # In a real app, you'd validate against external API or DB
            return User(username=username, full_name=username, email=f"{username}@external.api")
        except Exception:
            raise credentials_exception
    
    # Handle Bearer Token (JWT)
    elif authorization.startswith("Bearer "):
        try:
            token = authorization.replace("Bearer ", "")
            token_data = verify_token(token, credentials_exception)
            user = get_user(username=token_data.username)
            if user is None:
                raise credentials_exception
            return user
        except Exception:
            raise credentials_exception
    
    # Handle raw basic auth token (stored from external API)
    else:
        try:
            # If it's a raw basic auth token, decode it
            decoded = base64.b64decode(authorization).decode('utf-8')
            username, password = decoded.split(':', 1)
            
            # For basic auth, create a simple user object
            return User(username=username, full_name=username, email=f"{username}@external.api")
        except Exception as e:
            # If base64 decoding fails, it might not be a valid auth token
            print(f"Auth debug: Failed to decode authorization token: {authorization[:20]}..., Error: {e}")
            raise credentials_exception

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login", response_model=Token)
async def login(login_request: LoginRequest):
    user = authenticate_user(login_request.username, login_request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    print(f"Chat request from {current_user.username}: {chat_request.message}")
    print(f"Frontend sent user_id: {chat_request.user_id}")
    
    # PRIORITY: Use the user_id from frontend (localStorage) if available
    # This ensures we always use the ObjectId from the original authentication
    frontend_user_id = chat_request.user_id if chat_request.user_id and chat_request.user_id != current_user.username else None
    
    # PRIORITY: Extract current_company from frontend user_context (localStorage)
    frontend_current_company = None
    if hasattr(chat_request, 'user_context') and chat_request.user_context:
        frontend_current_company = chat_request.user_context.get("current_company")
        print(f"Found current_company from frontend user_context: {frontend_current_company}")
    
    # Get authenticated user info from agent manager for additional context
    auth_agent = agent_manager.get_agent("auth")
    user_info = None
    if auth_agent and auth_agent.is_user_authenticated(current_user.username):
        user_info = auth_agent.get_user_info(current_user.username)
    
    # Build user context prioritizing frontend data (from localStorage)
    if frontend_user_id:
        # Use the user_id from frontend (localStorage) - this is the definitive ObjectId
        print(f"Using frontend user_id from localStorage: {frontend_user_id}")
        
        # PRIORITY: Use frontend current_company if available, fallback to auth agent
        effective_current_company = frontend_current_company or (user_info.get("current_company") if user_info else None)
        print(f"Using current_company: {effective_current_company} (frontend: {frontend_current_company}, auth: {user_info.get('current_company') if user_info else None})")
        
        if user_info:
            user_record = user_info.get("user_record")
            chat_request.user_context = {
                "user_id": frontend_user_id,  # Always use frontend ObjectId
                "username": current_user.username,
                "name": user_info.get("name"),
                "email": user_info.get("email"),
                "current_company": effective_current_company,  # Use prioritized current_company
                "user_record": user_record
            }
        else:
            # Minimal context with frontend user_id and current_company
            chat_request.user_context = {
                "user_id": frontend_user_id,  # Always use frontend ObjectId
                "username": current_user.username,
                "current_company": frontend_current_company  # Include current_company from frontend
            }
    elif user_info:
        # Fallback to auth agent data if no frontend user_id
        user_record = user_info.get("user_record")
        user_id = user_info.get("user_id")
        
        # PRIORITY: Use frontend current_company if available, fallback to auth agent
        effective_current_company = frontend_current_company or user_info.get("current_company")
        print(f"Using auth agent user_id: {user_id}")
        print(f"Using current_company: {effective_current_company} (frontend: {frontend_current_company}, auth: {user_info.get('current_company')})")
        
        chat_request.user_id = user_id or current_user.username
        chat_request.user_context = {
            "user_id": user_id or current_user.username,
            "username": current_user.username,
            "name": user_info.get("name"),
            "email": user_info.get("email"), 
            "current_company": effective_current_company,  # Use prioritized current_company
            "user_record": user_record
        }
    else:
        # Final fallback to username - still include frontend current_company if available
        print(f"Using fallback username: {current_user.username}")
        chat_request.user_id = current_user.username
        chat_request.user_context = {
            "user_id": current_user.username,
            "username": current_user.username,
            "current_company": frontend_current_company  # Include frontend current_company even in fallback
        }
    
    # Process the message through the AI agent
    response = await agent_service.process_message(chat_request)
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/auth/direct")
async def direct_auth(login_request: LoginRequest):
    """Direct authentication using the external auth API"""
    try:
        success, user_info, error = await agent_manager.authenticate_user_and_setup(
            login_request.username, 
            login_request.password
        )
        
        if success:
            # Create a JWT token for our backend
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user_info.get("username", user_info.get("user_id"))}, 
                expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "direct_auth": True,
                "user_info": user_info
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Direct authentication failed: {error}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication service error: {str(e)}"
        )

class UserCompaniesRequest(BaseModel):
    user_id: str

@app.post("/user_companies")
async def get_user_companies(
    request: Request,
    user_request: UserCompaniesRequest,
    current_user: User = Depends(get_current_user)
):
    """Get companies for a specific user (used when selecting consignors)"""
    user_id = user_request.user_id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required"
        )
    
    try:
        # Use the agent manager's method to call getUserCompany API
        companies_response = await agent_manager._call_get_user_companies_api(user_id)
        
        if companies_response.get("success"):
            return {
                "success": True,
                "companies": companies_response.get("companies", []),
                "total": companies_response.get("total", 0)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to get companies: {companies_response.get('error', 'Unknown error')}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user companies: {str(e)}"
        )

@app.get("/")
async def root():
    return {"message": "🚛 Truck & Rolling Radius Management API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)