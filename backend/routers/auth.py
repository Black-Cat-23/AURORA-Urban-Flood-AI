from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from dependencies import Token, authenticate_user, create_access_token, timedelta, ACCESS_TOKEN_EXPIRE_MINUTES, get_user, verify_password

router = APIRouter(
    prefix="/auth",
    tags=["Authentication & RBAC"]
)

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        import logging
        logging.warning(f"[AUDIT] FAILED LOGIN ATTEMPT: Invalid credentials for username '{form_data.username}'.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Embed the specific Role and Scope (Ward ID) directly into the encrypted JWT Token
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"], "ward_id": user["ward_id"]}, 
        expires_delta=access_token_expires
    )
    
    import logging
    logging.info(f"[AUDIT] SUCCESSFUL LOGIN: User '{user['username']}' assigned role '{user['role']}' with scope '{user['ward_id']}'.")
    
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"], "ward": user.get("ward_id")}
