"""Tests for billing endpoints."""

import pytest
from httpx import AsyncClient


class TestBillingEndpoints:
    """Tests for billing API endpoints."""

    @pytest.mark.asyncio
    async def test_get_subscription_returns_501(self, async_client: AsyncClient) -> None:
        """Test get subscription endpoint returns 501."""
        response = await async_client.get("/api/v1/billing/subscription")
        assert response.status_code == 501
        assert response.json()["detail"] == "Not implemented"

    @pytest.mark.asyncio
    async def test_create_checkout_session_returns_501(self, async_client: AsyncClient) -> None:
        """Test create checkout session returns 501."""
        response = await async_client.post(
            "/api/v1/billing/checkout",
            json={
                "plan": "basic_monthly",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
        )
        assert response.status_code == 501
        assert response.json()["detail"] == "Not implemented"

    @pytest.mark.asyncio
    async def test_create_portal_session_returns_501(self, async_client: AsyncClient) -> None:
        """Test create portal session returns 501."""
        response = await async_client.post("/api/v1/billing/portal")
        assert response.status_code == 501
        assert response.json()["detail"] == "Not implemented"

    @pytest.mark.asyncio
    async def test_cancel_subscription_returns_501(self, async_client: AsyncClient) -> None:
        """Test cancel subscription returns 501."""
        response = await async_client.post("/api/v1/billing/cancel")
        assert response.status_code == 501
        assert response.json()["detail"] == "Not implemented"

    @pytest.mark.asyncio
    async def test_reactivate_subscription_returns_501(self, async_client: AsyncClient) -> None:
        """Test reactivate subscription returns 501."""
        response = await async_client.post("/api/v1/billing/reactivate")
        assert response.status_code == 501
        assert response.json()["detail"] == "Not implemented"

    @pytest.mark.asyncio
    async def test_list_invoices_returns_501(self, async_client: AsyncClient) -> None:
        """Test list invoices returns 501."""
        response = await async_client.get("/api/v1/billing/invoices")
        assert response.status_code == 501
        assert response.json()["detail"] == "Not implemented"

    @pytest.mark.asyncio
    async def test_stripe_webhook_returns_501(self, async_client: AsyncClient) -> None:
        """Test stripe webhook returns 501."""
        response = await async_client.post("/api/v1/billing/webhook")
        assert response.status_code == 501
        assert response.json()["detail"] == "Not implemented"


class TestBillingModels:
    """Tests for billing Pydantic models."""

    def test_subscription_response_model(self) -> None:
        """Test SubscriptionResponse model."""
        from app.api.v1.billing import SubscriptionResponse

        sub = SubscriptionResponse(
            id="sub_123",
            plan="basic_monthly",
            status="active",
            current_period_start="2024-01-01T00:00:00Z",
            current_period_end="2024-02-01T00:00:00Z",
            cancel_at_period_end=False,
        )
        assert sub.id == "sub_123"
        assert sub.plan == "basic_monthly"
        assert sub.status == "active"
        assert sub.cancel_at_period_end is False

    def test_create_checkout_request_model(self) -> None:
        """Test CreateCheckoutRequest model."""
        from app.api.v1.billing import CreateCheckoutRequest

        request = CreateCheckoutRequest(
            plan="pro_yearly",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert request.plan == "pro_yearly"
        assert request.success_url == "https://example.com/success"

    def test_checkout_session_response_model(self) -> None:
        """Test CheckoutSessionResponse model."""
        from app.api.v1.billing import CheckoutSessionResponse

        response = CheckoutSessionResponse(
            checkout_url="https://checkout.stripe.com/c/pay/123",
            session_id="cs_test_123",
        )
        assert response.checkout_url == "https://checkout.stripe.com/c/pay/123"
        assert response.session_id == "cs_test_123"

    def test_portal_session_response_model(self) -> None:
        """Test PortalSessionResponse model."""
        from app.api.v1.billing import PortalSessionResponse

        response = PortalSessionResponse(portal_url="https://billing.stripe.com/p/session/123")
        assert response.portal_url == "https://billing.stripe.com/p/session/123"

    def test_invoice_response_model(self) -> None:
        """Test InvoiceResponse model."""
        from app.api.v1.billing import InvoiceResponse

        invoice = InvoiceResponse(
            id="in_123",
            amount=2999,
            currency="usd",
            status="paid",
            created_at="2024-01-15T00:00:00Z",
            pdf_url="https://invoice.stripe.com/pdf/123",
        )
        assert invoice.id == "in_123"
        assert invoice.amount == 2999
        assert invoice.currency == "usd"
        assert invoice.pdf_url == "https://invoice.stripe.com/pdf/123"

    def test_invoice_response_optional_pdf(self) -> None:
        """Test InvoiceResponse with optional pdf_url."""
        from app.api.v1.billing import InvoiceResponse

        invoice = InvoiceResponse(
            id="in_123",
            amount=2999,
            currency="usd",
            status="pending",
            created_at="2024-01-15T00:00:00Z",
        )
        assert invoice.pdf_url is None
