"""
Custom API routes for GoHighLevel webhook integration.

This module handles incoming webhooks from GoHighLevel and converts them
to the LangGraph threads API format.
"""

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging
import httpx
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for custom routes
app = FastAPI(title="Meta Ryan GHL Webhook Handler")

# Pydantic model for GHL webhook data
class GHLWebhookData(BaseModel):
    id: str  # contact.id
    name: Optional[str] = None  # contact.name
    email: Optional[str] = None  # contact.email
    phone: str  # contact.phone
    message: str  # message.body


@app.post("/ghl-webhook")
async def handle_ghl_webhook(
    webhook_data: GHLWebhookData, 
    request: Request,
    x_webhook_secret: Optional[str] = Header(None)
):
    """
    Handle incoming webhooks from GoHighLevel.
    
    This endpoint:
    1. Receives webhook data from GHL
    2. Creates or retrieves a thread for the contact
    3. Sends the message to the supervisor graph
    4. Returns the response to GHL
    """
    try:
        # Optional: Check webhook secret if configured
        expected_secret = os.getenv("GHL_WEBHOOK_SECRET")
        if expected_secret and x_webhook_secret != expected_secret:
            logger.warning(f"Invalid webhook secret from {request.client.host}")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        
        logger.info(f"Received GHL webhook: contact_id={webhook_data.id}, phone={webhook_data.phone}")
        logger.info(f"Message: {webhook_data.message}")
        
        # Get the base URL from request headers or environment
        host = request.headers.get("host", "localhost:2024")
        protocol = "https" if "langgraph.app" in host else "http"
        base_url = f"{protocol}://{host}"
        
        # Format phone number (ensure it has country code)
        phone = webhook_data.phone
        if not phone.startswith("+"):
            # Assume US number if no country code
            phone = f"+1{phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')}"
        
        # Create thread metadata
        thread_metadata = {
            "phone_number": phone,
            "contact_id": webhook_data.id,
            "contact_name": webhook_data.name,
            "contact_email": webhook_data.email,
            "source": "ghl_webhook"
        }
        
        async with httpx.AsyncClient() as client:
            # Step 1: Search for existing thread with this contact_id
            search_response = await client.post(
                f"{base_url}/threads/search",
                json={
                    "metadata": {"contact_id": webhook_data.id},
                    "limit": 1
                },
                timeout=30.0
            )
            
            threads = search_response.json() if search_response.status_code == 200 else []
            
            # Step 2: Create thread if it doesn't exist
            if not threads:
                logger.info(f"Creating new thread for contact {webhook_data.id}")
                create_response = await client.post(
                    f"{base_url}/threads",
                    json={"metadata": thread_metadata},
                    timeout=30.0
                )
                
                if create_response.status_code != 200:
                    logger.error(f"Failed to create thread: {create_response.text}")
                    raise HTTPException(status_code=500, detail="Failed to create thread")
                
                thread = create_response.json()
                thread_id = thread["thread_id"]
            else:
                thread_id = threads[0]["thread_id"]
                logger.info(f"Using existing thread {thread_id} for contact {webhook_data.id}")
            
            # Step 3: Send message to supervisor graph
            logger.info(f"Sending message to supervisor graph on thread {thread_id}")
            
            # Return immediately to GHL to prevent retries, process in background
            import asyncio
            
            async def process_in_background():
                try:
                    run_response = await client.post(
                        f"{base_url}/threads/{thread_id}/runs/wait",
                        json={
                            "assistant_id": "supervisor",
                            "input": {
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": webhook_data.message
                                    }
                                ],
                                "phone_number": phone,
                                "contact_id": webhook_data.id
                            },
                            "metadata": thread_metadata,
                            "config": {
                                "configurable": thread_metadata
                            }
                        },
                        timeout=60.0  # Give more time for processing
                    )
                    if run_response.status_code == 200:
                        logger.info(f"Successfully processed message for contact {webhook_data.id}")
                    else:
                        logger.error(f"Failed to process message: {run_response.text}")
                except Exception as e:
                    logger.error(f"Background processing error: {e}")
            
            # Start background processing
            asyncio.create_task(process_in_background())
            
            # Return immediately to prevent GHL retries
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Webhook received, processing message",
                    "contact_id": webhook_data.id,
                    "thread_id": thread_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                status_code=200
            )
            
    except httpx.TimeoutException:
        logger.error("Timeout while processing webhook")
        raise HTTPException(status_code=504, detail="Processing timeout")
    except Exception as e:
        logger.error(f"Error processing GHL webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint for the webhook handler."""
    return {"status": "healthy", "service": "ghl-webhook-handler"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Meta Ryan GHL Webhook Handler",
        "version": "1.0.0",
        "endpoints": {
            "/ghl-webhook": "POST - Handle GoHighLevel webhooks",
            "/health": "GET - Health check",
            "/": "GET - API information"
        }
    }