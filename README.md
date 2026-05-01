# Trend Yemen — Current Stable Baseline

هذا المستند يصف **الحالة الحالية الفعلية** للنظام كما هو معتمد الآن داخل الريبو.

## 1) الهدف الحالي للنظام
النظام يعمل كـ **Admin Control Center** لإدارة منتج واحد بشكل احترافي من داخل لوحة الإدارة، مع الحفاظ على baseline مستقرة وقابلة للتوسع لاحقًا.

المسار الحالي المعتمد:
1. رفع صورة + سعر يدويًا
2. إنشاء صف جديد في Google Sheets
3. تشغيل enrichment الأساسي عبر orchestrator
4. إدارة media من داخل Admin
5. اختيار الأصل النهائي
6. commit للأصل النهائي إلى Google Drive
7. توليد محتوى publish-ready

## 2) المعمارية الحالية المختصرة

### طبقة التشغيل الأساسية
- `main.py`
  - نقطة الدخول الرئيسية
  - Flask routes
  - Admin UI
  - create / retry / stuck resolution / media / content actions

- `core/orchestrator.py`
  - يلتقط الصفوف `Pending`
  - يمررها إلى `AIService`
  - يكتب النتائج الأساسية في Google Sheets

- `storage/sheets_store.py`
  - مصدر الكتابة/القراءة الرئيسي لجدول `Products`
  - يضمن وجود الأعمدة المطلوبة
  - يدير media/content/ownership field updates

### طبقة القراءة الإدارية
- `services/admin_read_service.py`
  - تبني admin record موحدة read-only
  - تعرض:
    - base record
    - media contract
    - ownership contract
    - workspace assets
    - retry / stuck visibility
    - content visibility
    - readiness snapshot

### طبقة media
- `services/media_matching_service.py`
  - تبني matched media candidates
  - تدمج:
    - original seed media
    - CJ supplier candidates
    - Pexels fallback lifestyle

- `services/manual_asset_service.py`
  - تحفظ manual image/video محليًا
  - تبني `ManualAssetsJSON`
  - لا تكتب إلى Drive

- `services/drive_asset_service.py`
  - commit للأصل النهائي فقط
  - تستخدم **OAuth user credentials**
  - ترفع داخل:
    - `TrendYemenProductsDrive/<ProductCode>/`
  - لا تعتمد على Service Account لرفع owned assets

### طبقة المورد والمحتوى
- `services/cj_supplier_service.py`
  - on-demand CJ retrieval
  - safe matching
  - canonical payload mapping

- `services/content_output_service.py`
  - eligibility checks
  - content write-back
  - تعتمد على `SEOService`

- `services/seo_service.py`
  - commercial Arabic content generation
  - strategy-aware copy
  - sanitization / polish logic

## 3) Product Creation Flow
1. Admin يرفع صورة + سعر عبر `/admin/create_product`
2. الصورة تحفظ محليًا كـ seed image
3. الصف يضاف إلى Google Sheets بحالة `Pending`
4. `ProductCode` تُثبت مبكرًا من البداية
5. orchestrator يعالج الصف ويكتب:
   - `ProductName`
   - `SKU`
   - `CategoryID`
   - `QualityStatus`
   - `ErrorMessage`

## 4) Media Pipeline الحالي

### Step 1 — Workspace + Selection
- Match Media
- Product Workspace
- Manual image/video intake
- Final media selection

### Step 2 — Ownership + Stable Preview
- Ownership fields داخل نفس row:
  - `ProductCode`
  - `OwnedAssetsJSON`
  - `PrimaryImageAssetID`
  - `PrimaryVideoAssetID`
  - `GalleryAssetIDsJSON`
- commit final asset إلى Google Drive
- stable preview تفضّل owned assets عند توفرها

## 5) Google Integration Contract

### Google Sheets
- ما زالت تعمل عبر **Service Account**
- تستخدم `GOOGLE_CREDENTIALS`
- لا يوجد تغيير على هذا المسار حاليًا

### Google Drive owned asset commit
- يعمل عبر **OAuth user credentials**
- لا يستخدم Service Account للرفع
- يعتمد على:
  - `DRIVE_FOLDER_ID`
  - `GOOGLE_DRIVE_OAUTH_TOKEN_FILE`
- الملفات المرفوعة تحفظ داخل مجلد المنتج فقط

## 6) Ownership Layer الحالية
الهوية الأساسية للمنتج الآن هي:
- `ProductCode`

والقسم يبقى metadata قابلة للتغيير:
- `CategoryID`

الأصول المملوكة تحفظ داخل:
- `OwnedAssetsJSON`

والـ pointers الحالية:
- `PrimaryImageAssetID`
- `PrimaryVideoAssetID`
- `GalleryAssetIDsJSON`

هذا يمهّد لاحقًا لـ:
- Product Pages
- publishing
- gallery متعددة
- suppliers إضافيين

## 7) ما هو stable فعليًا الآن
- Admin UI / Control Center
- Product creation flow
- retry guardrails
- stuck processing handling
- media matching baseline
- manual asset intake
- final media selection
- owned asset commit إلى Google Drive عبر OAuth
- stable preview ownership read
- content generation baseline

## 8) ما الذي لا يجب كسره
- `main.py` routes الحالية
- `storage/sheets_store.py` contracts الحالية
- `services/admin_read_service.py` read model
- create flow
- retry/stuck flows
- media matching baseline
- ownership write/read contracts

## 9) ما الذي لا يزال مؤجلًا
- Product Pages الفعلية
- publishing automation
- bulk operations
- advanced cleanup / file deletion
- supplier expansion beyond current baseline
- refactor عام

## 10) قاعدة العمل الحالية
أي تطوير جديد يجب أن يلتزم بـ:
- أقل blast radius ممكن
- patches صغيرة ومحسوبة
- branch منفصل للتجارب
- diff قبل الاعتماد عند الملفات الحساسة
- بدون full overwrite إلا عند الضرورة القصوى
