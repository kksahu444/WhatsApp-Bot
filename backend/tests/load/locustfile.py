"""
Locust Load Testing Configuration
"""

from locust import HttpUser, task, between


class WebhookUser(HttpUser):
    """Simulates WhatsApp webhook traffic."""
    
    wait_time = between(1, 3)
    
    @task(10)
    def product_search(self):
        """Simulate product search messages."""
        self.client.post(
            "/api/v1/webhook/whatsapp",
            json={
                "phone": "+6281234567890",
                "message": "cari sepatu nike",
                "message_id": f"msg-{self.environment.runner.user_count}",
            },
            headers={"X-API-Key": "test-key"}
        )
    
    @task(5)
    def view_cart(self):
        """Simulate viewing cart."""
        self.client.post(
            "/api/v1/webhook/whatsapp",
            json={
                "phone": "+6281234567890",
                "message": "lihat keranjang",
                "message_id": f"msg-cart-{self.environment.runner.user_count}",
            },
            headers={"X-API-Key": "test-key"}
        )
    
    @task(2)
    def checkout(self):
        """Simulate checkout."""
        self.client.post(
            "/api/v1/webhook/whatsapp",
            json={
                "phone": "+6281234567890",
                "message": "checkout",
                "message_id": f"msg-checkout-{self.environment.runner.user_count}",
            },
            headers={"X-API-Key": "test-key"}
        )
    
    @task(3)
    def health_check(self):
        """Check API health."""
        self.client.get("/health")


class AdminUser(HttpUser):
    """Simulates admin dashboard API traffic."""
    
    wait_time = between(2, 5)
    
    @task(5)
    def list_orders(self):
        """List orders."""
        self.client.get(
            "/api/v1/orders",
            headers={"X-API-Key": "test-key"}
        )
    
    @task(3)
    def list_products(self):
        """List products."""
        self.client.get(
            "/api/v1/products",
            headers={"X-API-Key": "test-key"}
        )
    
    @task(2)
    def get_analytics(self):
        """Get analytics."""
        self.client.get(
            "/api/v1/analytics/overview",
            headers={"X-API-Key": "test-key"}
        )
