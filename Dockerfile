# استخدم صورة Python الرسمية
FROM python:3.12-slim

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملفات المشروع
COPY requirements.txt .
COPY . .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# تعيين المتغير PORT الافتراضي
ENV PORT=8080

# تشغيل التطبيق
CMD ["python", "main.py"]
