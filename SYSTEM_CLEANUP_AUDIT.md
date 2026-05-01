# SYSTEM_CLEANUP_AUDIT

هذا الملف هو **التقرير النهائي الحالي** لاتخاذ قرار تنظيف النظام بدون حذف فعلي بعد.

الهدف من هذا التقرير:
- تحديد ما يجب إبقاؤه
- تحديد ما يمكن حذفه لاحقًا دفعة واحدة
- توضيح مستوى الثقة لكل مجموعة
- منع أي حذف يسبق التحقق الحقيقي من execution path

---

## 1) Audit Method

تم بناء هذا التقرير من خلال:
1. مراجعة execution path الأساسية الحالية
2. مراجعة طبقات التشغيل الفعلية:
   - Flask app / Admin routes
   - orchestrator
   - Sheets store
   - admin read model
   - media matching
   - manual asset intake
   - Drive ownership commit
   - content generation
3. مراجعة التبعيات المباشرة بين الخدمات الأساسية
4. مقارنة الطبقات الحالية مع الطبقات legacy الواضحة
5. مراجعة docs الحالية وتحديثها لتطابق baseline الحالية

### Important limitation
هذا التقرير **أقوى من import search فقط**، لكنه ليس مسحًا حرفيًا byte-by-byte لكل ملف في الريبو.

بسبب حدود أدوات الاستعراض الحالية، أي ملف لم يظهر له دور واضح في execution path ولم تتم مراجعته صراحة هنا يتم تصنيفه:
- `needs verification`

ولا يتم اعتباره `safe to delete` إلا إذا كان لدينا دليل واضح جدًا على عدم استخدامه.

---

## 2) Current Execution Path (Source of Truth)

### Core runtime path
- `main.py`
- `core/orchestrator.py`
- `storage/sheets_store.py`
- `services/ai_service.py`
- `adapters/vision_adapter.py`

### Admin / control / read path
- `main.py`
- `services/admin_read_service.py`
- `storage/sheets_store.py`

### Media / ownership path
- `services/media_matching_service.py`
- `services/manual_asset_service.py`
- `services/drive_asset_service.py`
- `services/cj_supplier_service.py`
- `adapters/pexels_adapter.py`

### Content path
- `services/content_output_service.py`
- `services/seo_service.py`

### Shared utility path
- `monitoring/logger.py`

هذا هو المسار الحي الذي يجب حمايته.

---

# 3) Final Classification

## A) Safe to delete (100% unused)

### Current decision
**لا يوجد ملف في هذه الفئة حاليًا.**

### السبب
لا يوجد لدينا حاليًا ملف ثبت 100% أنه:
- خارج execution path
- ولا يوجد له استخدام مباشر أو غير مباشر
- ولا يوجد احتمال معقول أن يكون مرتبطًا بتشغيل أو مسار legacy ما زال قائمًا

### risk level
- **Very low**, لأننا لم نضع أي ملف هنا بدون يقين كامل.

---

## B) Likely safe (95%)

### `adapters/cj_adapter.py`
- **classification:** likely safe
- **confidence:** 95%
- **why:**
  - توجد الآن طبقة CJ أحدث وأكثر ثراءً في:
    - `services/cj_supplier_service.py`
  - media matching الحالية تعتمد على `CJSupplierService`
  - `adapters/cj_adapter.py` تمثل طبقة CJ أقدم وأبسط
  - لا يظهر لها دور واضح في execution path الحالية
  - لا يوجد أي دليل فعلي داخل المراجعة الحالية أنها جزء من admin/media/content/ownership baseline
- **where it used to belong:**
  - طبقة CJ قديمة لجلب منتج واحد بطريقة مبسطة
- **why it is no longer necessary:**
  - تم استبدال مسؤوليتها عمليًا بطبقة أكثر اكتمالًا هي `services/cj_supplier_service.py`
- **why not 100% safe yet:**
  - لم يتم إثبات عدم وجود reference مخفية خارج نطاق المراجعة الحالية
  - لذلك لا تزال تحتاج verification نهائية قبل الحذف الفعلي

### Batch deletion recommendation for group B
- `adapters/cj_adapter.py`

### risk level
- **Low**
- الخطر الأساسي فقط إذا كان هناك reference قديمة غير ظاهرة في ملفات خارج نطاق المراجعة الحالية

---

## C) Needs verification

هذه الفئة لا تعني أن الملف unused.
تعني فقط أنه **لا يوجد لدينا دليل كافٍ الآن** للحذف الآمن.

### Any file outside the audited runtime set
- **classification:** needs verification
- **why:**
  - لم تتم مراجعته صراحة داخل هذا التقرير
  - لا يجوز افتراض أنه ميت فقط لأنه غير مذكور في execution path الأساسية

### Legacy docs / startup files / environment helpers خارج baseline الحالية
- **classification:** needs verification
- **why:**
  - قد تكون قديمة
  - وقد تكون غير مستخدمة
  - لكن لم تتم مراجعتها صراحة ضمن هذا التقرير

### Final / ownership transitional fields inside the sheet contract
- **not files, but areas needing verification before cleanup refactor**
- `FinalImageURL`
- `FinalPrimaryMediaURL`
- `FinalGalleryMediaJSON`
- `OwnedAssetsJSON`
- `PrimaryImageAssetID`
- `PrimaryVideoAssetID`
- `GalleryAssetIDsJSON`
- **why:**
  - يوجد overlap مرحلي مقصود
  - لا يجوز حذف أي field أو تبسيط contract الآن بدون pass منفصلة خاصة بالعقود

### risk level
- **Unknown / medium**
- الحذف هنا قبل verification سيكون عالي المخاطرة

