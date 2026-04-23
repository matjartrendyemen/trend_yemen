import json
import os

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
            "tone": "مطمئن، واثق، عملي، ويعطي إحساسًا بالراحة من أول سطر.",
            "instagram_format": "Hook → Relief benefit → Practical usage angle → CTA → Hashtags",
            "hook_templates": [
                "إذا كان الانزعاج اليومي يسرق راحتك، هذا هو الفرق الذي ستشعر به.",
                "الراحة ليست رفاهية عندما يكون يومك مليئًا بالحركة والجهد.",
                "حين يصبح التعب جزءًا من يومك، تحتاج حلًا يمنحك راحة واضحة.",
                "ابدأ يومك بإحساس أخف وراحة تلمسها من الاستخدام الأول.",
            ],
            "title_templates": [
                "{product_name} | راحة أوضح ليوم أخف",
                "{product_name} | حل عملي للراحة اليومية",
                "{product_name} | فرق تشعر به مع كل استخدام",
            ],
            "description_formulas": [
                "مصمم لمن يبحث عن تخفيف الإزعاج اليومي واستعادة راحته بأسلوب عملي. {product_name} يمنحك تجربة أكثر راحة وثقة، ويجعل الاستخدام اليومي أبسط وأهدأ.",
                "عندما يتحول الانزعاج إلى عبء يومي، يصبح الحل العملي ضرورة. {product_name} يساعدك على الانتقال من التعب المستمر إلى إحساس أوضح بالراحة والانسيابية.",
                "إذا كنت تبحث عن وسيلة مريحة تدعم يومك وتخفف الضغط المتكرر، فإن {product_name} يقدم زاوية استخدام ذكية ومريحة تناسب الروتين اليومي.",
            ],
            "benefit_lines": [
                "راحة أسرع، استخدام أسهل، وإحساس أفضل مع كل مرة.",
                "يدعم يومك براحة أوضح ويخفف الإزعاج الذي يستهلك طاقتك.",
                "خيار عملي لكل من يريد راحة محسوسة بدون تعقيد.",
            ],
            "angle_lines": [
                "مثالي للاستخدام اليومي لمن يريد فرقًا واضحًا في الراحة.",
                "يعطيك إحساسًا أفضل أثناء الروتين اليومي المزدحم.",
                "مناسب لمن يبحث عن حل مريح وعملي بدل الاستمرار مع نفس الإزعاج.",
            ],
            "cta_templates": [
                "اطلبه الآن وابدأ فرق الراحة من اليوم.",
                "جرّبه اليوم وخفف العبء عن يومك خطوة بخطوة.",
                "امنح نفسك راحة تستحقها وابدأ من الآن.",
            ],
            "keyword_stems": [
                "راحة يومية", "تخفيف الانزعاج", "حل عملي", "استخدام مريح", "منتج صحي", "راحة أفضل",
            ],
            "hashtag_stems": [
                "راحة", "صحة", "يومك_أخف", "حل_عملي", "منتجات_مميزة",
            ],
        },
        "beauty": {
            "display_name": "Beauty",
            "tone": "راقٍ، أنثوي أو جمالي، ويعطي إحساسًا بالثقة والإشراقة.",
            "instagram_format": "Hook → Confidence benefit → Beauty angle → CTA → Hashtags",
            "hook_templates": [
                "تفاصيل الجمال الصغيرة هي التي تصنع حضورك الحقيقي.",
                "حين تهتمين بنفسك بالطريقة الصحيحة، يظهر الفرق بسرعة.",
                "إشراقتك تبدأ من اختيار يمنحك ثقة أكثر كل يوم.",
                "لمسة واحدة مدروسة كفيلة بأن تغيّر إحساسك بنفسك.",
            ],
            "title_templates": [
                "{product_name} | لمسة جمال بثقة أعلى",
                "{product_name} | إشراقة أجمل كل يوم",
                "{product_name} | عناية تبرز جمالك الطبيعي",
            ],
            "description_formulas": [
                "{product_name} يمنحك إحساسًا أجمل بالعناية اليومية، ويضيف لمسة أناقة وثقة تظهر في التفاصيل. اختيار مناسب لمن تريد نتيجة أنعم، أرقى، وأكثر حضورًا.",
                "إذا كنتِ تبحثين عن عناية تمنحك إشراقة أوضح وثقة أكثر، فإن {product_name} يقدم تجربة مريحة وجذابة تناسب روتينك اليومي.",
                "من العناية العادية إلى إحساس أجمل بالمظهر والثقة، يأتي {product_name} كخيار ذكي يعزز حضورك ويلفت الانتباه بطريقة ناعمة.",
            ],
            "benefit_lines": [
                "إشراقة أوضح وثقة أكبر في إطلالتك اليومية.",
                "عناية تبرز جمالك بأسلوب أنيق وغير مبالغ فيه.",
                "لمسة عملية تمنحك حضورًا أجمل ونتيجة أحبّ إلى النفس.",
            ],
            "angle_lines": [
                "مناسب لروتين يومي يوازن بين الجمال والعملية.",
                "اختيار جميل لمن تحب التفاصيل المرتبة والإحساس الراقي.",
                "يمنحك نتيجة تبدو طبيعية ومحببة من أول استخدام.",
            ],
            "cta_templates": [
                "امنحي نفسك لمسة أجمل اليوم.",
                "اختاري الجمال الذي يليق بك وابدئي من الآن.",
                "دلّلي نفسك بخيار يمنحك حضورًا أجمل وثقة أكبر.",
            ],
            "keyword_stems": [
                "عناية يومية", "إشراقة", "ثقة", "جمال", "منتج تجميلي", "روتين عناية",
            ],
            "hashtag_stems": [
                "جمال", "عناية", "إشراقة", "ثقة", "روتين_جمال",
            ],
        },
        "home_convenience": {
            "display_name": "Home convenience",
            "tone": "عملي، ذكي، مريح، ويعد بتوفير الوقت والجهد.",
            "instagram_format": "Hook → Convenience benefit → Home angle → CTA → Hashtags",
            "hook_templates": [
                "الأشياء الذكية في البيت ليست رفاهية عندما تصنع فرقًا يوميًا.",
                "كلما صار البيت أسهل، صار يومك أخف وأهدأ.",
                "الحل البسيط الذي يختصر عليك وقتًا وجهدًا كل يوم.",
                "من الفوضى أو الإزعاج إلى ترتيب وراحة أكثر في خطوة واحدة.",
            ],
            "title_templates": [
                "{product_name} | راحة أكثر في يومك",
                "{product_name} | حل منزلي عملي وذكي",
                "{product_name} | سهولة يومية بلمسة ذكية",
            ],
            "description_formulas": [
                "{product_name} صُمم ليحوّل التفاصيل المزعجة في البيت إلى تجربة أسهل وأكثر ترتيبًا. عملي، مريح، ويمنحك وقتًا وجهدًا أقل مع نتيجة أوضح.",
                "إذا كنت تبحث عن طريقة أذكى لتسهيل يومك داخل المنزل، فإن {product_name} يقدم راحة عملية تساعدك على إنجاز أكثر بجهد أقل.",
                "من الإزعاج اليومي إلى السهولة والتنظيم، يأتي {product_name} كخيار يريحك ويجعل الروتين المنزلي أكثر بساطة وأناقة.",
            ],
            "benefit_lines": [
                "يوفر وقتك ويخفف الجهد في الاستخدام اليومي.",
                "يجعل التفاصيل المنزلية أسهل وأكثر ترتيبًا.",
                "اختيار عملي يضيف راحة واضحة داخل البيت.",
            ],
            "angle_lines": [
                "مثالي للروتين اليومي الذي يحتاج حلولًا بسيطة وفعالة.",
                "مناسب لكل من يحب البيت المرتب والتعامل الأسهل مع التفاصيل.",
                "فكرة عملية توفر عليك تعبًا متكررًا في اليوم.",
            ],
            "cta_templates": [
                "خففي الجهد وخلّي يومك أسهل من الآن.",
                "جرّبيه اليوم واستمتعي براحة أوضح في البيت.",
                "اختاري الحل العملي الذي يختصر عليك الكثير.",
            ],
            "keyword_stems": [
                "راحة منزلية", "تنظيم", "حل عملي", "توفير وقت", "منتج منزلي", "سهولة يومية",
            ],
            "hashtag_stems": [
                "منزل", "راحة_منزلية", "تنظيم", "حل_عملي", "يومك_أسهل",
            ],
        },
        "gadget": {
            "display_name": "Gadget",
            "tone": "حديث، سريع، ذكي، ويبرز العملية والقيمة.",
            "instagram_format": "Hook → Smart benefit → Tech angle → CTA → Hashtags",
            "hook_templates": [
                "الحل الذكي هو الذي يختصر عليك الوقت من أول استخدام.",
                "التفاصيل التقنية الصغيرة تصنع فرقًا كبيرًا في يومك.",
                "لما يكون المنتج عمليًا وذكيًا، تعرف أن اختيارك كان في مكانه.",
                "أداء أفضل وراحة أكثر في أداة واحدة.",
            ],
            "title_templates": [
                "{product_name} | الحل الأذكى ليومك",
                "{product_name} | تقنية عملية بشكل أبسط",
                "{product_name} | أداء ذكي بقيمة أعلى",
            ],
            "description_formulas": [
                "{product_name} يقدم لك تجربة أكثر ذكاءً وعملية، ويجمع بين السهولة والأداء في استخدام يومي مريح. مناسب لمن يحب الحلول السريعة والواضحة.",
                "إذا كنت تبحث عن أداة تجعل يومك أسرع وأكثر سلاسة، فإن {product_name} يمنحك زاوية استخدام ذكية وعملية من أول تجربة.",
                "من التعقيد إلى السهولة، ومن البطء إلى العملية، يأتي {product_name} ليمنحك قيمة واضحة في كل استخدام.",
            ],
            "benefit_lines": [
                "أداء عملي، تجربة أسهل، واستخدام يواكب يومك.",
                "أداة ذكية تضيف راحة وسرعة إلى روتينك اليومي.",
                "مناسبة لمن يريد نتيجة واضحة بدون تعقيد.",
            ],
            "angle_lines": [
                "تصميم عملي يناسب الاستخدام المتكرر واليومي.",
                "خيار مناسب لمن يقدّر الأداء وسهولة الاستخدام معًا.",
                "فكرة ذكية تعطيك قيمة حقيقية من أول مرة.",
            ],
            "cta_templates": [
                "جرّب الحل الأذكى اليوم.",
                "اختر الأداة العملية التي تسهّل يومك الآن.",
                "ابدأ تجربة أكثر ذكاءً من الآن.",
            ],
            "keyword_stems": [
                "أداة ذكية", "تقنية عملية", "حل سريع", "منتج إلكتروني", "أداء عملي", "استخدام يومي",
            ],
            "hashtag_stems": [
                "تقنية", "أداة_ذكية", "حل_أذكى", "عملي", "منتجات_تقنية",
            ],
        },
        "fitness": {
            "display_name": "Fitness",
            "tone": "مُلهم، منظم، مشجع على الالتزام والتقدّم.",
            "instagram_format": "Hook → Motivation benefit → Fitness angle → CTA → Hashtags",
            "hook_templates": [
                "النتائج تبدأ من قرار صغير تلتزم به كل يوم.",
                "إذا كنت تريد بداية أقوى، ابدأ بخطوة عملية اليوم.",
                "من الكسل إلى النشاط... الفرق يبدأ باختيار صحيح.",
                "كل تقدم حقيقي يبدأ بأداة تدعمك على الاستمرار.",
            ],
            "title_templates": [
                "{product_name} | بداية أقوى لنتيجة أوضح",
                "{product_name} | خيار عملي لنشاطك اليومي",
                "{product_name} | التزام أسهل ونتيجة أقرب",
            ],
            "description_formulas": [
                "{product_name} يساعدك على جعل روتينك أكثر التزامًا وفعالية، ويمنحك إحساسًا بالنشاط والقدرة على الاستمرار. مناسب لمن يريد بداية عملية ونتيجة أوضح مع الوقت.",
                "إذا كان هدفك تحسين نشاطك اليومي أو دعم تمرينك بشكل أذكى، فإن {product_name} يقدم لك نقطة بداية مريحة ومحفزة.",
                "من التردد إلى الالتزام، ومن البداية المتقطعة إلى الاستمرار، يأتي {product_name} كأداة عملية تدعم تقدمك بشكل أفضل.",
            ],
            "benefit_lines": [
                "يشجعك على الالتزام ويجعل خطوتك الأولى أسهل.",
                "مناسب لروتين نشيط أكثر وتنظيم أفضل لرحلتك.",
                "خيار عملي لمن يريد نتيجة تبدأ من عادة يومية ثابتة.",
            ],
            "angle_lines": [
                "مثالي لمن يريد دعمًا عمليًا للنشاط والالتزام.",
                "يدخل بسهولة في روتينك اليومي بدون تعقيد.",
                "يمنحك دفعة بداية جيدة نحو أسلوب حياة أكثر نشاطًا.",
            ],
            "cta_templates": [
                "ابدأ التغيير من الآن.",
                "خذ أول خطوة اليوم وخلّي الالتزام أسهل.",
                "جرّبه اليوم وابدأ رحلة نشاط أقوى.",
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
            "tone": "مطمئن، عائلي، عملي، ويركز على الراحة اليومية.",
            "instagram_format": "Hook → Family benefit → Trust angle → CTA → Hashtags",
            "hook_templates": [
                "راحة العائلة تبدأ من التفاصيل التي تسهّل يومكم.",
                "كل اختيار عملي للأسرة ينعكس على راحة اليوم كاملًا.",
                "عندما يكون المنتج مناسبًا للعائلة، تشعر بالفرق في كل يوم.",
                "الراحة، السهولة، والاطمئنان... هذا ما تحتاجه الأسرة فعلًا.",
            ],
            "title_templates": [
                "{product_name} | راحة أكثر لك ولعائلتك",
                "{product_name} | اختيار عملي للأسرة",
                "{product_name} | سهولة يومية لكل البيت",
            ],
            "description_formulas": [
                "{product_name} خيار عملي يساعد على جعل اليوم العائلي أكثر راحة وسهولة. مناسب لمن يبحث عن منتج يدعم الروتين اليومي ويمنح الأسرة إحساسًا أكبر بالراحة والتنظيم.",
                "إذا كنت تريد منتجًا يضيف سهولة حقيقية إلى يوم الأسرة، فإن {product_name} يقدم لك زاوية استخدام مريحة ومناسبة للحياة اليومية.",
                "من التعب في التفاصيل الصغيرة إلى راحة أوضح لكل البيت، يأتي {product_name} كاختيار ذكي للعائلة التي تحب السهولة والاطمئنان.",
            ],
            "benefit_lines": [
                "يساعد على جعل الروتين اليومي أكثر راحة وتنظيمًا.",
                "خيار مناسب للعائلة التي تحب السهولة والعملية.",
                "منتج يضيف فرقًا ملموسًا في التفاصيل اليومية.",
            ],
            "angle_lines": [
                "مناسب للاستخدام اليومي داخل البيت أو مع العائلة.",
                "يعطي إحساسًا أفضل بالترتيب والراحة والثقة في الاختيار.",
                "اختيار عملي لمن يريد راحة أكثر بدون تعقيد.",
            ],
            "cta_templates": [
                "وفّر راحة أكثر لك ولعائلتك من اليوم.",
                "اختر الحل العملي الذي يسهّل يوم الأسرة.",
                "اجعل يومكم أسهل وابدأ بالاختيار المناسب الآن.",
            ],
            "keyword_stems": [
                "راحة الأسرة", "منتج عائلي", "سهولة يومية", "للمنزل", "للأطفال", "حل عملي",
            ],
            "hashtag_stems": [
                "عائلة", "راحة_الأسرة", "أطفال", "منزل", "حل_عملي",
            ],
        },
        "general": {
            "display_name": "General commercial",
            "tone": "تجاري راقٍ، مختصر، واثق، ويركز على الفائدة العملية.",
            "instagram_format": "Hook → Value line → Selling angle → CTA → Hashtags",
            "hook_templates": [
                "هناك منتجات تلفت النظر، وهناك منتجات تصنع فرقًا حقيقيًا.",
                "اختيارك الأفضل هو الذي يجمع بين الشكل العملي والقيمة الواضحة.",
                "إذا كنت تبحث عن شيء يضيف فرقًا ملموسًا ليومك، فهذا خيار يستحق الانتباه.",
                "التفاصيل الذكية هي التي تجعل المنتج أقرب إلى قرار الشراء.",
            ],
            "title_templates": [
                "{product_name} | قيمة أوضح واختيار أذكى",
                "{product_name} | منتج عملي يستحق التجربة",
                "{product_name} | فرق واضح في الاستخدام اليومي",
            ],
            "description_formulas": [
                "{product_name} يقدم قيمة عملية وتجربة استخدام مريحة، ويجمع بين الفائدة الواضحة والأسلوب المرتب في منتج واحد. مناسب لمن يبحث عن اختيار ذكي وسهل المراجعة والشراء.",
                "إذا كنت تريد منتجًا يبدو جيدًا ويقدم فائدة فعلية، فإن {product_name} يمنحك زاوية بيع واضحة ومقنعة من أول نظرة.",
                "من الخيارات العادية إلى الاختيار الأكثر إقناعًا، يأتي {product_name} كمنتج يوازن بين العملية والقيمة بطريقة جذابة.",
            ],
            "benefit_lines": [
                "قيمة عملية، شكل مقنع، وتجربة استخدام مريحة.",
                "منتج يمنحك سببًا واضحًا للاقتناء من أول مرة.",
                "خيار مناسب لمن يريد فائدة حقيقية بدون مبالغة.",
            ],
            "angle_lines": [
                "مناسب للاستخدام اليومي ويقدّم فائدة واضحة للمشتري.",
                "يعطي انطباعًا جيدًا ويضيف قيمة حقيقية في التفاصيل.",
                "اختيار عملي لمن يحب الجودة الواضحة والنتيجة المريحة.",
            ],
            "cta_templates": [
                "اطلبه الآن واستمتع بقيمة أوضح من أول تجربة.",
                "جرّبه اليوم واختر المنتج الذي يصنع فرقًا فعلًا.",
                "ابدأ بتجربة أذكى واختيار أكثر إقناعًا.",
            ],
            "keyword_stems": [
                "منتج عملي", "قيمة واضحة", "اختيار ذكي", "منتج مميز", "سهولة استخدام", "أفضل اختيار",
            ],
            "hashtag_stems": [
                "منتجات_مميزة", "اختيار_ذكي", "قيمة", "عملي", "ترند_اليمن",
            ],
        },
    }

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

    def _normalize_keywords(self, values):
        if isinstance(values, list):
            items = [self._clean(item) for item in values if self._clean(item)]
            deduped = []
            seen = set()
            for item in items:
                lowered = item.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                deduped.append(item)
            return ", ".join(deduped[:8])

        text = self._clean(values)
        if not text:
            return ""

        parts = [part.strip() for part in text.replace("\n", ",").split(",")]
        parts = [part for part in parts if part]
        return self._normalize_keywords(parts)

    def _normalize_hashtags(self, values):
        if isinstance(values, list):
            tags = []
            seen = set()
            for item in values:
                text = self._clean(item)
                if not text:
                    continue
                text = text.replace(" ", "_")
                if not text.startswith("#"):
                    text = "#" + text
                lowered = text.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                tags.append(text)
            return " ".join(tags[:8])

        text = self._clean(values)
        if not text:
            return ""

        parts = text.replace("\n", " ").split()
        normalized = []
        for part in parts:
            cleaned = self._clean(part)
            if not cleaned:
                continue
            cleaned = cleaned.replace(" ", "_")
            if not cleaned.startswith("#"):
                cleaned = "#" + cleaned
            normalized.append(cleaned)
        return self._normalize_hashtags(normalized)

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
        clean_name = self._clean(product_name) or "منتج مميز"
        clean_category = self._clean(category_id)
        clean_price = self._normalize_price_text(manual_price)
        clean_media_url = self._clean(final_media_url)
        clean_media_status = self._clean(final_media_status) or "selected"

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
        title_template = self._pick_variant(strategy_profile["title_templates"], seed_text + "|title")
        description_formula = self._pick_variant(strategy_profile["description_formulas"], seed_text + "|description")
        benefit_line = self._pick_variant(strategy_profile["benefit_lines"], seed_text + "|benefit")
        angle_line = self._pick_variant(strategy_profile["angle_lines"], seed_text + "|angle")
        cta = self._pick_variant(strategy_profile["cta_templates"], seed_text + "|cta")

        keyword_candidates = [
            clean_name,
            clean_category,
            clean_price,
            strategy_profile["display_name"],
            *strategy_profile["keyword_stems"],
        ]
        hashtag_candidates = [
            "ترند_اليمن",
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
            "tone_rules": strategy_profile["tone"],
            "instagram_format": strategy_profile["instagram_format"],
            "hook": hook,
            "title_template": title_template,
            "description_formula": description_formula,
            "benefit_line": benefit_line,
            "angle_line": angle_line,
            "cta": cta,
            "keyword_candidates": keyword_candidates,
            "hashtag_candidates": hashtag_candidates,
        }

    def _render_template(self, template, brief):
        return self._clean(template).format(
            product_name=brief["product_name"],
            category=brief["category_id"] or "فئة متنوعة",
            price=brief["manual_price"],
        )

    def _build_deterministic_payload(self, brief):
        marketing_title = self._render_template(brief["title_template"], brief)
        marketing_description = self._render_template(brief["description_formula"], brief)

        social_lines = [
            brief["hook"],
            f"{brief['benefit_line']} بسعر {brief['manual_price']}.",
            brief["angle_line"],
            brief["cta"],
            self._normalize_hashtags(brief["hashtag_candidates"]),
        ]
        social_post = "\n".join([self._clean(line) for line in social_lines if self._clean(line)])

        seo_keywords = self._normalize_keywords(brief["keyword_candidates"])
        seo_hashtags = self._normalize_hashtags(brief["hashtag_candidates"])

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
أنت Senior Arabic Direct Response Copywriter متخصص بمحتوى المتاجر والإنستغرام للسوق اليمني.
المطلوب: كتابة محتوى تجاري يبدو بشريًا، مقنعًا، مختصرًا، غير مبتذل، وغير آلي.

