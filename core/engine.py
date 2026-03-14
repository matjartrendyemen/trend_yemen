import uuid
import re
from monitoring.logger import system_log

class ProductEngine:
    @staticmethod
    def generate_smart_sku(prefix="TY"):
        """
        توليد رمز فريد للمنتج بصيغة TY-XXXX.
        يستخدم مكتبة uuid المدمجة في بايثون 3.12.3 ولا تحتاج لتثبيت خارجي.
        """
        unique_id = str(uuid.uuid4())[:4].upper()
        sku = f"{prefix}-{unique_id}"
        system_log.info(f"🆕 SKU Generated: {sku}")
        return sku

    @staticmethod
    def format_folder_name(sku, title_ar):
        """تنظيف الاسم العربي وتجهيزه ليكون اسماً لمجلد في Google Drive"""
        # إبقاء الحروف العربية والإنجليزية والأرقام فقط
        clean_name = re.sub(r'[^\w\s\u0600-\u06FF]', '', title_ar).strip()
        return f"{sku} - {clean_name}"[:50]
