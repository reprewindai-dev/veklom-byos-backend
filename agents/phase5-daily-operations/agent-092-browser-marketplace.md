# Agent-092 — BROWSER AGENT: Marketplace & Purchase (Hands)

**Phase:** Cross-phase — Browser Interaction
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Automate and test the marketplace browsing → listing detail → purchase → download flow using browser interaction. This agent has "hands" — it clicks through the entire purchase funnel.

## Automated Flows

1. **Browse & Search**:
   - Navigate to /marketplace
   - Test category filtering
   - Test search functionality
   - Verify listing cards render correctly
2. **Purchase Flow**:
   - Click listing → view detail page
   - Click "Purchase" → Stripe checkout
   - Complete Stripe test payment (card 4242...)
   - Verify redirect to confirmation
   - Download purchased file
3. **Vendor Dashboard**:
   - Navigate to vendor dashboard
   - Verify listing management UI
   - Create new listing via UI
   - Upload files via browser file picker
4. **Wallet Top-Up**:
   - Navigate to /billing
   - Click top-up pack
   - Complete Stripe checkout
   - Verify wallet balance update

## Playwright Script

```python
async def test_purchase_flow(page):
    await page.goto("https://veklom.com/marketplace")
    await page.click('.listing-card:first-child')
    await page.click('button:text("Purchase")')
    # Handle Stripe checkout iframe
    stripe_frame = page.frame_locator('iframe[name="stripe-checkout"]')
    await stripe_frame.locator('[name="cardNumber"]').fill('4242424242424242')
    # ...
```

## Success Metrics

| Metric | Target |
|---|---|
| Purchase flow automated | Yes |
| Vendor listing creation automated | Yes |
| Wallet top-up automated | Yes |
| Screenshot evidence | Every step |

## Dependencies

- Agent-090 (browser lead), Agent-001 (Stripe Connect)