التزم بهذه الاستراتيجية:
- Strategy: {brief["strategy_name"]}
- Tone: {brief["tone_rules"]}
- Instagram Format: {brief["instagram_format"]}

المدخلات:
- ProductName: {brief["product_name"]}
- CategoryID: {brief["category_id"]}
- ManualPrice: {brief["manual_price"]}
- FinalMediaPresent: {"yes" if brief["final_media_present"] else "no"}
- FinalMediaStatus: {brief["final_media_status"]}

العناصر الإرشادية:
- Hook direction: {brief["hook"]}
- Description formula direction: {brief["description_formula"]}
- Benefit line direction: {brief["benefit_line"]}
- Selling angle direction: {brief["angle_line"]}
- CTA direction: {brief["cta"]}
- Keyword hints: {keyword_candidates}
- Hashtag hints: {hashtag_candidates}

قواعد صارمة:
- العربية يجب أن تكون احترافية وتجارية ومقنعة
- لا تستخدم لغة ركيكة أو تشغيلية أو إدارية
- لا تقل: جاهز للمراجعة / الحالة الإعلامية / داخل المتجر
- اجعل MarketingTitle قصيرًا وقويًا
- اجعل MarketingDescription مقنعًا ويعكس زاوية البيع
- اجعل SocialPost بصيغة إنستغرام تحويلية: Hook ثم قيمة ثم زاوية بيع ثم CTA ثم hashtags
- لا تغيّر السعر
- لا تضف وعودًا غير منطقية
- لا تُرجع أي شرح خارج JSON

