# Amazon Signal Sources

## Source Priority

1. Movers & Shakers
   - Best for detecting fast-rising products.
   - Capture rank, category, ASIN, product name, URL, image, and any visible movement text.
2. Best Sellers
   - Best for proving stable demand.
   - Capture rank and category carefully; category context matters more than absolute rank.
3. New Releases
   - Best for early product direction discovery.
   - Use as a watchlist source, not proof of demand.
4. Homepage modules
   - Best for seasonal/event themes and Amazon merchandising priorities.
   - Do not treat homepage appearance as sales validation by itself.

## Minimal Fields

Use this lean schema for Amazon-to-funnel handoff:

```json
{
  "source": "amazon",
  "signal_type": "best_seller | mover | new_release | homepage_module",
  "source_url": "https://www.amazon.com/...",
  "category": "Category or module name",
  "rank": 1,
  "asin": "ASIN or null",
  "product_name": "Visible Amazon title",
  "brand": "Brand if visible or inferred from title",
  "product_url": "Canonical Amazon URL",
  "image_url": "Primary image URL",
  "captured_at": "ISO-8601",
  "generalized_concept": "Brand-free concept",
  "brand_locked": true,
  "risk_notes": ["IP/brand/platform/logistics/compliance notes"],
  "suitable_for_cross_platform_validation": true
}
```

## Generalization Examples

- Amazon Echo Spot -> smart bedside alarm clock with speaker and display.
- Fire TV Stick -> streaming device accessories, remote covers, HDMI cable/holder, TV setup accessories.
- Ring Chime -> smart doorbell chime/accessory.
- Blink Outdoor 4 -> wireless outdoor security camera category; watch privacy/security compliance.
- WYZE Bulb Cam -> light-bulb security camera concept.
- JBL Go 4 -> waterproof ultra-portable Bluetooth speaker.
- Owala FreeSip -> insulated straw water bottle with one-hand lid.
- Under Armour golf polo -> moisture-wicking golf polo, not the brand itself.

## Risk Filters

Reject or downgrade:

- Amazon, Apple, JBL, Ring, Blink, Under Armour, Nike, Adidas, Disney, FIFA, or other strong brand/IP-locked goods when evaluating direct resale/private label.
- Gift cards, pharmacy, streaming services, media subscriptions, and non-physical services.
- Products requiring medical claims, safety certification, wireless compliance, surveillance/privacy handling, batteries, liquids, oversized shipping, or platform-restricted ad claims.

## Anti-Blocking Guardrails

- Prefer saved HTML and list pages over repeated detail-page visits.
- Do not parallelize Amazon page loads.
- Do not open every product detail page from a list.
- For one research pass, keep detail-page visits to 5-10 items.
- Stop immediately on CAPTCHA, abnormal traffic, repeated challenge pages, or login verification loops.
- Record `risk_signal_seen` rather than trying to bypass a block.

## Cross-Platform Handoff

After Amazon extraction, validate each generalized concept with:

- TikTok/short video: recent videos, growth, engagement, demonstrability.
- Facebook Ads Library: active advertisers, creative angles, duration of ads.
- YouTube: reviews, `Amazon must haves`, `TikTok made me buy it`, product roundups.
- Google Trends: keyword direction and seasonality.
- AliExpress/1688/CJ/Doba: supplier count, price band, shipping constraints, differentiation potential.
