# PROJECT_CONTEXT

هذا الملف مرجع سياقي سريع للحالة الحالية المعتمدة للمشروع.

## Source of Truth
- الفرع العامل للتنظيف والتنظيم: `foundation/system-cleanup`
- baseline المستقرة الحالية مبنية فوق `main`
- لا يتم اعتماد أي فرضية قديمة تخالف ما هو موجود فعليًا في الكود

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

## Current Stable Foundations
### Admin Control Center
- overview / product detail / admin ui
- retryable failure visibility
- stuck processing handling
- manual resolve actions

### Media Layer
- original seed image
- CJ supplier candidates
- Pexels fallback
- manual uploaded assets
- workspace-based final selection

### Ownership Layer
- `ProductCode`
- `OwnedAssetsJSON`
- `PrimaryImageAssetID`
- `PrimaryVideoAssetID`
- `GalleryAssetIDsJSON`

### Content Layer
- `ContentOutputService`
- `SEOService`
- publish-ready commercial fields in Sheets

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

## Contracts that should stay stable
- `SheetsStore` column contracts
- admin read model shape
- `FinalPrimaryMediaURL` selection flow
- ownership field names
- Drive commit route behavior
- manual asset intake contract

## Important Constraints
- لا refactor كبير
- لا حذف ملفات بدون تحقق 100%
- لا تغيير architecture واسعة الآن
- لا كسر أي flow تعمل فعليًا

## Current Cleanup Goal
المرحلة الحالية ليست بناء features جديدة، بل:
- تثبيت baseline
- توضيح execution path
- تحديث docs
- تصنيف الملفات غير الواضحة
- التحضير لحذف آمن لاحقًا
