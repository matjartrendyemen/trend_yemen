# AI_HANDOFF

هذا الملف هو **أسرع handoff هندسي** لأي AI أو مطور جديد.

الغرض منه:
- فهم النظام الحالي خلال دقائق
- معرفة نقطة الدخول الحقيقية
- معرفة ما هو stable وما هو legacy
- معرفة ما الذي لا يجب كسره

---

## How to Understand This Repo in 5 Minutes

### اقرأ هذه الملفات أولًا
1. `README.md`
   - الصورة العامة للريبو والحالة الحالية
2. `AI_HANDOFF.md`
   - quick engineering handoff
3. `PROJECT_CONTEXT.md`
   - current baseline + system scope
4. `ENVIRONMENT_MAP.md`
   - environment and credential split
5. `main.py`
   - entrypoint الحقيقي وFlask routes الحية

### Real entrypoint
- `main.py`

### Primary execution path
- `main.py`
- `core/orchestrator.py`
- `storage/sheets_store.py`
- `services/admin_read_service.py`
- `services/media_matching_service.py`
- `services/manual_asset_service.py`
- `services/drive_asset_service.py`
- `services/content_output_service.py`
- `services/seo_service.py`

---

## Current Stable Baseline

الـ baseline الحالية مستقرة وتشمل:
- Admin Control Center
- product creation flow
- Product Workspace
- media matching
- manual asset upload
- manual asset normalization
- select final media from workspace
- Product Ownership Foundation
- Drive OAuth uploader
- Commit Final Asset
- Drive folder by ProductCode
- stable preview ownership projection
- content generation baseline
- cleanup audit baseline

### Completed milestones already in repo
- Admin Workspace
- `product_workspace_assets`
- Manual Asset Upload
- Manual Asset Normalization
- Select from Workspace
- Ownership fields
- Drive OAuth uploader
- Commit Final Asset
- Drive folder by ProductCode
- cleanup audit
- deletion of `adapters/cj_adapter.py`

---

## Source of Truth Definition

### Final truth for structured product data
- Google Sheets (`Products`)

### Final truth for owned assets
- Google Drive
- final owned files live inside:
  - `TrendYemenProductsDrive/<ProductCode>/`

### Read authority
- `services/admin_read_service.py`

### Write authority
- `storage/sheets_store.py`
- `services/drive_asset_service.py`

### Important distinction
- Service Account remains the trusted path for Google Sheets and related sheet operations
- OAuth Gmail user credentials are used for owned asset upload to Drive

---

## System Architecture

### Core runtime
- `main.py`
  - Flask app
  - Admin routes
  - create / retry / stuck resolution / media / content actions

- `core/orchestrator.py`
  - scans pending rows
  - runs enrichment flow

- `storage/sheets_store.py`
  - canonical write/read contract for sheet columns

### Admin read model
- `services/admin_read_service.py`
  - admin record
  - readiness
  - failure visibility
  - Product Workspace projection
  - ownership projection
  - stable preview projection

### Media layer
- `services/media_matching_service.py`
- `services/manual_asset_service.py`
- `services/drive_asset_service.py`
- `services/cj_supplier_service.py`
- `adapters/pexels_adapter.py`

### Content layer
- `services/content_output_service.py`
- `services/seo_service.py`

---

## Current Execution Paths

### Product creation flow
1. `/admin/create_product`
2. save seed image locally
3. append pending row to Sheets
4. assign `ProductCode`
5. orchestrator later enriches the row

### Product Workspace flow
1. `/admin/product` or `/admin/ui`
2. `AdminReadService` builds workspace view
3. sources can include:
   - original
   - CJ
   - Pexels fallback
   - manual uploads
4. final asset can be selected from workspace

### Ownership flow
1. final media is selected
2. `/admin/commit_final_asset`
3. `DriveAssetService` uploads into Drive via OAuth
4. owned asset entry is written back to Sheets
5. stable preview switches to owned asset when available

### Content flow
1. `/admin/generate_content`
2. `ContentOutputService`
3. `SEOService`
4. write publish-ready fields to Sheets

---

## Admin Control Center

### Current active routes
- `/health`
- `/stats`
- `/retry_failed`
- `/retry_row`
- `/delete_row`
- `/list_products`
- `/admin/overview`
- `/admin/product`
- `/admin/match_media`
- `/admin/select_final_media`
- `/admin/commit_final_asset`
- `/admin/generate_content`
- `/admin/create_product`
- `/admin/upload_manual_assets`
- `/admin/ui`

