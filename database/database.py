import aiomysql
from config import settings

async def create_pool() -> aiomysql.Pool:
    db = settings.db
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
    
class Database:
    def __init__(self, pool: aiomysql.Pool) -> None:
        self.pool = pool
    
    async def fetchall(self, query, args = ()) -> list[dict]:
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                return await cur.fetchall()
            
    async def fetchmany(self, size: int, query, args = ()) -> list[dict]:
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                return await cur.fetchmany(size)
            
    async def fetchone(self, query, args = ()) -> dict | None:
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                return await cur.fetchone()
            
    async def execute(self, query, args = ()) -> None:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                await conn.commit()