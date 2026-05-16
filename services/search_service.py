from fastapi import HTTPException
from database.database import Database
from database.auth import get_key_id_from_username

async def search(db: Database, use_and: bool, **kwargs):
    whitelist = {
        "image_id", "title", "description",
        "username", "file_name", "mime_type",
        "uploaded_before", "uploaded_after",
        "updated_before", "updated_after",
        "file_size_greater", "file_size_less"
    }
    
    unknown_keys = set(kwargs.keys()) - whitelist
    if unknown_keys:
        raise HTTPException(400, f"Unknown search parameters: {', '.join(sorted(unknown_keys))}")
    
    conditions = {}
    
    for key, value in kwargs.items():
        if value is None:
            continue
        
        if key in ("mime_type", "image_id"):
            conditions[f"{key} = %s"] = value
        
        elif key in ("title", "description", "file_name"):
            conditions[f"{key} LIKE %s"] = value
        
        elif key == "username":
            key_id = await get_key_id_from_username(db, value)
            if not key_id:
                continue
            conditions["key_id = %s"] = key_id
            
        elif key in ("uploaded_before", "uploaded_after", "updated_before", "updated_after"):
            column, check = key.split("_", 1)
            operator = "<" if check == "before" else ">"
            conditions[f"{column} {operator} %s"] = value
            
        elif key in ("file_size_greater", "file_size_less"):
            operator = "<" if key.endswith("less") else ">"
            conditions[f"file_size {operator} %s"] = value
    
    if not conditions:
        return await db.fetchall("SELECT * FROM images")
    
    query = f"SELECT * FROM images WHERE {(' AND ' if use_and else ' OR ').join(conditions.keys())}"
    parameters = tuple(conditions.values())
    
    return await db.fetchall(query, parameters)