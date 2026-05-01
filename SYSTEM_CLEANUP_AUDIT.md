# SYSTEM_CLEANUP_AUDIT

هذا الملف هو audit أولية لمرحلة التنظيم والاستقرار.

## Audit Scope
هذه المراجعة اعتمدت على الملفات الأساسية في execution path الحالية:
- `main.py`
- `core/orchestrator.py`
- `storage/sheets_store.py`
- `services/admin_read_service.py`
- `services/ai_service.py`
- `services/media_matching_service.py`
- `services/manual_asset_service.py`
- `services/drive_asset_service.py`
- `services/content_output_service.py`
- `services/seo_service.py`
- `services/cj_supplier_service.py`
- `adapters/vision_adapter.py`
- `adapters/pexels_adapter.py`
- `adapters/cj_adapter.py`
- `monitoring/logger.py`

> ملاحظة: هذه audit لا تعني أن كل ملفات الريبو تم التحقق منها 100%. أي ملف خارج هذا النطاق يبقى "needs verification" حتى تتم مراجعته صراحة.

---

## 1) Active / Used in Current Execution Path

### `main.py`
- **الحالة:** used
- **السبب:** نقطة الدخول الأساسية وواجهة Flask وكل Admin routes الحالية.

### `core/orchestrator.py`
- **الحالة:** used
- **السبب:** مسار معالجة صفوف `Pending` ما زال يعتمد عليه.

### `storage/sheets_store.py`
- **الحالة:** used
- **السبب:** طبقة التخزين الرئيسية للشيت، وتشمل media/content/ownership updates.

### `services/admin_read_service.py`
- **الحالة:** used
- **السبب:** read model الحالية للـ Admin وownership/stable preview/workspace.

### `services/ai_service.py`
- **الحالة:** used
- **السبب:** يمر عبره orchestrator في enrichment الأساسي.

### `services/media_matching_service.py`
- **الحالة:** used
- **السبب:** match media candidates وبناء source priority الحالية.

### `services/manual_asset_service.py`
- **الحالة:** used
- **السبب:** manual image/video intake local layer.

### `services/drive_asset_service.py`
- **الحالة:** used
- **السبب:** owned asset commit إلى Google Drive عبر OAuth.

### `services/content_output_service.py`
- **الحالة:** used
- **السبب:** content generation eligibility + write-back.

### `services/seo_service.py`
- **الحالة:** used
- **السبب:** commercial content generation layer الحالية.

### `services/cj_supplier_service.py`
- **الحالة:** used
- **السبب:** CJ retrieval + safe matching + canonical candidate payloads.

### `adapters/vision_adapter.py`
- **الحالة:** used
- **السبب:** AIService تعتمد عليه في vision extraction.

### `adapters/pexels_adapter.py`
- **الحالة:** used
- **السبب:** lifestyle fallback داخل media matching.

### `monitoring/logger.py`
- **الحالة:** used
- **السبب:** مستعمل من عدة طبقات فعالة مثل vision/pexels/seo.

---

## 2) Candidate for Removal

### `adapters/cj_adapter.py`
- **الحالة:** candidate_for_removal
- **درجة الثقة:** عالية نسبيًا
- **سبب الترشيح:**
  - يوجد الآن مسار CJ أحدث وأوضح في:
    - `services/cj_supplier_service.py`
  - media layer الحالية تعتمد على `CJSupplierService`
  - الملف يبدو legacy بطبقة auth/fetch أقدم وأبسط
  - لا يظهر له دور واضح داخل execution path التي تمت مراجعتها
- **القرار الآن:**
  - **لا يُحذف بعد**
  - يظل مرشحًا للحذف بعد verification نهائية على مستوى repo imports/search الكامل

---

## 3) Needs Verification

### أي ملف خارج نطاق audit الحالية
- **الحالة:** needs_verification
- **السبب:** لم تتم مراجعته صراحة داخل هذه pass
- **القرار:** لا حذف ولا refactor قبل فتحه ومراجعته فعليًا

### أي docs أو ملفات تشغيل قديمة غير مذكورة هنا
- **الحالة:** needs_verification
- **السبب:** قد تكون قديمة أو غير محدثة أو خارج المسار الحالي
- **القرار:** مراجعة منفصلة قبل أي حذف

---

## 4) Duplicate Responsibilities / Overlaps

### A) CJ integration overlap
- `adapters/cj_adapter.py`
- `services/cj_supplier_service.py`

**التقييم:**
- هذا أقوى overlap واضح حاليًا
- المسار الأحدث والأغنى وظيفيًا هو `services/cj_supplier_service.py`
- `adapters/cj_adapter.py` تبدو legacy candidate

### B) Media identity overlap in sheet fields
- `ImageURL`
- `SeedMediaURL`

**التقييم:**
- يوجد تداخل وظيفي جزئي
- لكن لا يزال هذا التداخل مقبولًا حاليًا لأن `ImageURL` تمثل الإدخال الخام و`SeedMediaURL` تمثل seed contract الحالية
- **لا يوصى بتعديلهما الآن**

### C) Final media overlap
- `FinalImageURL`
- `FinalPrimaryMediaURL`
- ownership layer (`OwnedAssetsJSON`, `PrimaryImageAssetID`, `PrimaryVideoAssetID`)

**التقييم:**
- هذا overlap مقصود حاليًا بسبب التطور المرحلي للنظام
- `FinalImageURL` تبدو legacy fallback
- `FinalPrimaryMediaURL` هي final selection الحالية
- ownership fields هي الاتجاه المعماري الصحيح للمستقبل
- **لا حذف الآن**

### D) Gallery overlap
- `FinalGalleryMediaJSON`
- `GalleryAssetIDsJSON`
- `OwnedAssetsJSON`

**التقييم:**
- يوجد تداخل مرحلي
- ownership pointers هي الاتجاه الصحيح طويل المدى
- لكن الحقول القديمة لا تزال جزءًا من baseline الحالية
- **لا حذف الآن**

### E) Drive responsibility split
- `storage/sheets_store.py` لديها Drive scope ضمن credentials
- `services/drive_asset_service.py` تستخدم OAuth لرفع owned assets

**التقييم:**
- هذا ليس duplicate problem الآن
- بل split intentional:
  - Sheets path منفصلة
  - Drive ownership upload path منفصلة
- **يجب إبقاؤه كما هو الآن**

---

## 5) Files / Areas needing documentation alignment

### `README.md`
- **الحالة السابقة:** outdated
- **الإجراء:** تم تحديثها لتصف baseline الحالية

### `PROJECT_CONTEXT.md`
- **الحالة السابقة:** غير موجود
- **الإجراء:** تم إنشاؤه

### `ENVIRONMENT_MAP.md`
- **الحالة السابقة:** غير موجود
- **الإجراء:** تم إنشاؤه

---

## 6) Safe Next Actions
1. عدم حذف أي ملف فعلي الآن
2. اعتماد `adapters/cj_adapter.py` كأول مرشح حذف بعد verification نهائية
3. الإبقاء على ownership/data overlaps الحالية حتى مرحلة cleanup المقصودة
4. عدم إجراء refactor عام أثناء cleanup
5. استخدام هذا الملف كمرجع قرار قبل أي حذف فعلي لاحق

---

## 7) Current Cleanup Decision
- **الحذف الآن:** لا يوجد
- **مرشح حذف واضح:** `adapters/cj_adapter.py`
- **ملفات تحتاج تحقق إضافي:** أي ملف خارج نطاق audit الحالية
- **baseline الحالية:** مستقرة ويجب عدم كسرها أثناء cleanup
