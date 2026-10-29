import bcrypt
import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import HTTPException
load_dotenv()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
def hash_password(password:str):
    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )
    return hashed.decode("utf-8")
def verify_password(password:str, hashed_password:str):
    verify = bcrypt.checkpw(
        password.encode("utf-8"),
        hashed_password.encode("utf-8"),
        
    )
    return verify
def create_access_token(data:dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes = 30)
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt
def verify_access_token(token:str):
    try:
        payload = jwt.decode(
            token, 
            JWT_SECRET_KEY, algorithms = ["HS256"]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code = 401, detail = "Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException (
            status_code = 401, detail = "Invalid token"
        )
    return payload