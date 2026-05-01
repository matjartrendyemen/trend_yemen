# ROADMAP

هذا الملف يوضح خارطة الطريق بعد تثبيت الـ baseline الحالية.

القاعدة الأساسية:
- لا refactor عام الآن
- لا حذف بدون audit
- لا تغيير runtime behavior في مرحلة التوثيق والتنظيم

---

## Current State
الريبو الآن في حالة مستقرة نسبيًا وتشمل:
- Admin Control Center
- Product creation flow
- Product Workspace
- manual asset upload + normalization
- final media selection
- Product Ownership Foundation
- Drive OAuth uploader
- Commit Final Asset
- content generation baseline
- cleanup audit baseline

---

## Immediate Goal
الهدف القادم ليس إعادة بناء النظام، بل التحرك من baseline مستقرة إلى system growth controlled.

---

## Next Implementation Phases

### Phase 1 — Legacy Backend Deletion Pass
**goal:** حذف الطبقات legacy الواضحة غير المستخدمة بعد مراجعة نهائية واعتماد صريح.

**candidate set now:**
- `adapters/drive_adapter.py`
- `adapters/google_repository.py`
- `adapters/sheets_adapter.py`
- `automation/auto_repair.py`
- `core/engine.py`
- `google_repository.py`
- `services/admin_contracts.py`
- `services/sheet_service.py`
- `services/vision_service.py`
- `storage/drive_store.py`
- `system_audit_log.csv`
- possibly root `package.json` / `package-lock.json`

**why this phase matters:**
- تقليل التشويش
- منع قراءة طبقات قديمة باعتبارها source of truth
- تحسين وضوح handoff future

**not included:**
- refactor
- contract simplification
- frontend subtree decision

---

### Phase 2 — Frontend Store Decision Pass
**goal:** اتخاذ قرار واضح بخصوص `trend-yemen-store/`

**questions to answer:**
- هل تبقى داخل نفس الريبو؟
- هل تعتبر subproject نشطة؟
- هل تؤجل؟
- هل تؤرشف؟

**why this phase matters:**
- لأن وجود subtree frontend داخل نفس الريبو يسبب ambiguity أثناء cleanup والهاندأوف

---

### Phase 3 — Ownership & Gallery Hardening
**goal:** توسيع ownership layer بشكل آمن بعد baseline الحالية

**potential scope:**
- multi-gallery ownership rules
- clearer primary vs gallery separation
- safer asset lifecycle rules
- deactivation/reactivation rules

**why deferred now:**
- لأن ownership الأساسية تعمل حاليًا
- والهدف الحالي هو الثبات لا التوسعة

---

### Phase 4 — Product Pages Foundation
**goal:** استهلاك `ProductCode` + ownership + content fields لبناء product pages لاحقًا

**why deferred now:**
- لا نريد فتح frontend/pages قبل تثبيت backend/data ownership بالكامل

---

### Phase 5 — Publishing Automation
**goal:** البناء فوق المحتوى والأصول الحالية للتوزيع والنشر لاحقًا

**why deferred now:**
- لأن النظام ما زال في مرحلة تثبيت data/media/ownership baseline

---

## Explicitly Deferred Work
- advanced gallery management
- product pages
- publishing automation
- supplier expansion beyond current baseline
- pricing sync
- order sync
- analytics
- storefront/product discovery work
- general refactor

---

## Safety Rules for Future Work
- `main.py` تُعدّل فقط بـ patch صغيرة
- ownership field names لا تتغير بدون phase مستقلة
- Sheets contract لا تبسّط أو تعاد تسميتها الآن
- Drive OAuth path لا تعاد هندستها الآن
- أي deletion pass تبدأ من audit مكتوبة ومعتمدة

---

## Recommended Order
1. merge documentation/cleanup clarity work
2. decide legacy backend deletion pass
3. decide frontend subtree status
4. then only start next real implementation phase

---

## Branch Recommendation
بعد اعتماد التوثيق:
- keep: `main`
- keep temporarily: `foundation/system-cleanup`
- create next phase branch from documented baseline:
  - `planning/next-phase-ready`
