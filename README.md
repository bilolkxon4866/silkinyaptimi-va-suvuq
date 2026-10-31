# Silkinyaptimi? va Sovuq urishi

Ochiq, bepul ma'lumotlar asosidagi ikkita Telegram bot.

| Mahsulot | Bot | Kim uchun |
|---|---|---|
| 🌍 «Silkinyaptimi?» | **@BOT_USERNAME_1** | Kechasi silkinishdan uyg'onib, "zilzilami yoki tuyuldimi?" deb o'ylagan odam |
| ❄️ «Sovuq urishi» | **@BOT_USERNAME_2** | Toshkent va atrofidagi tomorqa egasi. Kechki sovuq bahorda o'rik guli va ko'chatni, kuzda uzumni nobud qiladi |

Ikkala bot ham o'rnatishsiz ishlaydi: havolani oching, **Start** bosing va joylashuvni yuboring.

## Tekshirish uchun nimani bosish kerak

### 🌍 Silkinyaptimi?

1. **Start** → **📍 Joylashuvni yangilash** → joylashuvni yuboring.
2. **🌍 Silkindimi?** Bot soniyalarda javob beradi.
   - Oxirgi 30 daqiqada yaqin atrofda seziladigan zilzila bo'lmasa (odatiy holat):
     bot tinchlantiradi va keyingi 30 daqiqa kuzatishni boshlaydi. Shu vaqt ichida
     hodisa paydo bo'lsa, o'zi yozadi. Bo'lmasa, oxirida "hech narsa bo'lmadi"
     deb xabar beradi.
   - Javobni zilzila bilan ko'rmoqchi bo'lsangiz, joylashuvni yaqinda zilzila bo'lgan
     hududga yuboring. Masalan, [USGS xaritasi](https://earthquake.usgs.gov/earthquakes/map/)
     yoki [EMSC](https://www.emsc-csem.org/) dan oxirgi 30 daqiqadagi M4+ hodisani
     toping va 📎 → Location orqali xaritada o'sha joyni tanlang.
3. **🔔 Obuna** bosilsa, seziladigan zilzilalar haqida avtomatik xabar keladi.

### ❄️ Sovuq urishi

1. **Start** → **📍 Joyni o'zgartirish** → joylashuvni yuboring. Javobda
   darhol 10 yillik arxivdan maslahat keladi: «Uzumni 18-oktabrgacha uzib oling,
   oxirgi 10 yilning 9 tasida birinchi sovuq shundan keyin kelgan».
2. **❄️ Yaqin kechalar**: keyingi 2 kecha sovuq bo'ladimi.
3. **🤔 Ishonsa bo'ladimi?**: bu model, termometr emas. Qanchalik aniqligi ham
   shu yerda tushuntiriladi.
4. **/namuna**: sovuq kutilganda keladigan ogohlantirish namunasi. Tekshiruv
   vaqtida haqiqiy sovuq bo'lmasligi mumkin, shuning uchun qo'shilgan.

## Ishga tushirish (lokal)

```bash
python -m venv venv
venv\Scripts\activate                 # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # tokenlarni @BotFather'dan olib yozing
python run.py                         # ikkala bot birga
python -m unittest discover -s tests -t .   # 21 ta test, internet kerak emas
```

Har bir botni alohida ham ishga tushirish mumkin: `python -m bot.main` yoki
`python -m frost.main`.

### Hosting (bepul)

[Render](https://render.com) → New → Blueprint → shu repo (`render.yaml`).
`BOT_TOKEN` va `FROST_BOT_TOKEN` qiymatlarini kiriting. Bepul tarif 15 daqiqa
so'rov kelmasa uxlab qoladi va bildirishnomalar to'xtaydi. Shuning uchun
[cron-job.org](https://cron-job.org) da servis manziliga har 10 daqiqada ping
qo'yiladi (`run.py` `/` manzilida `ok` qaytaradi).

## Nega aynan shu shakl

- **Telegram bot.** O'zbekistonda deyarli hamma Telegram'da, buvilar ham.
  O'rnatish va ro'yxatdan o'tish kerak emas. Bildirishnoma telefonga o'zi keladi.
  Ikkala mahsulotning asosiy qiymati ham shunda: "o'zi yozadi".
- **Tugmalar, buyruqlar emas.** Yarim tunda yoki bog'da `/check` yozib o'tirilmaydi.
- **So'z, grafik emas.** Topshiriq ham shuni so'raydi. Grafikni buvi o'qimaydi,
  "18-oktabrgacha uzing" degan gapni esa tushunadi.

## Nimani o'zim hal qildim

Batafsil: [docs/silkinyaptimi.md](docs/silkinyaptimi.md) va [docs/sovuq.md](docs/sovuq.md).

**Silkinyaptimi?**
- **«Seziladigan» zilzila.** Gipotsentrgacha masofa magnitudaga bog'liq radiusdan
  kichik bo'lishi kerak: M3 da 40 km, M4 da 120 km, M5 da 300 km, M6 da 800 km.
  Radiuslar Markaziy Osiyo uchun ataylab kengroq olingan, chunki Hindukushdagi
  chuqur zilzilalar Toshkentda seziladi.
- **Ikki manbani birlashtirish.** Ikki yozuv bitta zilzila hisoblanadi, agar
  vaqt farqi ≤ 60 s, masofa ≤ 100 km va magnituda farqi ≤ 1.0 bo'lsa. Bir
  manbaning ikki hodisasi hech qachon birlashmaydi.
- **Kimga ishonish.** Tartib: Mw → seysmolog tekshirgan qiymat → EMSC
  (mahalliy agentlik o'lchovi). Ikkala qiymat ham ko'rsatiladi, sababi bilan.
- **Kechikish.** Ma'lumot 2–20 daqiqa kechikib keladi. Shuning uchun
  "hali yo'q" degan javob o'rniga bot 30 daqiqa kuzatishni va'da qiladi.

**Sovuq urishi**
- **Uch daraja.** Yerda qirov: +2° va ochiq, shamolsiz tun. Sovuq: 0°.
  Kuchli sovuq: −2°. Ikki metrdagi nol va yerdagi qirov bir narsa emas.
- **«10 yildan 9 tasida».** 10 yil ichidagi ikkinchi eng kech bahorgi
  (ikkinchi eng erta kuzgi) sovuq sanasi olinadi. Eng yomon yil ham aytiladi.
- **Vaqt mintaqasi.** Hamma so'rovlar `timezone=auto` bilan beriladi. Usiz
  Open-Meteo GMT qaytaradi va "sovuq soat 1 da" degan noto'g'ri javob chiqadi.
- **Qishda jimlik.** Ogohlantirish faslini har bir joy uchun arxivdan
  hisoblaymiz, aks holda qishda har kuni xabar keladi.

## Nimani qisqartirdim

- **3-mahsulot qilinmadi.** Ikkita to'liq mahsulot uchta chala mahsulotdan yaxshi.
- Render bepul tarifida disk vaqtinchalik. Qayta deploydan keyin SQLite tozalanadi
  va foydalanuvchi joyni qayta yuborishi kerak bo'ladi. Doimiy disk pullik.
- Prognoz aniqligi (1–2°) o'zimiz o'lchagan raqam emas, umumiy taxmin.
  Prognozni arxiv bilan solishtirib, haqiqiy xatoni o'lchash keyingi qadam.
- Hovlidagi termometr ko'rsatkichini kiritib, botni "kalibrlash" imkoniyati yo'q.
- Ko'chat turi bo'yicha alohida chegara yo'q (pomidor, uzum, o'rik bitta jadvalda).
- Zilzila botida joyni nom bilan qidirish yo'q, faqat Telegram joylashuvi bor.
- Ikki manbadagi bir xil zilzilani birlashtirish faqat sun'iy test ma'lumotlarida
  tekshirilgan. Haqiqiy ikki manbali O'rta Osiyo hodisasida hali sinalmagan.

## Tuzilishi

```
run.py                    # ikkala bot bitta jarayonda + health server
bot/                      # «Silkinyaptimi?»
  main.py                 #   handlerlar, monitoring (har 60 s)
  database/db.py          #   SQLite: users, subscriptions, watches, sent_notifications
  services/earthquake.py  #   USGS/EMSC: olish, birlashtirish, sezilish
  services/messages.py    #   matnlar
  services/timezones.py   #   koordinata → vaqt mintaqasi
frost/                    # «Sovuq urishi»
  main.py                 #   handlerlar, monitoring (har soat)
  analysis.py             #   chegaralar, arxiv statistikasi, prognoz tunlari
  messages.py             #   matnlar
  openmeteo.py            #   Open-Meteo prognoz va arxiv (kesh bilan)
  db.py                   #   SQLite: users, climate_cache, alerts
tests/                    # 21 ta test, internetsiz
docs/                     # har bir mahsulot qoidalari batafsil
```

Ma'lumotlar: [USGS](https://earthquake.usgs.gov/fdsnws/event/1/),
[EMSC](https://www.seismicportal.eu/fdsnws/event/1/),
[Open-Meteo](https://open-meteo.com/). Hammasi bepul va kalitsiz.
Javoblar keshlanadi: prognoz 30 daqiqaga, 10 yillik arxiv xulosasi bazada doimiy saqlanadi.
