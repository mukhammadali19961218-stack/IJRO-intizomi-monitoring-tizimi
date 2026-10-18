# IJRO INTIZOMI MONITORING TIZIMI (IES)

Davlat tashkilotida ijro intizomini nazorat qilish, topshiriqlar bajarilishini monitoring qilish, muddatlar va yuqori xavfdagi vazifalarni real vaqt rejimida kuzatish uchun mo‘ljallangan to‘liq avtomatlashtirilgan mahalliy (local) platforma.

---

## 🚀 ASOSIY IMKONIYATLAR

1. **Texnologik Stack:**
   - **Frontend:** React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite (SPA).
   - **Backend:** Mahalliy Node.js (Express), o‘rnatilgan yuqori tezlikdagi SQLite (`node:sqlite`), `bcryptjs`, `jsonwebtoken`.
   - **Xavfsizlik:** Yagona admin hisobi, parollar xeshlangan (bcrypt), barcha API so‘rovlari JWT token bilan himoyalangan.
   - **Ma'lumotlar saqlanishi:** Ma'lumotlar SQLite bazasida (`database/dashboard.db`) xavfsiz saqlanadi, dastur qayta ishga tushganda yoki sahifa yangilanganda yo‘qolmaydi.

2. **Rasmiy va Zamonaviy Dizayn (Talab 2):**
   - Interfeys to‘liq o‘zbek tilida.
   - Oq va och kulrang rasmiy fon, to‘q ko‘k aksentlar, o‘qilishi oson jadvallar va ixcham kartochkalar.
   - Chap menyuda aniq 3 ta bo‘lim: **“Umumiy ko‘rinish”**, **“Topshiriqlar”**, **“Sozlamalar”**.
   - Yuqori panelda **“Ma’lumotlarni yangilash”** tugmasi va oxirgi muvaffaqiyatli yangilanish vaqti.

3. **Umumiy Ko‘rinish va Svod (Talab 3):**
   - **5 ta asosiy KPI ko‘rsatkichi:**
     - Jami topshiriqlar soni
     - Bajarilgan topshiriqlar soni (va foizi)
     - Jarayondagi topshiriqlar soni
     - Muddati o‘tgan topshiriqlar soni (qizil indikator)
     - Yuqori xavf topshiriqlari (alohida sariq indikator, jami songa qayta qo‘shilmaydi)
   - **Boshqarmalar va Rahbarlar:** Rahbar rasmi (yoki monogramma harflar), F.I.Sh., boshqarma nomi, ko‘rsatkichlar va bajarilish foizi progress bari.
   - **Interaktivlik:** Har qanday kartochka yoki boshqarma bosilganda to‘g‘ridan-to‘g‘ri tegishli topshiriqlar ro‘yxati ochiladi.
   - **Barcha faol manbalarning jamlangan svod jadvali.**

4. **Universal Excel Importi va Ustunlarni Moslashtirish (Talab 4):**
   - 7–8 ta turli tuzilishdagi Excel fayllarini alohida import qilish (bitta majburiy shablonga bog‘lanmagan).
   - Har bir fayl alohida topshiriq/yo‘nalishga biriktiriladi va uning alohida svodi mavjud.
   - Varaq (sheet) va sarlavha qatorini (header row) tanlash imkoniyati.
   - Ko‘p tilli (o‘zbekcha, ruscha, inglizcha) ustunlarni avtomatik aniqlash (Auto-Detection).
   - Aniqlanmaganlarini admin oldindan ko‘rish oynasida moslashtiradi va bu moslashuv manba uchun saqlanadi.
   - Bo‘sh qatorlar, birlashtirilgan kataklar (merged cells) va turli sana formatlarini to‘g‘ri qabul qilish.
   - "Jami" va oraliq jami qatorlarini filtrlab, ikki marta hisoblamaslik.

5. **Eski Ma’lumotlarni Xavfsiz Almashtirish (Talab 5):**
   - Har bir topshiriq/manba uchun doimiy ID (`task_1`, `task_2`, ...).
   - Mavjud manbaga yangi fayl yuklanganda FAQAT shu manbaning eski ma'lumotlari yangilanadi, boshqa manbalar saqlanadi.
   - Eski va yangi yozuvlar birlashtirilmaydi, dublikat paydo bo‘lmaydi (100 ta o‘rniga 80 ta yuklansa, natija aniq 80 bo‘ladi).
   - **Atomik tranzaksiya:** yangi fayl to‘liq tekshirilib, xatosiz bo‘lsagina almashtiriladi; xatolik yuz bersa, eski ishlaydigan ma'lumotlar saqlanadi (ROLLBACK).

