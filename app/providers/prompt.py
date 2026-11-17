"""Provayderlar uchun ko'rsatma matnlari."""

# --- 1-bosqich: ko'rish ---
READ_PROMPT = (
    "Bu pochta yorlig'i, yuk hujjati yoki manzil yozilgan qog'oz. "
    "Suratdagi BARCHA matnni qatorma-qator o'qib ber. Hech narsani tushirib "
    "qoldirma: raqamlar, telefonlar, manzillar, sarlavhalar — hammasi kerak.\n"
    "Faqat o'qigan matnni yoz. Izoh va kirish jumlasi qo'shma.\n"
    "Agar matn QALAM yoki RUCHKA bilan QO'LDA yozilgan bo'lsa, matndan keyin "
    "alohida oxirgi qatorga QOLYOZMA deb yoz. Printerda chop etilgan bosma "
    "matn bo'lsa, hech narsa qo'shma."
)

# --- 2-bosqich: tartiblash ---
STRUCTURE_SYSTEM = (
    "Sen yorliqdan o'qilgan matnni maydonlarga ajratuvchi tizimsan.\n\n"
    "QOIDALAR:\n"
    "1. Matnda nechta tomon borligini aniqla. Agar FAQAT BITTA odam "
    "ko'rsatilgan bo'lsa (bitta ism, bitta telefon, bitta manzil), u "
    "QABUL QILUVCHI hisoblanadi -> recipient_name, recipient_phone, "
    "recipient_address. sender_* maydonlari bo'sh qoladi.\n"
    "2. Ko'cha, shahar yoki uy raqami bo'lgan qator — MANZIL, uni *_address "
    "ga yoz. Hech qachon tracking_number ga yozma.\n"
    "3. tracking_number — faqat jo'natma KODI (masalan 'UZ 4827 9163 05'). "
    "Matnda bunday kod bo'lmasa, bo'sh qoldir.\n"
    "4. Matnda bo'lmagan maydonni bo'sh satr qoldir. 'null' deb YOZMA.\n"
    "5. Matnda QO'LYOZMA so'zi bo'lsa, yozuv qo'lda yozilgan: o'qishda xato "
    "bo'lishi mumkin, shuning uchun TO'LDIRGAN maydonlaringni "
    "uncertain_fields ga qo'sh. QO'LYOZMA so'zining o'zi maydon emas.\n"
    "6. uncertain_fields ga faqat MAYDON NOMLARINI yoz, qiymat emas.\n\n"
    "MISOL.\n"
    "Matn:\n"
    "Toshkent Amir Temur 15\n"
    "+998 90 111 22 33\n"
    "Bobur Aliyev\n"
    "QO'LYOZMA\n"
    "Javob: recipient_name='Bobur Aliyev', recipient_phone='+998 90 111 22 33', "
    "recipient_address='Toshkent Amir Temur 15', qolgani bo'sh, "
    "uncertain_fields=['recipient_name','recipient_phone','recipient_address']"
)

STRUCTURE_USER = (
    "Yorliqdan o'qilgan matn:\n"
    "---\n{text}\n---\n\n"
    "Shu matndan maydonlarni ajrat:\n"
    "jo'natuvchi -> sender_name, sender_phone, sender_address\n"
    "qabul qiluvchi -> recipient_name, recipient_phone, recipient_address\n"
    "jo'natma kodi -> tracking_number\n"
    "og'irlik -> weight\n"
    "xizmat turi -> service_type"
)

SYSTEM_PROMPT = STRUCTURE_SYSTEM
USER_PROMPT = (
    "Ushbu pochta yorlig'idan maydonlarni ajratib ol. "
    "Telefon raqamlarini suratdagidek, o'zgartirmasdan yoz."
)
