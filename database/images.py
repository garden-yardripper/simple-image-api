from pydantic import BaseModel, field_validator, field_serializer
from .database import Database
from urllib.parse import urljoin
from datetime import datetime

class Image(BaseModel):
    image_id: str
    key_id: str
    file_path: str
    file_name: str | None
    file_size: int | None
    mime_type: str | None
    title: str | None
    description: str | None
    private: bool
    uploaded: datetime
    last_updated: datetime
    
    @classmethod
    @field_validator("uploaded", "last_updated", mode="before")
    def convert_timestamp_to_datetime(cls, value):
        if isinstance(value, float) or isinstance(value, int):
            return datetime.fromtimestamp(value)
        return value
    
    @field_serializer("uploaded", "last_updated")
    def serialize_datetime_to_timestamp(self, time: datetime) -> float:
        return time.timestamp()

class UploadedImage(BaseModel):
    image_id: str
    hosted_link: str
    mimetype: str | None
    title: str | None
    description: str | None
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
            file_size, mime_type, title, description, private
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
        (image_id, key_id, file_path, file_name, file_size, mime_type, title, description, private)
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

async def get_image_data_from_id(db: Database, image_id: str) -> Image | None:
    result = await db.fetchone("SELECT * FROM images WHERE image_id = %s", (image_id,))
    if not result:
        return None
    return Image.model_validate(result)