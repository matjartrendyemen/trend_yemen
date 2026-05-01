# ENVIRONMENT_MAP

هذا الملف يوضح خريطة البيئة الحالية كما تعمل الآن.

## 1) Core Runtime
- التطبيق يعمل عبر `main.py`
- التشغيل الحالي يعتمد على local runtime baseline مستقرة

## 2) Google Sheets Layer
### Variables
- `GOOGLE_CREDENTIALS`
- `SPREADSHEET_ID`

### Used by
- `storage/sheets_store.py`
- `core/orchestrator.py`
- أي طبقة تعتمد على `SheetsStore`

## 3) Google Drive Owned Asset Commit Layer
هذه الطبقة منفصلة عن طبقة الشيت.

### Variables
- `DRIVE_FOLDER_ID`
- `GOOGLE_DRIVE_OAUTH_TOKEN_FILE`

### Bootstrap-only variable
- `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET_FILE`

### Used by
- `services/drive_asset_service.py`

### Rule
- `DRIVE_FOLDER_ID` هو الجذر
- ملفات المنتج ترفع داخل مجلد فرعي خاص بالمنتج
- هذه الطبقة تستخدم OAuth user credentials فقط

## 4) AI Layer
### Variable
- `GEMINI_API_KEY`

### Used by
- `adapters/vision_adapter.py`
- `services/seo_service.py`

## 5) CJ Supplier Layer
### Variable
- `CJ_API_KEY`

### Used by
- `services/cj_supplier_service.py`

## 6) Pexels Layer
### Variable
- `PEXELS_API_KEY`

### Used by
- `adapters/pexels_adapter.py`

## 7) Local Asset Storage
- seed images تحفظ محليًا أولًا
- manual assets تحفظ محليًا أولًا
- commit إلى Drive يحدث فقط بعد final selection

## 8) Separate frontend subtree
- `trend-yemen-store/` تمثل Astro frontend subproject منفصلة
- لها package/config/runtime الخاصة بها
- ليست جزءًا من Flask backend runtime الحالية
- لا ينبغي تقييمها كأنها جزء من Google Sheets / Drive / Admin execution path

## 9) Separation Rules
- Sheets path منفصل عن Drive upload path
- لا يتم استخدام نفس اعتماد الرفع لكلتا الطبقتين
- subtree الواجهة منفصلة عن backend runtime
- هذه القواعد جزء من baseline الحالية
