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
            "cta_short_forms": [
                "اطلبه الآن",
                "ابدأ فرق الراحة اليوم",
                "جرّبه من اليوم",
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
            "cta_short_forms": [
                "اختاري لمستك الأجمل اليوم",
                "امنحي نفسك إشراقة أجمل",
                "ابدئي عنايتك الآن",
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
            "cta_short_forms": [
                "اجعلي يومك أسهل الآن",
                "اختاري الراحة العملية",
                "ابدئي الحل الأذكى اليوم",
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
            "cta_short_forms": [
                "جرّب الحل الأذكى الآن",
                "ابدأ تجربة أذكى اليوم",
                "اختر الأداء العملي الآن",
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
            "cta_short_forms": [
                "ابدأ التغيير الآن",
                "خذ أول خطوة اليوم",
                "ابدأ نشاطك من الآن",
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
            "cta_short_forms": [
                "وفّر راحة أكثر لعائلتك",
                "اختر الحل العملي اليوم",
                "اجعل يومكم أسهل الآن",
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
            "cta_short_forms": [
                "اطلبه الآن",
                "جرّبه اليوم",
                "ابدأ اختيارًا أذكى الآن",
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
        "preview",
        "raw",
        "system",
        "جاهز للمراجعة",
        "الحالة الإعلامية",
        "داخل المتجر",
        "داخل متجر",
        "قابل للمراجعة",
        "منتج مميز",
    ]

    MIN_HASHTAGS = 2
    MAX_HASHTAGS = 6
    MAX_TITLE_LENGTH = 68
    MAX_DESCRIPTION_LENGTH = 260
    MAX_SOCIAL_LENGTH = 340
    MAX_KEYWORDS = 8

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

    def _strip_system_phrases(self, text):
        cleaned = self._clean(text)
        if not cleaned:
            return ""

        result = cleaned
        for phrase in self.BANNED_SYSTEM_PHRASES:
            if not phrase:
                continue
            result = re.sub(re.escape(phrase), "", result, flags=re.IGNORECASE)

        result = result.replace("..", ".")
        result = result.replace("،،", "،")
        result = re.sub(r"[|_/]+", " ", result)
        result = re.sub(r"\s+([،.!؟])", r"\1", result)
        result = re.sub(r"([،.!؟]){2,}", r"\1", result)
        return self._collapse_whitespace(result)

    def _split_words(self, text):
        return [word for word in re.split(r"\s+", self._clean(text)) if word]

    def _normalize_product_name(self, value):
        text = self._strip_system_phrases(value)
        text = re.sub(r"[-–—]+", " ", text)
        tokens = self._split_words(text)

        cleaned_tokens = []
        for token in tokens:
            stripped = re.sub(r"[^\w\u0600-\u06FF]+", "", token)
            if not stripped:
                continue
            if len(stripped) > 28:
                continue
            cleaned_tokens.append(stripped)

        cleaned_tokens = self._unique_preserve_order(cleaned_tokens)
        if len(cleaned_tokens) > 6:
            cleaned_tokens = cleaned_tokens[:6]

        marketing_name = " ".join(cleaned_tokens)
        marketing_name = self._collapse_whitespace(marketing_name)
        return marketing_name or "اختيار عملي"

    def _normalize_category_text(self, value):
        text = self._strip_system_phrases(value)
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

    def _truncate_safely(self, text, max_length):
        cleaned = self._clean(text)
        if len(cleaned) <= max_length:
            return cleaned
        shortened = cleaned[:max_length].rstrip(" ،.!؟")
        return shortened + "..."

    def _sanitize_text(self, text, product_name="", max_length=600):
        cleaned = self._strip_system_phrases(text)
        cleaned = self._remove_excess_name_repetition(cleaned, product_name, max_occurrences=1)
        cleaned = re.sub(r"\s+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip(" -|،\n\t")
        cleaned = self._collapse_whitespace(cleaned.replace(" \n", "\n"))
        cleaned = self._truncate_safely(cleaned, max_length)
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

            if len(normalized) > 28:
                normalized = self._truncate_safely(normalized, 28).rstrip(".")

            lowered = normalized.lower()
            if lowered in seen:
                continue

            seen.add(lowered)
            cleaned_items.append(normalized)

        return ", ".join(cleaned_items[: self.MAX_KEYWORDS])

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

            if len(normalized) > 24:
                normalized = normalized[:24].rstrip("_")

            if not normalized:
                continue

            tag = "#" + normalized
            lowered = tag.lower()

            if lowered in seen:
                continue

            seen.add(lowered)
            cleaned_tags.append(tag)

        return " ".join(cleaned_tags[: self.MAX_HASHTAGS])

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

    def _strengthen_cta(self, cta, strategy_profile, seed_text):
        short_forms = strategy_profile.get("cta_short_forms") or []
        fallback_cta = self._pick_variant(short_forms, seed_text + "|cta_short")
        candidate = self._sanitize_text(cta or fallback_cta, max_length=55)

        if not candidate:
            candidate = fallback_cta or "اطلبه الآن"

        if len(candidate) > 55:
            candidate = self._truncate_safely(candidate, 55)

        return candidate

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
        raw_cta = self._pick_variant(strategy_profile["cta_templates"], seed_text + "|cta")
        title_template = self._pick_variant(strategy_profile["title_templates"], seed_text + "|title")
        strong_cta = self._strengthen_cta(raw_cta, strategy_profile, seed_text)

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
            "cta": strong_cta,
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
        title = self._sanitize_text(title, product_name=brief["product_name"], max_length=self.MAX_TITLE_LENGTH)
        words = self._split_words(title)
        if len(words) > 8:
            title = self._truncate_safely(" ".join(words[:8]), self.MAX_TITLE_LENGTH)
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
            self._sanitize_text(brief["hook"], product_name=brief["product_name"], max_length=110),
            self._sanitize_text(self._render_template(brief["solution_line"], brief), product_name=brief["product_name"], max_length=120),
            self._sanitize_text(brief["cta"], product_name=brief["product_name"], max_length=55),
            seo_hashtags,
        ]
        return "\n".join([line for line in lines if self._clean(line)])

    def _condense_social_post(self, social_post, brief, seo_hashtags):
        raw_lines = re.split(r"[\n\r]+", self._clean(social_post))
        clean_lines = []

        for line in raw_lines:
            sanitized = self._sanitize_text(line, product_name=brief["product_name"], max_length=120)
            if sanitized:
                clean_lines.append(sanitized)

        clean_lines = self._unique_preserve_order(clean_lines)

        if not clean_lines:
            clean_lines = [
                self._sanitize_text(brief["hook"], product_name=brief["product_name"], max_length=110),
                self._sanitize_text(self._render_template(brief["solution_line"], brief), product_name=brief["product_name"], max_length=120),
            ]

        condensed = []

        if clean_lines:
            condensed.append(clean_lines[0])

        benefit_line = None
        for line in clean_lines[1:]:
            if brief["cta"] not in line and not line.startswith("#"):
                benefit_line = line
                break

        if not benefit_line:
            benefit_line = self._sanitize_text(
                self._render_template(brief["desire_line"], brief),
                product_name=brief["product_name"],
                max_length=120,
            )

        condensed.append(benefit_line)
        condensed.append(self._sanitize_text(brief["cta"], product_name=brief["product_name"], max_length=55))
        condensed.append(seo_hashtags)

        final_post = "\n".join([line for line in condensed if self._clean(line)])
        return self._truncate_safely(final_post, self.MAX_SOCIAL_LENGTH)

    def _has_raw_long_chunk(self, text):
        for token in self._split_words(text):
            if len(token) > 28:
                return True
        return False

    def _validate_quality(self, payload, brief):
        title = self._clean(payload.get("marketing_title"))
        description = self._clean(payload.get("marketing_description"))
        social_post = self._clean(payload.get("social_post"))
        hashtags = self._clean(payload.get("seo_hashtags"))
        keywords = self._clean(payload.get("seo_keywords"))
        product_name = self._clean(brief["product_name"])
        cta = self._clean(brief["cta"])

        if not title:
            return False, "Quality gate rejected: MarketingTitle is empty"

        if len(title) > self.MAX_TITLE_LENGTH:
            return False, "Quality gate rejected: MarketingTitle is too long"

        if len(self._split_words(title)) > 8:
            return False, "Quality gate rejected: MarketingTitle is too long structurally"

        if self._has_raw_long_chunk(title):
            return False, "Quality gate rejected: MarketingTitle still looks raw"

        if not description:
            return False, "Quality gate rejected: MarketingDescription is empty"

        if self._has_raw_long_chunk(description):
            return False, "Quality gate rejected: MarketingDescription contains raw long strings"

        if not social_post:
            return False, "Quality gate rejected: SocialPost is empty"

        if len(social_post) > self.MAX_SOCIAL_LENGTH:
            return False, "Quality gate rejected: SocialPost is too long"

        if cta and cta not in social_post:
            return False, "Quality gate rejected: CTA is missing from SocialPost"

        hashtag_list = [tag for tag in hashtags.split() if tag.startswith("#")]
        if len(hashtag_list) < self.MIN_HASHTAGS:
            return False, "Quality gate rejected: not enough hashtags"

        if len(hashtag_list) > self.MAX_HASHTAGS:
            return False, "Quality gate rejected: too many hashtags"

        if not keywords:
            return False, "Quality gate rejected: SEOKeywords is empty"

        if self._count_occurrences(title, product_name) > 1:
            return False, "Quality gate rejected: product name repeats too much in title"

        if self._count_occurrences(description, product_name) > 2:
            return False, "Quality gate rejected: product name repeats too much in description"

        if self._count_occurrences(social_post, product_name) > 2:
            return False, "Quality gate rejected: product name repeats too much in SocialPost"

        for phrase in self.BANNED_SYSTEM_PHRASES:
            if phrase and phrase.lower() in title.lower():
                return False, "Quality gate rejected: MarketingTitle still contains raw/system wording"
            if phrase and phrase.lower() in description.lower():
                return False, "Quality gate rejected: MarketingDescription still contains raw/system wording"
            if phrase and phrase.lower() in social_post.lower():
                return False, "Quality gate rejected: SocialPost still contains raw/system wording"

        return True, ""

    def _apply_quality_gate(self, payload, brief):
        seo_keywords = self._normalize_keywords(payload.get("seo_keywords"))
        seo_hashtags = self._normalize_hashtags(payload.get("seo_hashtags"))

        sanitized = {
            "marketing_title": self._compose_marketing_title(brief) if not self._clean(payload.get("marketing_title")) else self._sanitize_text(
                payload.get("marketing_title"),
                product_name=brief["product_name"],
                max_length=self.MAX_TITLE_LENGTH,
            ),
            "marketing_description": self._compose_marketing_description(brief) if not self._clean(payload.get("marketing_description")) else self._sanitize_text(
                payload.get("marketing_description"),
                product_name=brief["product_name"],
                max_length=self.MAX_DESCRIPTION_LENGTH,
            ),
            "social_post": self._clean(payload.get("social_post")),
            "seo_keywords": seo_keywords or self._normalize_keywords(brief["keyword_candidates"]),
            "seo_hashtags": seo_hashtags or self._normalize_hashtags(brief["hashtag_candidates"]),
            "status": "ready",
            "error_message": "",
        }

        if not sanitized["social_post"]:
            sanitized["social_post"] = self._compose_social_post(brief, sanitized["seo_hashtags"])

        sanitized["marketing_title"] = self._truncate_safely(sanitized["marketing_title"], self.MAX_TITLE_LENGTH)
        sanitized["social_post"] = self._condense_social_post(sanitized["social_post"], brief, sanitized["seo_hashtags"])

        passed, reason = self._validate_quality(sanitized, brief)
        if not passed:
            return {
                "marketing_title": sanitized["marketing_title"],
                "marketing_description": sanitized["marketing_description"],
                "social_post": sanitized["social_post"],
                "seo_keywords": sanitized["seo_keywords"],
                "seo_hashtags": sanitized["seo_hashtags"],
                "status": "gated_failed",
                "error_message": reason,
            }

        return sanitized

    def _build_deterministic_payload(self, brief):
        seo_keywords = self._normalize_keywords(brief["keyword_candidates"])
        seo_hashtags = self._normalize_hashtags(brief["hashtag_candidates"])

        marketing_title = self._compose_marketing_title(brief)
        marketing_description = self._compose_marketing_description(brief)
        social_post = self._compose_social_post(brief, seo_hashtags)

        return self._apply_quality_gate(
            {
                "marketing_title": marketing_title,
                "marketing_description": marketing_description,
                "social_post": social_post,
                "seo_keywords": seo_keywords,
                "seo_hashtags": seo_hashtags,
                "status": "ready",
                "error_message": "",
            },
            brief,
        )

    def _build_ai_prompt(self, brief):
        keyword_candidates = ", ".join([self._clean(item) for item in brief["keyword_candidates"] if self._clean(item)])
        hashtag_candidates = " ".join(
            [("#" + self._clean(item).replace(" ", "_").lstrip("#")) for item in brief["hashtag_candidates"] if self._clean(item)]
        )

        return f"""
أنت Senior Arabic Direct Response Copywriter.
المطلوب كتابة commercial copy عربي احترافي جدًا، بشري، مقنع، مناسب للنشر المباشر، وقابل للتحويل.

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
- اجعل MarketingTitle قصيرة وقوية
- اجعل MarketingDescription مقنعة وواضحة
- اجعل SocialPost قصيرة نسبيًا وقابلة للتحويل
- اجعل CTA مباشرة وقوية
- اجعل hashtags نظيفة ومحدودة
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

        return self._apply_quality_gate(merged, brief)

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
