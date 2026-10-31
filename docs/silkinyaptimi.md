# «Silkinyaptimi?» — batafsil qoidalar

Kechasi silkindi. Zilzila bo'ldimi yoki tuyuldimi? Bu Telegram bot bir tugma bilan
javob beradi. Ma'lumot ikki ochiq, bepul manbadan olinadi: **USGS** va **EMSC**.

## Imkoniyatlar

| Tugma | Nima qiladi |
|---|---|
| 📍 Joylashuvni yangilash | Joy bir marta so'raladi va bazada saqlanadi. Shu koordinatadan vaqt mintaqasi ham aniqlanadi. |
| 🌍 Silkindimi? | Oxirgi 30 daqiqada joyingizda sezilishi mumkin bo'lgan hodisa bo'lganini soniyalarda aytadi: qayerda, magnituda, chuqurlik, masofa, mahalliy vaqt, manba. Hodisa topilmasa, bot 30 daqiqa kuzatib turadi va hodisa paydo bo'lsa yozadi. Hech narsa topilmasa, buni ham aytadi. |
| 🔔 / 🔕 Obuna | Joyingizda sezilishi mumkin bo'lgan har bir zilzila haqida avtomatik xabar keladi. |

## «Seziladigan» nimani anglatadi

Zilzila **seziladigan** hisoblanadi, agar sizdan gipotsentrgacha bo'lgan masofa
(epitsentrgacha masofa va chuqurlik hisobga olinadi) quyidagi radiusdan kichik bo'lsa:

| Magnituda | Sezilish radiusi |
|---|---|
| < 2.5 | sezilmaydi deb hisoblanadi |
| 2.5 – 3.0 | 15 km |
| 3.0 – 4.0 | 40 km |
| 4.0 – 5.0 | 120 km |
| 5.0 – 6.0 | 300 km |
| 6.0 – 7.0 | 800 km |
| ≥ 7.0 | 1500 km |

Nega aynan shunday:

- Radiuslar USGS «Did You Feel It?» hisobotlaridagi odatiy sezilish masofalariga
  tayanadi. Odam M3 ni bir necha o'n km ichida sezadi, M4 ni 100 km atrofida sezadi.
  Kuchli zilzilalar esa yuzlab km uzoqda seziladi.
- Radiuslar ataylab biroz keng olingan. Markaziy Osiyoda yer qobig'i tebranishni uzoqqa
  yetkazadi. Masalan, Hindukushdagi chuqur (~200 km) M6+ zilzilalar Toshkentda
  muntazam seziladi.
- Chuqurlik hisobga olinadi. 150 km chuqurlikdagi M3 zilzila tepasida turgan odam
  uchun ham sezilmaydi.
- Manbalar har xil magnituda bersa, sezilishni **kattarog'i** bo'yicha baholaymiz.
  Sezilgan zilzila haqida jim qolgandan ko'ra, "sezilgan bo'lishi mumkin" deb
  yozish yaxshiroq.
- Xabarda kuch ham taxminan aytiladi. Radiusning uchdan biri ichida bo'lsa
  "aniq sezilgan bo'lishi mumkin" deyiladi, undan uzoqda "yengil" deyiladi.

Bu qoidalar `bot/services/earthquake.py` faylidagi `FELT_RADIUS_KM` ro'yxatida turadi.

## Ikki manba, bitta hodisa

USGS va EMSC bitta silkinishni har xil tasvirlaydi. Vaqt bir necha soniya farq
qiladi, koordinata o'nlab km farq qiladi, magnituda turlari ham har xil (mb, ML, Mw).
Ikki yozuv **bitta zilzila** deb hisoblanadi, agar:

- ular har xil manbadan kelgan bo'lsa (bir manbaning ikki hodisasi hech qachon
  birlashmaydi, chunki bu ketma-ket silkinishlar bo'lishi mumkin);
- vaqt farqi ≤ 60 soniya bo'lsa;
- epitsentrlar orasidagi masofa ≤ 100 km bo'lsa;
- magnituda farqi ≤ 1.0 bo'lsa.

Birlashtirilgan hodisa barcha manba ID'larini saqlaydi (`USGS:us7000…`,
`EMSC:20261031_…`). Yuborilgan xabarlar ana shu ID'lar bo'yicha belgilanadi.
Shuning uchun ikkinchi manba 10 daqiqa kechikib kelsa ham xabar qayta yuborilmaydi.

## Magnitudalar farq qilsa, kimga ishonish kerak

Ikkala qiymat ham ko'rsatiladi, ishonchlirog'i sababi bilan belgilanadi. Tartib:

1. **Moment magnituda (Mw, Mww).** Bu kuchli zilzila energiyasini eng to'g'ri
   o'lchaydi. Qaysi manbada bo'lsa, o'sha ustun.
2. **Seysmolog tekshirgan qiymat.** USGS `status = reviewed`.
3. **EMSC.** Kichik va o'rta zilzilalarda EMSC hududdagi mahalliy agentliklar
   (masalan, Qozog'iston NDC, O'zbekiston seysmologiya instituti) o'lchovini
   beradi. USGS esa O'rta Osiyo uchun ko'pincha uzoq stansiyalar bo'yicha `mb`
   hisoblaydi va avtomatik yozuvni kech yangilaydi.

## Vaqt mintaqasi

Manbalar vaqtni UTC'da beradi. Joylashuv saqlanganda koordinatadan IANA mintaqasi
aniqlanadi (`timezonefinder`, internet kerak emas), masalan `Asia/Tashkent` yoki
`Asia/Bishkek`. Har bir xabarda mahalliy vaqt, UTC farqi va "12 daqiqa oldin"
ko'rinishidagi nisbiy vaqt beriladi. Kecha yarmidan keyin sana ham to'g'ri chiqadi.

## «Hali bilmayman» javobi

Zilzila haqidagi rasmiy ma'lumot odatda 2–20 daqiqada chiqadi. Shuning uchun:

- Hech narsa topilmasa, bot "hech narsa yo'q" deb qo'ymaydi. U ma'lumot hali
  yo'lda bo'lishi mumkinligini tushuntiradi va 30 daqiqa o'zi kuzatishni va'da
  qiladi. Foydalanuvchiga ekran oldida kutish shart emas.
- Kuzatuv davomida hodisa paydo bo'lsa, darhol xabar beradi.
- 30 daqiqa ichida hech narsa topilmasa, bot o'zi tinchlantiruvchi yakuniy xabar
  yuboradi.
- Manbalar javob bermasa, bu zilzila bilan bog'liq emasligi aytiladi va kuzatuv
  baribir yoqiladi. Bitta manba ishlamasa, qolgani bilan tekshiriladi va bu ochiq
  aytiladi.
- Monitoring yangi hodisani vaqti bo'yicha emas, ID'si bo'yicha aniqlaydi. Shu
  sababli kechikib e'lon qilingan zilzila ham o'tkazib yuborilmaydi.
