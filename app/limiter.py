
from app.database import redis_client

# Maximum requests allowed
REQUEST_LIMIT = 5

# Time window in seconds
WINDOW_SECONDS = 60


# Generate Redis key
def get_key(client_id):
    return f"rate_limit:{client_id}"


# Redis script for atomic counting
RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])

if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

local ttl = redis.call('TTL', KEYS[1])

return {count, ttl}
"""


# Check whether request is allowed
def check_rate_limit(client_id):

    key = get_key(client_id)

    result = redis_client.eval(
        RATE_LIMIT_SCRIPT,
        1,
        key,
        WINDOW_SECONDS
    )

    count = int(result[0])
    remaining_time = int(result[1])

    allowed = count <= REQUEST_LIMIT

    return {
        "allowed": allowed,
        "request_count": count,
        "remaining_requests": max(
            0, REQUEST_LIMIT - count
        ),
        "retry_after": max(0, remaining_time)
    }


# Get current status without increasing counter
def get_rate_limit_status(client_id):

    key = get_key(client_id)

    count = redis_client.get(key)
    ttl = redis_client.ttl(key)

    if count is None:
        count = 0
        ttl = 0

    count = int(count)

    return {
        "request_count": count,
        "remaining_requests": max(
            0, REQUEST_LIMIT - count
        ),
        "reset_in": max(0, int(ttl))
    }
