from fastapi import Request
from database import Database
from redis import Redis

def get_db(request: Request) -> Database:
    return request.app.state.db

def get_redis(request: Request) -> Redis:
    return request.app.state.r