أرجع JSON صالحًا فقط بهذه المفاتيح:
{{
  "marketing_title": "...",
  "marketing_description": "...",
  "social_post": "...",
  "seo_keywords": ["...", "..."],
  "seo_hashtags": ["#...", "#..."]
}}
""".strip()

    def _merge_ai_payload_with_brief(self, ai_payload, brief, fallback):
        if not isinstance(ai_payload, dict):
            return fallback

        marketing_title = self._clean(ai_payload.get("marketing_title")) or fallback["marketing_title"]
        marketing_description = self._clean(ai_payload.get("marketing_description")) or fallback["marketing_description"]
        social_post = self._clean(ai_payload.get("social_post")) or fallback["social_post"]

        seo_keywords = self._normalize_keywords(ai_payload.get("seo_keywords")) or fallback["seo_keywords"]
        seo_hashtags = self._normalize_hashtags(ai_payload.get("seo_hashtags")) or fallback["seo_hashtags"]

        if brief["cta"] not in social_post:
            social_post = "\n".join([social_post, brief["cta"], seo_hashtags])

        if seo_hashtags not in social_post:
            social_post = "\n".join([social_post, seo_hashtags])

        return {
            "marketing_title": marketing_title,
            "marketing_description": marketing_description,
            "social_post": social_post,
            "seo_keywords": seo_keywords,
            "seo_hashtags": seo_hashtags,
            "status": "ready",
            "error_message": "",
        }

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
