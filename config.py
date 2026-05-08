from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field

class DBSettings(BaseModel):
    host: str
    user: str
    password: str
    name: str
    port: int
    min_pool_size: int = Field(alias="minpoolsize")
    max_pool_size: int = Field(alias="maxpoolsize")

class RedisSettings(BaseModel):
    host: str
    max_connections: int = Field(alias="maxconnections")
    port: int

class Settings(BaseSettings):
    db: DBSettings
    redis: RedisSettings
    
    rate_limit: int = Field(alias="ratelimit")
    per_seconds: int = Field(alias="perseconds")
    image_directory: str = Field(alias="imagedirectory")

    model_config = SettingsConfigDict(
        env_nested_delimiter="_",
        case_sensitive=False
    )

settings = Settings(_env_file=".env") # type: ignore # will be populated when the .env is read