# «Sovuq urishi»: batafsil qoidalar

## «Sovuq urishi» nima: chegaralar

Sovuq urishining yagona ta'rifi yo'q. Ob-havo stansiyasi haroratni 2 m
balandlikda o'lchaydi, ko'chat esa yerda turadi. Ochiq va shamolsiz tunda yer
yuzi havodan 2–4° sovuqroq bo'ladi. Shuning uchun 2 m dagi «+1°» ko'chat
uchun allaqachon qirov bo'lishi mumkin. Biz uch darajani ajratamiz. Hammasi
modelning 2 m dagi harorati bo'yicha:

| Daraja | Shart | Nima nobud bo'ladi |
|---|---|---|
| ❄️ Yerda qirov | ≤ +2° **va** tun ochiq (bulut ≤ 30%) hamda shamolsiz (≤ 10 km/s), **yoki** model yer yuzini ≤ 0° deb hisoblasa | Pomidor, bodring, qalampir ko'chati, gullar |
| ❄️ Sovuq | ≤ 0° | Ochilgan o'rik va shaftoli guli, uzum bargi |
| ❄️ Kuchli sovuq | ≤ −2° | Gul va tugunchaning katta qismi, uzum. Quvurdagi suv muzlaydi |

Nega aynan shu raqamlar:

- **+2°.** Bu radiatsion qirovning keng tarqalgan belgisi. U modelning odatiy
  1–2° xatosini ham qoplaydi. Bulutli yoki shamolli tunda +2° qirov bermaydi,
  shuning uchun bunday tunda ogohlantirmaymiz. Aks holda bahorda har ikki
  kunda bir xabar kelib, odam e'tibor bermay qo'yadi.
- **0°.** Bu suv muzlaydigan nuqta va o'rik guli uchun xavf boshlanadigan chegara.
  Ochiq gul taxminan −1…−2° da shikastlanadi.
- **−2°.** Bu darajada mevali daraxt gulining sezilarli qismi nobud bo'ladi.
  Maslahat ro'yxati ham shunga qarab kengayadi: quvur va kranlarni o'rash qo'shiladi.

## Ogohlantirish qachon keladi

- Prognoz soat sayin tekshiriladi (Open-Meteo, 4 kun oldinga, soatlik).
- Tun soat 18:00 dan 09:00 gacha deb olinadi va ertalabki sana bilan ataladi.
- Keyingi **48 soat** ichidagi xavfli tun topilsa, darhol xabar keladi. Odatda
  bu 1–2 kun oldin bo'ladi.
- Prognoz kuchaysa (masalan, qirov sovuqqa aylansa), qayta yoziladi.
  Pasaysa, qayta yozilmaydi.
- O'sha kuni **kechqurun soat 17 dan keyin** bitta eslatma keladi. Agar
  prognoz yaxshilangan bo'lsa, "yaxshi xabar, sovuq kutilmayapti" deyiladi.
- **Qish o'rtasida ogohlantirish o'chadi.** Dekabr–fevralda deyarli har kecha
  sovuq, bunday xabar shovqin bo'lib qoladi. Fasl har bir joy uchun arxivdan
  hisoblanadi: odatiy oxirgi bahorgi sovuqdan 3 hafta oldin boshlanadi va
  odatiy birinchi kuzgi sovuqdan 3 hafta keyin tugaydi. Toshkentda bu
  taxminan 24-fevraldan 26-noyabrgacha.

## 10 yillik arxivdan bitta maslahat

1. Oxirgi 10 ta **to'liq** yil olinadi (hozir 2016–2025). Yarim yil
   «10 yildan 9 tasida» degan hisobni buzadi.
2. Soatlik harorat **joyning mahalliy vaqtida** so'raladi (`timezone=auto`).
   Har kunning eng past harorati va u qaysi soatda bo'lgani olinadi.
3. Har yil uchun oxirgi bahorgi va birinchi kuzgi sovuq sanasi topiladi.
   Bu ikkala chegara uchun alohida qilinadi: 0° va +2°.
4. Bahor uchun 10 yil ichidagi **ikkinchi eng kech** sana olinadi. Uning
   ma'nosi: «10 yildan 9 tasida shu kundan keyin sovuq bo'lmagan». Kuz uchun
   esa **ikkinchi eng erta** sana olinadi va undan bir kun oldin «shu kungacha
   yig'ib oling» deyiladi.
5. Ekranda faslga mos **bitta asosiy maslahat** chiqadi: bahorda "ko'chatni
   qachon o'tqazish", kuzda "uzumni qachongacha uzish". Qolgani pastda,
   qisqa satrlarda beriladi. Eng yomon yil ham ko'rsatiladi, chunki "10 yildan
   9 tasida" degani "har doim" degani emas.

Ko'chat (+2°, qirov) va gul yoki uzum (0°, sovuq) uchun chegara har xil
olingan. Pomidor ko'chati o'rik gulidan nozikroq.

## Vaqt mintaqasi

`timezone` parametri berilmasa, Open-Meteo vaqtni **GMT**'da qaytaradi.
Shunda «sovuq soat 1 da» degan javob chiqadi, aslida esa Toshkentda bu
soat 6. Kunlar ham noto'g'ri bo'linadi: Toshkentdagi tungi 00:00–05:00 oldingi
kunga tushib qoladi. Shuning uchun:

- arxiv ham, prognoz ham `timezone=auto` bilan so'raladi. Open-Meteo
  koordinatadan mintaqani o'zi aniqlaydi va uni bazaga saqlaymiz;
- "hozir" ham o'sha mintaqada hisoblanadi;
- testda sovuq soati mahalliy vaqtda tekshiriladi (`test_frost_hour_is_local`).

## Halollik: bu model, termometr emas

Har bir ogohlantirish va maslahat oxirida shu haqida bitta satr bor.
«🤔 Ishonsa bo'ladimi?» tugmasi to'liq tushuntiradi:

- model taxminan 10×10 km maydonni bir xil deb hisoblaydi va sizning
  balandligingizni ko'rsatadi;
- pastqam joy, soy va ariq bo'yi 1–3° sovuqroq bo'ladi, devor yoni esa iliqroq;
- 1 kunlik prognoz odatda 1–2° xato qiladi, 2 kunlik prognoz 2–3° gacha.
  Bu umumiy ma'lum taxmin. Biz uni o'zimiz o'lchamadik;
- maslahat: hovliga termometr osing va bir necha tong solishtiring.
