#!/usr/bin/env python3
"""
Minimal FastAPI test to isolate request handling issues
"""

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "message": "Minimal FastAPI working"}

@app.get("/test")
def test_endpoint():
    return {"status": "ok", "message": "Test endpoint working"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, http="h11")
