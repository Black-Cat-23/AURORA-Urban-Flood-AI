from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# Security configurations
SECRET_KEY = "AURORA_SUPER_SECRET_KEY_FOR_HACKATHON"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Models ---
class UserData(BaseModel):
    username: str
    role: str # "Citizen", "Ward Officer", "City Admin", "System Admin"
    ward_id: Optional[str] = None # Only for Ward Officers

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    ward_id: Optional[str] = None

# --- Mock Database of Enrolled Users ---
# In a true deployment, this hooks to PostgreSQL. Passwords are 'citizentest', 'officertest', 'admintest', 'systest'
users_db = {
    "citizen_1": {
        "username": "citizen_1",
        "full_name": "Ramesh Kumar",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW", # citizentest
        "role": "Citizen",
        "ward_id": None
    },
    "officer_hwest": {
        "username": "officer_hwest",
        "full_name": "Anita Desai",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW", # officertest
        "role": "Ward Officer",
        "ward_id": "Ward H-West" # Rigidly bound to H-West
    },
    "city_admin": {
        "username": "city_admin",
        "full_name": "Municipal Commissioner",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW", # admintest
        "role": "City Admin",
        "ward_id": None
    },
    "sys_admin": {
        "username": "sys_admin",
        "full_name": "Tech Ops Lead",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW", # systest
        "role": "System Admin",
        "ward_id": None
    }
}

# --- Core Security Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(username: str):
    if username in users_db:
        return users_db[username]
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Authorization Dependencies (The Middleware) ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        ward_id: str = payload.get("ward_id")
        
        if username is None or role is None:
            raise credentials_exception
            
        token_data = TokenData(username=username, role=role, ward_id=ward_id)
    except JWTError:
        raise credentials_exception
        
    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
        
    return UserData(**user)

# Role Requirement Verification Generator
def require_role(allowed_roles: list[str]):
    def role_checker(current_user: UserData = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            
            # FIRE AUDIT LOGGING EVENT FOR UNAUTHORIZED ESCALATION ATTEMPT
            import logging
            logging.warning(f"[AUDIT] SECURITY BREACH BLOCKED: User '{current_user.username}' (Role: {current_user.role}) attempted unauthorized action requiring roles: {allowed_roles}.")
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {allowed_roles}. Your role: {current_user.role}"
            )
        return current_user
    return role_checker
