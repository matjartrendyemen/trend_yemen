import json
import os
import re

from google import genai
from monitoring.logger import system_log


class SEOService:
    STRATEGY_KEYWORDS = {
        "health_pain_relief": [
            "pain", "relief", "health", "massage", "therapy", "back", "neck", "knee",
            "joint", "posture", "medical", "wellness", "heat", "pain relief",
            "muscle", "recovery", "صحة", "ألم", "آلام", "ظهر", "رقبة", "ركبة",
            "مفاصل", "مساج", "علاج", "حراري", "استشفاء", "عضلات",
        ],
        "beauty": [
            "beauty", "skin", "skincare", "hair", "face", "cosmetic", "makeup",
            "glow", "serum", "cleanser", "beauty care", "جمال", "بشرة", "شعر",
            "عناية", "سيروم", "مكياج", "تفتيح", "نضارة", "إشراقة",
        ],
        "home_convenience": [
            "home", "kitchen", "organizer", "storage", "clean", "cleaning", "vacuum",
            "household", "smart home", "convenience", "راحة منزلية", "منزل", "مطبخ",
            "ترتيب", "تنظيم", "تنظيف", "مريّح", "عملي", "منزلي",
        ],
        "gadget": [
            "gadget", "device", "smart", "tech", "charger", "wireless", "portable",
            "usb", "led", "holder", "accessory", "electronic", "أداة ذكية", "تقنية",
            "جهاز", "إلكتروني", "ذكي", "شاحن", "محمول", "عملي",
        ],
        "fitness": [
            "fitness", "sport", "training", "workout", "exercise", "gym", "running",
            "yoga", "resistance", "active", "رياضة", "لياقة", "تمرين", "تدريب",
            "جيم", "نشاط", "مقاومة", "تمارين",
        ],
        "kids_family": [
            "kids", "kid", "baby", "child", "family", "children", "mother", "parent",
            "school", "toys", "feeding", "safety", "أطفال", "طفل", "بيبي", "رضيع",
            "عائلة", "أسرة", "أم", "مدرسة", "ألعاب", "أمان",
        ],
    }

    STRATEGY_LIBRARY = {
        "health_pain_relief": {
            "display_name": "Health / Pain relief",
            "tone_rules": "عربي راقٍ، مطمئن، مقنع، عملي، بعيد عن المبالغة واللغة الطبية الثقيلة.",
            "instagram_format": "Hook -> Relief -> Desire -> CTA -> Hashtags",
            "hook_templates": [
                "إذا كان الانزعاج اليومي يأخذ من راحتك، فهذا النوع من الحلول يصنع فرقًا واضحًا.",
                "الراحة الحقيقية تبدأ عندما تختار ما يخفف عنك العبء اليومي.",
                "حين يتحول التعب إلى عادة يومية، يصبح الحل العملي ضرورة لا رفاهية.",
                "امنح يومك إحساسًا أخف وراحة أوضح من أول استخدام.",
            ],
            "pain_lines": [
                "كثير من الناس يتعاملون يوميًا مع توتر أو إجهاد يستهلك الراحة والتركيز.",
                "الانزعاج المتكرر يجعل أبسط المهام أثقل مما يجب.",
                "حين يطول الإحساس بعدم الراحة، يبدأ أثره على جودة اليوم كله.",
            ],
            "solution_lines": [
                "{product_name} يقدم طريقة أكثر راحة وعملية لدعم يومك بدون تعقيد.",
                "{product_name} يساعدك على جعل الاستخدام اليومي أكثر راحة وانسيابية.",
                "{product_name} صُمم ليمنحك تجربة مريحة وواضحة الأثر من الاستخدام الأول.",
            ],
            "desire_lines": [
                "النتيجة هي إحساس أفضل بالحركة وراحة أكثر في تفاصيل يومك.",
                "الفرق الحقيقي أنه يضيف إلى روتينك راحة تشعر بها وثقة أكبر في الاستخدام.",
                "هذا النوع من الاختيارات يمنحك هدوءًا أكبر وقدرة أفضل على الاستمرار في يومك.",
            ],
            "cta_templates": [
                "اطلبه الآن وابدأ فرق الراحة من اليوم.",
                "جرّبه اليوم وخفف العبء عن يومك بخطوة بسيطة.",
                "ابدأ من الآن بخيار يمنحك راحة أوضح كل يوم.",
            ],
            "title_templates": [
                "{product_name} | راحة أوضح ليوم أخف",
                "{product_name} | حل عملي للراحة اليومية",
                "{product_name} | فرق تشعر به مع كل استخدام",
            ],
            "keyword_stems": [
                "راحة يومية", "تخفيف الانزعاج", "حل عملي", "استخدام مريح", "راحة أفضل", "اختيار ذكي",
            ],
            "hashtag_stems": [
                "راحة", "صحة", "يومك_أخف", "حل_عملي", "اختيار_أفضل",
            ],
        },
        "beauty": {
            "display_name": "Beauty",
            "tone_rules": "عربي أنيق، واثق، جمالي، غير مبتذل، يركز على الإشراقة والثقة.",
            "instagram_format": "Hook -> Beauty benefit -> Confidence angle -> CTA -> Hashtags",
            "hook_templates": [
                "الفرق في الإطلالة يبدأ من العناية التي تعكس حضورك الحقيقي.",
                "حين تختارين العناية الصحيحة، يظهر أثرها في التفاصيل الجميلة.",
                "الإشراقة ليست صدفة، بل نتيجة اختيار يمنحك إحساسًا أجمل بنفسك.",
                "الجمال الأجمل هو الذي يبدو طبيعيًا ويترك أثرًا واثقًا.",
            ],
            "pain_lines": [
                "روتين العناية العادي لا يمنح دائمًا النتيجة التي تشعرين معها بالرضا الكامل.",
                "أحيانًا يكون المطلوب لمسة مدروسة لا تغييرًا مبالغًا فيه.",
                "حين تغيب النتيجة الواضحة، يصبح الجمال أقل تعبيرًا عن حضورك الحقيقي.",
            ],
            "solution_lines": [
                "{product_name} يمنحك تجربة عناية أجمل وأكثر نعومة في الإحساس والنتيجة.",
                "{product_name} يضيف إلى روتينك لمسة أنيقة تعزز الجمال الطبيعي بثقة.",
                "{product_name} صُمم ليمنحك حضورًا أجمل دون تكلف أو مبالغة.",
            ],
            "desire_lines": [
                "النتيجة هي إشراقة أوضح وثقة أكثر في كل إطلالة.",
                "هذا النوع من المنتجات يجعل العناية اليومية أكثر متعة وأقرب للنتيجة التي ترغبين بها.",
                "يعطيك إحساسًا بالجمال المرتب والحضور الأنيق في كل مرة.",
            ],
            "cta_templates": [
                "امنحي نفسك لمسة أجمل اليوم.",
                "اختاري الجمال الذي يليق بك وابدئي من الآن.",
                "دلّلي نفسك بخيار يمنحك إشراقة وثقة أكثر.",
            ],
            "title_templates": [
                "{product_name} | لمسة جمال بثقة أعلى",
                "{product_name} | إشراقة أجمل كل يوم",
                "{product_name} | عناية تبرز جمالك الطبيعي",
            ],
            "keyword_stems": [
                "عناية يومية", "إشراقة", "ثقة", "جمال", "روتين عناية", "نتيجة أنيقة",
            ],
            "hashtag_stems": [
                "جمال", "عناية", "إشراقة", "ثقة", "روتين_جمال",
            ],
        },
        "home_convenience": {
            "display_name": "Home convenience",
            "tone_rules": "عربي عملي، ذكي، مرتب، يركز على السهولة وتوفير الوقت والجهد.",
            "instagram_format": "Hook -> Convenience benefit -> Home angle -> CTA -> Hashtags",
            "hook_templates": [
                "الأشياء التي تجعل البيت أسهل هي غالبًا الأفضل قيمة في الاستخدام اليومي.",
                "حين تصبح التفاصيل المنزلية أبسط، يصبح يومك كله أخف.",
                "الحل العملي هو الذي يختصر عليك الجهد من أول مرة.",
                "من الفوضى أو الإزعاج إلى راحة أوضح بخطوة واحدة.",
            ],
            "pain_lines": [
                "التفاصيل الصغيرة في البيت قد تستهلك وقتًا وجهدًا أكثر مما تستحق.",
                "حين يكون الروتين اليومي مرهقًا، تصبح الحلول العملية أكثر أهمية من أي وقت.",
                "الإزعاج المتكرر داخل البيت يجعل أبسط المهام أقل راحة مما يجب.",
            ],
            "solution_lines": [
                "{product_name} صُمم ليجعل الاستخدام اليومي أسهل وأكثر ترتيبًا وراحة.",
                "{product_name} يمنحك طريقة أذكى للتعامل مع الروتين اليومي داخل البيت.",
                "{product_name} يضيف إلى يومك سهولة واضحة ويوفر عليك جهدًا متكررًا.",
            ],
            "desire_lines": [
                "النتيجة هي يوم أكثر ترتيبًا، وجهد أقل، وراحة أكبر في التفاصيل.",
                "هذا النوع من الخيارات يعطي البيت إحساسًا أفضل بالسهولة والتنظيم.",
                "كل استخدام يمنحك شعورًا أن يومك صار أبسط وأخف.",
            ],
            "cta_templates": [
                "خففي الجهد وخلّي يومك أسهل من الآن.",
                "اختاري الحل العملي الذي يريحك كل يوم.",
                "ابدئي اليوم بخيار يختصر عليك الوقت والجهد.",
            ],
            "title_templates": [
                "{product_name} | راحة أكثر في يومك",
                "{product_name} | حل منزلي عملي وذكي",
                "{product_name} | سهولة يومية بلمسة ذكية",
            ],
            "keyword_stems": [
                "راحة منزلية", "تنظيم", "حل عملي", "توفير وقت", "سهولة يومية", "استخدام ذكي",
            ],
            "hashtag_stems": [
                "منزل", "راحة_منزلية", "تنظيم", "حل_عملي", "يومك_أسهل",
            ],
        },
        "gadget": {
            "display_name": "Gadget",
            "tone_rules": "عربي حديث، واثق، سريع الإيقاع، يركز على الذكاء والعملية والقيمة.",
            "instagram_format": "Hook -> Smart value -> Practical angle -> CTA -> Hashtags",
            "hook_templates": [
                "الحل الأذكى هو الذي يختصر عليك الوقت من أول استخدام.",
                "أحيانًا أداة واحدة عملية تغيّر طريقة يومك بالكامل.",
                "حين يجتمع الذكاء والسهولة في منتج واحد، يصبح القرار أسهل.",
                "التفاصيل التقنية الأفضل هي التي تشعر بقيمتها فورًا.",
            ],
            "pain_lines": [
                "الأدوات التقليدية لا تمنح دائمًا السرعة أو السهولة التي يحتاجها يومك.",
                "حين يكون الاستخدام معقدًا، تضيع القيمة مهما بدا المنتج جيدًا.",
                "الروتين الأسرع يحتاج حلولًا أذكى لا خطوات إضافية.",
            ],
            "solution_lines": [
                "{product_name} يقدم تجربة عملية وذكية تمنحك أداءً أسهل وأكثر سلاسة.",
                "{product_name} يجمع بين العملية والسرعة بطريقة تناسب الاستخدام اليومي.",
                "{product_name} صُمم ليضيف قيمة واضحة ونتيجة ملموسة من أول تجربة.",
            ],
            "desire_lines": [
                "النتيجة هي استخدام أسرع، إحساس أفضل بالعملية، وراحة أكبر في التفاصيل.",
                "هذا النوع من المنتجات يمنحك شعورًا أنك اخترت الحل الأذكى فعلًا.",
                "الفائدة الحقيقية هنا أنك تحصل على قيمة واضحة بدون تعقيد.",
            ],
            "cta_templates": [
                "جرّب الحل الأذكى اليوم.",
                "ابدأ تجربة أكثر عملية من الآن.",
                "اختر الأداة التي تمنحك قيمة أوضح من أول استخدام.",
            ],
            "title_templates": [
                "{product_name} | الحل الأذكى ليومك",
                "{product_name} | تقنية عملية بشكل أبسط",
                "{product_name} | أداء ذكي بقيمة أعلى",
            ],
            "keyword_stems": [
                "أداة ذكية", "تقنية عملية", "حل سريع", "منتج إلكتروني", "أداء عملي", "قيمة واضحة",
            ],
            "hashtag_stems": [
                "تقنية", "أداة_ذكية", "حل_أذكى", "عملي", "منتجات_تقنية",
            ],
        },
        "fitness": {
            "display_name": "Fitness",
            "tone_rules": "عربي محفّز، منظم، مشجع على الالتزام والتقدّم، بعيد عن الصراخ التسويقي.",
            "instagram_format": "Hook -> Motivation -> Progress angle -> CTA -> Hashtags",
            "hook_templates": [
                "النتيجة تبدأ من قرار صغير تلتزم به كل يوم.",
                "إذا كنت تريد بداية أقوى، ابدأ بأداة تدعمك فعليًا.",
                "من الكسل إلى النشاط، الفرق يبدأ باختيار صحيح.",
                "كل تقدّم واضح يحتاج بداية عملية ومستمرة.",
            ],
            "pain_lines": [
                "أكبر تحدٍ في أي بداية ليس الحماس فقط، بل الاستمرار بثبات.",
                "حين يغيب التنظيم أو الدعم العملي، تصبح البداية أصعب مما يجب.",
                "الرغبة وحدها لا تكفي إذا لم يكن معك ما يساعدك على الالتزام.",
            ],
            "solution_lines": [
                "{product_name} يساعدك على جعل روتينك أكثر التزامًا ووضوحًا من البداية.",
                "{product_name} يضيف إلى يومك عاملًا عمليًا يشجّعك على الاستمرار.",
                "{product_name} صُمم ليمنحك بداية أسهل وشعورًا أفضل بالتقدّم.",
            ],
            "desire_lines": [
                "النتيجة هي إحساس أقوى بالنشاط وخطوة أوضح نحو هدفك.",
                "هذا النوع من المنتجات يجعل الالتزام أسهل والرحلة أكثر واقعية.",
                "يعطيك دفعة عملية نحو عادة أفضل ونتيجة أقرب مما تتوقع.",
            ],
            "cta_templates": [
                "ابدأ التغيير من الآن.",
                "خذ أول خطوة اليوم وخلّي الالتزام أسهل.",
                "جرّبه اليوم وابدأ رحلة نشاط أقوى.",
            ],
            "title_templates": [
                "{product_name} | بداية أقوى لنتيجة أوضح",
                "{product_name} | خيار عملي لنشاطك اليومي",
                "{product_name} | التزام أسهل ونتيجة أقرب",
            ],
            "keyword_stems": [
                "لياقة", "نشاط", "تمرين", "التزام", "نتيجة أفضل", "روتين رياضي",
            ],
            "hashtag_stems": [
                "لياقة", "نشاط", "ابدأ_الآن", "تمرين", "نتيجة_أفضل",
            ],
        },
        "kids_family": {
            "display_name": "Kids / family",
            "tone_rules": "عربي مطمئن، عائلي، عملي، يركز على الراحة اليومية والثقة والسهولة.",
            "instagram_format": "Hook -> Family benefit -> Trust angle -> CTA -> Hashtags",
            "hook_templates": [
                "راحة العائلة تبدأ من التفاصيل التي تسهّل اليوم كله.",
                "كل اختيار عملي للأسرة ينعكس على راحة البيت بشكل واضح.",
                "حين يكون المنتج مناسبًا للعائلة، تشعر بالفرق في كل يوم.",
                "السهولة، الراحة، والاطمئنان... هذا ما تحتاجه الأسرة فعلًا.",
            ],
            "pain_lines": [
                "تفاصيل اليوم العائلي قد تصبح مرهقة عندما لا تكون الحلول عملية بما يكفي.",
                "حين تتكرر المهام نفسها كل يوم، تصبح الراحة والسهولة مطلبًا أساسيًا.",
                "كل شيء يخفف الضغط عن الأسرة يصنع فرقًا أكبر مما يبدو.",
            ],
            "solution_lines": [
                "{product_name} خيار عملي يساعد على جعل اليوم أكثر راحة وسهولة.",
                "{product_name} يمنح الأسرة طريقة أسهل للتعامل مع التفاصيل اليومية.",
                "{product_name} صُمم ليضيف راحة أوضح إلى الروتين اليومي للعائلة.",
            ],
            "desire_lines": [
                "النتيجة هي إحساس أفضل بالراحة والتنظيم والثقة في الاختيار.",
                "هذا النوع من المنتجات يجعل اليوم العائلي أخف وأكثر هدوءًا.",
                "يعطيك شعورًا أن التفاصيل اليومية أصبحت أسهل وأكثر ترتيبًا.",
            ],
            "cta_templates": [
                "وفّر راحة أكثر لك ولعائلتك من اليوم.",
                "اختر الحل العملي الذي يسهّل يوم الأسرة.",
                "اجعل يومكم أسهل بخيار مناسب من الآن.",
            ],
            "title_templates": [
                "{product_name} | راحة أكثر لك ولعائلتك",
                "{product_name} | اختيار عملي للأسرة",
                "{product_name} | سهولة يومية لكل البيت",
            ],
            "keyword_stems": [
                "راحة الأسرة", "منتج عائلي", "سهولة يومية", "للأطفال", "للعائلة", "حل عملي",
            ],
            "hashtag_stems": [
                "عائلة", "راحة_الأسرة", "أطفال", "سهولة_يومية", "حل_عملي",
            ],
        },
        "general": {
            "display_name": "General commercial",
            "tone_rules": "عربي تجاري راقٍ، مختصر، واثق، مقنع، غير آلي.",
            "instagram_format": "Hook -> Value -> Selling angle -> CTA -> Hashtags",
            "hook_templates": [
                "هناك منتجات عادية، وهناك منتجات تصنع فرقًا فعليًا في الاستخدام.",
                "الاختيار الذكي هو الذي يمنحك فائدة واضحة من أول مرة.",
                "إذا كنت تبحث عن قيمة عملية وشكل مقنع، فهذا النوع يستحق الانتباه.",
                "الفرق الحقيقي يظهر عندما يجتمع الذكاء والنتيجة في منتج واحد.",
            ],
            "pain_lines": [
                "كثير من الخيارات تبدو جيدة، لكن القليل منها يمنحك قيمة واضحة فعلًا.",
                "المنتج الجيد ليس مجرد شكل؛ بل فائدة تشعر بها في الاستخدام اليومي.",
                "حين يكون الاختيار غير موفق، تضيع القيمة مهما بدا المنتج جذابًا.",
            ],
            "solution_lines": [
                "{product_name} يجمع بين العملية والقيمة بشكل يسهّل قرار الشراء.",
                "{product_name} يقدم تجربة استخدام مريحة وفائدة واضحة من البداية.",
                "{product_name} صُمم ليكون اختيارًا أذكى لمن يبحث عن نتيجة مقنعة.",
            ],
            "desire_lines": [
                "النتيجة هي منتج يعطيك إحساسًا أفضل بالاختيار والقيمة.",
                "هذا النوع من المنتجات يجعل قرار الشراء أكثر راحة وثقة.",
                "يعطيك سببًا واضحًا للاقتناء بدل مجرد الانبهار المؤقت.",
            ],
            "cta_templates": [
                "اطلبه الآن واستمتع بقيمة أوضح من أول تجربة.",
                "جرّبه اليوم واختر المنتج الذي يصنع فرقًا فعلًا.",
                "ابدأ بتجربة أذكى واختيار أكثر إقناعًا.",
            ],
            "title_templates": [
                "{product_name} | قيمة أوضح واختيار أذكى",
                "{product_name} | منتج عملي يستحق التجربة",
                "{product_name} | فرق واضح في الاستخدام اليومي",
            ],
            "keyword_stems": [
                "منتج عملي", "قيمة واضحة", "اختيار ذكي", "منتج مميز", "سهولة استخدام", "أفضل اختيار",
            ],
            "hashtag_stems": [
                "منتجات_مميزة", "اختيار_ذكي", "قيمة", "عملي", "اختيار_أفضل",
            ],
        },
    }

    BANNED_SYSTEM_PHRASES = [
        "trend yemen",
        "selected",
        "approved",
        "ready",
        "finalized",
        "home",
        "جاهز للمراجعة",
        "الحالة الإعلامية",
        "داخل المتجر",
        "داخل متجر",
        "قابل للمراجعة",
        "preview",
        "raw",
        "system",
    ]

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

    def _normalize_product_name(self, value):
        text = self._clean(value)
        text = re.sub(r"[|_/]+", " ", text)
        text = self._collapse_whitespace(text)

        parts = text.split()
        if len(parts) > 8:
            text = " ".join(parts[:8])

        return text or "منتج مميز"

    def _normalize_category_text(self, value):
        text = self._clean(value)
        text = re.sub(r"[_|/]+", " ", text)
        return self._collapse_whitespace(text)

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

    def _strip_system_phrases(self, text):
        cleaned = self._clean(text)
        if not cleaned:
            return ""

        result = cleaned
        for phrase in self.BANNED_SYSTEM_PHRASES:
            pattern = re.compile(rf"\b{re.escape(phrase)}\b", flags=re.IGNORECASE)
            result = pattern.sub("", result)

        result = result.replace("..", ".")
        result = result.replace("،،", "،")
        result = re.sub(r"\s+([،.!؟])", r"\1", result)
        result = re.sub(r"([،.!؟]){2,}", r"\1", result)
        return self._collapse_whitespace(result)

    def _limit_product_name_repetition(self, text, product_name, max_occurrences=1):
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

        for idx, match in enumerate(matches):
            result_parts.append(cleaned_text[last_index:match.start()])
            if idx < max_occurrences:
                result_parts.append(match.group(0))
            last_index = match.end()

        result_parts.append(cleaned_text[last_index:])
        result = "".join(result_parts)
        return self._collapse_whitespace(result)

    def _sanitize_text(self, text, product_name="", max_length=600):
        cleaned = self._strip_system_phrases(text)
        cleaned = self._limit_product_name_repetition(cleaned, product_name, max_occurrences=1)
        cleaned = re.sub(r"\s+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip(" -|،\n\t")
        cleaned = self._collapse_whitespace(cleaned.replace(" \n", "\n")).replace(" \n", "\n")

        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rstrip(" ،.!؟") + "..."

        return cleaned

    def _normalize_keywords(self, values):
        items = []

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
            normalized = re.sub(r"[#]+", "", normalized)
            normalized = self._collapse_whitespace(normalized)
            if not normalized:
                continue

            lowered = normalized.lower()
            if lowered in seen:
                continue

            seen.add(lowered)
            cleaned_items.append(normalized)

        return ", ".join(cleaned_items[:8])

    def _normalize_hashtags(self, values):
        items = []

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
            normalized = normalized.replace(" ", "_").replace(",", "").replace("،", "")
            normalized = normalized.lstrip("#")
            normalized = re.sub(r"[^0-9A-Za-z_\u0600-\u06FF]+", "", normalized)

            if not normalized:
                continue

            tag = "#" + normalized
            lowered = tag.lower()

            if lowered in seen:
                continue

            seen.add(lowered)
            cleaned_tags.append(tag)

        return " ".join(cleaned_tags[:8])

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

    def _normalize_price_text(self, value):
        price_text = self._clean(value)
        return price_text or "السعر متوفر عند الطلب"

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

        hook = self._pick_variant(strategy_profile["hook_templates"], seed_text + "|hook")
        pain_line = self._pick_variant(strategy_profile["pain_lines"], seed_text + "|pain")
        solution_line = self._pick_variant(strategy_profile["solution_lines"], seed_text + "|solution")
        desire_line = self._pick_variant(strategy_profile["desire_lines"], seed_text + "|desire")
        cta = self._pick_variant(strategy_profile["cta_templates"], seed_text + "|cta")
        title_template = self._pick_variant(strategy_profile["title_templates"], seed_text + "|title")

        keyword_candidates = [
            clean_name,
            clean_category,
            strategy_profile["display_name"],
            *strategy_profile["keyword_stems"],
        ]

        hashtag_candidates = [
            clean_name.replace(" ", "_"),
            clean_category.replace(" ", "_"),
            *strategy_profile["hashtag_stems"],
        ]

        return {
            "product_name": clean_name,
            "category_id": clean_category,
            "manual_price": clean_price,
            "final_media_present": bool(clean_media_url),
            "final_media_status": clean_media_status,
            "strategy_key": strategy_profile["strategy_key"],
            "strategy_name": strategy_profile["display_name"],
            "tone_rules": strategy_profile["tone_rules"],
            "instagram_format": strategy_profile["instagram_format"],
            "hook": hook,
            "pain_line": pain_line,
            "solution_line": solution_line,
            "desire_line": desire_line,
            "cta": cta,
            "title_template": title_template,
            "keyword_candidates": keyword_candidates,
            "hashtag_candidates": hashtag_candidates,
        }

    def _render_template(self, template, brief):
        return self._clean(template).format(
            product_name=brief["product_name"],
            category=brief["category_id"] or "فئة متنوعة",
            price=brief["manual_price"],
        )

    def _compose_marketing_title(self, brief):
        title = self._render_template(brief["title_template"], brief)
        return self._sanitize_text(title, product_name=brief["product_name"], max_length=90)

    def _compose_marketing_description(self, brief):
        description = " ".join([
            self._render_template(brief["pain_line"], brief),
            self._render_template(brief["solution_line"], brief),
            self._render_template(brief["desire_line"], brief),
            f"بسعر {brief['manual_price']}.",
        ])
        return self._sanitize_text(description, product_name=brief["product_name"], max_length=320)

    def _compose_social_post(self, brief, seo_hashtags):
        lines = [
            self._sanitize_text(brief["hook"], product_name=brief["product_name"], max_length=120),
            self._sanitize_text(self._render_template(brief["solution_line"], brief), product_name=brief["product_name"], max_length=160),
            self._sanitize_text(self._render_template(brief["desire_line"], brief), product_name=brief["product_name"], max_length=160),
            f"السعر: {brief['manual_price']}",
            self._sanitize_text(brief["cta"], product_name=brief["product_name"], max_length=120),
            seo_hashtags,
        ]
        return "\n".join([line for line in lines if self._clean(line)])

    def _build_deterministic_payload(self, brief):
        seo_keywords = self._normalize_keywords(brief["keyword_candidates"])
        seo_hashtags = self._normalize_hashtags(brief["hashtag_candidates"])

        marketing_title = self._compose_marketing_title(brief)
        marketing_description = self._compose_marketing_description(brief)
        social_post = self._compose_social_post(brief, seo_hashtags)

        return {
            "marketing_title": marketing_title,
            "marketing_description": marketing_description,
            "social_post": social_post,
            "seo_keywords": seo_keywords,
            "seo_hashtags": seo_hashtags,
            "status": "ready",
            "error_message": "",
        }

    def _build_ai_prompt(self, brief):
        keyword_candidates = ", ".join([self._clean(item) for item in brief["keyword_candidates"] if self._clean(item)])
        hashtag_candidates = " ".join(
            [("#" + self._clean(item).replace(" ", "_").lstrip("#")) for item in brief["hashtag_candidates"] if self._clean(item)]
        )

        return f"""
أنت Senior Arabic Direct Response Copywriter.
المطلوب كتابة commercial copy عربي احترافي جدًا، يبدو بشريًا ومقنعًا ومناسبًا للنشر المباشر.

الاستراتيجية:
- Strategy: {brief["strategy_name"]}
- Tone Rules: {brief["tone_rules"]}
- Instagram Format: {brief["instagram_format"]}

المدخلات:
- ProductName: {brief["product_name"]}
- CategoryID: {brief["category_id"]}
- ManualPrice: {brief["manual_price"]}
- FinalMediaPresent: {"yes" if brief["final_media_present"] else "no"}
- FinalMediaStatus: {brief["final_media_status"]}

المحاور التجارية:
- Hook: {brief["hook"]}
- Pain: {brief["pain_line"]}
- Solution: {brief["solution_line"]}
- Desire: {brief["desire_line"]}
- CTA: {brief["cta"]}

SEO hints:
- Keywords: {keyword_candidates}
- Hashtags: {hashtag_candidates}

قواعد صارمة:
- لا تستخدم wording تشغيلي أو إداري أو آلي
- لا تستخدم: selected / approved / ready / finalized / Trend Yemen / home
- لا تكرر اسم المنتج بشكل خام أو ممل
- اجعل MarketingTitle قصيرة وقوية وبيعية
- اجعل MarketingDescription مقنعة وواضحة الزاوية
- اجعل SocialPost بصيغة تحويلية حقيقية: Hook ثم benefit ثم angle ثم CTA ثم hashtags
- لا تغيّر السعر
- لا تضف أي شرح خارج JSON

أعد JSON فقط:
{{
  "marketing_title": "...",
  "marketing_description": "...",
  "social_post": "...",
  "seo_keywords": ["...", "..."],
  "seo_hashtags": ["#...", "#..."]
}}
""".strip()

    def _sanitize_payload(self, payload, brief):
        marketing_title = self._sanitize_text(
            payload.get("marketing_title", ""),
            product_name=brief["product_name"],
            max_length=90,
        )
        marketing_description = self._sanitize_text(
            payload.get("marketing_description", ""),
            product_name=brief["product_name"],
            max_length=320,
        )
        social_post = self._clean(payload.get("social_post", ""))
        seo_keywords = self._normalize_keywords(payload.get("seo_keywords"))
        seo_hashtags = self._normalize_hashtags(payload.get("seo_hashtags"))

        if not marketing_title:
            marketing_title = self._compose_marketing_title(brief)

        if not marketing_description:
            marketing_description = self._compose_marketing_description(brief)

        if not social_post:
            social_post = self._compose_social_post(brief, seo_hashtags)

        social_post = self._sanitize_text(
            social_post,
            product_name=brief["product_name"],
            max_length=700,
        )

        if brief["cta"] not in social_post:
            social_post = "\n".join([social_post, brief["cta"]])

        if not seo_hashtags:
            seo_hashtags = self._normalize_hashtags(brief["hashtag_candidates"])

        if seo_hashtags not in social_post:
            social_post = "\n".join([social_post, seo_hashtags])

        return {
            "marketing_title": marketing_title,
            "marketing_description": marketing_description,
            "social_post": social_post,
            "seo_keywords": seo_keywords or self._normalize_keywords(brief["keyword_candidates"]),
            "seo_hashtags": seo_hashtags,
            "status": "ready",
            "error_message": "",
        }

    def _merge_ai_payload_with_brief(self, ai_payload, brief, fallback):
        if not isinstance(ai_payload, dict):
            return fallback

        merged = {
            "marketing_title": ai_payload.get("marketing_title", fallback["marketing_title"]),
            "marketing_description": ai_payload.get("marketing_description", fallback["marketing_description"]),
            "social_post": ai_payload.get("social_post", fallback["social_post"]),
            "seo_keywords": ai_payload.get("seo_keywords", fallback["seo_keywords"]),
            "seo_hashtags": ai_payload.get("seo_hashtags", fallback["seo_hashtags"]),
            "status": "ready",
            "error_message": "",
        }

        return self._sanitize_payload(merged, brief)

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

        fallback = self._build_deterministic_payload(brief)

        if not self.client:
            system_log.warning(
                f"SEOService fallback mode used for: {brief['product_name']} | strategy={brief['strategy_key']}"
            )
            return fallback

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
                return fallback

            merged = self._merge_ai_payload_with_brief(parsed, brief, fallback)
            system_log.info(
                f"✅ Commercial content generated for: {brief['product_name']} | strategy={brief['strategy_key']}"
            )
            return merged

        except Exception as e:
            system_log.error(
                f"❌ SEOService generate_publish_ready_content error for {brief['product_name']}: {e}"
            )
            return fallback

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
