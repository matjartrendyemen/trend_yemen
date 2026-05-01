# SYSTEM_CLEANUP_AUDIT

هذا المستند هو **التقرير النهائي الشامل الحالي** لتنظيف الريبو اعتمادًا على:
- `repo_files.txt` من الفرع `temp/repo-files-export`
- مراجعة execution path الحالية
- مراجعة imports/references الظاهرة
- مراجعة Flask routes والخدمات الأساسية
- مراجعة الملفات legacy الواضحة

> هذا التقرير **static repository audit**. لا يوجد حذف إضافي هنا، ولا refactor، ولا تغيير runtime behavior.

---

## 1) Source of truth for this audit

### File inventory source
- `repo_files.txt` من الفرع `temp/repo-files-export`

### Current active baseline source
- الفرع العامل: `foundation/system-cleanup`
- الـ backend/runtime الحالية تعتمد على:
  - `main.py`
  - `core/orchestrator.py`
  - `storage/sheets_store.py`
  - `services/admin_read_service.py`
  - `services/ai_service.py`
  - `services/media_matching_service.py`
  - `services/manual_asset_service.py`
  - `services/drive_asset_service.py`
  - `services/cj_supplier_service.py`
  - `services/content_output_service.py`
  - `services/seo_service.py`
  - `services/smart_encoding.py`
  - `adapters/vision_adapter.py`
  - `adapters/pexels_adapter.py`
  - `monitoring/logger.py`

### Important boundary
- subtree `trend-yemen-store/` موجودة داخل نفس الريبو، لكنها **ليست جزءًا من Flask/Admin runtime الحالية**
- لذلك تم التعامل معها كـ subproject مستقلة أثناء هذا الـ audit

---

## 2) Category definitions

- **Must keep**
  - يدخل بوضوح في execution path الحالية
  - أو هو جزء من package/runtime structure الحالية

- **Safe to delete**
  - لا يوجد له دور runtime واضح
  - ولا import/reference واضحة
  - ولا يظهر كجزء من subproject حية
  - مع ثقة عالية جدًا

- **Likely legacy**
  - يبدو قديمًا أو مستبدلًا بطبقة أحدث
  - لا يظهر له دور واضح في execution path الحالية
  - لكن لا يزال الأفضل حذفه بقرار صريح وليس افتراضًا صامتًا

- **Needs runtime verification**
  - لا يدخل في backend الحالية
  - لكن قد يكون جزءًا من subproject أخرى أو tooling مستقل
  - static audit وحدها لا تكفي للحذف النهائي

- **Documentation**
  - ملفات شرح/عقود/مراحل/ملاحظات
  - لا تدخل في runtime behavior

- **Config/runtime**
  - ملفات بيئة/تشغيل/بناء/حزم/إعدادات
  - لا تُعامل ككود application logic

---

## 3) Current live execution path

### Backend / Admin runtime
- `main.py` يستورد مباشرة:
  - `MasterOrchestrator`
  - `SheetsStore`
  - `AdminReadService`
  - `ContentOutputService`
  - `MediaMatchingService`
  - `ManualAssetService`
  - `DriveAssetService` fileciteturn154file0

### Content path
- `ContentOutputService` تعتمد على `SEOService` وتكتب content fields في Sheets. fileciteturn113file0

### Manual assets path
- `ManualAssetService` تحفظ manual assets محليًا وتبني refs فقط. fileciteturn114file0

### Ownership / Drive path
- `DriveAssetService` الحالية تستخدم OAuth token وتضمن product-folder upload داخل `DRIVE_FOLDER_ID`. fileciteturn115file0

### CJ supplier path
- `CJSupplierService` هي طبقة CJ الفعالة الآن. fileciteturn116file0

### Storage path
- `SheetsStore` هي طبقة الشيت الفعالة الحالية، وتشمل ownership columns. fileciteturn122file0

---

# 4) Full file inventory classification

## Root files

