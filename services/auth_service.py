from database import Database, auth
from database.auth import UserApiKey
from responses import ApiKeyInvalidError, ApiKeyMissingError

async def check_for_key(db: Database, api_key: str) -> UserApiKey:
    if not api_key:
        raise ApiKeyMissingError
    
    user_key = UserApiKey.from_full_key(api_key)
    if not await auth.validate_key(db, user_key):
        raise ApiKeyInvalidError
    return user_key