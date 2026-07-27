# Decision 0001: Storage and secrets

## Status

Accepted — 2026-07-27

## Decision

- ใช้ Supabase เป็นฐานข้อมูลกลางสำหรับข้อมูลที่หลายคนแก้ไข
- ใช้ Markdown ใน GitHub สำหรับบริบท ฟังก์ชัน ประวัติ และคู่มือติดตั้ง
- ใช้ Streamlit Secrets สำหรับ `TEAM_SECRET_KEY`, URL และ anon/publishable key
- ไม่เก็บข้อมูลปฏิทินหลักใน Markdown
- ไม่ใช้ Supabase service-role key ในตัวแอป

## Reason

ไฟล์ Markdown เหมาะกับการถ่ายทอดความรู้ให้คนหรือ AI แต่ไม่เหมาะกับการเขียนพร้อมกัน
หลายคน Supabase จัดการข้อมูลร่วมกัน การยืนยันตัวตน และสิทธิ์ระดับแถวได้ดีกว่า