### `.env.example`
- **category:** Config/runtime
- **execution path:** no
- **reference:** environment contract only
- **role:** env template
- **reason:** مرجع للمتغيرات المطلوبة، لا يدخل في runtime مباشرة لكنه ضروري كعقد إعداد.

### `.gitignore`
- **category:** Config/runtime
- **execution path:** no
- **reference:** git/tooling only
- **role:** repo hygiene
- **reason:** ملف إدارة تتبع Git.

### `AI_HANDOFF.md`
- **category:** Documentation
- **execution path:** no
- **reference:** no runtime reference
- **role:** handoff doc
- **reason:** مستند توضيحي/تشغيلي وليس جزءًا من التطبيق.

### `Dockerfile`
- **category:** Config/runtime
- **execution path:** no direct app import
- **reference:** deployment/build only
- **role:** container runtime config
- **reason:** ملف تشغيل/نشر، لا يدخل في منطق التطبيق.

### `FINAL_TECHNICAL_SUMMARY.md`
- **category:** Documentation
- **execution path:** no
- **reference:** no runtime reference
- **role:** technical summary
- **reason:** توثيق مرجعي للحالة الفنية.

### `README.md`
- **category:** Documentation
- **execution path:** no
- **reference:** repo entry documentation
- **role:** current baseline explanation
- **reason:** تم تحديثها لتعكس النظام الحالي.

### `README_AUTONOMOUS.md`
- **category:** Documentation
- **execution path:** no
- **reference:** no runtime reference
- **role:** historical/operational doc
- **reason:** توثيق إضافي، ليس runtime.

### `RUNTIME_CONTRACT.md`
- **category:** Documentation
- **execution path:** no
- **reference:** runtime contract doc
- **role:** runtime reference
- **reason:** مستند contract للتشغيل.

### `google_repository.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found
- **role:** older Google Sheets repository abstraction
- **reason:** يوفر طبقة قديمة بديلة لـ `SheetsStore` الحالية، ويستخدم contract أقدم تعتمد على row/column assumptions مختلفة. fileciteturn147file0

### `main.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** Flask entrypoint
- **role:** main runtime entry
- **reason:** نقطة التشغيل الأساسية وواجهة الإدارة الحالية. fileciteturn154file0

### `package-lock.json`
- **category:** Likely legacy
- **execution path:** no clear current backend path
- **reference:** tied to root `package.json`
- **role:** root node lockfile
- **reason:** يوجد subproject frontend منفصلة لها lockfile خاص بها؛ الملف الجذري لا يظهر جزءًا من runtime الحالية.

### `package.json`
- **category:** Likely legacy
- **execution path:** no clear current backend path
- **reference:** no clear app path
- **role:** root node package file
- **reason:** يحتوي فقط dependency محدودة ولا يظهر ضمن backend الحالية أو subtree الواجهة المستقلة. fileciteturn162file0

### `requirements.txt`
- **category:** Config/runtime
- **execution path:** dependency manifest
- **reference:** Python runtime setup
- **role:** backend dependencies
- **reason:** مطلوب لتثبيت بيئة الباك إند.

### `runtime.txt`
- **category:** Config/runtime
- **execution path:** deployment/runtime config
- **reference:** platform runtime hint
- **role:** Python runtime version file
- **reason:** ملف تشغيل/نشر.

### `start_trend_yemen.example.ps1`
- **category:** Config/runtime
- **execution path:** no app import
- **reference:** runtime startup template
- **role:** startup template
- **reason:** ملف مثال للتشغيل وليس كود منطق تطبيق.

### `system_audit_log.csv`
- **category:** Likely legacy
- **execution path:** no
- **reference:** no clear reference found
- **role:** generated audit/log artifact
- **reason:** artifact مسجلة داخل الريبو وليست جزءًا من التطبيق أو التوثيق التشغيلي الأساسية.

### `PROJECT_CONTEXT.md`
- **category:** Documentation
- **execution path:** no
- **reference:** repo context doc
- **role:** current project context
- **reason:** مستند سياقي محدث.

