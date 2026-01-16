# Caching Proxy Server

A high-performance caching proxy server built with FastAPI and Redis, designed to cache HTTP responses from upstream servers to improve response times and reduce load on backend services.

## Overview

This project implements a caching proxy server that sits between clients and upstream APIs. It caches successful HTTP responses in Redis, serving cached content for subsequent identical requests. The server is built using FastAPI for high performance and includes comprehensive error handling, logging, and asynchronous caching operations.

## Features

- **High-Performance Caching**: Redis-backed caching with configurable expiry times
- **Asynchronous Operations**: Non-blocking cache storage using ThreadPoolExecutor
- **Comprehensive Error Handling**: Robust error handling for network issues, Redis failures, and upstream server problems
- **Detailed Logging**: Structured logging with both console and file output
- **Environment-Based Configuration**: Secure configuration management using environment variables
- **Cache Management**: Built-in endpoint for cache clearing operations
- **Data Compression**: Efficient storage using gzip compression and pickle serialization
- **Health Monitoring**: Cache hit/miss indicators via response headers

## Architecture

```
Client Request → FastAPI Server → Check Redis Cache
    ↓ (Cache Miss)         ↓ (Cache Hit)
Upstream Server ← Fetch Data ← Return Cached Data
    ↓                        ↓
Cache Response → Store in Redis → Return Response
```

## Prerequisites

- Python 3.13+
- Redis Server
- pip (Python package manager)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Caching-Proxy-Server
   ```



2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # or using uv
   uv sync
   ```

3. **Windows Setting for service redis-server  setup**
    ```
    if you are on windows 
    install Wsl (window sub-system for linux)
    open wsl 
    run commands:
      sudo apt update (this will download the list of available software or versiona from the internet )
      sudo apt install redis-server   

    for starting the redis-server
       sudo service redis-server start
    for checking the status 
       redis-cli ping (if redis-server is running then it will prints PONG)
         or 
       for more detailed status:
       sudo service redis-server status

    To stop the redis-server :         
       sudo service redis-server stop
    ```
         


4. **Start Redis server:**
   ```bash
   sudo service redis-server start
   ```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
# Upstream server URL to proxy requests to
PROXY_URL=https://dummyjson.com

# Cache expiry time in seconds
DATA_EXPIRY=3600

# Redis server configuration
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Environment Variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `PROXY_URL` | string | Yes | Base URL of the upstream server to proxy requests to |
| `DATA_EXPIRY` | integer | Yes | Cache expiry time in seconds |
| `REDIS_HOST` | string | Yes | Redis server hostname |
| `REDIS_PORT` | integer | Yes | Redis server port |

## Usage

1. **Start the server:**
   ```bash
    uv run fastapi dev api.py
   ```

2. **Make requests through the proxy:**
   ```bash
   # Example request to upstream API through proxy
   curl http://localhost:8000/products/1

   # Check cache status in response headers
   curl -I http://localhost:8000/products/1
   ```

## API Endpoints

### Proxy Endpoint

**GET `/{path:path}`**

Proxies requests to the upstream server with caching.

- **Parameters:**
  - `path` (string): The path to proxy to the upstream server

- **Response Headers:**
  - `X-CACHE`: Indicates cache status (`HIT` or `MISS`)

- **Example:**
  ```bash
  GET /products/1
  # Proxies to: https://dummyjson.com/products/1
  ```

### Cache Management

**POST `/clear/incache`**

Clears all cached data from Redis.

- **Response:**
  ```json
  {
    "status": "Cache cleared successfully",
    "message": "All cached data has been removed"
  }
  ```

## Cache Behavior

- **Cache Key**: Generated as `cache:{request_path}`
- **Cache Storage**: Only successful responses (HTTP 200) are cached
- **Cache Expiry**: Configurable via `DATA_EXPIRY` environment variable
- **Cache Headers**: Response includes `X-CACHE` header indicating hit/miss status
- **Asynchronous Caching**: Cache storage happens in background threads to avoid blocking responses

## Logging

The application provides comprehensive logging:

- **Log Levels**: INFO, DEBUG, WARNING, ERROR
- **Output Destinations**: Console and `proxy_server.log` file
- **Log Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Sample Log Output

```
2024-01-16 10:24:03,840 - Caching-Proxy-Server.api - INFO - Environment variables validated successfully
2024-01-16 10:24:03,840 - Caching-Proxy-Server.api - INFO - Configuration loaded: Proxy URL=https://dummyjson.com, Redis=localhost:6379, Cache expiry=3600s
2024-01-16 10:24:04,614 - Caching-Proxy-Server.api - INFO - Fetching from upstream: https://dummyjson.com/products/1
```

## Error Handling

The server handles various error scenarios:

- **Redis Connection Failures**: Returns HTTP 503 with appropriate error message
- **Upstream Server Errors**: Returns HTTP 502 for upstream failures
- **Invalid Configuration**: Application exits with error during startup
- **Network Timeouts**: Configurable timeouts for upstream requests

## Development

### Project Structure

```
Caching-Proxy-Server/
├── api.py              # Main FastAPI application
├── utility.py          # Helper functions for upstream fetching and data serialization
├── __init__.py         # Package initialization
├── .env                # Environment configuration
├── pyproject.toml      # Project dependencies and configuration
├── uv.lock            # Dependency lock file
├── proxy_server.log   # Application logs
└── README.md          # This file
```

### Key Components

- **`api.py`**: Contains the FastAPI application, route handlers, Redis connection management, and caching logic
- **`utility.py`**: Provides utility functions for upstream server communication and data serialization/deserialization

`

## Performance Considerations

- **Connection Pooling**: Redis connections are pooled for efficiency
- **Asynchronous Caching**: Cache operations don't block request processing
- **Data Compression**: Cached data is compressed to reduce memory usage
- **Timeout Configuration**: Appropriate timeouts prevent hanging requests

## Monitoring

Monitor the application through:

- **Response Headers**: Check `X-CACHE` header for cache performance
- **Logs**: Review `proxy_server.log` for detailed operation information
- **Redis**: Monitor Redis memory usage and connection statistics

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Ensure Redis server is running
   - Check `REDIS_HOST` and `REDIS_PORT` configuration

2. **Upstream Server Errors**
   - Verify `PROXY_URL` is accessible
   - Check network connectivity

3. **Cache Not Working**
   - Verify Redis is responding to ping
   - Check cache expiry settings

