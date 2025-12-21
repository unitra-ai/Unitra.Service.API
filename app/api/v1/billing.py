"""Billing endpoints for subscription management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class SubscriptionResponse(BaseModel):
    """Subscription details response."""

    id: str
    plan: str
    status: str
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool


class CreateCheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    plan: str  # e.g., "basic_monthly", "pro_yearly"
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    """Checkout session response."""

    checkout_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    """Customer portal session response."""

    portal_url: str


class InvoiceResponse(BaseModel):
    """Invoice details."""

    id: str
    amount: int
    currency: str
    status: str
    created_at: str
    pdf_url: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription() -> SubscriptionResponse:
    """Get current user's subscription details.

    TODO: Implement subscription retrieval.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
) -> CheckoutSessionResponse:
    """Create a Stripe checkout session for subscription.

    TODO: Implement Stripe checkout session creation.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal_session() -> PortalSessionResponse:
    """Create a Stripe customer portal session.

    TODO: Implement Stripe customer portal session creation.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/cancel")
async def cancel_subscription() -> dict[str, str]:
    """Cancel current subscription at period end.

    TODO: Implement subscription cancellation.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/reactivate")
async def reactivate_subscription() -> dict[str, str]:
    """Reactivate a cancelled subscription before period end.

    TODO: Implement subscription reactivation.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices() -> list[InvoiceResponse]:
    """List user's invoices.

    TODO: Implement invoice listing.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/webhook")
async def stripe_webhook() -> dict[str, str]:
    """Handle Stripe webhook events.

    TODO: Implement Stripe webhook handling.
    """
    raise HTTPException(status_code=501, detail="Not implemented")
