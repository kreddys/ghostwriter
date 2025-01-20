"""Ghost API token generation utilities."""

import jwt
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_ghost_token(admin_api_key: str) -> str:
    """
    Generate a Ghost Admin API token using JWT.
    
    Args:
        admin_api_key (str): Ghost Admin API key in format 'id:secret'
        
    Returns:
        str: Generated JWT token
    """
    try:
        # Split the key into ID and SECRET
        key_id, secret = admin_api_key.split(':')
        
        # Create the token payload
        iat = int(datetime.now().timestamp())
        
        header = {
            'alg': 'HS256',
            'typ': 'JWT',
            'kid': key_id
        }
        
        payload = {
            'iat': iat,
            'exp': iat + 5 * 60,  # Token expires in 5 minutes
            'aud': '/admin/'
        }
        
        # Create the token
        token = jwt.encode(
            payload, 
            bytes.fromhex(secret), 
            algorithm='HS256', 
            headers=header
        )
        
        return token
        
    except Exception as e:
        logger.error(f"Error generating Ghost token: {str(e)}")
        raise