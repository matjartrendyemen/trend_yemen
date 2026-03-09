import os
import google.genai as genai

# أنشئ عميل باستخدام مفتاح API من المتغيرات السرية
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# اطبع قائمة النماذج المتاحة وطرقها
models = client.models.list()
for m in models:
    print(m.name, "=>", m.supported_generation_methods)