### `ENVIRONMENT_MAP.md`
- **category:** Documentation
- **execution path:** no
- **reference:** environment doc
- **role:** current environment split reference
- **reason:** يشرح فصل Sheets عن Drive OAuth وscope الواجهة المستقلة.

### `SYSTEM_CLEANUP_AUDIT.md`
- **category:** Documentation
- **execution path:** no
- **reference:** cleanup decision doc
- **role:** source of truth for cleanup decisions
- **reason:** هذا المستند نفسه مرجع cleanup الحالي.

---

## adapters/

### `adapters/__init__.py`
- **category:** Must keep
- **execution path:** indirect package support
- **reference:** package marker for adapter imports
- **role:** package structure
- **reason:** يدعم استيراد adapter modules الحالية مثل `vision_adapter` و`pexels_adapter`.

### `adapters/cj_adapter.py`
- **category:** Safe to delete
- **execution path:** no current path
- **reference:** no clear current reference
- **role:** old CJ adapter
- **reason:** تم استبداله فعليًا بـ `services/cj_supplier_service.py` وتم حذفه على فرع cleanup.

### `adapters/drive_adapter.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found
- **role:** older Drive adapter
- **reason:** يعتمد على `service_account.json` و`core_engine` غير الموجودة في الشجرة الحالية، ويتداخل مع `services/drive_asset_service.py` و`storage/drive_store.py`. fileciteturn144file0

### `adapters/google_repository.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found
- **role:** mock/placeholder Google repository
- **reason:** stub بسيطة لا تمثل التكامل الحقيقي الحالي مع Google. fileciteturn145file0

### `adapters/pexels_adapter.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** used in current media fallback path
- **role:** Pexels fallback provider
- **reason:** fallback lifestyle enrichment الحالية. fileciteturn120file0

### `adapters/sheets_adapter.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found
- **role:** older Sheets adapter
- **reason:** يعتمد على `service_account.json` و`core_engine` القديمين، ويتداخل مع `storage/sheets_store.py` الحالية. fileciteturn146file0

### `adapters/vision_adapter.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** current AI path
- **role:** Gemini vision adapter
- **reason:** طبقة الرؤية المستخدمة في enrichment الحالية. fileciteturn119file0

---

## automation/

### `automation/auto_repair.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found for `api_retry_policy`
- **role:** retry helper
- **reason:** helper عامة لا تظهر ضمن current Flask/orchestrator/media/content path. fileciteturn148file0

---

## core/

### `core/engine.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found for `ProductEngine`
- **role:** old SKU/folder naming utility
- **reason:** utility قديمة لا تظهر ضمن current ownership or create flow الحالية. fileciteturn149file0

### `core/orchestrator.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** imported by `main.py`
- **role:** pending row processing orchestrator
- **reason:** جزء أساسي من backend pipeline الحالية. fileciteturn154file0

---

## docs/

### `docs/ADMIN_BACKEND_ARCHITECTURE.md`
- **category:** Documentation
- **execution path:** no
- **reference:** architecture doc
- **role:** internal backend architecture notes
- **reason:** مستند تصميم وليس runtime.

### `docs/ADMIN_SCOPE.md`
- **category:** Documentation
- **execution path:** no
- **reference:** scope doc
- **role:** admin scope notes
- **reason:** توثيق نطاق وليس runtime.

### `docs/B3_ADMIN_READ_SERVICE.md`
- **category:** Documentation
- **execution path:** no
- **reference:** historical implementation doc
- **role:** admin read phase notes
- **reason:** مستند مشروع/مرحلة.

### `docs/PHASE_1_ADMIN_CORE.md`
- **category:** Documentation
- **execution path:** no
- **reference:** phase doc
- **role:** implementation phase notes
- **reason:** مستند مرحلة.

### `docs/PROJECT_RUNTIME_STATE.md`
- **category:** Documentation
- **execution path:** no
- **reference:** runtime state doc
- **role:** project state reference
- **reason:** مستند متابعة وليس runtime code.

