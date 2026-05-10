from pydantic import BaseModel
from .database import Database
from urllib.parse import urljoin

class Image(BaseModel):
    image_id: str
    hosted_link: str
    mimetype: str | None
    title: str | None
    description: str | None

class UploadedImage(Image):
    private: bool

async def store_image_metadata(
    db: Database,
    image_id: str,
    key_id: str,
    base_url: str,
    file_extension: str,
    file_path: str,
    file_name: str | None,
    file_size: int | None,
    mime_type: str | None,
    title: str | None,
    description: str | None,
    private: bool
) -> UploadedImage:
    """Returns the UploadedImage object."""
    
    await db.execute("""
        INSERT INTO images (
            image_id, key_id, file_path, file_name, 
            file_size, mime_type, title, description, public
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
        (image_id, key_id, file_path, file_name, file_size, mime_type, title, description, not private)
    )
    
    image = UploadedImage(
        image_id=image_id,
        hosted_link=urljoin(base_url, f"images/{image_id}.{file_extension}"),
        mimetype=mime_type,
        title=title,
        description=description,
        private=private
    )
            
    return image