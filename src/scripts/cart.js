// منطق سلة المشتريات العائمة لمتجر ترند اليمن
export const initCart = (whatsappNumber) => {
    let cart = JSON.parse(localStorage.getItem('ty_cart')) ||;

    const updateWhatsAppLink = () => {
        let message = "أهلاً متجر ترند اليمن، أود طلب المنتجات التالية:\n";
        cart.forEach(item => {
            message += `- ${item.name} | السعر: ${item.price_yer} ريال يمني\n`;
        });
        return `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(message)}`;
    };

    console.log("🛒 Cart Engine Ready for WhatsApp:", whatsappNumber);
    // نظام الحماية: السعر اليمني يتم حسابه بناءً على معادلة 139.8
};