---

## D) Must keep

### `main.py`
- **classification:** must keep
- **why:** Flask entrypoint + Admin routes + operational control surface

### `core/orchestrator.py`
- **classification:** must keep
- **why:** pending row processing runtime path

### `storage/sheets_store.py`
- **classification:** must keep
- **why:** central storage contract for rows, media, content, ownership

### `services/admin_read_service.py`
- **classification:** must keep
- **why:** current read model for Admin, workspace, ownership, stable preview, guardrails

### `services/ai_service.py`
- **classification:** must keep
- **why:** current orchestrator enrichment path

### `adapters/vision_adapter.py`
- **classification:** must keep
- **why:** AIService depends on it for product extraction

### `services/media_matching_service.py`
- **classification:** must keep
- **why:** current media pipeline candidate generation and source priority logic

### `services/manual_asset_service.py`
- **classification:** must keep
- **why:** manual image/video intake path

### `services/drive_asset_service.py`
- **classification:** must keep
- **why:** owned asset commit path via OAuth + product-folder upload contract

### `services/cj_supplier_service.py`
- **classification:** must keep
- **why:** current CJ safe matching + canonical payload generation path

### `adapters/pexels_adapter.py`
- **classification:** must keep
- **why:** current lifestyle fallback path

### `services/content_output_service.py`
- **classification:** must keep
- **why:** publish-ready content write-back and eligibility path

### `services/seo_service.py`
- **classification:** must keep
- **why:** commercial Arabic content engine baseline

### `monitoring/logger.py`
- **classification:** must keep
- **why:** shared logging utility used by current active adapters/services

### `README.md`
- **classification:** must keep
- **why:** now updated to reflect the true current baseline

### `PROJECT_CONTEXT.md`
- **classification:** must keep
- **why:** current project-state reference for future work

### `ENVIRONMENT_MAP.md`
- **classification:** must keep
- **why:** current environment split reference

### `SYSTEM_CLEANUP_AUDIT.md`
- **classification:** must keep
- **why:** cleanup decision reference before any deletion phase

### risk level
- **High if removed incorrectly**
- هذه المجموعة تمثل baseline الحية الحالية

---

# 4) Duplicate Responsibilities

## CJ overlap
### files
- `adapters/cj_adapter.py`
- `services/cj_supplier_service.py`

### assessment
- overlap واضح
- الطبقة المعتمدة حاليًا هي `services/cj_supplier_service.py`
- `adapters/cj_adapter.py` legacy candidate

## Media identity overlap
### fields
- `ImageURL`
- `SeedMediaURL`

### assessment
- overlap مرحلي لكنه مقبول الآن
- `ImageURL` تمثل الإدخال الخام
- `SeedMediaURL` تمثل seed contract الحالية
- لا cleanup الآن

## Final media overlap
### fields
- `FinalImageURL`
- `FinalPrimaryMediaURL`
- ownership pointers/registry

### assessment
- overlap intentional during transition
- ownership layer هي الاتجاه الصحيح طويل المدى
- لا حذف الآن

## Gallery overlap
### fields
- `FinalGalleryMediaJSON`
- `GalleryAssetIDsJSON`
- `OwnedAssetsJSON`

### assessment
- overlap مرحلي
- لا cleanup contract الآن

## Drive responsibility split
### areas
- Sheets path via service credentials
- owned asset commit path via OAuth

### assessment
- هذا split intentional وليس duplicate problem
- يجب إبقاؤه كما هو

---

# 5) Documentation status

## `README.md`
- **previous state:** outdated
- **current state:** updated to current baseline

## `PROJECT_CONTEXT.md`
- **previous state:** missing
- **current state:** added

## `ENVIRONMENT_MAP.md`
- **previous state:** missing
- **current state:** added

---

# 6) Final Batch Deletion Candidate List

## Group A — Safe to delete (100%)
- **none currently**

## Group B — Likely safe (95%)
- `adapters/cj_adapter.py`

## Group C — Needs verification
- أي ملف لم تتم مراجعته صراحة في هذا التقرير
- أي docs أو helpers قديمة خارج execution-path set

## Group D — Must keep
- `main.py`
- `core/orchestrator.py`
- `storage/sheets_store.py`
- `services/admin_read_service.py`
- `services/ai_service.py`
- `adapters/vision_adapter.py`
- `services/media_matching_service.py`
- `services/manual_asset_service.py`
- `services/drive_asset_service.py`
- `services/cj_supplier_service.py`
- `adapters/pexels_adapter.py`
- `services/content_output_service.py`
- `services/seo_service.py`
- `monitoring/logger.py`
- `README.md`
- `PROJECT_CONTEXT.md`
- `ENVIRONMENT_MAP.md`
- `SYSTEM_CLEANUP_AUDIT.md`

---

# 7) Recommended Next Decision

إذا كان الهدف هو **حذف دفعة واحدة بشكل آمن**، فالقرار الحالي الصحيح هو:

1. **عدم حذف Group A** لأنه فارغ
2. **اعتماد `adapters/cj_adapter.py` فقط كأول ملف حذف دفعي محتمل**
3. عدم حذف أي شيء من Group C قبل verification إضافية
4. حماية Group D بالكامل

---

# 8) Final Risk Summary

## Very low risk
- عدم حذف أي ملف الآن
- أو حذف ملفات Group A فقط (حاليًا لا يوجد)

## Low risk
- حذف `adapters/cj_adapter.py` بعد موافقة صريحة

## Medium to high risk
- حذف أي ملف خارج هذا التقرير
- أو حذف حقول/عقود ownership/final media الآن
- أو cleanup مع refactor في نفس المرحلة
