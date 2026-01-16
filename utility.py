from requests import Response , RequestException , Timeout , ConnectionError
import requests
import gzip
import pickle
import logging
from typing import Any , Optional

logger = logging.getLogger(__name__)
def fetchFromUpstreamServer(url: str) -> Optional[Response]:
    """
    Fetch data from upstream server with proper error handling.

    Args:
        url: The URL to fetch data from

    Returns:
        Response object if successful, None if failed

    Raises:
        No exceptions are raised - errors are logged and None is returned
    """
    try:
        logger.debug(f"Fetching from upstream server: {url}")
        response: Response = requests.get(
            url,
            timeout=(4, 12),
            stream=True,
            headers={
                "User-Agent": "CachingProxy/2.0",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
        )
        logger.debug(f"Upstream response received: status={response.status_code}")
        return response

    except Timeout as e:
        logger.error(f"Timeout error fetching from upstream server {url}: {e}")
    except ConnectionError as e:
        logger.error(f"Connection error fetching from upstream server {url}: {e}")
    except RequestException as e:
        logger.error(f"Request error fetching from upstream server {url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching from upstream server {url}: {e}")

    return None
    
def serilizeData(data: dict[str, Any]) -> bytes:
    """
    Compress data for efficient storage (less memory consumed).

    Args:
        data: Upstream Server data to serialize

    Returns:
        Compressed bytes

    Raises:
        Exception: If serialization or compression fails
    """
    try:
        logger.debug("Serializing data for cache storage")
        raw_bytes = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        compressed_data = gzip.compress(raw_bytes, compresslevel=6)
        logger.debug(f"Data serialized: original_size={len(raw_bytes)}, compressed_size={len(compressed_data)}")
        return compressed_data
    except (pickle.PicklingError, gzip.BadGzipFile, Exception) as e:
        logger.error(f"Error serializing data: {e}")
        raise Exception(f"Data serialization failed: {e}")


def decerilizaeData(serialized_data: bytes) -> dict[str, Any]:
    """
    Decompress data from bytes to original data structure.

    Args:
        serialized_data: Compressed bytes to deserialize

    Returns:
        Original Upstream server data

    Raises:
        Exception: If decompression or deserialization fails
    """
    try:
        logger.debug(f"Deserializing data from cache: size={len(serialized_data)}")
        decompressed_data = gzip.decompress(serialized_data)
        original_data = pickle.loads(decompressed_data)
        logger.debug("Data deserialized successfully")
        return original_data
    except (gzip.BadGzipFile, pickle.UnpicklingError, Exception) as e:
        logger.error(f"Error deserializing data: {e}")
        raise Exception(f"Data deserialization failed: {e}")