6. **Avtomatik Yangilanish (Talab 6):**
   - Oddiy yuklangan nusxa bilan kompyuterdagi kuzatiladigan Excel faylini farqlash.
   - Mahalliy papkani (`watch_directory`) kuzatish (Watchdog / Chokidar).
   - Excel faylida Ctrl+S bosilganda backend o‘zgarishni aniqlaydi, yozish tugashini kutadi va manbani avtomatik qayta import qiladi.
   - "Ma’lumotlarni yangilash" tugmasi barcha ulangan manbalarni qayta o‘qiydi.

7. **Hisob-kitob Qoidalari (Talab 7):**
   - Bajarilish foizi = `bajarilgan / jami * 100` (jami nol bo‘lsa, 0%).
   - Bajarilmagan va muddati o‘tgan topshiriq “Muddati o‘tgan” hisoblanadi.
   - Yuqori xavf qoidasi: muddati kelishiga 3 kun yoki undan kam qolgan topshiriqlar; chegarani Sozlamalarda (1–30 kun) o‘zgartirish mumkin.
   - Sanalar `Asia/Tashkent` vaqt mintaqasida hisoblanadi.

---

## 🖥 WINDOWSDA O‘RNATISH VA ISHGA TUSHIRISH

### 1-usul: Bitta tugma orqali ishga tushirish (Tavsiya etiladi)

Loyiha papkasidagi **`start.bat`** faylini ikki marta bosing.

U avtomatik ravishda:
1. Node.js borligini tekshiradi;
2. Server paketlarini tekshiradi;
3. Serverni ishga tushiradi (`http://127.0.0.1:8000`);
4. Standart brauzeringizda tizimni ochadi.

### 2-usul: Buyruqlar satri orqali ishga tushirish

```powershell
# 1. Server papkasiga o'tish va paketlarni o'rnatish
cd d:\dashboard\server
npm install

# 2. Serverni ishga tushirish
node src/index.js
```

So‘ng brauzerda quyidagi manzilni oching:
👉 **`http://127.0.0.1:8000`**

---

## 🔐 STANDART KIRISH MA'LUMOTLARI

- **Foydalanuvchi nomi (Login):** `admin`
- **Parol:** `admin123`

*(Tizimga kirgach, "Sozlamalar" bo‘limidan administrator parolini xohlagan vaqtda o‘zgartirishingiz mumkin)*

---

## 📂 EXCEL MANBALARINI ULASH VA YANGILASH YO‘RIQNOMASI

### 1. Yangi Excel faylini import qilish:
1. Chap menyudagi **“Sozlamalar”** bo‘limiga o‘ting.
2. **“Yangi manba qo‘shish”** tugmasini bosing.
3. Manba nomini kiriting va kompyuterdan `.xlsx` faylni tanlang.
4. Tizim avtomatik ravishda varaqlar va ustunlarni aniqlaydi. Kerak bo‘lsa, varaqni, sarlavha qatorini va ustunlarni moslashtiring.
5. **“Manbani saqlash va import qilish”** tugmasini bosing.

### 2. Mavjud manbaga yangi Excel yuklash (Eski ma'lumotlarni almashtirish):
1. **“Sozlamalar”** bo‘limida kerakli manba kartochkasidagi **“Faylni almashtirish”** tugmasini bosing.
2. Yangi Excel faylni tanlang va tasdiqlang.
3. Faqat shu manbaning eski yozuvlari yangi ma'lumotlar bilan to‘liq almashtiriladi, boshqa manbalarga tegilmaydi!

### 3. Kompyuterdagi Excel faylini saqlashda avtomatik yangilanish:
1. **“Sozlamalar”** bo‘limida **“Backend kuzatadigan mahalliy papka yo‘li”**ni belgilang (masalan, `D:\dashboard\data\watched`).
2. Shu papkadagi Excel faylini ochib, ma'lumotlarni o‘zgartiring va **Ctrl+S** ni bosing.
3. Dashboard sahifasida hech qanday F5 tugmasisiz bir necha soniyada ko‘rsatkichlar avtomatik yangilanadi!
