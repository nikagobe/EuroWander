"""
AWS Lambda entry point for EuroWander API.

Mangum translates API Gateway/ALB events into ASGI requests
that FastAPI can process, then converts the response back
to a Lambda-compatible format.
"""

from mangum import Mangum

from app.main import app

# The handler AWS Lambda will invoke.
# Supports: API Gateway REST (v1), HTTP API (v2), and ALB.
handler = Mangum(app, lifespan="auto")