### Do not break
- create flow
- retry/stuck flow
- Product Workspace rendering
- ownership commit path
- content generation path

---

## System Boundaries

### Inside the current system
- Flask backend
- Admin Control Center
- Google Sheets storage path
- Product Workspace
- manual assets
- ownership layer
- content generation baseline

### Outside the current system
- `trend-yemen-store/` frontend subtree
- full legacy deletion pass
- advanced gallery management
- product pages
- publishing automation
- supplier expansion beyond baseline
- pricing sync
- ordering sync
- analytics
- general refactor

### What must not be touched now
- large refactor of `main.py`
- ownership field names
- current Sheets contracts
- current Drive OAuth path
- current AdminReadService output shape without explicit phase decision

---

## Legacy / unclear areas
راجع دائمًا:
- `SYSTEM_CLEANUP_AUDIT.md`

### Current meaning
- legacy files are not auto-deleted
- unclear files are not touched without explicit decision
- `trend-yemen-store/` is a separate decision track

---

## Deferred Work (intentionally postponed)
- full legacy deletion
- frontend store decision
- advanced gallery management
- product pages
- publishing automation
- supplier expansion
- pricing/order sync
- analytics
- general refactor

### Why deferred
- للحفاظ على baseline الحالية
- لتقليل blast radius
- لمنع كسر النظام أثناء تثبيت architecture الحالية

---

## Decision Log

### Why OAuth instead of Service Account for Drive owned assets?
- لأن owned asset uploads المطلوبة كانت داخل مجلد Gmail/My Drive عملي
- Service Account لا تناسب هذا المسار كما نُفّذ حاليًا
- لذلك تم اعتماد OAuth user credentials لمسار owned asset upload فقط

### Why is ProductCode the identity?
- لأن المنتج قد ينتقل بين أقسام أو تتغير metadata
- نحتاج هوية ثابتة لا تتغير بتغير القسم
- لذلك `ProductCode` هي anchor الأساسية للمنتج

### Why Category is not part of identity?
- لأن القسم metadata قابلة للتغيير لاحقًا
- ربط الهوية بالقسم يسبب كسرًا عند النقل أو إعادة التصنيف

### Why are assets tied to product, not category?
- لأن الصور/الفيديو والمحتوى يجب أن تبقى مع المنتج حتى لو تغيّر القسم
- وهذا يدعم product pages وfuture publishing لاحقًا

### Why no refactor now?
- لأن الهدف الحالي هو الوضوح والاستقرار
- وليس إعادة بناء النظام
- أي refactor يجب أن تأتي ضمن phase مستقلة لها blast-radius control واضح

### Why no blind deletion?
- لأن cleanup بدون audit قد تكسر مسارات قديمة لا تزال مرتبطة بتشغيل أو tooling
- لذلك تم اعتماد قاعدة: no deletion without audit

---

## Safety Rules
- لا تكسر flows الحية
- لا refactor عام
- لا full overwrite للملفات الحساسة إلا عند الضرورة القصوى
- `main.py` تُعدّل فقط بـ patch صغيرة ومحسوبة
- لا حذف ملفات بدون audit
- لا تغيير runtime behavior في phases التوثيق والتنظيم

---

## Branch State (current snapshot)
- `main`
  - runtime stable branch
- `foundation/system-cleanup`
  - documentation and cleanup-analysis branch
- `temp/repo-files-export`
  - temporary audit helper branch

### Keep
- `main`
- `foundation/system-cleanup` حتى يتم اعتماد ودمج التوثيق

### Delete later
- `temp/repo-files-export` بعد انتهاء الحاجة إليه

### Recommended next clean branch
- `planning/next-phase-ready`
  - branch نظيف للمرحلة القادمة بعد تثبيت التوثيق

---

## What not to touch
- current Admin baseline
- current Product Workspace contract
- current ownership field names
- current Drive OAuth uploader logic
- current Sheets storage contract
- current content generation flow

إذا احتجت قرارًا عن أي ملف أو feature غير واضحة:
- ارجع أولًا إلى `README.md`
- ثم `PROJECT_CONTEXT.md`
- ثم `ENVIRONMENT_MAP.md`
- ثم `SYSTEM_CLEANUP_AUDIT.md`
