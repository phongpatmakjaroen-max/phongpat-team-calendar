-- Run after supabase_schema.sql. Safe to run more than once.
insert into public.events
  (title, details, start_date, end_date, item_type, pin_color, priority, status)
values
  ('วันปีใหม่', 'วันหยุดร้านประจำปี 2569', '2026-01-01', '2026-01-01', 'holiday', 'brown', 'normal', 'not_started'),
  ('ชดเชยวันปีใหม่', 'วันหยุดร้านประจำปี 2569', '2026-01-02', '2026-01-02', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันสงกรานต์', 'วันหยุดร้านประจำปี 2569', '2026-04-13', '2026-04-13', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันสงกรานต์', 'วันหยุดร้านประจำปี 2569', '2026-04-14', '2026-04-14', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันสงกรานต์', 'วันหยุดร้านประจำปี 2569', '2026-04-15', '2026-04-15', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันแรงงานแห่งชาติ', 'วันหยุดร้านประจำปี 2569', '2026-05-01', '2026-05-01', 'holiday', 'brown', 'normal', 'not_started'),
  ('ชดเชยวันวิสาขบูชา', 'วันหยุดร้านประจำปี 2569', '2026-06-01', '2026-06-01', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันเฉลิมพระชนมพรรษาสมเด็จพระนางเจ้าฯ พระบรมราชินี', 'วันหยุดร้านประจำปี 2569', '2026-06-03', '2026-06-03', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันเฉลิมพระชนมพรรษาพระบาทสมเด็จพระเจ้าอยู่หัว', 'วันหยุดร้านประจำปี 2569', '2026-07-28', '2026-07-28', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันอาสาฬหบูชา', 'วันหยุดร้านประจำปี 2569', '2026-07-29', '2026-07-29', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันแม่แห่งชาติ', 'วันหยุดร้านประจำปี 2569', '2026-08-12', '2026-08-12', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันคล้ายวันสวรรคต รัชกาลที่ 9', 'วันหยุดร้านประจำปี 2569', '2026-10-13', '2026-10-13', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันปิยมหาราช', 'วันหยุดร้านประจำปี 2569', '2026-10-23', '2026-10-23', 'holiday', 'brown', 'normal', 'not_started'),
  ('ชดเชยวันพ่อแห่งชาติ', 'วันหยุดร้านประจำปี 2569', '2026-12-07', '2026-12-07', 'holiday', 'brown', 'normal', 'not_started'),
  ('วันสิ้นปี', 'วันหยุดร้านประจำปี 2569', '2026-12-31', '2026-12-31', 'holiday', 'brown', 'normal', 'not_started'),
  ('ส่ง Mycloud ไม่ได้', 'รายการแจ้งข้อมูล ไม่ต้องติ๊กเสร็จ', '2026-08-06', '2026-08-07', 'info', 'orange', 'normal', 'not_started')
on conflict (title, start_date, end_date, item_type) do nothing;
