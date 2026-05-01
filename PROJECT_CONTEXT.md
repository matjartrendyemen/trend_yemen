# PROJECT_CONTEXT

هذا الملف هو مرجع سياقي سريع للحالة الحالية المعتمدة للمشروع.

## Source of Truth
- الفرع العامل للتنظيف والتنظيم: `foundation/system-cleanup`
- baseline المستقرة الحالية مبنية فوق `main`
- لا يتم اعتماد أي فرضية قديمة تخالف ما هو موجود فعليًا في الكود والتوثيق الحالية

---

## Current Product Model
النظام الحالي يدعم **Single Product Curated Workflow**:
1. رفع صورة + سعر
2. إنشاء row في Google Sheets
3. enrichment أساسي عبر orchestrator
4. إدارة media من Admin
5. manual assets + supplier assets + fallback assets
6. final selection
7. ownership commit إلى Google Drive
8. publish-ready content generation

---

## Current Stable Foundations

### Admin Control Center
- overview / product detail / admin ui
- retryable failure visibility
- stuck processing handling
- manual resolve actions

### Product Workspace
- `product_workspace_assets`
- original media
- CJ supplier candidates
- Pexels fallback
- manual uploaded assets
- final selection from workspace

### Ownership Layer
- `ProductCode`
- `OwnedAssetsJSON`
- `PrimaryImageAssetID`
- `PrimaryVideoAssetID`
- `GalleryAssetIDsJSON`
- stable preview from owned assets

### Content Layer
- `ContentOutputService`
- `SEOService`
- publish-ready commercial fields in Sheets

---

## What has already been completed
- Admin Workspace
- `product_workspace_assets`
- Manual Asset Upload
- Manual Asset Normalization
- Select from Workspace
- Product Ownership Foundation
- Drive OAuth uploader
- Commit Final Asset
- Drive folder by ProductCode
- cleanup audit baseline
- deletion of `adapters/cj_adapter.py`

---

## Current Execution Path

### Create + Process
- `main.py`
- `core/orchestrator.py`
- `services/ai_service.py`
- `storage/sheets_store.py`

### Admin Read + Control
- `services/admin_read_service.py`
- `main.py`

### Media + Ownership
- `services/media_matching_service.py`
- `services/manual_asset_service.py`
- `services/drive_asset_service.py`
- `services/cj_supplier_service.py`
- `adapters/pexels_adapter.py`

### Content
- `services/content_output_service.py`
- `services/seo_service.py`

---

## System Boundaries

### Inside current backend system
- Flask backend
- Admin Control Center
- Product Workspace
- Google Sheets storage path
- Drive owned asset commit path
- content generation baseline

### Outside current backend scope
- `trend-yemen-store/` frontend subtree
- full legacy deletion
- advanced gallery management
- product pages
- publishing automation
- supplier expansion beyond baseline
- pricing sync
- order sync
- analytics
- general refactor

---

## Contracts that should stay stable
- `SheetsStore` column contracts
- admin read model shape
- `FinalPrimaryMediaURL` selection flow
- ownership field names
- Drive commit route behavior
- manual asset intake contract

---

## Important Constraints
- لا refactor كبير
- لا حذف ملفات بدون audit
- لا تغيير architecture واسعة الآن
- لا كسر أي flow تعمل فعليًا
- `main.py` ملف حساس ويعدل فقط بـ patch صغيرة ومحسوبة

---

## Current Cleanup Goal
المرحلة الحالية ليست بناء features جديدة، بل:
- تثبيت baseline
- توضيح execution path
- تحديث docs
- تصنيف الملفات غير الواضحة
- التحضير لقرارات cleanup وphases القادمة بدون تشتت
