# DAILYLOOK.SM Team Calendar

ปฏิทินงานทีมสำหรับ dailylook.sm สร้างด้วย Streamlit และ Supabase ทุกคนที่เข้าสู่ระบบจะเห็นข้อมูลชุดเดียวกัน

## ฟังก์ชัน

- เข้าสู่ระบบด้วยอีเมลและรหัสผ่าน
- งานแบบวันเดียวหรือช่วงวันที่
- สีหมุด 6 สีแทนประเภทงาน
- ผู้รับผิดชอบ/ผู้เกี่ยวข้องหลายคน
- งานที่ต้องติดตาม, รายการแจ้งข้อมูล และวันหยุด
- รายการแจ้งข้อมูล/วันหยุดไม่ต้องติ๊กและไม่นับเป็นงานค้าง
- สถานะ ยังไม่เริ่ม / กำลังทำ / รอตรวจ / เสร็จแล้ว
- มุมมองปฏิทินและกำหนดการทั้งหมดตั้งแต่ “ณ วันที่”
- ค้นหาและกรองตามสี คน และสถานะ
- ประวัติว่าใครเพิ่ม แก้ไข หรือลบรายการ เมื่อใด
- สิทธิ์ผู้ดูแลและสมาชิก
- Secret Key ของทีมสำหรับสมัครบัญชี และการอนุมัติสมาชิกโดยผู้ดูแล
- ส่งออกข้อมูลสำรองเป็น JSON, CSV และ Markdown

## 1. ตั้งค่า Supabase

1. สร้าง Project ที่ [Supabase](https://supabase.com/dashboard)
2. เปิด SQL Editor
3. รัน `supabase_schema.sql`
4. รัน `seed_2026.sql` เพื่อเพิ่มวันหยุดร้านปี 2569 ทั้ง 15 วัน และรายการ “ส่ง Mycloud ไม่ได้” วันที่ 6–7 สิงหาคม 2569
5. เปิด Project Settings > API แล้วเก็บ Project URL และ anon public key
6. ใน Authentication > URL Configuration เพิ่ม URL ของ Streamlit หลัง Deploy
7. บัญชีแรกที่สมัครจะเป็น `admin` อัตโนมัติ บัญชีถัดไปเป็น `member` และผู้ดูแลปรับสิทธิ์จากหน้า “ทีม” ได้

## 2. รันบนเครื่อง

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p .streamlit
```

สร้าง `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_ANON_KEY = "YOUR_ANON_KEY"
TEAM_SECRET_KEY = "ตั้งรหัสลับของทีมที่คาดเดายาก"
```

จากนั้นรัน:

```bash
streamlit run app.py
```

## 3. Deploy บน Streamlit Community Cloud

1. Push โฟลเดอร์นี้ขึ้น GitHub
2. เข้า [Streamlit Community Cloud](https://share.streamlit.io/)
3. เลือก Repository และกำหนด Main file path เป็น `app.py`
4. เปิด Advanced settings > Secrets แล้วใส่:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_ANON_KEY = "YOUR_ANON_KEY"
TEAM_SECRET_KEY = "ตั้งรหัสลับของทีมที่คาดเดายาก"
```

5. กด Deploy

อย่าใส่ Supabase service-role/secret key ใน GitHub หรือในตัวแอปนี้ แอปใช้เฉพาะ
anon/publishable key ร่วมกับ Row Level Security ส่วน `TEAM_SECRET_KEY` เป็นรหัสเชิญทีม
ที่สร้างขึ้นเองและเก็บใน Streamlit Secrets เท่านั้น

## 4. เอกสารสำหรับรับช่วงงาน

- `PROJECT_CONTEXT.md` — เป้าหมายและกติกาที่ห้ามหาย
- `FEATURES.md` — ฟังก์ชันที่มีแล้ว
- `CHANGELOG.md` — ประวัติการแก้ไข
- `DATABASE_SCHEMA.md` — คำอธิบายฐานข้อมูลและสิทธิ์
- `DEPLOYMENT.md` — ขั้นตอนนำขึ้นระบบ
- `TODO.md` — งานที่ยังเหลือ
- `docs/decisions/` — เหตุผลของการตัดสินใจทางเทคนิค

## 5. ตรวจโปรเจกต์ก่อน Deploy

```bash
python scripts/validate_project.py
```