### `docs/SMART_ENCODING.md`
- **category:** Documentation
- **execution path:** no
- **reference:** smart encoding doc
- **role:** feature notes
- **reason:** شرح feature وليس التطبيق نفسه.

---

## monitoring/

### `monitoring/logger.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** imported across active services/adapters
- **role:** shared logger
- **reason:** utility فعالة في المسار الحالي. fileciteturn123file0

---

## services/

### `services/__init__.py`
- **category:** Must keep
- **execution path:** indirect package support
- **reference:** package structure
- **role:** services package marker
- **reason:** يدعم بنية imports الحالية.

### `services/admin_contracts.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found for typed contracts
- **role:** typed dict contracts
- **reason:** عقود typing لا يظهر لها استخدام فعلي في current admin read path. fileciteturn150file0

### `services/admin_read_service.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** imported by `main.py`
- **role:** admin read model
- **reason:** طبقة القراءة الحالية للـ Admin والـ ownership/workspace.

### `services/ai_service.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** current orchestrator path
- **role:** AI enrichment service
- **reason:** مسار enrichment الأساسي الحالي.

### `services/cj_supplier_service.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** active media supplier path
- **role:** CJ service layer
- **reason:** طبقة CJ الحالية المعتمدة. fileciteturn116file0

### `services/content_output_service.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** imported by `main.py`
- **role:** content generation write-back layer
- **reason:** طبقة content الفعالة الحالية. fileciteturn113file0

### `services/drive_asset_service.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** imported by `main.py`
- **role:** Drive OAuth owned asset uploader
- **reason:** مسار ownership commit الحالي. fileciteturn115file0turn154file0

### `services/manual_asset_service.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** imported by `main.py`
- **role:** manual asset intake
- **reason:** جزء من current Product Workspace flow. fileciteturn114file0turn154file0

### `services/media_matching_service.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** imported by `main.py`
- **role:** media matching pipeline
- **reason:** current source-priority/media workspace layer.

### `services/seo_service.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** used by `ContentOutputService`
- **role:** Arabic commercial copy engine
- **reason:** content baseline الحالية. fileciteturn121file0turn113file0

### `services/sheet_service.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found for `SheetService`
- **role:** old sheet abstraction
- **reason:** يتداخل مع `storage/sheets_store.py` الحالية ويعتمد على contract أقدم قائم على columns ثابتة. fileciteturn151file0

### `services/smart_encoding.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** imported by `admin_read_service.py`
- **role:** admin readiness/smart encoding helper
- **reason:** جزء مباشر من current admin read path.

### `services/vision_service.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found for `VisionService`
- **role:** thin wrapper around vision adapter
- **reason:** wrapper بديلة لا تظهر في المسار الحالي لأن AI path تستخدم services/adapters أخرى مباشرة. fileciteturn152file0

---

## storage/

### `storage/__init__.py`
- **category:** Must keep
- **execution path:** indirect package support
- **reference:** package structure
- **role:** storage package marker
- **reason:** يدعم imports الحالية.

### `storage/drive_store.py`
- **category:** Likely legacy
- **execution path:** no clear current path
- **reference:** no clear reference found for `DriveStore`
- **role:** old Drive service-account store
- **reason:** يتداخل مع `services/drive_asset_service.py` الحالية ويستخدم service-account upload path القديمة. fileciteturn153file0

### `storage/sheets_store.py`
- **category:** Must keep
- **execution path:** yes
- **reference:** imported by `main.py` and admin/orchestrator path
- **role:** canonical sheet storage layer
- **reason:** الطبقة المركزية الحالية لعقد البيانات. fileciteturn122file0turn154file0

---

## trend-yemen-store/ (separate frontend subproject)

### `trend-yemen-store/.gitignore`
- **category:** Config/runtime
- **execution path:** no current backend path
- **reference:** frontend repo hygiene
- **role:** frontend git config
- **reason:** config خاصة بالـ subproject.

