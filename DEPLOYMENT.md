# Deployment

## Supabase

1. สร้าง Supabase Project
2. เปิด SQL Editor และรัน `supabase_schema.sql`
3. รัน `seed_2026.sql`
4. คัดลอก Project URL และ anon/publishable key
5. ตั้งค่า Authentication ตามคำแนะนำใน `README.md`

## GitHub

1. สร้าง Private Repository
2. Push ไฟล์ทั้งหมด ยกเว้นไฟล์ที่ `.gitignore` ระบุ
3. ตรวจว่าไม่มี `.streamlit/secrets.toml`, `.env` หรือกุญแจจริงใน Commit

## Streamlit Community Cloud

1. เลือก GitHub Repository
2. ตั้ง Main file path เป็น `app.py`
3. ใส่ค่าใน Advanced settings > Secrets:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_ANON_KEY = "YOUR_ANON_OR_PUBLISHABLE_KEY"
TEAM_SECRET_KEY = "รหัสเชิญทีมที่ยาวและคาดเดายาก"
```

4. Deploy
5. สมัครบัญชีแรกเพื่อให้ Trigger ตั้งเป็นผู้ดูแล
6. ทดสอบบัญชีสมาชิกอีกหนึ่งบัญชี ตั้งแต่ Secret Key จนถึงการอนุมัติ

## หลังแก้โค้ด

Push Commit ใหม่ไปยัง Branch ที่ Streamlit ใช้อยู่ ระบบจะนำเวอร์ชันใหม่ขึ้นให้อัตโนมัติ
