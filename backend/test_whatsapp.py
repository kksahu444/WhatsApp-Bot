"""
Test WhatsApp Integration Locally.

Simulates Meta webhook payloads to test the full flow without WhatsApp.

Usage:
    python -m backend.test_whatsapp
"""

import asyncio
import httpx
from loguru import logger


# Test payloads simulating Meta webhooks
TEST_PAYLOADS = {
    "text_message": {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15551234567",
                        "phone_number_id": "123456789"
                    },
                    "contacts": [{
                        "profile": {"name": "Test User"},
                        "wa_id": "919999999999"
                    }],
                    "messages": [{
                        "from": "919999999999",
                        "id": "wamid.test_message_001",
                        "type": "text",
                        "text": {"body": "show me laptops"},
                        "timestamp": "1701878400"
                    }]
                },
                "field": "messages"
            }]
        }]
    },
    
    "greeting": {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": "919999999999",
                        "id": "wamid.test_greeting_001",
                        "type": "text",
                        "text": {"body": "hi"},
                        "timestamp": "1701878401"
                    }]
                },
                "field": "messages"
            }]
        }]
    },
    
    "add_to_cart": {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": "919999999999",
                        "id": "wamid.test_cart_001",
                        "type": "text",
                        "text": {"body": "add iPhone 15 Pro to cart"},
                        "timestamp": "1701878402"
                    }]
                },
                "field": "messages"
            }]
        }]
    },
    
    "view_cart": {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": "919999999999",
                        "id": "wamid.test_view_cart_001",
                        "type": "text",
                        "text": {"body": "show my cart"},
                        "timestamp": "1701878403"
                    }]
                },
                "field": "messages"
            }]
        }]
    },
    
    "status_update": {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15551234567",
                        "phone_number_id": "123456789"
                    },
                    "statuses": [{
                        "id": "wamid.sent_message_001",
                        "status": "delivered",
                        "timestamp": "1701878410",
                        "recipient_id": "919999999999"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
}


async def test_webhook_verification():
    """Test webhook verification endpoint."""
    print("\n" + "=" * 60)
    print("🧪 Test 1: Webhook Verification")
    print("=" * 60)
    
    verify_token = "your_secret_verify_token_123"
    challenge = "challenge_string_12345"
    
    url = f"http://localhost:8000/whatsapp/webhook?hub.mode=subscribe&hub.verify_token={verify_token}&hub.challenge={challenge}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200 and response.text == challenge:
            print("   ✅ Verification passed!")
        else:
            print("   ❌ Verification failed!")


async def test_message_webhook(name: str, payload: dict):
    """Test message webhook."""
    print(f"\n📝 Testing: {name}")
    print("-" * 40)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/whatsapp/webhook",
            json=payload,
            timeout=15.0
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        if response.status_code == 200:
            print("   ✅ Webhook accepted!")
            # Wait a bit for background processing
            await asyncio.sleep(2)
        else:
            print("   ❌ Webhook failed!")


async def test_health_check():
    """Test health check endpoint."""
    print("\n" + "=" * 60)
    print("🧪 Test: Health Check")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/whatsapp/health",
            timeout=10.0
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")


async def main():
    """Run all WhatsApp integration tests."""
    print("=" * 60)
    print("🚀 WhatsApp Integration Tests")
    print("=" * 60)
    print("\n⚠️  Make sure the server is running:")
    print("    uvicorn backend.main:app --reload")
    print()
    
    try:
        # Test 1: Health check
        await test_health_check()
        
        # Test 2: Webhook verification
        await test_webhook_verification()
        
        # Test 3: Message webhooks
        print("\n" + "=" * 60)
        print("🧪 Testing Message Webhooks")
        print("=" * 60)
        
        for name, payload in TEST_PAYLOADS.items():
            await test_message_webhook(name, payload)
            await asyncio.sleep(1)  # Small delay between tests
        
        print("\n" + "=" * 60)
        print("✅ All WhatsApp tests completed!")
        print("=" * 60)
        print("\n💡 Note: Check server logs for background processing output")
        print("   Message responses are sent via WhatsApp API (not visible here)")
        
    except httpx.ConnectError:
        print("\n❌ Connection failed!")
        print("   Make sure the server is running:")
        print("   uvicorn backend.main:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
