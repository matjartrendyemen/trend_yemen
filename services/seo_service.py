import json
import os
import re
from typing import Any, Dict, List

from google import genai
from monitoring.logger import system_log


class SEOService:
    STRATEGY_KEYWORDS = {
        "health_pain_relief": [
            "pain", "relief", "health", "massage", "therapy", "back", "neck", "knee",
            "joint", "posture", "medical", "wellness", "muscle", "recovery",
            "صحة", "ألم", "آلام", "ظهر", "رقبة", "ركبة", "مفاصل", "مساج", "علاج", "عضلات",
        ],
        "beauty": [
            "beauty", "skin", "skincare", "hair", "face", "cosmetic", "makeup",
            "glow", "serum", "cleanser", "جمال", "بشرة", "شعر", "عناية", "سيروم",
            "مكياج", "نضارة", "إشراقة",
        ],
        "home_convenience": [
            "home", "kitchen", "organizer", "storage", "clean", "cleaning", "vacuum",
            "household", "convenience", "منزل", "مطبخ", "ترتيب", "تنظيم", "تنظيف",
            "عملي", "منزلي",
        ],
        "gadget": [
            "gadget", "device", "smart", "tech", "charger", "wireless", "portable",
            "usb", "led", "accessory", "electronic", "تقنية", "جهاز", "إلكتروني",
            "ذكي", "شاحن", "محمول",
        ],
        "fitness": [
            "fitness", "sport", "training", "workout", "exercise", "gym", "running",
            "yoga", "active", "رياضة", "لياقة", "تمرين", "تدريب", "نشاط",
        ],
        "kids_family": [
            "kids", "kid", "baby", "child", "family", "children", "parent", "school",
            "toys", "feeding", "safety", "أطفال", "طفل", "بيبي", "عائلة", "أسرة",
            "ألعاب", "أمان",
        ],
    }

    STRATEGY_LIBRARY = {
        "health_pain_relief": {
            "display_name": "Health / Pain relief",
            "hook_templates": [
                "إذا كان الانزعاج اليومي يسرق راحتك، فهذا النوع من الحلول يصنع فرقًا واضحًا.",
                "الراحة الحقيقية تبدأ من اختيار عملي يخفف عبء يومك.",
                "حين يتحول التعب إلى عادة يومية، يصبح الحل المريح ضرورة.",
            ],
            "title_templates": [
                "{product_name} | راحة أوضح كل يوم",
                "{product_name} | حل عملي للراحة اليومية",
                "{product_name} | فرق تشعر به من أول استخدام",
            ],
            "pain_lines": [
                "الانزعاج المتكرر يجعل أبسط تفاصيل اليوم أثقل مما يجب.",
                "حين يطول التعب، يتأثر إحساسك بالراحة والتركيز.",
            ],
            "solution_lines": [
                "{product_name} يمنحك استخدامًا مريحًا وعمليًا يناسب روتينك اليومي.",
                "{product_name} يساعدك على جعل يومك أخف وأكثر راحة.",
            ],
            "desire_lines": [
                "النتيجة هي إحساس أفضل بالراحة وانسيابية أوضح في يومك.",
                "هذا النوع من الاختيارات يضيف إلى يومك راحة تشعر بها فعلًا.",
            ],
            "cta_short_forms": [
                "اطلبه الآن",
                "ابدأ فرق الراحة اليوم",
                "جرّبه من اليوم",
            ],
            "keyword_stems": [
                "راحة يومية", "تخفيف الانزعاج", "حل عملي", "استخدام مريح", "راحة أفضل",
            ],
            "hashtag_stems": [
                "راحة", "صحة", "حل_عملي", "يومك_أخف",
            ],
        },
        "beauty": {
            "display_name": "Beauty",
            "hook_templates": [
                "الإشراقة الجميلة تبدأ من عناية تعكس حضورك الحقيقي.",
                "حين تختارين العناية الصحيحة، يظهر الفرق في التفاصيل.",
                "الجمال الأجمل هو الذي يبدو طبيعيًا ويترك أثرًا واثقًا.",
            ],
            "title_templates": [
                "{product_name} | لمسة جمال أجمل",
                "{product_name} | إشراقة وثقة كل يوم",
                "{product_name} | عناية تبرز جمالك",
            ],
            "pain_lines": [
                "العناية العادية لا تمنح دائمًا النتيجة التي تشعرين معها بالرضا الكامل.",
                "أحيانًا تكون اللمسة الصحيحة أهم من أي مبالغة.",
            ],
            "solution_lines": [
                "{product_name} يضيف إلى روتينك لمسة أنيقة ونتيجة أحب إلى النفس.",
                "{product_name} يمنحك تجربة عناية أجمل وأكثر حضورًا.",
            ],
            "desire_lines": [
                "النتيجة هي إشراقة أوضح وثقة أكبر في الإطلالة.",
                "هذا النوع من العناية يجعل حضورك أجمل بطريقة راقية.",
            ],
            "cta_short_forms": [
                "اختاري لمستك الأجمل",
                "امنحي نفسك إشراقة أجمل",
                "ابدئي عنايتك الآن",
            ],
            "keyword_stems": [
                "عناية يومية", "إشراقة", "ثقة", "جمال", "روتين عناية",
            ],
            "hashtag_stems": [
                "جمال", "عناية", "إشراقة", "روتين_جمال",
            ],
        },
        "home_convenience": {
            "display_name": "Home convenience",
            "hook_templates": [
                "الأشياء التي تجعل البيت أسهل هي الأفضل قيمة في اليوم العادي.",
                "حين تصبح التفاصيل المنزلية أبسط، يصبح يومك أخف.",
                "الحل العملي هو الذي يختصر عليك الجهد من أول مرة.",
            ],
            "title_templates": [
                "{product_name} | راحة أكثر في يومك",
                "{product_name} | حل منزلي عملي",
                "{product_name} | سهولة يومية بلمسة ذكية",
            ],
            "pain_lines": [
                "التفاصيل الصغيرة في البيت قد تستهلك وقتًا وجهدًا أكثر مما تستحق.",
                "الإزعاج المتكرر داخل البيت يجعل الروتين اليومي أقل راحة.",
            ],
            "solution_lines": [
                "{product_name} يجعل الاستخدام اليومي أسهل وأكثر ترتيبًا.",
                "{product_name} يمنحك طريقة أذكى للتعامل مع الروتين المنزلي.",
            ],
            "desire_lines": [
                "النتيجة هي جهد أقل وراحة أوضح في تفاصيل اليوم.",
                "هذا النوع من الخيارات يجعل البيت أسهل وأكثر ترتيبًا.",
            ],
            "cta_short_forms": [
                "اجعلي يومك أسهل",
                "اختاري الحل العملي",
                "ابدئي الراحة من الآن",
            ],
            "keyword_stems": [
                "راحة منزلية", "تنظيم", "حل عملي", "سهولة يومية", "توفير وقت",
            ],
            "hashtag_stems": [
                "منزل", "راحة_منزلية", "تنظيم", "حل_عملي",
            ],
        },
        "gadget": {
            "display_name": "Gadget",
            "hook_templates": [
                "الحل الأذكى هو الذي يختصر عليك الوقت من أول استخدام.",
                "أحيانًا أداة واحدة عملية تغيّر إيقاع يومك بالكامل.",
                "حين يجتمع الذكاء والسهولة، يصبح القرار أسهل.",
            ],
            "title_templates": [
                "{product_name} | الحل الأذكى ليومك",
                "{product_name} | أداء عملي بشكل أبسط",
                "{product_name} | أداة ذكية بقيمة واضحة",
            ],
            "pain_lines": [
                "الأدوات التقليدية لا تمنح دائمًا السرعة أو السهولة التي يحتاجها يومك.",
                "حين يكون الاستخدام معقدًا، تضيع القيمة مهما بدا المنتج جيدًا.",
            ],
            "solution_lines": [
                "{product_name} يقدم تجربة عملية وذكية تناسب الاستخدام اليومي.",
                "{product_name} يجمع بين السهولة والقيمة في أداة واحدة.",
            ],
            "desire_lines": [
                "النتيجة هي استخدام أسرع وراحة أكبر في التفاصيل.",
                "هذا النوع من المنتجات يمنحك إحساسًا أنك اخترت الحل الأذكى فعلًا.",
            ],
            "cta_short_forms": [
                "جرّب الحل الأذكى",
                "ابدأ تجربة أذكى",
                "اختر الأداء العملي",
            ],
            "keyword_stems": [
                "أداة ذكية", "تقنية عملية", "حل سريع", "أداء عملي", "قيمة واضحة",
            ],
            "hashtag_stems": [
                "تقنية", "أداة_ذكية", "حل_أذكى", "عملي",
            ],
        },
        "fitness": {
            "display_name": "Fitness",
            "hook_templates": [
                "النتيجة تبدأ من قرار صغير تلتزم به كل يوم.",
                "إذا كنت تريد بداية أقوى، ابدأ بأداة تدعمك فعليًا.",
                "من الكسل إلى النشاط، الفرق يبدأ باختيار صحيح.",
            ],
            "title_templates": [
                "{product_name} | بداية أقوى لنتيجة أوضح",
                "{product_name} | خيار عملي لنشاطك اليومي",
                "{product_name} | التزام أسهل ونتيجة أقرب",
            ],
            "pain_lines": [
                "أكبر تحدٍ في أي بداية ليس الحماس فقط، بل الاستمرار بثبات.",
                "حين يغيب الدعم العملي، تصبح البداية أصعب مما يجب.",
            ],
            "solution_lines": [
                "{product_name} يساعدك على جعل روتينك أكثر التزامًا ووضوحًا.",
                "{product_name} يضيف إلى يومك عاملًا عمليًا يشجّعك على الاستمرار.",
            ],
            "desire_lines": [
                "النتيجة هي إحساس أقوى بالنشاط وخطوة أوضح نحو هدفك.",
                "هذا النوع من المنتجات يجعل الالتزام أسهل والرحلة أكثر واقعية.",
            ],
            "cta_short_forms": [
                "ابدأ التغيير الآن",
                "خذ أول خطوة اليوم",
                "ابدأ نشاطك من الآن",
            ],
            "keyword_stems": [
                "لياقة", "نشاط", "تمرين", "التزام", "نتيجة أفضل",
            ],
            "hashtag_stems": [
                "لياقة", "نشاط", "تمرين", "ابدأ_الآن",
            ],
        },
        "kids_family": {
            "display_name": "Kids / family",
            "hook_templates": [
                "راحة العائلة تبدأ من التفاصيل التي تسهّل اليوم كله.",
                "كل اختيار عملي للأسرة ينعكس على راحة البيت بشكل واضح.",
                "السهولة والاطمئنان هما ما تحتاجه الأسرة فعلًا.",
            ],
            "title_templates": [
                "{product_name} | راحة أكثر للعائلة",
                "{product_name} | اختيار عملي للأسرة",
                "{product_name} | سهولة يومية لكل البيت",
            ],
            "pain_lines": [
                "تفاصيل اليوم العائلي قد تصبح مرهقة عندما لا تكون الحلول عملية بما يكفي.",
                "كل شيء يخفف الضغط عن الأسرة يصنع فرقًا واضحًا.",
            ],
            "solution_lines": [
                "{product_name} يساعد على جعل اليوم أكثر راحة وسهولة.",
                "{product_name} يمنح الأسرة طريقة أسهل للتعامل مع التفاصيل اليومية.",
            ],
            "desire_lines": [
                "النتيجة هي إحساس أفضل بالراحة والتنظيم والثقة في الاختيار.",
                "هذا النوع من المنتجات يجعل اليوم العائلي أخف وأكثر هدوءًا.",
            ],
            "cta_short_forms": [
                "وفّر راحة أكثر لعائلتك",
                "اختر الحل العملي اليوم",
                "اجعل يومكم أسهل الآن",
            ],
            "keyword_stems": [
                "راحة الأسرة", "منتج عائلي", "سهولة يومية", "حل عملي",
            ],
            "hashtag_stems": [
                "عائلة", "راحة_الأسرة", "أطفال", "حل_عملي",
            ],
        },
        "general": {
            "display_name": "General commercial",
            "hook_templates": [
                "الاختيار الذكي هو الذي يمنحك فائدة واضحة من أول مرة.",
                "إذا كنت تبحث عن قيمة عملية وشكل مقنع، فهذا النوع يستحق الانتباه.",
                "هناك منتجات عادية، وهناك منتجات تصنع فرقًا فعليًا.",
            ],
            "title_templates": [
                "{product_name} | اختيار عملي يستحق التجربة",
                "{product_name} | قيمة أوضح واستخدام أسهل",
                "{product_name} | فرق واضح في الاستخدام اليومي",
            ],
            "pain_lines": [
                "كثير من الخيارات تبدو جيدة، لكن القليل منها يمنحك قيمة واضحة فعلًا.",
                "حين يكون الاختيار غير موفق، تضيع القيمة مهما بدا المنتج جذابًا.",
            ],
            "solution_lines": [
                "{product_name} يجمع بين العملية والقيمة بشكل يسهّل قرار الشراء.",
                "{product_name} يقدم استخدامًا مريحًا وفائدة واضحة من البداية.",
            ],
            "desire_lines": [
                "النتيجة هي منتج يعطيك إحساسًا أفضل بالاختيار والقيمة.",
                "هذا النوع من المنتجات يجعل قرار الشراء أكثر راحة وثقة.",
            ],
            "cta_short_forms": [
                "اطلبه الآن",
                "جرّبه اليوم",
                "ابدأ اختيارًا أذكى",
            ],
            "keyword_stems": [
                "منتج عملي", "قيمة واضحة", "اختيار ذكي", "سهولة استخدام",
            ],
            "hashtag_stems": [
                "منتجات_مميزة", "اختيار_ذكي", "عملي",
            ],
        },
    }

    ENGLISH_TO_ARABIC = {
        "wireless": "لاسلكي",
        "smart": "ذكي",
        "portable": "محمول",
        "charger": "شاحن",
        "massager": "مساج",
        "massage": "مساج",
        "device": "جهاز",
        "gadget": "أداة",
        "fitness": "لياقة",
        "beauty": "جمال",
        "home": "منزلي",
        "kitchen": "مطبخ",
        "baby": "أطفال",
        "kids": "أطفال",
        "family": "عائلي",
        "relief": "راحة",
        "pain": "ألم",
        "serum": "سيروم",
        "cleanser": "منظف",
        "usb": "منفذ",
    }

    BANNED_SYSTEM_PHRASES = [
        "trend yemen",
        "selected",
        "approved",
        "ready",
        "finalized",
        "preview",
        "raw",
        "system",
        "جاهز للمراجعة",
        "الحالة الإعلامية",
        "داخل المتجر",
        "داخل متجر",
        "قابل للمراجعة",
        "content status",
        "marketing output",
    ]

    MIN_HASHTAGS = 2
    MAX_HASHTAGS = 5
    MAX_TITLE_LENGTH = 58
    MAX_DESCRIPTION_LENGTH = 260
    MAX_SOCIAL_LENGTH = 280
    MAX_KEYWORDS = 6

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model_id = "gemini-1.5-flash"

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                system_log.error(f"❌ SEOService client init error: {e}")
                self.client = None

    def _clean(self, value):
        return str(value or "").strip()

    def _collapse_whitespace(self, text):
        return re.sub(r"\s+", " ", self._clean(text)).strip()

    def _split_words(self, text):
        return [word for word in re.split(r"\s+", self._clean(text)) if word]

    def _join_non_empty(self, values, delimiter=" "):
        return delimiter.join([self._clean(value) for value in values if self._clean(value)])

    def _checksum(self, text):
        normalized = self._clean(text)
        return sum(ord(ch) for ch in normalized)

    def _pick_variant(self, options, seed_text):
        valid_options = [item for item in options if self._clean(item)]
        if not valid_options:
            return ""
        index = self._checksum(seed_text) % len(valid_options)
        return valid_options[index]

    def _extract_first_json_object(self, text):
        raw = self._clean(text)
        if not raw:
            return None

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        candidate = raw[start:end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            return None

    def _strip_system_phrases(self, text):
        cleaned = self._clean(text)
        if not cleaned:
            return ""

        result = cleaned
        for phrase in self.BANNED_SYSTEM_PHRASES:
            if phrase:
                result = re.sub(re.escape(phrase), "", result, flags=re.IGNORECASE)

        result = result.replace("..", ".").replace("،،", "،")
        result = re.sub(r"[|_/]+", " ", result)
        result = re.sub(r"\s+([،.!؟])", r"\1", result)
        result = re.sub(r"([،.!؟]){2,}", r"\1", result)
        return self._collapse_whitespace(result)

    def _translate_known_english(self, text):
        tokens = self._split_words(text)
        translated = []

        for token in tokens:
            stripped = re.sub(r"[^\w\u0600-\u06FF]+", "", token)
            lowered = stripped.lower()
            translated.append(self.ENGLISH_TO_ARABIC.get(lowered, token))

        return self._collapse_whitespace(" ".join(translated))

    def _unique_preserve_order(self, items):
        result = []
        seen = set()

        for item in items:
            normalized = self._clean(item)
            lowered = normalized.lower()
            if not normalized or lowered in seen:
                continue
            seen.add(lowered)
            result.append(normalized)

        return result

    def _truncate_safely(self, text, max_length):
        cleaned = self._clean(text)
        if len(cleaned) <= max_length:
            return cleaned
        shortened = cleaned[:max_length].rstrip(" ،.!؟")
        return shortened + "..."

    def _contains_long_raw_token(self, text):
        for token in self._split_words(text):
            plain = re.sub(r"[^\w\u0600-\u06FF]+", "", token)
            if not plain:
                continue
            if len(plain) > 24:
                return True
            if re.search(r"[A-Za-z]", plain) and re.search(r"\d", plain) and len(plain) > 10:
                return True
        return False

    def _count_occurrences(self, text, term):
        if not self._clean(text) or not self._clean(term):
            return 0
        return len(re.findall(re.escape(term), text, flags=re.IGNORECASE))

    def _remove_excess_name_repetition(self, text, product_name, max_occurrences=1):
        cleaned_text = self._clean(text)
        cleaned_name = self._clean(product_name)

        if not cleaned_text or not cleaned_name:
            return cleaned_text

        pattern = re.compile(re.escape(cleaned_name), flags=re.IGNORECASE)
        matches = list(pattern.finditer(cleaned_text))
        if len(matches) <= max_occurrences:
            return cleaned_text

        result_parts = []
        last_index = 0
        kept = 0

        for match in matches:
            result_parts.append(cleaned_text[last_index:match.start()])
            if kept < max_occurrences:
                result_parts.append(match.group(0))
                kept += 1
            last_index = match.end()

        result_parts.append(cleaned_text[last_index:])
        return self._collapse_whitespace("".join(result_parts))

    def _sanitize_text(self, text, product_name="", max_length=600):
        cleaned = self._strip_system_phrases(text)
        cleaned = self._translate_known_english(cleaned)
        cleaned = self._remove_excess_name_repetition(cleaned, product_name, max_occurrences=1)
        cleaned = re.sub(r"\s+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip(" -|،\n\t")
        cleaned = self._collapse_whitespace(cleaned.replace(" \n", "\n"))
        cleaned = self._truncate_safely(cleaned, max_length)
        return cleaned

    def _normalize_product_name(self, value):
        text = self._strip_system_phrases(value)
        text = self._translate_known_english(text)
        text = re.sub(r"[-–—]+", " ", text)

        tokens = self._split_words(text)
        cleaned_tokens = []

        for token in tokens:
            stripped = re.sub(r"[^\w\u0600-\u06FF]+", "", token)
            if not stripped:
                continue
            if len(stripped) > 16:
                continue
            if re.search(r"\d", stripped) and len(stripped) > 6:
                continue
            cleaned_tokens.append(stripped)

        cleaned_tokens = self._unique_preserve_order(cleaned_tokens)[:4]
        marketing_name = self._collapse_whitespace(" ".join(cleaned_tokens))
        if not marketing_name or self._contains_long_raw_token(marketing_name):
            return "اختيار عملي"

        return marketing_name

    def _normalize_category_text(self, value):
        text = self._strip_system_phrases(value)
        text = self._translate_known_english(text)
        text = re.sub(r"[_|/]+", " ", text)
        return self._collapse_whitespace(text)

    def _normalize_price_text(self, value):
        price_text = self._clean(value)
        return price_text or "السعر متوفر"

    def _normalize_keywords(self, values):
        items: List[str] = []

        if isinstance(values, list):
            items = [self._clean(item) for item in values if self._clean(item)]
        else:
            text = self._clean(values)
            if text:
                items = [part.strip() for part in text.replace("\n", ",").split(",") if part.strip()]

        cleaned_items = []
        seen = set()

        for item in items:
            normalized = self._strip_system_phrases(item)
            normalized = self._translate_known_english(normalized)
            normalized = re.sub(r"[#]+", "", normalized)
            normalized = self._collapse_whitespace(normalized)

            if not normalized:
                continue
            if self._contains_long_raw_token(normalized):
                continue

            lowered = normalized.lower()
            if lowered in seen:
                continue

            seen.add(lowered)
            cleaned_items.append(normalized)

        return ", ".join(cleaned_items[: self.MAX_KEYWORDS])

    def _normalize_hashtags(self, values):
        items: List[str] = []

        if isinstance(values, list):
            items = [self._clean(item) for item in values if self._clean(item)]
        else:
            text = self._clean(values)
            if text:
                items = text.replace("\n", " ").split()

        cleaned_tags = []
        seen = set()

        for item in items:
            normalized = self._strip_system_phrases(item)
            normalized = self._translate_known_english(normalized)
            normalized = normalized.replace(" ", "_").replace(",", "").replace("،", "")
            normalized = normalized.lstrip("#")
            normalized = re.sub(r"[^0-9A-Za-z_\u0600-\u06FF]+", "", normalized)

            if not normalized:
                continue
            if len(normalized) > 18:
                continue

            tag = "#" + normalized
            lowered = tag.lower()
            if lowered in seen:
                continue

            seen.add(lowered)
            cleaned_tags.append(tag)

        return " ".join(cleaned_tags[: self.MAX_HASHTAGS])

    def infer_strategy_hint(self, product_name, category_id):
        searchable_text = self._join_non_empty([product_name, category_id], delimiter=" ").lower()

        best_strategy = "general"
        best_score = 0

        for strategy_key, keywords in self.STRATEGY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                token = self._clean(keyword).lower()
                if token and token in searchable_text:
                    score += 1

            if score > best_score:
                best_score = score
                best_strategy = strategy_key

        return best_strategy

    def _build_strategy_profile(self, product_name, category_id, strategy_hint=""):
        hinted = self._clean(strategy_hint).lower()
        inferred = self.infer_strategy_hint(product_name, category_id)

        if hinted in self.STRATEGY_LIBRARY:
            strategy_key = hinted
        else:
            strategy_key = inferred if inferred in self.STRATEGY_LIBRARY else "general"

        return {
            "strategy_key": strategy_key,
            **self.STRATEGY_LIBRARY.get(strategy_key, self.STRATEGY_LIBRARY["general"]),
        }

    def _strengthen_cta(self, cta, strategy_profile, seed_text):
        short_forms = strategy_profile.get("cta_short_forms") or []
        fallback_cta = self._pick_variant(short_forms, seed_text + "|cta_short")
        candidate = self._sanitize_text(cta or fallback_cta, max_length=38)

        if not candidate:
            candidate = fallback_cta or "اطلبه الآن"

        return self._truncate_safely(candidate, 38)

    def build_content_brief(
        self,
        product_name,
        category_id,
        manual_price,
        final_media_url,
        final_media_status,
        strategy_hint="",
    ):
        clean_name = self._normalize_product_name(product_name)
        clean_category = self._normalize_category_text(category_id)
        clean_price = self._normalize_price_text(manual_price)
        clean_media_url = self._clean(final_media_url)
        clean_media_status = self._clean(final_media_status) or "final"

        strategy_profile = self._build_strategy_profile(
            product_name=clean_name,
            category_id=clean_category,
            strategy_hint=strategy_hint,
        )

        seed_text = self._join_non_empty(
            [clean_name, clean_category, clean_price, strategy_profile["strategy_key"]],
            delimiter="|",
        )

        return {
            "product_name": clean_name,
            "category_id": clean_category,
            "manual_price": clean_price,
            "final_media_present": bool(clean_media_url),
            "final_media_status": clean_media_status,
            "strategy_key": strategy_profile["strategy_key"],
            "strategy_name": strategy_profile["display_name"],
            "hook": self._pick_variant(strategy_profile["hook_templates"], seed_text + "|hook"),
            "title_template": self._pick_variant(strategy_profile["title_templates"], seed_text + "|title"),
            "pain_line": self._pick_variant(strategy_profile["pain_lines"], seed_text + "|pain"),
            "solution_line": self._pick_variant(strategy_profile["solution_lines"], seed_text + "|solution"),
            "desire_line": self._pick_variant(strategy_profile["desire_lines"], seed_text + "|desire"),
            "cta": self._strengthen_cta(
                self._pick_variant(strategy_profile["cta_short_forms"], seed_text + "|cta"),
                strategy_profile,
                seed_text,
            ),
            "keyword_candidates": [
                clean_name,
                clean_category,
                *strategy_profile["keyword_stems"],
            ],
            "hashtag_candidates": [
                clean_name.replace(" ", "_"),
                clean_category.replace(" ", "_"),
                *strategy_profile["hashtag_stems"],
            ],
        }

    def _render_template(self, template, brief):
        return self._clean(template).format(
            product_name=brief["product_name"],
            category=brief["category_id"] or "فئة متنوعة",
            price=brief["manual_price"],
        )

    def _compose_marketing_title(self, brief):
        title = self._render_template(brief["title_template"], brief)
        title = self._sanitize_text(title, product_name=brief["product_name"], max_length=self.MAX_TITLE_LENGTH)
        words = self._split_words(title)
        if len(words) > 7:
            title = self._truncate_safely(" ".join(words[:7]), self.MAX_TITLE_LENGTH)
        return title

    def _compose_marketing_description(self, brief):
        description = " ".join([
            self._render_template(brief["pain_line"], brief),
            self._render_template(brief["solution_line"], brief),
            self._render_template(brief["desire_line"], brief),
            f"بسعر {brief['manual_price']}.",
        ])
        return self._sanitize_text(
            description,
            product_name=brief["product_name"],
            max_length=self.MAX_DESCRIPTION_LENGTH,
        )

    def _compose_social_post(self, brief, seo_hashtags):
        lines = [
            self._sanitize_text(brief["hook"], product_name=brief["product_name"], max_length=85),
            self._sanitize_text(self._render_template(brief["solution_line"], brief), product_name=brief["product_name"], max_length=95),
            f"السعر: {brief['manual_price']}",
            self._sanitize_text(brief["cta"], product_name=brief["product_name"], max_length=38),
            seo_hashtags,
        ]
        return "\n".join([line for line in lines if self._clean(line)])

    def _condense_social_post(self, social_post, brief, seo_hashtags):
        raw_lines = re.split(r"[\n\r]+", self._clean(social_post))
        clean_lines = []

        for line in raw_lines:
            sanitized = self._sanitize_text(
                line,
                product_name=brief["product_name"],
                max_length=95,
            )
            if sanitized:
                clean_lines.append(sanitized)

        clean_lines = self._unique_preserve_order(clean_lines)

        if not clean_lines:
            clean_lines = [
                self._sanitize_text(brief["hook"], product_name=brief["product_name"], max_length=85),
                self._sanitize_text(self._render_template(brief["solution_line"], brief), product_name=brief["product_name"], max_length=95),
            ]

        condensed = [clean_lines[0]]

        benefit_line = None
        for line in clean_lines[1:]:
            if brief["cta"] not in line and not line.startswith("#") and not line.startswith("السعر:"):
                benefit_line = line
                break

        if not benefit_line:
            benefit_line = self._sanitize_text(
                self._render_template(brief["desire_line"], brief),
                product_name=brief["product_name"],
                max_length=85,
            )

        condensed.append(benefit_line)
        condensed.append(f"السعر: {brief['manual_price']}")
        condensed.append(self._sanitize_text(brief["cta"], product_name=brief["product_name"], max_length=38))
        condensed.append(seo_hashtags)

        final_post = "\n".join([line for line in condensed if self._clean(line)])
        return self._truncate_safely(final_post, self.MAX_SOCIAL_LENGTH)

    def _build_failed_payload(self, brief, stage, error_message, partial_payload=None):
        partial_payload = partial_payload or {}
        return {
            "status": "failed",
            "error_message": self._clean(error_message) or "Content generation failed",
            "marketing_title": self._clean(partial_payload.get("marketing_title")),
            "marketing_description": self._clean(partial_payload.get("marketing_description")),
            "social_post": self._clean(partial_payload.get("social_post")),
            "seo_keywords": self._clean(partial_payload.get("seo_keywords")),
            "seo_hashtags": self._clean(partial_payload.get("seo_hashtags")),
            "debug_stage": self._clean(stage),
            "debug_source": self._clean(partial_payload.get("debug_source")),
            "debug_strategy": self._clean(brief.get("strategy_key")),
            "debug_payload_keys": ",".join(sorted(list(partial_payload.keys()))) if isinstance(partial_payload, dict) else "",
        }

    def _build_ready_payload(self, brief, payload_dict, source):
        seo_keywords = self._normalize_keywords(payload_dict.get("seo_keywords"))
        seo_hashtags = self._normalize_hashtags(payload_dict.get("seo_hashtags"))

        marketing_title = self._clean(payload_dict.get("marketing_title")) or self._compose_marketing_title(brief)
        marketing_description = self._clean(payload_dict.get("marketing_description")) or self._compose_marketing_description(brief)
        social_post = self._clean(payload_dict.get("social_post")) or self._compose_social_post(brief, seo_hashtags)

        marketing_title = self._sanitize_text(marketing_title, product_name=brief["product_name"], max_length=self.MAX_TITLE_LENGTH)
        marketing_description = self._sanitize_text(marketing_description, product_name=brief["product_name"], max_length=self.MAX_DESCRIPTION_LENGTH)
        social_post = self._condense_social_post(social_post, brief, seo_hashtags)

        if not seo_keywords:
            seo_keywords = self._normalize_keywords(brief["keyword_candidates"])

        if not seo_hashtags:
            seo_hashtags = self._normalize_hashtags(brief["hashtag_candidates"])

        normalized = {
            "status": "ready",
            "error_message": "",
            "marketing_title": marketing_title,
            "marketing_description": marketing_description,
            "social_post": social_post,
            "seo_keywords": seo_keywords,
            "seo_hashtags": seo_hashtags,
            "debug_stage": "final_ready",
            "debug_source": source,
            "debug_strategy": brief.get("strategy_key", ""),
        }

        is_valid, reason = self._validate_quality(normalized, brief)
        if not is_valid:
            return self._build_failed_payload(
                brief=brief,
                stage="quality_gate",
                error_message=reason,
                partial_payload={**normalized, "debug_source": source},
            )

        return normalized

    def _validate_quality(self, payload, brief):
        title = self._clean(payload.get("marketing_title"))
        description = self._clean(payload.get("marketing_description"))
        social_post = self._clean(payload.get("social_post"))
        keywords = self._clean(payload.get("seo_keywords"))
        hashtags = self._clean(payload.get("seo_hashtags"))
        product_name = self._clean(brief.get("product_name"))
        cta = self._clean(brief.get("cta"))

        if not title:
            return False, "Quality gate rejected: MarketingTitle is empty"
        if not description:
            return False, "Quality gate rejected: MarketingDescription is empty"
        if not social_post:
            return False, "Quality gate rejected: SocialPost is empty"
        if not keywords:
            return False, "Quality gate rejected: SEOKeywords is empty"
        if not hashtags:
            return False, "Quality gate rejected: SEOHashtags is empty"

        if len(title) > self.MAX_TITLE_LENGTH:
            return False, "Quality gate rejected: MarketingTitle is too long"
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            return False, "Quality gate rejected: MarketingDescription is too long"
        if len(social_post) > self.MAX_SOCIAL_LENGTH:
            return False, "Quality gate rejected: SocialPost is too long"

        if self._contains_long_raw_token(title):
            return False, "Quality gate rejected: MarketingTitle contains raw long strings"
        if self._contains_long_raw_token(description):
            return False, "Quality gate rejected: MarketingDescription contains raw long strings"
        if self._contains_long_raw_token(social_post):
            return False, "Quality gate rejected: SocialPost contains raw long strings"
        if self._contains_long_raw_token(keywords):
            return False, "Quality gate rejected: SEOKeywords contain raw long strings"

        if product_name and self._count_occurrences(title, product_name) > 1:
            return False, "Quality gate rejected: product name repeats too much in title"
        if product_name and self._count_occurrences(description, product_name) > 2:
            return False, "Quality gate rejected: product name repeats too much in description"
        if product_name and self._count_occurrences(social_post, product_name) > 2:
            return False, "Quality gate rejected: product name repeats too much in SocialPost"

        if cta and cta not in social_post:
            return False, "Quality gate rejected: CTA missing from SocialPost"

        hashtag_list = [tag for tag in hashtags.split() if tag.startswith("#")]
        if len(hashtag_list) < self.MIN_HASHTAGS:
            return False, "Quality gate rejected: not enough hashtags"
        if len(hashtag_list) > self.MAX_HASHTAGS:
            return False, "Quality gate rejected: too many hashtags"

        return True, ""

    def _normalize_ai_payload(self, raw_payload):
        if not isinstance(raw_payload, dict):
            return {}

        return {
            "marketing_title": self._clean(raw_payload.get("marketing_title") or raw_payload.get("title")),
            "marketing_description": self._clean(raw_payload.get("marketing_description") or raw_payload.get("description")),
            "social_post": self._clean(raw_payload.get("social_post") or raw_payload.get("post")),
            "seo_keywords": raw_payload.get("seo_keywords") or raw_payload.get("keywords") or "",
            "seo_hashtags": raw_payload.get("seo_hashtags") or raw_payload.get("hashtags") or "",
        }

    def _build_ai_prompt(self, brief):
        keyword_candidates = ", ".join([self._clean(item) for item in brief["keyword_candidates"] if self._clean(item)])
        hashtag_candidates = " ".join(
            [("#" + self._clean(item).replace(" ", "_").lstrip("#")) for item in brief["hashtag_candidates"] if self._clean(item)]
        )

        return f"""
أنت Senior Arabic Direct Response Copywriter.
المطلوب كتابة retail-grade commercial copy عربي احترافي، قصير، بشري، مناسب لإعلان متجر حقيقي.

المدخلات:
- ProductName: {brief["product_name"]}
- CategoryID: {brief["category_id"]}
- ManualPrice: {brief["manual_price"]}
- Strategy: {brief["strategy_name"]}

اتبع هذا الهيكل:
- Hook: {brief["hook"]}
- Pain: {brief["pain_line"]}
- Solution: {brief["solution_line"]}
- Desire: {brief["desire_line"]}
- CTA: {brief["cta"]}

SEO hints:
- Keywords: {keyword_candidates}
- Hashtags: {hashtag_candidates}

قواعد صارمة:
- العنوان عربي وقصير
- لا تستخدم wording تشغيلي أو إداري
- لا تكرر اسم المنتج بشكل خام
- SocialPost قصيرة وتحويلية
- CTA واضحة
- لا تغيّر السعر
- أرجع JSON فقط:

{{
  "marketing_title": "...",
  "marketing_description": "...",
  "social_post": "...",
  "seo_keywords": ["...", "..."],
  "seo_hashtags": ["#...", "#..."]
}}
""".strip()

    def generate_publish_ready_content(
        self,
        product_name,
        category_id,
        manual_price,
        final_media_url,
        final_media_status,
        strategy_hint="",
        content_brief=None,
    ):
        brief = content_brief or self.build_content_brief(
            product_name=product_name,
            category_id=category_id,
            manual_price=manual_price,
            final_media_url=final_media_url,
            final_media_status=final_media_status,
            strategy_hint=strategy_hint,
        )

        deterministic_seed = {
            "marketing_title": self._compose_marketing_title(brief),
            "marketing_description": self._compose_marketing_description(brief),
            "social_post": "",
            "seo_keywords": self._normalize_keywords(brief["keyword_candidates"]),
            "seo_hashtags": self._normalize_hashtags(brief["hashtag_candidates"]),
        }
        deterministic_seed["social_post"] = self._compose_social_post(brief, deterministic_seed["seo_hashtags"])

        deterministic_ready = self._build_ready_payload(
            brief=brief,
            payload_dict=deterministic_seed,
            source="deterministic_fallback",
        )

        if not self.client:
            system_log.warning(
                f"SEOService fallback mode used for: {brief['product_name']} | strategy={brief['strategy_key']}"
            )
            return deterministic_ready

        prompt = self._build_ai_prompt(brief)

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
            )
            response_text = self._clean(getattr(response, "text", ""))
            parsed = self._extract_first_json_object(response_text)

            if not isinstance(parsed, dict):
                system_log.warning(
                    f"SEOService JSON parse fallback used for: {brief['product_name']} | strategy={brief['strategy_key']}"
                )
                if deterministic_ready.get("status") == "ready":
                    return deterministic_ready
                return self._build_failed_payload(
                    brief=brief,
                    stage="json_parse",
                    error_message="AI response did not return valid JSON and fallback also failed",
                    partial_payload=deterministic_ready,
                )

            ai_payload = self._normalize_ai_payload(parsed)
            ready_payload = self._build_ready_payload(
                brief=brief,
                payload_dict=ai_payload,
                source="ai_payload",
            )

            if ready_payload.get("status") == "ready":
                system_log.info(
                    f"✅ Retail-grade content generated for: {brief['product_name']} | strategy={brief['strategy_key']}"
                )
                return ready_payload

            if deterministic_ready.get("status") == "ready":
                system_log.warning(
                    f"SEOService AI payload rejected by gate; deterministic fallback used for: {brief['product_name']}"
                )
                return deterministic_ready

            return self._build_failed_payload(
                brief=brief,
                stage="quality_gate",
                error_message=ready_payload.get("error_message") or deterministic_ready.get("error_message") or "Content generation failed",
                partial_payload={
                    **ai_payload,
                    "debug_source": "ai_and_fallback_failed",
                    "seo_keywords": ai_payload.get("seo_keywords", ""),
                    "seo_hashtags": ai_payload.get("seo_hashtags", ""),
                },
            )

        except Exception as e:
            system_log.error(
                f"❌ SEOService generate_publish_ready_content error for {brief['product_name']}: {e}"
            )

            if deterministic_ready.get("status") == "ready":
                return deterministic_ready

            return self._build_failed_payload(
                brief=brief,
                stage="exception",
                error_message=str(e),
                partial_payload=deterministic_ready,
            )

    def generate_yemeni_post(self, title: str, price_usd: float) -> dict:
        title_text = self._clean(title)

        try:
            price_value = float(price_usd)
        except Exception:
            price_value = 0.0

        fallback = {
            "price_sar": round(price_value * 3.75, 2),
            "price_yer": round(round(price_value * 3.75, 2) * 139.8, 2),
            "social_post": f"جديدنا: {title_text or 'منتج مميز'}",
        }

        if not self.client:
            return fallback

        try:
            prompt = f"""
اكتب بوست تسويقي جذاب لمنتج {title_text} لجمهور يمني.
السعر التقديري بالدولار: {price_value}.
أخرج النص فقط بدون شرح إضافي.
""".strip()

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
            )

            social_post = self._clean(getattr(response, "text", "")) or fallback["social_post"]

            system_log.info(f"✅ SEO generated for: {title_text}")
            return {
                "price_sar": fallback["price_sar"],
                "price_yer": fallback["price_yer"],
                "social_post": social_post,
            }
        except Exception as e:
            system_log.error(f"❌ SEO Error: {e}")
            return fallback