### `trend-yemen-store/.vscode/extensions.json`
- **category:** Config/runtime
- **execution path:** no
- **reference:** editor config only
- **role:** frontend workspace config
- **reason:** ليست جزءًا من التطبيق.

### `trend-yemen-store/.vscode/launch.json`
- **category:** Config/runtime
- **execution path:** no
- **reference:** editor/debug config only
- **role:** frontend workspace debug config
- **reason:** ليست runtime application logic.

### `trend-yemen-store/README.md`
- **category:** Documentation
- **execution path:** no
- **reference:** frontend subproject doc
- **role:** frontend readme
- **reason:** توثيق للـ subproject.

### `trend-yemen-store/astro.config.mjs`
- **category:** Config/runtime
- **execution path:** frontend only
- **reference:** Astro config
- **role:** frontend build config
- **reason:** config للـ subproject المنفصلة.

### `trend-yemen-store/package-lock.json`
- **category:** Config/runtime
- **execution path:** frontend only
- **reference:** frontend package lock
- **role:** frontend dependency lockfile
- **reason:** تخص subtree الواجهة المستقلة.

### `trend-yemen-store/package.json`
- **category:** Config/runtime
- **execution path:** frontend only
- **reference:** Astro scripts/dependencies
- **role:** frontend package manifest
- **reason:** subproject واضحة ومقصودة بداخلها build scripts. fileciteturn163file0

### `trend-yemen-store/public/favicon.ico`
- **category:** Needs runtime verification
- **execution path:** not backend; frontend asset only
- **reference:** likely Astro asset convention
- **role:** frontend static asset
- **reason:** يبدو جزءًا من subproject الواجهة، لكنه خارج backend runtime الحالية.

### `trend-yemen-store/public/favicon.svg`
- **category:** Needs runtime verification
- **execution path:** not backend; frontend asset only
- **reference:** likely Astro asset convention
- **role:** frontend static asset
- **reason:** أصل واجهة static مرتبط بالـ subproject.

### `trend-yemen-store/src/components/FloatingCart.astro`
- **category:** Needs runtime verification
- **execution path:** not backend current path
- **reference:** likely frontend component usage
- **role:** Astro component
- **reason:** ملف واجهة ضمن subproject مستقلة، لا يدخل في current Flask runtime.

### `trend-yemen-store/src/components/ProductCard.astro`
- **category:** Needs runtime verification
- **execution path:** not backend current path
- **reference:** likely frontend component usage
- **role:** Astro component
- **reason:** ملف واجهة ضمن subproject مستقلة.

### `trend-yemen-store/src/lib/utils.js`
- **category:** Needs runtime verification
- **execution path:** not backend current path
- **reference:** likely frontend helper usage
- **role:** frontend utility file
- **reason:** helper للـ subproject الواجهة وليس للـ backend.

### `trend-yemen-store/src/pages/admin.astro`
- **category:** Needs runtime verification
- **execution path:** not backend current path
- **reference:** Astro page convention
- **role:** frontend admin page candidate
- **reason:** route frontend محتملة داخل subproject مستقلة وليست Flask route.

### `trend-yemen-store/src/pages/index.astro`
- **category:** Needs runtime verification
- **execution path:** not backend current path
- **reference:** Astro page convention
- **role:** frontend index page candidate
- **reason:** route frontend ضمن subproject مستقلة.

### `trend-yemen-store/tsconfig.json`
- **category:** Config/runtime
- **execution path:** frontend only
- **reference:** TS tooling config
- **role:** frontend config
- **reason:** config للـ subproject.

---

## 5) Duplicate responsibility summary

### Active duplicate/overlap candidates
- `google_repository.py` vs `storage/sheets_store.py`
- `services/sheet_service.py` vs `storage/sheets_store.py`
- `storage/drive_store.py` vs `services/drive_asset_service.py`
- `adapters/drive_adapter.py` vs `services/drive_asset_service.py`
- `adapters/sheets_adapter.py` vs `storage/sheets_store.py`
- `services/vision_service.py` vs active AI/vision path
- `adapters/google_repository.py` vs actual Google integration layers

