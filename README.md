# Parcel Vision

Pochta yorlig'i suratidan ma'lumotni avtomatik ajratib oluvchi xizmat.
Surat yuklanadi — qabul qiluvchi, jo'natuvchi, manzil, telefon, trek raqami va
og'irlik strukturali JSON bo'lib qaytadi va bazaga yoziladi.

**Model lokal ishlaydi.** Mijoz ma'lumoti mashinadan chiqmaydi, API kaliti va
oylik to'lov kerak emas.

## Nega lokal model

Pochta yorlig'ida mijozning ismi, manzili va telefoni bo'ladi. Buni tashqi
API'ga yuborish — ma'lumot himoyasi masalasi. Shuning uchun default provayder
**Ollama + Qwen2.5-VL**: model o'z serveringizda turadi, trafik tashqariga
chiqmaydi, doimiy xarajat nol.

Aniqlik muhimroq bo'lgan joy uchun **Claude** provayderi ham bor — konfiguratsiyada
bitta qator o'zgaradi, kod o'zgarmaydi.

## Arxitektura

```
Surat ──> FastAPI ──> VisionProvider ──> strukturali JSON ──> SQLite
                           │
              ┌────────────┴────────────┐
         OllamaProvider           ClaudeProvider
      (lokal, tekin, maxfiy)    (pullik, aniqroq)
```

`VisionProvider` — umumiy interfeys. **Yangi provayder qo'shish** uchun shu
interfeysni implement qilgan bitta klass yozib, registrga bir qator qo'shiladi;
boshqa hech qayerga tegilmaydi.

## Yo'l-yo'lakay topilgan nuqson

Birinchi versiyada model maydonlarning yarmini bo'sh qoldirardi. Dastlab buni
model zaifligi deb o'ylab, 3B dan 7B ga ko'tardim — **natija o'zgarmadi**.

Shuning uchun sababni izolyatsiya qildim. Modeldan sxemasiz, shunchaki
"suratdagi matnni o'qib ber" deb so'radim — **hamma matnni mukammal qaytardi**.
Demak muammo ko'rishda emas, `format` cheklovida edi.

Keyin bir xil matnda ikki sxemani solishtirdim:

| Sxema | Natija |
|---|---|
| `anyOf: [string, null]` (Pydantic `Optional` shunday beradi) | model buzildi, hammasini bitta maydonga tiqdi |
| oddiy `string` + `required` | hamma maydon to'ldi |

Ildiz sabab: Ollama'ning grammatik dekodlashi `anyOf` ni eplay olmaydi.

**Yechim:** modelga *tekis* sxema beriladi (har maydon `string`, topilmasa bo'sh
satr), bo'sh satr esa kod darajasida `None` ga aylantiriladi. Tashqi API
kontrakti o'zgarmadi — `LabelData` hamon `null` qaytaradi.

Tuzatgandan keyin **3B model ham 9/9 maydonni to'g'ri beradi**, ya'ni 7B shart
emas edi. Saboq: model hajmini oshirishdan oldin sababni o'lchash kerak.

| Model | Disk | Vaqt | Natija |
|---|---|---|---|
| `qwen2.5vl:3b` | 3,2 GB | ~16 s | 9/9 |
| `qwen2.5vl:7b` | 6,0 GB | ~15 s | 9/9, `service_type` tozaroq |

## Ikkinchi topilma: ishonchlilikni modelga ishonib bo'lmaydi

Qo'lda yozilgan yorliqda model manzilni to'g'ri o'qiydi, lekin harf va raqamlarda
adashadi (`Shota` -> `shato`, `112` -> `412`). Bunday maydonni operator
tekshirishi kerak, shuning uchun ular `uncertain_fields` ga tushishi shart.

