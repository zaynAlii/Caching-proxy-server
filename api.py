from fastapi import FastAPI , Request , Response , Depends , HTTPException
from fastapi.exceptions import RequestValidationError
# from starlette.exceptions import HTTPException as StarletteHTTPException

from concurrent.futures import ThreadPoolExecutor
import requests
import logging
import sys

from redis import Redis , ConnectionPool , ConnectionError , TimeoutError
from  typing import Any
import pickle
import gzip
from dotenv import load_dotenv
import os
from typing import Annotated
from .utility import fetchFromUpstreamServer , serilizeData , decerilizaeData

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('proxy_server.log')
    ]
)
logger = logging.getLogger(__name__)

# Environment variable validation
def validate_environment_variables():
    """Validate required environment variables at startup."""
    required_vars = {
        "PROXY_URL": str,
        "DATA_EXPIRY": int,
        "REDIS_HOST": str,
        "REDIS_PORT": int
    }

    missing_vars = []
    invalid_vars = []

    for var_name, var_type in required_vars.items():
        value = os.environ.get(var_name)
        if value is None:
            missing_vars.append(var_name)
            continue

        try:
            if var_type == int:
                int(value)
            elif var_type == str and not value.strip():
                raise ValueError("Empty string")
        except (ValueError, TypeError):
            invalid_vars.append(f"{var_name} (expected {var_type.__name__})")

    if missing_vars or invalid_vars:
        error_msg = "Environment variable validation failed:"
        if missing_vars:
            error_msg += f"\nMissing required variables: {', '.join(missing_vars)}"
        if invalid_vars:
            error_msg += f"\nInvalid variables: {', '.join(invalid_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Environment variables validated successfully")

# Validate environment variables at startup
try:
    validate_environment_variables()
    proxy_URL: str = os.environ["PROXY_URL"]
    DATAEXPIRY: int = int(os.environ["DATA_EXPIRY"])
    RedisHost: str = os.environ["REDIS_HOST"]
    Redisport: int = int(os.environ["REDIS_PORT"])
    logger.info(f"Configuration loaded: Proxy URL={proxy_URL}, Redis={RedisHost}:{Redisport}, Cache expiry={DATAEXPIRY}s")
except ValueError as e:
    sys.exit(1)





app:FastAPI=FastAPI()




redis_coonect:ConnectionPool=ConnectionPool(
  host=RedisHost,
  port=Redisport,
  db=0,
  max_connections=20,
  socket_connect_timeout=5,
  socket_timeout =5  ,
  retry_on_timeout=True  
)



executor= ThreadPoolExecutor(max_workers=12)

def get_Redis()->Redis:
    """
       Dependency injection to get redis Client with error handling

    Returns:
        Redis: Redis client instance

    Raises:
        HTTPException: If Redis connection fails
    """
    try:
        redis_client:Redis = Redis(connection_pool=redis_coonect)
        # Test the connection
        redis_client.ping()
        return redis_client
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Cache service temporarily unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected Redis error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Cache service error. Please try again later."
        )

# dependencyRedisClient=Annotated[Redis , Depends(get_Redis)]


@app.api_route("/{path:path}",methods=["GET"])
def CachingProxyHandler(path:str , request:Request , redis:Redis=Depends(get_Redis) ):
    
    
    chache_key=f"cache:{request.url.path}"
    
    
    
    try :
        Cached_DataIs = redis.get(chache_key)
        if Cached_DataIs is not None:    
            # print(f"Cached_DataIs: Is this {Cached_DataIs}")
            deserelizetion=decerilizaeData(Cached_DataIs)
            # print(deserelizetion)
            response= Response(
                content=deserelizetion["content"],
                status_code=deserelizetion["status_code"],
                headers=deserelizetion["headers"]
            )
            
            response.headers["X-CACHE"]="SMACH-HIT"
            print("\n\\n\nn===================================================",response.headers["X-CACHE"],"=============================================================\n\n\n\n")
            return response
        
    
    except Exception as e :
        pass    
    
    
    # Fetch from upstream server
    full_url = f"{proxy_URL}{request.url.path}"
    logger.info(f"Fetching from upstream: {full_url}")

    try:
        results = fetchFromUpstreamServer(full_url)
        if results is None:
            logger.error(f"Upstream server returned None for URL: {full_url}")
            raise HTTPException(
                status_code=502,
                detail="Upstream server error: Unable to fetch data"
            )

        # Create response from upstream data
        response = Response(
            content=results.content,
            status_code=results.status_code,
            headers=results.headers
        )

        response.headers["X-CACHE"] = "MISS"
        # logger.info(f"Upstream response: status={results.status_code}, content_length={len(results.content) if results.content else 0}")
        print("\n\n================================================",response.headers["X-CACHE"],"=====================================================\n\n")
        # Cache successful responses (2xx status codes)
        if  results.status_code ==200:
            response_data = {
                "content": results.content,
                "status_code": results.status_code,
                "headers": dict(results.headers)  # Convert to dict for serialization
            }
            try:
                executor.submit(storeInChache, redis, chache_key, response_data, DATAEXPIRY)
                logger.debug(f"Submitted cache storage task for key: {chache_key}")
            except Exception as e:
                logger.error(f"Failed to submit cache storage task: {e}")
        else:
            logger.warning(f"Not caching non-success response: status={results.status_code}")

        return response

    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error during upstream fetch for {full_url}: {e}")
        raise HTTPException(
            status_code=502,
            detail="Upstream server error: Service temporarily unavailable"
        )

def storeInChache(redisClient: Redis, key: str, data: dict[str, Any], expiry: int):
    """
    Store data in cache asynchronously with proper error handling.

    Args:
        redisClient: Redis client instance
        key: Cache key
        data: Data to cache
        expiry: Expiry time in seconds
    """
    try:
        logger.debug(f"Storing data in cache for key: {key}")
        serialized_data = serilizeData(data)
        result = redisClient.set(key, serialized_data, ex=expiry)

        if result:
            logger.debug(f"Successfully cached data for key: {key}")
        else:
            logger.warning(f"Failed to cache data for key: {key} - Redis set returned False")

    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection error while caching key {key}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while caching key {key}: {e}")
        # Note: We don't raise exceptions here as this is async and shouldn't break the main response
    
@app.post("/clear/incache")
def clearCache(redis: Redis = Depends(get_Redis)):
    """
    Clear all cached data
    """
    try:
        logger.info("Clearing cache database")
        result = redis.flushdb()
        if result:
            logger.info("Cache cleared successfully")
            return {"status": "Cache cleared successfully", "message": "All cached data has been removed"}
        else:
            logger.warning("Cache flush returned False - may not have cleared properly")
            return {"status": "Cache clear attempted", "message": "Cache clear operation completed"}

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear cache. Please try again later."
        )
