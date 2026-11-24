
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime, timezone

from app.database import (
    clients_collection,
    history_collection,
    check_connections
)

from app.limiter import (
    check_rate_limit,
    get_rate_limit_status
)

app = FastAPI(title="Rate Limiter")


# Client registration model
class ClientCreate(BaseModel):
    client_id: str
    name: str


# Home endpoint
@app.get("/")
def home():
    return {
        "message": "Rate Limiter API is running"
    }


# Health check endpoint
@app.get("/health")
def health():

    try:
        check_connections()

        return {
            "status": "healthy",
            "mongodb": "connected",
            "redis": "connected"
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )


# Register a new client
@app.post("/clients")
def register_client(client: ClientCreate):

    existing = clients_collection.find_one({
        "client_id": client.client_id
    })

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Client already exists"
        )

    clients_collection.insert_one({
        "client_id": client.client_id,
        "name": client.name,
        "created_at": datetime.now(timezone.utc)
    })

    return {
        "message": "Client registered successfully",
        "client_id": client.client_id
    }


# Test rate limiter
@app.get("/api/test")
def test_rate_limiter(
    x_client_id: str = Header(...)
):

    client = clients_collection.find_one({
        "client_id": x_client_id
    })

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not registered"
        )

    result = check_rate_limit(x_client_id)

    # Save request history
    history_collection.insert_one({
        "client_id": x_client_id,
        "timestamp": datetime.now(timezone.utc),
        "allowed": result["allowed"],
        "status_code": (
            200 if result["allowed"] else 429
        )
    })

    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={
                "Retry-After": str(
                    result["retry_after"]
                )
            }
        )

    return {
        "message": "Request allowed",
        "client_id": x_client_id,
        "request_count": result["request_count"],
        "remaining_requests": result["remaining_requests"],
        "reset_in": result["retry_after"]
    }


# Check current quota
@app.get("/api/status/{client_id}")
def rate_limit_status(client_id: str):

    client = clients_collection.find_one({
        "client_id": client_id
    })

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not registered"
        )

    return get_rate_limit_status(client_id)


# View request history
@app.get("/api/history/{client_id}")
def request_history(client_id: str):

    client = clients_collection.find_one({
        "client_id": client_id
    })

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not registered"
        )

    records = list(
        history_collection.find(
            {"client_id": client_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(20)
    )

    return {
        "client_id": client_id,
        "total_records": len(records),
        "history": records
    }
