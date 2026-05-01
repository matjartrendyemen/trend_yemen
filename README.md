# Trend Yemen — Current Stable Baseline

هذا الملف هو **أول نقطة دخول** لفهم الريبو بسرعة.

إذا كنت AI أو مطورًا جديدًا، اقرأ بالترتيب:
1. `README.md`
2. `AI_HANDOFF.md`
3. `PROJECT_CONTEXT.md`
4. `ENVIRONMENT_MAP.md`
5. `main.py`

---

## What this repo is
النظام الحالي هو **Flask backend + Admin Control Center** لإدارة منتج واحد بشكل curated داخل لوحة الإدارة.

المسار الحالي المعتمد:
1. رفع صورة + سعر يدويًا
2. إنشاء صف جديد في Google Sheets
3. تشغيل enrichment الأساسي عبر orchestrator
4. إدارة media من داخل Admin
5. رفع أصول يدوية عند الحاجة
6. اختيار الأصل النهائي من Product Workspace
7. commit للأصل النهائي إلى Google Drive
8. توليد محتوى publish-ready

---

## Current Stable Baseline
الـ baseline المستقرة الآن تشمل:
- Admin overview / product detail / admin ui
- create product flow
- retry / stuck processing guardrails
- media matching
- Product Workspace
- manual asset upload + normalization
- select final media from workspace
- Product Ownership fields
- Drive OAuth owned asset commit
- stable preview from ownership layer
- content generation baseline

### Completed milestones already in repo
- Admin Workspace
- `product_workspace_assets`
- Manual Asset Upload
- Manual Asset Normalization
- Select from Workspace
- Ownership fields
- Drive OAuth uploader
- Commit Final Asset
- Drive folder by `ProductCode`
- cleanup audit baseline
- deletion of `adapters/cj_adapter.py`

---

## How to Understand This Repo in 5 Minutes

### First files to read
1. `README.md`
   - الصورة العامة
2. `AI_HANDOFF.md`
   - entry path + source of truth + safety rules + ignore filter
3. `main.py`
   - entrypoint الحقيقي وFlask routes الحية
4. `services/admin_read_service.py`
   - طبقة القراءة الإدارية والـ workspace والـ ownership projection
5. `storage/sheets_store.py`
   - طبقة الكتابة الأساسية وعقد Google Sheets

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

## Source of Truth Definition

### Final truth for structured data
- Google Sheets (`Products` tab)

### Final truth for owned media
- Google Drive
  - root folder via `DRIVE_FOLDER_ID`
  - final owned files inside `TrendYemenProductsDrive/<ProductCode>/`

### Read authority
- `services/admin_read_service.py`

### Write authority
- `storage/sheets_store.py`
- `services/drive_asset_service.py`

---

## System Architecture (current)

### Core runtime
- `main.py`
  - Flask entrypoint
  - Admin routes
  - create / retry / stuck resolution / media / content actions

- `core/orchestrator.py`
  - يلتقط الصفوف `Pending`
  - يمررها إلى `AIService`
  - يكتب النتائج الأساسية إلى Sheets

- `storage/sheets_store.py`
  - storage contract الحالية
  - media/content/ownership updates

### Admin read model
- `services/admin_read_service.py`
  - base record
  - readiness
  - failure visibility
  - Product Workspace projection
  - ownership projection
  - stable preview fields

### Media layer
- `services/media_matching_service.py`
  - original seed
  - CJ supplier candidates
  - Pexels fallback

- `services/manual_asset_service.py`
  - manual image/video intake
  - local refs
  - `ManualAssetsJSON`

- `services/drive_asset_service.py`
  - owned asset commit only
  - OAuth uploader
  - product folder by `ProductCode`

### Content layer
- `services/content_output_service.py`
- `services/seo_service.py`

---

## Product Creation Flow
1. Admin يرفع صورة + سعر عبر `/admin/create_product`
2. الصورة تحفظ محليًا كـ seed image
3. الصف يضاف إلى Google Sheets بحالة `Pending`
4. `ProductCode` تثبت مبكرًا من البداية
5. orchestrator يعالج الصف ويكتب الحقول الأساسية

---

## Media Pipeline (current)

### Step 1 — Workspace + Selection
- Match Media
- Product Workspace
- Manual asset upload
- Manual asset normalization
- Select final media

### Step 2 — Ownership + Stable Preview
- `ProductCode`
- `OwnedAssetsJSON`
- `PrimaryImageAssetID`
- `PrimaryVideoAssetID`
- `GalleryAssetIDsJSON`
- Commit Final Asset
- stable preview prefers owned assets

---

## Key Architectural Decisions
- `ProductCode` هي الهوية الثابتة للمنتج
- `CategoryID` metadata فقط وليست جزءًا من الهوية
- الأصول ترتبط بالمنتج وليس بالقسم
- Google Sheets تبقى source of truth للبيانات
- Google Drive تبقى storage للأصول المملوكة
- owned asset upload تستخدم OAuth Gmail user credentials
- Service Account تبقى لمسارات الشيت والمسارات المناسبة فقط
- `main.py` ملف حساس وكبير ويُعدَّل فقط بـ patch صغيرة ومحسوبة
- لا حذف بدون audit
- لا refactor بدون phase مستقلة

---

## AI Focus Filter

### Level 1 — Hard Ignore
لا تُلمس نهائيًا الآن:
- `trend-yemen-store/`
- payment / Pixpay / checkout

### Level 2 — Soft Ignore
تُراجع لاحقًا فقط:
- legacy files المصنفة في `SYSTEM_CLEANUP_AUDIT.md`

### Level 3 — Historical Context
للقراءة فقط:
- docs القديمة / summaries
- `README_AUTONOMOUS.md`

### Re-entry Rules
إذا احتاج AI هذه المناطق:
- لا يعدّل مباشرة
- يفتح phase مستقلة
- لا يدمجها مع backend الحالي

### Why these areas are ignored
- خارج execution path الحالي
- لم تُختبر ضمن baseline
- تخص مراحل مستقبلية

### Critical warning
أي تعديل هنا بدون phase مستقلة قد:
- يكسر النظام
- يسبب تضارب contracts
- يخلط بين backend وfrontend

### Future activation
سيتم العمل عليها لاحقًا ضمن phases مستقلة مثل:
- Frontend / Product Pages Phase
- Commerce / Checkout Phase
- Legacy Cleanup Phase

---

## What is in scope now
- Flask backend
- Admin Control Center
- Google Sheets storage path
- Product Workspace
- media selection
- ownership layer
- content generation baseline

## What is out of scope now
- full legacy deletion
- frontend store decision
- advanced gallery management
- product pages
- publishing automation
- supplier expansion
- pricing/order sync
- analytics
- general refactor

---

## Safety Rules
- لا تكسر flows الحية
- لا refactor عام
- لا full overwrite للملفات الحساسة إلا عند الضرورة القصوى
- `main.py` تُعدّل فقط بـ patch صغيرة مع diff واضح
- أي cleanup تبدأ بالتوثيق ثم audit ثم قرار منفصل

---

## Docs map
- `AI_HANDOFF.md` → quickest engineering handoff
- `PROJECT_CONTEXT.md` → current system context
- `ENVIRONMENT_MAP.md` → environment and credential split
- `SYSTEM_CLEANUP_AUDIT.md` → cleanup classification report
- `ROADMAP.md` → next implementation phases and deferred work

---

## Branch guidance (current)
- `main` = source of truth
- `planning/next-phase-ready` = next implementation branch

### Branches to keep
- `main`
- `planning/next-phase-ready`
