from contextlib import asynccontextmanager
import aiomysql
from pydantic import BaseModel
from config import settings
import logging

logger = logging.getLogger(__name__)

async def create_pool() -> aiomysql.Pool:
    db = settings.db
    logger.info("Creating database connection pool on host %s", db.host)
    return await aiomysql.create_pool(
        minsize=db.min_pool_size,
        maxsize=db.max_pool_size,
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        db=db.name,
        autocommit=False
    )

class QueryResult[T: (dict, list[dict], None)](BaseModel):
    rowcount: int
    lastrowid: int | None
    result: T

class Database:
    def __init__(self, pool: aiomysql.Pool) -> None:
        self.pool = pool
    
    @asynccontextmanager
    async def transaction(self):
        logger.debug("Database transaction started.")
        async with self.pool.acquire() as conn:
            try:
                yield conn
                await conn.commit()
                logger.debug("Database transaction committed successfully.")
            except Exception:
                logger.exception("Error occured, rolling back transaction.")
                await conn.rollback()
                raise
    
    async def fetchall(self, query: str, args = ()) -> QueryResult[list[dict]]:
        logger.debug("Fetching all with %s database query.", query.split()[0])
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                rows = await cur.fetchall()
                return QueryResult(rowcount=cur.rowcount, lastrowid=cur.lastrowid, result=rows)
            
    async def fetchmany(self, size: int, query: str, args = ()) -> QueryResult[list[dict]]:
        logger.debug("Fetching %s rows with %s database query.", size, query.split()[0])
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                rows = await cur.fetchmany(size)
                return QueryResult(rowcount=cur.rowcount, lastrowid=cur.lastrowid, result=rows)
            
    async def fetchone(self, query: str, args = ()) -> QueryResult[dict]:
        logger.debug("Fetching one with %s database query.", query.split()[0])
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                row = await cur.fetchone()
                return QueryResult(rowcount=cur.rowcount, lastrowid=cur.lastrowid, result=row)
            
    async def execute(self, query: str, args = ()) -> QueryResult[None]:
        logger.debug("Executing %s database query.", query.split()[0])
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                await conn.commit()
                return QueryResult(rowcount=cur.rowcount, lastrowid=cur.lastrowid, result=None)
                
    async def update_tables(self):
        logger.info("Updating database tables.")
        async with self.transaction() as conn:
            async with conn.cursor() as cur:
                # store API keys in binary instead of 64 character hex because it's more efficient
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS auth (
                        api_key BINARY(32) PRIMARY KEY,
                        salt BINARY(16),
                        key_id VARCHAR(32) NOT NULL UNIQUE,
                        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        username VARCHAR(20) UNIQUE,
                        key_id VARCHAR(32) NOT NULL,
                        FOREIGN KEY (key_id) 
                            REFERENCES auth(key_id) 
                            ON DELETE CASCADE
                    )
                """)
                
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS images (
                        -- identification
                        image_id UUID PRIMARY KEY,
                        key_id VARCHAR(32) NOT NULL UNIQUE,

                        -- file info
                        file_path VARCHAR(255),
                        file_name VARCHAR(100),
                        file_size MEDIUMINT,
                        mime_type VARCHAR(100),

                        -- metadata
                        title VARCHAR(255),
                        description TEXT,
                        private BOOLEAN,

                        -- timestamp
                        uploaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)