#!/usr/bin/env python3
"""
GoHighLevel Webhook Handler Script

This script receives webhook data from GoHighLevel and forwards it to the 
LangGraph supervisor agent through the threads API.

Usage:
    python ghl_webhook_handler.py

This will start a simple webhook server on port 8080 that GoHighLevel can send data to.
"""

from flask import Flask, request, jsonify
import requests
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
DEPLOYMENT_URL = "https://meta-ryan-e63beed228015a5fbcf0b5408aa860fa.us.langgraph.app"
API_KEY = "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"

def format_phone_number(phone):
    """Format phone number to include country code"""
    if not phone:
        return None
    
    # Remove all non-numeric characters
    phone = ''.join(c for c in phone if c.isdigit())
    
    # Add US country code if not present
    if not phone.startswith('1') and len(phone) == 10:
        phone = '1' + phone
    
    # Add + prefix
    if not phone.startswith('+'):
        phone = '+' + phone
    
    return phone


@app.route('/ghl-webhook', methods=['POST'])
def handle_ghl_webhook():
    """
    Handle incoming webhooks from GoHighLevel
    Expected format:
    {
        "id": "{{contact.id}}",
        "name": "{{contact.name}}",
        "email": "{{contact.email}}",
        "phone": "{{contact.phone}}",
        "message": "{{message.body}}"
    }
    """
    try:
        # Get webhook data
        webhook_data = request.get_json()
        logger.info(f"Received GHL webhook: {webhook_data}")
        
        # Extract and validate required fields
        contact_id = webhook_data.get('id')
        phone = webhook_data.get('phone')
        message = webhook_data.get('message')
        
        if not contact_id or not phone or not message:
            logger.error("Missing required fields in webhook data")
            return jsonify({
                "success": False,
                "error": "Missing required fields: id, phone, and message are required"
            }), 400
        
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Use deployment URL
        base_url = DEPLOYMENT_URL
        
        # Create thread metadata
        thread_metadata = {
            "phone_number": formatted_phone,
            "contact_id": contact_id,
            "contact_name": webhook_data.get('name'),
            "contact_email": webhook_data.get('email'),
            "source": "ghl_webhook"
        }
        
        # Headers with API key
        headers = {
            "Content-Type": "application/json",
            "x-api-key": API_KEY
        }
        
        # Step 1: Search for existing thread
        logger.info(f"Searching for existing thread for contact {contact_id}")
        search_response = requests.post(
            f"{base_url}/threads/search",
            json={
                "metadata": {"contact_id": contact_id},
                "limit": 1
            },
            headers=headers,
            timeout=30
        )
        
        threads = search_response.json() if search_response.status_code == 200 else []
        
        # Step 2: Create or get thread
        if not threads:
            logger.info(f"Creating new thread for contact {contact_id}")
            create_response = requests.post(
                f"{base_url}/threads",
                json={"metadata": thread_metadata},
                headers=headers,
                timeout=30
            )
            
            if create_response.status_code != 200:
                logger.error(f"Failed to create thread: {create_response.text}")
                return jsonify({
                    "success": False,
                    "error": "Failed to create thread"
                }), 500
            
            thread = create_response.json()
            thread_id = thread["thread_id"]
        else:
            thread_id = threads[0]["thread_id"]
            logger.info(f"Using existing thread {thread_id}")
        
        # Step 3: Send message to supervisor
        logger.info(f"Sending message to supervisor on thread {thread_id}")
        
        run_response = requests.post(
            f"{base_url}/threads/{thread_id}/runs/wait",
            json={
                "assistant_id": "supervisor",
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": message
                        }
                    ],
                    "phone_number": formatted_phone,
                    "contact_id": contact_id
                },
                "metadata": thread_metadata,
                "config": {
                    "configurable": thread_metadata
                }
            },
            headers=headers,
            timeout=60
        )
        
        if run_response.status_code != 200:
            logger.error(f"Failed to run supervisor: {run_response.text}")
            return jsonify({
                "success": False,
                "error": "Failed to process message"
            }), 500
        
        # Step 4: Extract response
        result = run_response.json()
        
        # Get the final response
        final_response = None
        if "final_response" in result:
            final_response = result["final_response"]
        elif "messages" in result and len(result["messages"]) > 0:
            # Get the last AI message
            for msg in reversed(result["messages"]):
                if msg.get("type") == "ai":
                    final_response = msg.get("content", "Message processed successfully.")
                    break
        
        if not final_response:
            final_response = "Message received and processed."
        
        # Step 5: Return response
        response_data = {
            "success": True,
            "thread_id": thread_id,
            "message": final_response,
            "contact_id": contact_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Successfully processed webhook for contact {contact_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "ghl-webhook-handler",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with information"""
    return jsonify({
        "service": "GoHighLevel Webhook Handler",
        "version": "1.0.0",
        "endpoints": {
            "/ghl-webhook": "POST - Handle GoHighLevel webhooks",
            "/health": "GET - Health check",
            "/": "GET - Service information"
        },
        "langgraph_url": LANGGRAPH_URL,
        "deployment_url": DEPLOYMENT_URL,
        "use_deployment": os.getenv("USE_DEPLOYMENT", "false")
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('WEBHOOK_PORT', 8080))
    logger.info(f"Starting GHL Webhook Handler on port {port}")
    logger.info(f"Webhook endpoint: http://localhost:{port}/ghl-webhook")
    logger.info(f"Deployment URL: {DEPLOYMENT_URL}")
    app.run(host='0.0.0.0', port=port, debug=False)