### Resolved duplicate
- `adapters/cj_adapter.py` removed in favor of `services/cj_supplier_service.py`

---

## 6) What docs were updated in this cleanup phase

### Updated
- `README.md`
- `PROJECT_CONTEXT.md`
- `ENVIRONMENT_MAP.md`

### What those updates now reflect
- Ownership layer
- Drive OAuth uploader
- Product Workspace
- Manual assets
- Media pipeline الحالية
- current Admin baseline
- separate frontend subtree scope

---

## 7) Final deletion decision lists

## A) Files safe to delete now
- `adapters/cj_adapter.py` *(already deleted on cleanup branch)*

## B) Files that should not be deleted now
- `main.py`
- `core/orchestrator.py`
- `storage/sheets_store.py`
- `storage/__init__.py`
- `services/__init__.py`
- `services/admin_read_service.py`
- `services/ai_service.py`
- `services/cj_supplier_service.py`
- `services/content_output_service.py`
- `services/drive_asset_service.py`
- `services/manual_asset_service.py`
- `services/media_matching_service.py`
- `services/seo_service.py`
- `services/smart_encoding.py`
- `adapters/__init__.py`
- `adapters/vision_adapter.py`
- `adapters/pexels_adapter.py`
- `monitoring/logger.py`
- `.env.example`
- `.gitignore`
- `Dockerfile`
- `requirements.txt`
- `runtime.txt`
- `start_trend_yemen.example.ps1`
- `README.md`
- `FINAL_TECHNICAL_SUMMARY.md`
- `RUNTIME_CONTRACT.md`
- `PROJECT_CONTEXT.md`
- `ENVIRONMENT_MAP.md`
- `SYSTEM_CLEANUP_AUDIT.md`
- كل ملفات `docs/`

## C) Files needing runtime verification before delete/keep decision
- `trend-yemen-store/public/favicon.ico`
- `trend-yemen-store/public/favicon.svg`
- `trend-yemen-store/src/components/FloatingCart.astro`
- `trend-yemen-store/src/components/ProductCard.astro`
- `trend-yemen-store/src/lib/utils.js`
- `trend-yemen-store/src/pages/admin.astro`
- `trend-yemen-store/src/pages/index.astro`

## D) Likely legacy files
- `adapters/drive_adapter.py`
- `adapters/google_repository.py`
- `adapters/sheets_adapter.py`
- `automation/auto_repair.py`
- `core/engine.py`
- `google_repository.py`
- `package-lock.json`
- `package.json`
- `services/admin_contracts.py`
- `services/sheet_service.py`
- `services/vision_service.py`
- `storage/drive_store.py`
- `system_audit_log.csv`

---

## 8) Risk level by group

### Safe to delete now
- **Very low risk**
- currently only `adapters/cj_adapter.py` and it is already removed

### Must not delete now
- **High risk if removed**
- هذه المجموعة تمثل backend/runtime/docs/config الفعالة الحالية

### Needs runtime verification
- **Medium risk**
- لأنها تخص subproject واجهة منفصلة ولم يتم اتخاذ قرار منتج نهائي حولها

### Likely legacy
- **Low to medium risk**
- تبدو قديمة أو مستبدلة static-wise، لكن يفضّل حذفها بقرار واعٍ منفصل وليس تلقائيًا

---

## 9) Final decision

بناءً على static repository audit الحالية:
- لا يوجد حذف إضافي آمن 100% الآن غير `adapters/cj_adapter.py` الذي تم حذفه بالفعل
- هناك مجموعة legacy واضحة يمكن مناقشة حذفها دفعة واحدة لاحقًا
- هناك subtree frontend منفصلة يجب عدم خلطها مع backend baseline
- cleanup التالية يجب أن تكون واحدة من خيارين فقط:
  1. **Legacy backend deletion pass** لملفات المجموعة D
  2. **Frontend subproject decision pass** لملفات المجموعة C