Avval buni modeldan so'radim — ko'rsatmada aniq yozilgan va misol ham berilgan
bo'lsa-da, **bajarmadi**. Shuning uchun qoida kodga ko'chirildi: ko'rish bosqichi
yozuv qo'lda ekanini bildirsa, to'ldirilgan har bir maydon avtomatik belgilanadi.

Saboq: modeldan *baho* so'rash mumkin, lekin *kafolat* kodda bo'lishi kerak.

Yo'l-yo'lakay yana ikkita nuqson tuzatildi:
- model bo'sh maydonga `"null"` degan **satr** yozardi — endi `None` ga aylantiriladi
- bo'sh maydonlar ham "ishonchsiz" deb belgilanardi — operator uchun ma'nosiz,
  endi faqat to'ldirilganlari belgilanadi

## Natijalar

| Surat | Maydon | Vaqt | Ishonchsizlik |
|---|---|---|---|
| Bosma yorliq | 9/9 to'g'ri | ~17 s | yo'q (to'g'ri) |
| Qo'lyozma, qiyshiq, soyada | 3/3 to'g'ri | ~10 s | uchalasi belgilangan (to'g'ri) |

Qo'lyozmada 3/9 — bu kamchilik emas: o'sha qog'ozda jo'natuvchi, trek raqami va
og'irlik umuman yo'q edi.

## Ma'lum cheklovlar

- Qo'l yozuvida harf/raqam xatolari bo'ladi. Tizim buni yashirmaydi —
  maydonni "tekshirilsin" deb belgilaydi.
- Bitta tomon ko'rsatilgan qog'ozda u qabul qiluvchi deb olinadi.
- Birinchi so'rov sekinroq: model xotiraga ko'tariladi.

## Muhim qarorlar

**Javob sxemaga majburlanadi.** Model erkin matn emas, berilgan JSON sxemasi
bo'yicha javob qaytaradi (Ollama `format`, Claude `tool_choice`). Shuning uchun
javobni regex bilan parse qilish shart emas.

**Modelga beriladigan sxema API kontraktidan ajratilgan** — sababi yuqorida.

**Xatolik jimgina o'tmaydi.** Model javob bermasa yoki javobni sxemaga moslab
bo'lmasa, `VisionError` tashlanadi va API `502` qaytaradi. Bo'sh natija
qaytarilmaydi — aks holda noto'g'ri ma'lumot jimgina hisobotga tushib ketadi.

**Ishonch darajasi.** Model o'zi ishonchi past bo'lgan maydonlarni
`uncertain_fields` ro'yxatiga qo'shadi; interfeysda ular sariq rangda
belgilanadi. Operator hamma maydonni emas, faqat shularni tekshiradi.

## Ishga tushirish

```bash
# 1. Model (bir marta, ~3.2 GB)
brew install ollama
ollama serve &
ollama pull qwen2.5vl:3b

# 2. Ilova
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

`http://localhost:8000` — interfeys ochiladi.

## API

| Endpoint | Nima qiladi |
|---|---|
| `POST /api/extract` | Surat yuboriladi (multipart `file`), strukturali natija qaytadi |
| `GET /api/extractions?limit=50` | Oxirgi natijalar |
| `GET /api/health` | Qaysi provayder faol va tayyormi |

```bash
curl -F "file=@samples/label.jpg" http://localhost:8000/api/extract
```

## Konfiguratsiya

| O'zgaruvchi | Default | Izoh |
|---|---|---|
| `VISION_PROVIDER` | `ollama` | `ollama` yoki `claude` |
| `OLLAMA_MODEL` | `qwen2.5vl:3b` | Kattaroq model: `qwen2.5vl:7b` |
| `OLLAMA_TIMEOUT` | `120` | Soniya |
| `ANTHROPIC_API_KEY` | — | Faqat `claude` provayderi uchun |
| `DB_PATH` | `data/extractions.db` | SQLite fayli |

## Stek

Python · FastAPI · Pydantic · Ollama (Qwen2.5-VL) · Anthropic API · SQLite · HTML/JS
