# Trend Yemen – AI Handoff (Live State)

## Current Reality (DO NOT BREAK)
- Backend pipeline working:
  Google Sheets → Pending → AI → Completed
- Running on Railway (Flask app + background orchestrator)
- Google Drive used for images
- AI: Gemini (google-genai)

## Admin System (ACTIVE)
Endpoints:
- /admin/overview
- /admin/product?row_id=
- /admin/ui

Admin UI:
- Shows products
- Shows readiness + missing fields
- Shows errors
- Retry/Delete working

## Smart Encoding (CORE IDEA)
Product identity is NOT just SKU.

Each product identity depends on:
- RowID
- SKU
- CategoryID
- Image (Drive)
- ProcessingStatus
- QualityStatus

Derived:
- readiness
- missing_fields
- anchors (category/image/sku/status)

## What is WORKING
- Sheets reading/writing
- AI processing
- Status transitions
- Admin overview API
- Admin UI basic

## What is NOT CONNECTED YET
- CJ integration
- Pexels/Pixabay
- SEO service
- Storefront (Astro broken)
- Upload system (manual product creation)

## Admin Vision (IMPORTANT)
Admin is NOT dashboard only.

It should:
1. Create product (upload image + price)
2. Trigger AI + enrichment
3. Store in Drive
4. Save structured data in Sheets
5. Allow edit/delete
6. Show readiness/errors

## Next Priority
1. Stabilize Admin as CONTROL CENTER
2. Improve image handling (Drive links)
3. Add product creation (upload)
4. Then connect CJ/Pexels
5. THEN storefront

## Critical Rule
DO NOT:
- Break pipeline
- Change Sheets schema randomly
- Refactor blindly

## Deployment Notes
- Railway currently used
- Env variables required:
  GOOGLE_CREDENTIALS
  SPREADSHEET_ID
  GEMINI_API_KEY

## Goal
Fully automated dropshipping system
(Admin → AI → Sources → Storefront)
