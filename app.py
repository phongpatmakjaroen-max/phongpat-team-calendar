from __future__ import annotations

import calendar
import csv
import hmac
import html
import io
import json
import os
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st
from dateutil.parser import isoparse
from supabase import Client, create_client


st.set_page_config(
    page_title="DAILYLOOK.SM | ปฏิทินงานทีม",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

PIN_COLORS = {
    "blue": ("ฟ้า", "#7FA9B8"),
    "green": ("เขียว", "#8DAA91"),
    "orange": ("ส้ม", "#D9A06E"),
    "pink": ("ชมพู", "#D99AA5"),
    "purple": ("ม่วง", "#A796B8"),
    "brown": ("น้ำตาล", "#AA8B73"),
}
PIN_SYMBOLS = {
    "blue": "🔵",
    "green": "🟢",
    "orange": "🟠",
    "pink": "🩷",
    "purple": "🟣",
    "brown": "🟤",
}
HOLIDAY_COLOR = "#7296A3"
STATUS_LABELS = {
    "not_started": "ยังไม่เริ่ม",
    "in_progress": "กำลังทำ",
    "waiting": "รอตรวจ/รอข้อมูล",
    "done": "เสร็จแล้ว",
}
ITEM_LABELS = {
    "task": "📌 งาน / กำหนดส่ง",
    "info": "📣 แจ้งข้อมูล / นัดหมาย",
    "holiday": "🏖️ วันหยุด / ปิดร้าน",
}
RECURRENCE_LABELS = {
    "none": "ไม่ทำซ้ำ",
    "daily": "ทุกวัน",
    "weekly": "ทุกสัปดาห์",
    "monthly": "ทุกเดือน",
}
LEAVE_STATUS_LABELS = {
    "pending": "รออนุมัติ",
    "approved": "อนุมัติแล้ว",
    "rejected": "ไม่อนุมัติ",
}
ATTACHMENT_BUCKET = "event-attachments"
MONTHS_TH = [
    "",
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
]
BANGKOK_TZ = ZoneInfo("Asia/Bangkok")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Mali:wght@400;500;600;700&display=swap');
        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: "Mali", "Noto Sans Thai", sans-serif !important;
        }
        :root {
            --cream: #f7f3ed;
            --paper: #fffdf9;
            --sidebar: #eaf3f5;
            --brown: #4b382b;
            --brown-soft: #9d7454;
            --blue: #7f9eaa;
            --blue-soft: #e5f0f2;
            --line: #e5dbcf;
            --muted: #8c8378;
        }
        .stApp { background: #f7f3ed; color: var(--brown); }
        h1, h2, h3 { color: var(--brown); letter-spacing: -0.02em; }
        p, label, [data-testid="stCaptionContainer"] { color: var(--muted); }
        .block-container { padding-top: 1.6rem; max-width: 1500px; }
        [data-testid="stSidebar"] {
            background: var(--sidebar);
            border-right: 1px solid #d7e3e5;
        }
        [data-testid="stMetric"] {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 14px 18px;
            box-shadow: 0 8px 24px rgba(75, 56, 43, .05);
        }
        .calendar-cell {
            min-height: 138px;
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 0;
            padding: 10px;
            margin-bottom: 10px;
            overflow: hidden;
        }
        .calendar-day-link {
            display: block;
            color: inherit !important;
            text-decoration: none !important;
            border-radius: 12px;
        }
        .calendar-day-link:hover .calendar-cell {
            border-color: var(--blue);
            box-shadow: 0 7px 18px rgba(75, 56, 43, .10);
            transform: translateY(-1px);
        }
        .calendar-day-link:focus-visible {
            outline: 3px solid #b8d1d7;
            outline-offset: 2px;
        }
        .calendar-cell {
            transition: border-color .16s ease, box-shadow .16s ease, transform .16s ease;
            cursor: pointer;
        }
        .calendar-scroll {
            width: 100%;
            overflow-x: auto;
            padding: 2px 2px 8px;
            margin-bottom: 8px;
            -webkit-overflow-scrolling: touch;
        }
        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, minmax(112px, 1fr));
            gap: 8px;
            min-width: 820px;
        }
        .calendar-weekday {
            color: var(--brown);
            font-weight: 700;
            text-align: center;
            padding: 7px 3px;
            background: #edf4f5;
            border: 1px solid #d7e3e5;
            border-radius: 10px;
        }
        .calendar-cell.today { border: 2px solid #9bb9c2; background: var(--blue-soft); }
        .calendar-cell.outside { opacity: .44; }
        .st-key-calendar_native div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: repeat(7, minmax(0, 1fr)) !important;
            gap: .45rem !important;
        }
        .st-key-calendar_native div[data-testid="stColumn"] {
            width: auto !important;
            min-width: 0 !important;
            flex: none !important;
        }
        .st-key-calendar_native [class*="st-key-calday_"] {
            min-height: 118px;
            padding: .36rem;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,.88);
        }
        .st-key-calendar_native [class*="st-key-calday_today_"] {
            border: 2px solid #9bb9c2;
            background: var(--blue-soft);
        }
        .st-key-calendar_native [class*="st-key-calday_outside_"] { opacity: .44; }
        .st-key-calendar_native [class*="st-key-calday_"] button {
            min-height: 1.9rem !important;
            padding: .12rem .25rem !important;
            border: 0 !important;
            background: transparent !important;
            color: var(--brown) !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }
        .st-key-calendar_native [class*="st-key-calday_"] button:hover {
            background: var(--blue-soft) !important;
            color: #355b68 !important;
        }
        .day-number { font-weight: 700; font-size: 1.1rem; margin-bottom: 7px; }
        .event-chip {
            display:block;
            border-radius: 10px;
            padding: 5px 7px;
            margin: 4px 0;
            color: var(--brown);
            font-size: .78rem;
            line-height: 1.25;
            overflow: hidden;
        }
        .event-chip.holiday {
            background: #e8f1f3 !important;
            border-left-color: var(--blue) !important;
            color: #37525c;
            font-weight: 600;
        }
        .timeline-card {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px 18px;
            margin: 9px 0 15px;
        }
        .month-agenda {
            background: var(--paper);
            border: 1px solid var(--line);
            border-left: 6px solid var(--event-color);
            border-radius: 16px;
            padding: 14px 16px;
            margin: 8px 0;
            box-shadow: 0 4px 15px rgba(75, 56, 43, .035);
        }
        .month-agenda.holiday {
            background: #edf4f5;
            border-color: #cddfe3;
            border-left-color: var(--blue);
        }
        .agenda-date {
            color: var(--blue);
            font-size: .82rem;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .holiday-badge {
            display:inline-block;
            background:#d9e9ec;
            color:#37525c;
            border-radius:999px;
            padding:3px 10px;
            font-size:.76rem;
            font-weight:700;
        }
        .muted { color:var(--muted); font-size:.9rem; }
        .info-badge {
            display:inline-block;
            background:#f1e8dc;
            border-radius:999px;
            padding:3px 10px;
            font-size:.78rem;
        }
        div[data-testid="stForm"] {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 14px;
        }
        .month-title {
            text-align:center;
            color:var(--brown);
            font-size:1.45rem;
            font-weight:700;
            padding-top:.2rem;
        }
        .brand-kicker {
            color:var(--blue);
            font-size:.82rem;
            font-weight:700;
            letter-spacing:.13em;
        }
        div.stButton > button[kind="primary"],
        div.stFormSubmitButton > button,
        button[kind="primaryFormSubmit"],
        button[data-testid="stBaseButton-primary"],
        button[data-testid="stBaseButton-primaryFormSubmit"] {
            background:#668993 !important;
            border-color:#668993 !important;
            color:#ffffff !important;
            box-shadow:0 4px 12px rgba(76, 112, 122, .16) !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div.stFormSubmitButton > button:hover,
        button[kind="primaryFormSubmit"]:hover,
        button[data-testid="stBaseButton-primary"]:hover,
        button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
            background:#537781 !important;
            border-color:#537781 !important;
            color:#ffffff !important;
        }
        div.stButton > button[kind="primary"] p,
        div.stFormSubmitButton > button p,
        button[kind="primaryFormSubmit"] p,
        button[data-testid="stBaseButton-primary"] p,
        button[data-testid="stBaseButton-primaryFormSubmit"] p {
            color:#ffffff !important;
            font-weight:700 !important;
        }
        div.stButton > button {
            border-color:var(--line);
            color:var(--brown);
            border-radius:10px;
        }
        div.stButton > button p {
            color:inherit !important;
        }
        [data-baseweb="tab-list"] button[aria-selected="true"] {
            color:var(--brown);
            border-bottom-color:var(--brown-soft);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong,
        [data-testid="stSidebar"] h3 {
            color:var(--brown);
        }
        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] {
            background:#fffefb !important;
            border-color:#d8e3e5 !important;
        }
        [data-baseweb="select"] span,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {
            color:var(--brown) !important;
            -webkit-text-fill-color:var(--brown) !important;
        }
        @media (max-width: 700px) {
            .block-container {
                padding: .75rem .35rem 2rem;
                max-width: 100%;
                overflow-x: hidden;
            }
            .calendar-scroll {
                width: 100%;
                margin: 0;
                padding: 1px 0 6px;
                overflow-x: hidden;
                border-radius: 10px;
            }
            .calendar-grid {
                width: 100%;
                min-width: 0;
                grid-template-columns: repeat(7, minmax(0, 1fr));
                gap: 2px;
            }
            .calendar-weekday {
                min-width: 0;
                padding: 5px 0;
                border-radius: 6px;
                font-size: .68rem;
            }
            .calendar-cell {
                min-width: 0;
                min-height: 92px;
                padding: 3px 2px;
                margin-bottom: 0;
            }
            .day-number {
                margin-bottom: 3px;
                font-size: .78rem;
                text-align: center;
            }
            .event-chip {
                min-width: 0;
                margin: 2px 0;
                padding: 3px 2px;
                border-left-width: 3px !important;
                border-radius: 5px;
                font-size: .54rem;
                line-height: 1.15;
                white-space: nowrap;
                text-overflow: ellipsis;
            }
            .calendar-cell .muted {
                display: block;
                font-size: .52rem;
                line-height: 1.1;
                text-align: center;
            }
            .st-key-calendar_native div[data-testid="stHorizontalBlock"] {
                gap: .12rem !important;
            }
            .st-key-calendar_native [class*="st-key-calday_"] {
                min-height: 76px;
                padding: .12rem;
                border-radius: 9px;
            }
            .st-key-calendar_native [class*="st-key-calday_"] button {
                min-height: 1.45rem !important;
                font-size: .66rem !important;
                padding: 0 !important;
            }
            .st-key-calendar_native .event-chip {
                padding: .08rem .1rem;
                border-left-width: 2px !important;
                border-radius: 4px;
                font-size: .46rem;
                line-height: 1.08;
            }
            .month-title { font-size: 1.1rem; padding-top: .35rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def secret(name: str) -> str | None:
    try:
        return st.secrets.get(name)
    except Exception:
        return os.getenv(name)


def supabase_ready() -> bool:
    return bool(
        secret("SUPABASE_URL")
        and secret("SUPABASE_ANON_KEY")
        and (secret("TEAM_ACCESS_CODE") or secret("TEAM_SECRET_KEY"))
    )


def get_supabase() -> Client:
    # Supabase's auth session lives on the client. Keeping the client in
    # st.session_state prevents one browser session from sharing auth state
    # with another user.
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(
            secret("SUPABASE_URL"), secret("SUPABASE_ANON_KEY")
        )
    return st.session_state.supabase_client


def current_user() -> Any | None:
    return st.session_state.get("member_id")


def actor_name() -> str:
    return st.session_state.get("member_name") or "ทีม DAILYLOOK.SM"


def actor_id() -> str | None:
    return st.session_state.get("member_id")


def login_screen(sb: Client) -> None:
    st.markdown('<div class="brand-kicker">DAILYLOOK.SM</div>', unsafe_allow_html=True)
    st.title("ปฏิทินงานทีม")
    if not st.session_state.get("team_access_granted"):
        st.subheader("กรอกรหัสทีมเพื่อเข้าใช้งาน")
        with st.form("team_code_login"):
            access_code = st.text_input("รหัสเข้าใช้งาน", type="password")
            if st.form_submit_button("ถัดไป", use_container_width=True):
                expected = secret("TEAM_ACCESS_CODE") or secret("TEAM_SECRET_KEY") or ""
                if not hmac.compare_digest(access_code.strip(), expected):
                    st.error("รหัสเข้าใช้งานไม่ถูกต้อง")
                    return
                st.session_state.team_access_granted = True
                st.rerun()
        return

    members = load_members(sb)
    if not members:
        st.subheader("สร้างผู้ดูแลคนแรก")
        st.caption("ตั้งชื่อและ PIN 4–8 หลักสำหรับแยกประวัติของแต่ละคน")
        with st.form("first_admin"):
            name = st.text_input("ชื่อที่แสดง")
            pin = st.text_input("PIN ส่วนตัว", type="password", max_chars=8)
            confirm_pin = st.text_input("ยืนยัน PIN", type="password", max_chars=8)
            if st.form_submit_button("สร้างผู้ดูแล", use_container_width=True):
                if not name.strip():
                    st.error("กรุณาใส่ชื่อ")
                elif not pin.isdigit() or not 4 <= len(pin) <= 8:
                    st.error("PIN ต้องเป็นตัวเลข 4–8 หลัก")
                elif pin != confirm_pin:
                    st.error("PIN ทั้งสองช่องไม่ตรงกัน")
                else:
                    result = sb.rpc(
                        "create_team_member",
                        {"member_name": name.strip(), "member_pin": pin, "member_role": "admin"},
                    ).execute()
                    member = (result.data or [None])[0]
                    if not member:
                        st.error("สร้างผู้ดูแลไม่สำเร็จ กรุณารันไฟล์ SQL ของ v10 ก่อน")
                    else:
                        set_member_session(member)
                        st.rerun()
        return

    st.subheader("เลือกชื่อและกรอก PIN")
    member_by_name = {member["name"]: member for member in members}
    with st.form("member_pin_login"):
        selected_name = st.selectbox("ชื่อผู้ใช้งาน", list(member_by_name))
        pin = st.text_input("PIN ส่วนตัว", type="password", max_chars=8)
        if st.form_submit_button("เข้าใช้งาน", use_container_width=True):
            result = sb.rpc(
                "verify_team_member_pin",
                {"member_id": member_by_name[selected_name]["id"], "member_pin": pin},
            ).execute()
            member = (result.data or [None])[0]
            if not member:
                st.error("PIN ไม่ถูกต้อง")
                return
            set_member_session(member)
            st.rerun()


def set_member_session(member: dict[str, Any]) -> None:
    st.session_state.member_id = member["id"]
    st.session_state.member_name = member["name"]
    st.session_state.member_role = member.get("role", "member")


def load_members(sb: Client) -> list[dict[str, Any]]:
    result = sb.rpc("list_team_members").execute()
    return result.data or []


def load_profile(sb: Client, user_id: str) -> dict[str, Any]:
    result = (
        sb.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
    )
    return result.data or {"display_name": "", "role": "member"}


def load_people(sb: Client) -> list[dict[str, Any]]:
    return (
        sb.table("people")
        .select("*")
        .eq("active", True)
        .order("name")
        .execute()
        .data
        or []
    )


def load_profiles(sb: Client) -> list[dict[str, Any]]:
    return (
        sb.table("profiles")
        .select("*")
        .eq("active", True)
        .order("display_name")
        .execute()
        .data
        or []
    )


def load_events(sb: Client, include_deleted: bool = False) -> list[dict[str, Any]]:
    query = (
        sb.table("events")
        .select("*, event_people(person_id, people(id,name))")
    )
    if include_deleted:
        query = query.not_.is_("deleted_at", "null")
    else:
        query = query.is_("deleted_at", "null")
    events = query.order("start_date").order("start_time").execute().data or []
    for event in events:
        event["people"] = [
            link["people"]
            for link in event.get("event_people", [])
            if link.get("people")
        ]
    return events if include_deleted else merge_builtin_thai_holidays(events)


def load_attachments(sb: Client, event_id: str) -> list[dict[str, Any]]:
    return (
        sb.table("event_attachments")
        .select("*")
        .eq("event_id", event_id)
        .order("created_at")
        .execute()
        .data
        or []
    )


def attachment_url(sb: Client, storage_path: str) -> str:
    return sb.storage.from_(ATTACHMENT_BUCKET).get_public_url(storage_path)


def upload_attachment(sb: Client, event_id: str, uploaded_file: Any) -> None:
    safe_name = os.path.basename(uploaded_file.name).replace("/", "_")
    storage_path = f"{event_id}/{uuid.uuid4().hex}-{safe_name}"
    content = uploaded_file.getvalue()
    sb.storage.from_(ATTACHMENT_BUCKET).upload(
        storage_path,
        content,
        {"content-type": uploaded_file.type or "application/octet-stream"},
    )
    sb.table("event_attachments").insert(
        {
            "event_id": event_id,
            "file_name": safe_name,
            "storage_path": storage_path,
            "mime_type": uploaded_file.type,
            "file_size": len(content),
            "uploaded_by": actor_id(),
        }
    ).execute()


def delete_attachment(sb: Client, attachment: dict[str, Any]) -> None:
    sb.storage.from_(ATTACHMENT_BUCKET).remove([attachment["storage_path"]])
    sb.table("event_attachments").delete().eq("id", attachment["id"]).execute()


THAI_HOLIDAYS_2026 = [
    ("วันขึ้นปีใหม่", "2026-01-01"),
    ("วันหยุดพิเศษช่วงปีใหม่", "2026-01-02"),
    ("วันมาฆบูชา", "2026-03-03"),
    ("วันจักรี", "2026-04-06"),
    ("วันสงกรานต์", "2026-04-13"),
    ("วันสงกรานต์", "2026-04-14"),
    ("วันสงกรานต์", "2026-04-15"),
    ("วันแรงงานแห่งชาติ", "2026-05-01"),
    ("วันฉัตรมงคล", "2026-05-04"),
    ("วันวิสาขบูชา", "2026-05-31"),
    ("วันหยุดชดเชยวันวิสาขบูชา", "2026-06-01"),
    ("วันเฉลิมพระชนมพรรษาสมเด็จพระนางเจ้าฯ พระบรมราชินี", "2026-06-03"),
    ("วันเฉลิมพระชนมพรรษาพระบาทสมเด็จพระเจ้าอยู่หัว", "2026-07-28"),
    ("วันอาสาฬหบูชา", "2026-07-29"),
    ("วันเข้าพรรษา", "2026-07-30"),
    ("วันแม่แห่งชาติ", "2026-08-12"),
    ("วันนวมินทรมหาราช", "2026-10-13"),
    ("วันหยุดพิเศษในพื้นที่กรุงเทพมหานคร", "2026-10-16"),
    ("วันปิยมหาราช", "2026-10-23"),
    ("วันพ่อแห่งชาติ", "2026-12-05"),
    ("วันหยุดชดเชยวันพ่อแห่งชาติ", "2026-12-07"),
    ("วันรัฐธรรมนูญ", "2026-12-10"),
    ("วันสิ้นปี", "2026-12-31"),
]


def merge_builtin_thai_holidays(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = {
        (event.get("title"), str(event.get("start_date")))
        for event in events
        if event.get("item_type") == "holiday"
    }
    merged = list(events)
    for title, holiday_date in THAI_HOLIDAYS_2026:
        if (title, holiday_date) in existing:
            continue
        merged.append(
            {
                "id": f"builtin-holiday-{holiday_date}-{title}",
                "title": title,
                "details": "วันหยุดตามปฏิทินไทย",
                "start_date": holiday_date,
                "end_date": holiday_date,
                "start_time": None,
                "item_type": "holiday",
                "pin_color": "blue",
                "priority": "normal",
                "status": "not_started",
                "people": [],
                "_builtin": True,
            }
        )
    merged.sort(key=lambda event: (str(event["start_date"]), event.get("start_time") or ""))
    return merged


def parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def event_covers(event: dict[str, Any], day: date) -> bool:
    return parse_date(event["start_date"]) <= day <= parse_date(event["end_date"])


def event_people_text(event: dict[str, Any]) -> str:
    return ", ".join(p["name"] for p in event.get("people", [])) or "—"


def format_range(event: dict[str, Any]) -> str:
    start = parse_date(event["start_date"])
    end = parse_date(event["end_date"])
    if start == end:
        return f"{start.day} {MONTHS_TH[start.month]} {start.year + 543}"
    return (
        f"{start.day} {MONTHS_TH[start.month]} {start.year + 543}"
        f" – {end.day} {MONTHS_TH[end.month]} {end.year + 543}"
    )


def log_action(
    sb: Client,
    event_id: str | None,
    action: str,
    changes: dict[str, Any],
) -> None:
    sb.table("audit_logs").insert(
        {
            "event_id": event_id,
            "action": action,
            "actor_id": actor_id(),
            "actor_name": actor_name(),
            "changes": changes,
        }
    ).execute()


def update_task_status(sb: Client, event: dict[str, Any], new_status: str) -> None:
    if event["item_type"] != "task" or new_status not in STATUS_LABELS:
        return
    old_status = event["status"]
    if new_status == old_status:
        return
    sb.table("events").update(
        {"status": new_status, "updated_by": actor_id()}
    ).eq("id", event["id"]).execute()
    log_action(
        sb,
        event["id"],
        "status",
        {"from": old_status, "to": new_status, "title": event["title"]},
    )


def upsert_event_people(
    sb: Client, event_id: str, person_ids: list[str]
) -> None:
    sb.table("event_people").delete().eq("event_id", event_id).execute()
    if person_ids:
        sb.table("event_people").insert(
            [{"event_id": event_id, "person_id": person_id} for person_id in person_ids]
        ).execute()


def can_manage_event(event: dict[str, Any], role: str) -> bool:
    """Admins manage every saved event; members manage only their own."""
    if event.get("_builtin") or event.get("_leave"):
        return False
    return role == "admin" or str(event.get("created_by") or "") == str(actor_id())


def delete_event(sb: Client, event: dict[str, Any]) -> None:
    """Move the event to trash so it can be restored."""
    log_action(
        sb,
        event["id"],
        "delete",
        {
            "title": event["title"],
            "created_by": event.get("created_by"),
        },
    )
    sb.table("events").update(
        {
            "deleted_at": datetime.now(BANGKOK_TZ).isoformat(),
            "deleted_by": actor_id(),
            "updated_by": actor_id(),
        }
    ).eq("id", event["id"]).execute()


def restore_event(sb: Client, event: dict[str, Any]) -> None:
    sb.table("events").update(
        {"deleted_at": None, "deleted_by": None, "updated_by": actor_id()}
    ).eq("id", event["id"]).execute()
    log_action(sb, event["id"], "restore", {"title": event["title"]})


def permanently_delete_event(sb: Client, event: dict[str, Any]) -> None:
    for attachment in load_attachments(sb, event["id"]):
        sb.storage.from_(ATTACHMENT_BUCKET).remove([attachment["storage_path"]])
    sb.table("event_people").delete().eq("event_id", event["id"]).execute()
    sb.table("events").delete().eq("id", event["id"]).execute()


def add_months(day: date, months: int = 1) -> date:
    month_index = day.year * 12 + day.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def recurrence_dates(start: date, until: date, recurrence: str) -> list[date]:
    dates: list[date] = []
    current = start
    while current <= until and len(dates) < 366:
        dates.append(current)
        if recurrence == "daily":
            current += timedelta(days=1)
        elif recurrence == "weekly":
            current += timedelta(days=7)
        elif recurrence == "monthly":
            current = add_months(current)
        else:
            break
    return dates


def render_attachments(
    sb: Client, event: dict[str, Any], allow_delete: bool = False
) -> None:
    if event.get("_builtin") or event.get("_leave"):
        return
    try:
        attachments = load_attachments(sb, event["id"])
    except Exception:
        return
    if not attachments:
        return
    st.caption("ไฟล์แนบ")
    for attachment in attachments:
        link_col, delete_col = st.columns([5, 1])
        link_col.markdown(
            f"[📎 {html.escape(attachment['file_name'])}]"
            f"({attachment_url(sb, attachment['storage_path'])})"
        )
        if allow_delete and delete_col.button(
            "ลบไฟล์", key=f"delete_attachment_{attachment['id']}"
        ):
            delete_attachment(sb, attachment)
            log_action(
                sb,
                event["id"],
                "delete_attachment",
                {"file_name": attachment["file_name"]},
            )
            st.rerun()


def event_form(
    sb: Client,
    people: list[dict[str, Any]],
    event: dict[str, Any] | None = None,
    form_key: str = "event_form",
) -> None:
    editing = event is not None
    title = "แก้ไขรายการ" if editing else "เพิ่มรายการ"
    person_by_name = {person["name"]: person["id"] for person in people}
    current_people = (
        [p["name"] for p in event.get("people", [])] if editing else []
    )
    with st.form(form_key, clear_on_submit=not editing):
        st.subheader(title)
        item_type = st.selectbox(
            "ลักษณะรายการ",
            list(ITEM_LABELS),
            format_func=ITEM_LABELS.get,
            index=list(ITEM_LABELS).index(event["item_type"]) if editing else 0,
            help=(
                "งาน / กำหนดส่ง = รายการที่ต้องติดตามสถานะ • "
                "แจ้งข้อมูล / นัดหมาย = ข้อมูลที่ไม่ต้องติ๊กเสร็จ • "
                "วันหยุด / ปิดร้าน = แสดงด้วยสีวันหยุดโดยเฉพาะ"
            ),
        )
        event_title = st.text_input("ชื่องาน / หัวข้อ", value=event["title"] if editing else "")
        details = st.text_area(
            "รายละเอียด", value=event.get("details", "") if editing else ""
        )
        col1, col2 = st.columns(2)
        start_date = col1.date_input(
            "วันที่เริ่มต้น",
            value=parse_date(event["start_date"]) if editing else date.today(),
            format="DD/MM/YYYY",
        )
        end_date = col2.date_input(
            "วันที่สิ้นสุด",
            value=parse_date(event["end_date"]) if editing else date.today(),
            format="DD/MM/YYYY",
        )
        col3, col4 = st.columns(2)
        has_time = col3.checkbox(
            "ระบุเวลา", value=bool(event.get("start_time")) if editing else False
        )
        event_time = col4.time_input(
            "เวลา",
            value=(
                time.fromisoformat(event["start_time"])
                if editing and event.get("start_time")
                else time(9, 0)
            ),
            help="เลือกเวลาได้ทันที ระบบจะบันทึกเวลานี้เมื่อทำเครื่องหมาย “ระบุเวลา”",
        )
        pin_color = st.selectbox(
            "สีหมุด",
            list(PIN_COLORS),
            format_func=lambda key: f"{PIN_SYMBOLS[key]} {PIN_COLORS[key][0]}",
            index=list(PIN_COLORS).index(event["pin_color"]) if editing else 0,
            help="สีหมุดใช้แยกกลุ่มงาน ส่วนรายการวันหยุดจะแสดงเป็นสีฟ้าอ่อนเสมอ",
        )
        priority = st.selectbox(
            "ความเร่งด่วน",
            ["normal", "urgent"],
            format_func=lambda key: "ด่วน" if key == "urgent" else "ปกติ",
            index=1 if editing and event.get("priority") == "urgent" else 0,
            help="ใช้กับลักษณะรายการ “งาน / กำหนดส่ง”",
        )
        selected_people = st.multiselect(
            "ผู้รับผิดชอบ / ผู้เกี่ยวข้อง",
            list(person_by_name),
            default=current_people,
        )
        status = st.selectbox(
            "สถานะ",
            list(STATUS_LABELS),
            format_func=STATUS_LABELS.get,
            index=list(STATUS_LABELS).index(event["status"]) if editing else 0,
            help="ใช้กับลักษณะรายการ “งาน / กำหนดส่ง”",
        )
        recurrence = st.selectbox(
            "ทำซ้ำ",
            list(RECURRENCE_LABELS),
            format_func=RECURRENCE_LABELS.get,
            index=(
                list(RECURRENCE_LABELS).index(event.get("recurrence", "none"))
                if editing else 0
            ),
            disabled=editing,
            help="ตอนสร้างใหม่ ระบบจะสร้างแต่ละรอบเป็นรายการที่แก้ไขแยกกันได้",
        )
        recurrence_until = st.date_input(
            "ทำซ้ำถึงวันที่",
            value=(
                parse_date(event["recurrence_until"])
                if editing and event.get("recurrence_until")
                else start_date
            ),
            format="DD/MM/YYYY",
            disabled=editing or recurrence == "none",
        )
        attachment = st.file_uploader(
            "แนบไฟล์ (ไม่เกิน 10 MB)",
            key=f"attachment_{form_key}",
            help="รองรับรูปภาพ PDF เอกสาร และไฟล์ทั่วไป",
        )
        submitted = st.form_submit_button(
            "บันทึกการแก้ไข" if editing else "เพิ่มรายการ",
            type="primary",
            use_container_width=True,
        )
        if submitted:
            if not event_title.strip():
                st.error("กรุณาใส่ชื่องานหรือหัวข้อ")
                return
            if end_date < start_date:
                st.error("วันที่สิ้นสุดต้องไม่ก่อนวันที่เริ่มต้น")
                return
            if recurrence != "none" and recurrence_until < start_date:
                st.error("วันสิ้นสุดการทำซ้ำต้องไม่ก่อนวันเริ่มต้น")
                return
            if attachment and attachment.size > 10 * 1024 * 1024:
                st.error("ไฟล์แนบต้องมีขนาดไม่เกิน 10 MB")
                return
            payload = {
                "title": event_title.strip(),
                "details": details.strip(),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "start_time": event_time.isoformat() if has_time else None,
                "item_type": item_type,
                "pin_color": pin_color,
                "priority": priority if item_type == "task" else "normal",
                "status": status if item_type == "task" else "not_started",
                "updated_by": actor_id(),
                "recurrence": recurrence,
                "recurrence_until": (
                    recurrence_until.isoformat() if recurrence != "none" else None
                ),
            }
            try:
                if editing:
                    result = (
                        sb.table("events")
                        .update(payload)
                        .eq("id", event["id"])
                        .execute()
                    )
                    event_id = event["id"]
                    action = "update"
                    if attachment:
                        upload_attachment(sb, event_id, attachment)
                else:
                    payload["created_by"] = actor_id()
                    duration = end_date - start_date
                    starts = recurrence_dates(
                        start_date,
                        recurrence_until if recurrence != "none" else start_date,
                        recurrence,
                    )
                    parent_id = str(uuid.uuid4()) if len(starts) > 1 else None
                    rows = []
                    for occurrence_start in starts:
                        row = dict(payload)
                        row["start_date"] = occurrence_start.isoformat()
                        row["end_date"] = (occurrence_start + duration).isoformat()
                        row["recurrence_parent_id"] = parent_id
                        rows.append(row)
                    result = sb.table("events").insert(rows).execute()
                    event_id = result.data[0]["id"]
                    for saved in result.data:
                        upsert_event_people(
                            sb,
                            saved["id"],
                            [person_by_name[name] for name in selected_people],
                        )
                    if attachment:
                        upload_attachment(sb, event_id, attachment)
                    action = "create"
                if editing:
                    upsert_event_people(
                        sb,
                        event_id,
                        [person_by_name[name] for name in selected_people],
                    )
                log_action(sb, event_id, action, payload)
                st.success("บันทึกรายการแล้ว")
                st.rerun()
            except Exception as exc:
                st.error(f"บันทึกไม่สำเร็จ: {exc}")


@st.dialog("รายการประจำวัน", width="large")
def day_schedule_dialog(
    sb: Client,
    people: list[dict[str, Any]],
    events: list[dict[str, Any]],
    selected_day: date,
    role: str,
) -> None:
    day_events = [event for event in events if event_covers(event, selected_day)]
    day_events.sort(
        key=lambda event: (
            event.get("start_time") or "99:99:99",
            event["title"].casefold(),
        )
    )

    st.markdown(
        f"### {selected_day.day} {MONTHS_TH[selected_day.month]} "
        f"{selected_day.year + 543}"
    )
    st.caption(f"กำหนดการทั้งหมด {len(day_events)} รายการ")

    if not day_events:
        st.info("วันนี้ยังไม่มีกำหนดการ")
    else:
        for event in day_events:
            is_holiday = event["item_type"] == "holiday"
            color_hex = (
                HOLIDAY_COLOR
                if is_holiday
                else PIN_COLORS[event.get("pin_color", "blue")][1]
            )
            event_time = (
                event["start_time"][:5] + " น."
                if event.get("start_time")
                else "ไม่ระบุเวลา"
            )
            status_text = (
                f" • {STATUS_LABELS[event['status']]}"
                if event["item_type"] == "task"
                else ""
            )
            details = html.escape(event.get("details") or "")
            details_html = f"<div>{details}</div>" if details else ""
            card_class = "month-agenda holiday" if is_holiday else "month-agenda"
            st.markdown(
                f"""
                <div class="{card_class}" style="--event-color:{color_hex}">
                  <div class="agenda-date">{event_time} • {ITEM_LABELS[event["item_type"]]}</div>
                  <strong>{html.escape(event["title"])}</strong>
                  <div class="muted">{html.escape(event_people_text(event))}{status_text}</div>
                  {details_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_attachments(
                sb, event, can_manage_event(event, role)
            )

        editable_day_events = [
            event for event in day_events if can_manage_event(event, role)
        ]
        if editable_day_events:
            with st.expander("แก้ไขหรือย้ายรายการของวันนี้เข้าถังขยะ"):
                event_by_label = {
                (
                    f"{(event.get('start_time') or '')[:5] or 'ไม่ระบุเวลา'} | "
                    f"{event['title']}"
                ): event
                    for event in editable_day_events
                }
                selected_label = st.selectbox(
                "เลือกรายการที่ต้องการแก้ไข",
                list(event_by_label),
                key=f"dialog_event_{selected_day.isoformat()}",
                )
                selected_event = event_by_label[selected_label]
                event_form(
                    sb,
                    people,
                    selected_event,
                    form_key=f"dialog_event_form_{selected_event['id']}",
                )
                st.divider()
                confirm_delete = st.checkbox(
                    "ยืนยันว่าต้องการย้ายรายการนี้เข้าถังขยะ",
                    key=f"dialog_confirm_delete_{selected_event['id']}",
                )
                if st.button(
                    "ย้ายเข้าถังขยะ",
                    disabled=not confirm_delete,
                    use_container_width=True,
                    key=f"dialog_delete_{selected_event['id']}",
                ):
                    try:
                        delete_event(sb, selected_event)
                        st.session_state.pop("selected_calendar_day", None)
                        st.success("ย้ายรายการเข้าถังขยะแล้ว")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"ลบไม่สำเร็จ: {exc}")

    if st.button("ปิด", use_container_width=True, key="close_day_dialog"):
        st.session_state.pop("selected_calendar_day", None)
        st.rerun()


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = year * 12 + month - 1 + delta
    return month_index // 12, month_index % 12 + 1


def monthly_agenda_view(
    events: list[dict[str, Any]], year: int, month: int
) -> None:
    month_start = date(year, month, 1)
    next_year, next_month = shift_month(year, month, 1)
    month_end = date(next_year, next_month, 1) - timedelta(days=1)
    monthly_events = [
        event
        for event in events
        if parse_date(event["start_date"]) <= month_end
        and parse_date(event["end_date"]) >= month_start
    ]
    monthly_events.sort(
        key=lambda event: (
            parse_date(event["start_date"]),
            event.get("start_time") or "99:99:99",
            event["title"].casefold(),
        )
    )

    st.markdown("---")
    st.markdown(f"### กำหนดการทั้งหมดในเดือน{MONTHS_TH[month]}")
    st.caption(
        f"รวม {len(monthly_events)} รายการ • เรียงตามวันที่และเวลา "
        "• วันหยุดแสดงด้วยการ์ดสีฟ้าอ่อน"
    )
    if not monthly_events:
        st.info("เดือนนี้ยังไม่มีกำหนดการ")
        return

    for event in monthly_events:
        is_holiday = event["item_type"] == "holiday"
        color_hex = (
            HOLIDAY_COLOR
            if is_holiday
            else PIN_COLORS[event.get("pin_color", "blue")][1]
        )
        event_time = (
            event["start_time"][:5] + " น."
            if event.get("start_time")
            else "ไม่ระบุเวลา"
        )
        kind_badge = (
            '<span class="holiday-badge">วันหยุด</span>'
            if is_holiday
            else f'<span class="info-badge">{ITEM_LABELS[event["item_type"]]}</span>'
        )
        status_text = (
            f" • {STATUS_LABELS[event['status']]}"
            if event["item_type"] == "task"
            else ""
        )
        details = html.escape(event.get("details") or "")
        details_html = f"<div>{details}</div>" if details else ""
        card_class = "month-agenda holiday" if is_holiday else "month-agenda"
        st.markdown(
            f"""
            <div class="{card_class}" style="--event-color:{color_hex}">
              <div class="agenda-date">{format_range(event)} • {event_time}</div>
              <strong>{html.escape(event["title"])}</strong> {kind_badge}
              <div class="muted">{html.escape(event_people_text(event))}{status_text}</div>
              {details_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def calendar_view(
    sb: Client,
    people: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> None:
    today = date.today()
    if "calendar_year" not in st.session_state:
        st.session_state.calendar_year = today.year
    if "calendar_month" not in st.session_state:
        st.session_state.calendar_month = today.month

    year = int(st.session_state.calendar_year)
    month = int(st.session_state.calendar_month)
    previous_col, title_col, next_col, today_col = st.columns([1, 3, 1, 1.5])
    if previous_col.button("◀", key="previous_month", use_container_width=True):
        year, month = shift_month(year, month, -1)
        st.session_state.calendar_year = year
        st.session_state.calendar_month = month
        st.rerun()
    title_col.markdown(
        f'<div class="month-title">{MONTHS_TH[month]} {year + 543}</div>',
        unsafe_allow_html=True,
    )
    if next_col.button("▶", key="next_month", use_container_width=True):
        year, month = shift_month(year, month, 1)
        st.session_state.calendar_year = year
        st.session_state.calendar_month = month
        st.rerun()
    if today_col.button(
        "เดือนนี้",
        key="current_month",
        use_container_width=True,
        disabled=(year == today.year and month == today.month),
    ):
        st.session_state.calendar_year = today.year
        st.session_state.calendar_month = today.month
        st.rerun()

    with st.expander("เลือกเดือน"):
        month_rows = [st.columns(4) for _ in range(3)]
        for number in range(1, 13):
            row, col = divmod(number - 1, 4)
            if month_rows[row][col].button(
                MONTHS_TH[number],
                key=f"choose_month_{number}",
                use_container_width=True,
                type="primary" if number == month else "secondary",
            ):
                st.session_state.calendar_month = number
                st.rerun()

    with st.container(key="calendar_native"):
        weekday_cols = st.columns(7, gap="small")
        for col, label in zip(
            weekday_cols, ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
        ):
            col.markdown(
                f'<div class="calendar-weekday">{label}</div>',
                unsafe_allow_html=True,
            )

        cal = calendar.Calendar(firstweekday=0)
        for week in cal.monthdatescalendar(int(year), month):
            week_cols = st.columns(7, gap="small")
            for col, day in zip(week_cols, week):
                day_events = [event for event in events if event_covers(event, day)]
                day_state = (
                    "today_" if day == today else "outside_" if day.month != month else ""
                )
                with col:
                    with st.container(key=f"calday_{day_state}{day.isoformat()}"):
                        if st.button(
                            str(day.day),
                            key=f"open_day_{day.isoformat()}",
                            use_container_width=True,
                            help=f"เปิดรายการวันที่ {day.day} {MONTHS_TH[day.month]}",
                        ):
                            st.session_state.selected_calendar_day = day.isoformat()
                        for event in day_events[:3]:
                            is_holiday = event["item_type"] == "holiday"
                            color = (
                                HOLIDAY_COLOR
                                if is_holiday
                                else PIN_COLORS[event.get("pin_color", "blue")][1]
                            )
                            icon = (
                                "ℹ️ "
                                if event["item_type"] == "info"
                                else "🏖️ "
                                if is_holiday
                                else "✓ "
                            )
                            chip_class = (
                                "event-chip holiday" if is_holiday else "event-chip"
                            )
                            st.markdown(
                                f'<span class="{chip_class}" '
                                f'style="background:{color}35;'
                                f'border-left:5px solid {color}">'
                                f'{icon}{html.escape(event["title"])}</span>',
                                unsafe_allow_html=True,
                            )
                        if len(day_events) > 3:
                            st.caption(f"+ อีก {len(day_events) - 3} รายการ")

    selected_day_value = st.session_state.get("selected_calendar_day")
    if selected_day_value:
        try:
            day_schedule_dialog(
                sb,
                people,
                events,
                date.fromisoformat(str(selected_day_value)),
                st.session_state.get("member_role", "member"),
            )
        except ValueError:
            st.session_state.pop("selected_calendar_day", None)

    monthly_agenda_view(events, year, month)


def filter_events(
    events: list[dict[str, Any]],
    query: str,
    color: str,
    person_id: str,
    status: str,
) -> list[dict[str, Any]]:
    query = query.casefold().strip()
    filtered = []
    for event in events:
        haystack = f'{event["title"]} {event.get("details", "")}'.casefold()
        people_ids = {p["id"] for p in event.get("people", [])}
        if query and query not in haystack:
            continue
        if color != "all" and event["pin_color"] != color:
            continue
        if person_id != "all" and person_id not in people_ids:
            continue
        if status != "all" and event["status"] != status:
            continue
        filtered.append(event)
    return filtered


def timeline_view(
    sb: Client,
    events: list[dict[str, Any]],
    people: list[dict[str, Any]],
) -> None:
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    query = f1.text_input("ค้นหาชื่องานหรือรายละเอียด")
    color = f2.selectbox(
        "สีหมุด",
        ["all", *PIN_COLORS],
        format_func=lambda key: "ทุกสี" if key == "all" else PIN_COLORS[key][0],
    )
    person_by_id = {person["id"]: person["name"] for person in people}
    person_id = f3.selectbox(
        "ผู้เกี่ยวข้อง",
        ["all", *person_by_id],
        format_func=lambda key: "ทุกคน" if key == "all" else person_by_id[key],
    )
    status = f4.selectbox(
        "สถานะ",
        ["all", *STATUS_LABELS],
        format_func=lambda key: "ทุกสถานะ" if key == "all" else STATUS_LABELS[key],
    )
    from_date = st.date_input(
        "ณ วันที่ (แสดงตั้งแต่วันนี้เป็นต้นไป)",
        value=date.today(),
        format="DD/MM/YYYY",
    )
    visible = filter_events(events, query, color, person_id, status)
    by_day: dict[date, list[dict[str, Any]]] = {}
    for event in visible:
        current = max(parse_date(event["start_date"]), from_date)
        last = parse_date(event["end_date"])
        while current <= last:
            by_day.setdefault(current, []).append(event)
            current += timedelta(days=1)
    if not by_day:
        st.info("ไม่พบรายการตามตัวกรองที่เลือก")
        return
    for day in sorted(by_day):
        st.markdown(
            f"### {day.day} {MONTHS_TH[day.month]} {day.year + 543}"
        )
        for event in sorted(
            by_day[day], key=lambda item: item.get("start_time") or "99:99:99"
        ):
            color_hex = PIN_COLORS[event["pin_color"]][1]
            kind = ITEM_LABELS[event["item_type"]]
            status_html = (
                f" • {STATUS_LABELS[event['status']]}"
                if event["item_type"] == "task"
                else " • ไม่ต้องติ๊กเสร็จ"
            )
            event_time = (
                event["start_time"][:5] + " น." if event.get("start_time") else "ไม่ระบุเวลา"
            )
            details = html.escape(event.get("details") or "ไม่มีรายละเอียด")
            st.markdown(
                f"""
                <div class="timeline-card" style="border-left:7px solid {color_hex}">
                  <strong>{html.escape(event["title"])}</strong>
                  <span class="info-badge">{kind}</span><br>
                  <span class="muted">{event_time} • {format_range(event)}{status_html}</span><br>
                  <span>{details}</span><br>
                  <span class="muted">ผู้เกี่ยวข้อง: {html.escape(event_people_text(event))}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if event["item_type"] == "task":
                action_col, save_col = st.columns([3, 1])
                selected_status = action_col.selectbox(
                    "อัปเดตสถานะ",
                    list(STATUS_LABELS),
                    index=list(STATUS_LABELS).index(event["status"]),
                    format_func=STATUS_LABELS.get,
                    key=f"timeline_status_{event['id']}_{day.isoformat()}",
                    label_visibility="collapsed",
                )
                if save_col.button(
                    "บันทึกสถานะ",
                    key=f"timeline_save_{event['id']}_{day.isoformat()}",
                    use_container_width=True,
                    disabled=selected_status == event["status"],
                ):
                    try:
                        update_task_status(sb, event, selected_status)
                        st.success("อัปเดตสถานะแล้ว")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"อัปเดตสถานะไม่สำเร็จ: {exc}")


def week_view(events: list[dict[str, Any]]) -> None:
    selected = st.date_input(
        "เลือกวันในสัปดาห์", value=date.today(), format="DD/MM/YYYY"
    )
    monday = selected - timedelta(days=selected.weekday())
    st.subheader(
        f"สัปดาห์ {monday.strftime('%d/%m/%Y')} – "
        f"{(monday + timedelta(days=6)).strftime('%d/%m/%Y')}"
    )
    columns = st.columns(7)
    day_names = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
    for offset, column in enumerate(columns):
        day = monday + timedelta(days=offset)
        with column:
            st.markdown(f"**{day_names[offset]} {day.day}/{day.month}**")
            day_events = sorted(
                [event for event in events if event_covers(event, day)],
                key=lambda event: event.get("start_time") or "99:99:99",
            )
            if not day_events:
                st.caption("—")
            for event in day_events:
                event_time = (
                    event["start_time"][:5] if event.get("start_time") else ""
                )
                st.markdown(
                    f"{PIN_SYMBOLS.get(event.get('pin_color'), '🔵')} "
                    f"**{html.escape(event['title'])}**"
                )
                st.caption(
                    " • ".join(
                        value for value in [event_time, event_people_text(event)] if value
                    )
                )


def alerts_view(events: list[dict[str, Any]]) -> None:
    today = date.today()
    open_tasks = [
        event
        for event in events
        if event["item_type"] == "task" and event["status"] != "done"
    ]
    overdue = [
        event for event in open_tasks if parse_date(event["end_date"]) < today
    ]
    due_soon = [
        event
        for event in open_tasks
        if today <= parse_date(event["end_date"]) <= today + timedelta(days=3)
    ]
    st.subheader("แจ้งเตือนงาน")
    if overdue:
        st.error(f"มีงานเกินกำหนด {len(overdue)} รายการ")
        for event in overdue:
            late = (today - parse_date(event["end_date"])).days
            st.markdown(f"• **{event['title']}** — เกินกำหนด {late} วัน")
    if due_soon:
        st.warning(f"มีงานใกล้ครบกำหนด {len(due_soon)} รายการ")
        for event in due_soon:
            remaining = (parse_date(event["end_date"]) - today).days
            label = "วันนี้" if remaining == 0 else f"อีก {remaining} วัน"
            st.markdown(f"• **{event['title']}** — {label}")
    if not overdue and not due_soon:
        st.success("ไม่มีงานเกินกำหนดหรืองานที่ครบกำหนดใน 3 วัน")


def dashboard_view(
    events: list[dict[str, Any]], members: list[dict[str, Any]]
) -> None:
    st.subheader("Dashboard รายบุคคล")
    member_names = {str(member["id"]): member["name"] for member in members}
    rows = []
    for member in members:
        member_id = str(member["id"])
        created = [
            event
            for event in events
            if not event.get("_builtin")
            and str(event.get("created_by") or "") == member_id
        ]
        tasks = [event for event in created if event["item_type"] == "task"]
        done = [event for event in tasks if event["status"] == "done"]
        overdue = [
            event
            for event in tasks
            if event["status"] != "done"
            and parse_date(event["end_date"]) < date.today()
        ]
        rows.append(
            {
                "สมาชิก": member["name"],
                "รายการที่สร้าง": len(created),
                "งานทั้งหมด": len(tasks),
                "เสร็จแล้ว": len(done),
                "เกินกำหนด": len(overdue),
                "สำเร็จ (%)": round(len(done) * 100 / len(tasks)) if tasks else 0,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    my_id = str(actor_id())
    my_events = [
        event
        for event in events
        if str(event.get("created_by") or "") == my_id
        and not event.get("_builtin")
    ]
    st.caption(
        f"คุณ {member_names.get(my_id, actor_name())} สร้างรายการทั้งหมด "
        f"{len(my_events)} รายการ"
    )


def trash_view(sb: Client, role: str) -> None:
    deleted = load_events(sb, include_deleted=True)
    st.subheader("ถังขยะ")
    st.caption("สมาชิกกู้คืนงานของตัวเองได้ ผู้ดูแลจัดการได้ทุกงาน")
    manageable = [
        event
        for event in deleted
        if role == "admin"
        or str(event.get("created_by") or "") == str(actor_id())
    ]
    if not manageable:
        st.info("ไม่มีรายการในถังขยะ")
        return
    for event in manageable:
        st.markdown(f"**{event['title']}** — {format_range(event)}")
        restore_col, delete_col = st.columns(2)
        if restore_col.button(
            "กู้คืน", key=f"restore_{event['id']}", use_container_width=True
        ):
            restore_event(sb, event)
            st.success("กู้คืนรายการแล้ว")
            st.rerun()
        confirm = delete_col.checkbox(
            "ลบถาวร", key=f"confirm_permanent_{event['id']}"
        )
        if delete_col.button(
            "ยืนยันลบถาวร",
            key=f"permanent_{event['id']}",
            disabled=not confirm,
            use_container_width=True,
        ):
            permanently_delete_event(sb, event)
            st.success("ลบถาวรแล้ว")
            st.rerun()


def load_leave_events(sb: Client) -> list[dict[str, Any]]:
    requests = (
        sb.table("leave_requests")
        .select("*")
        .eq("status", "approved")
        .execute()
        .data
        or []
    )
    return [
        {
            "id": f"leave-{request['id']}",
            "title": f"ลา: {request['member_name']} ({request['leave_type']})",
            "details": request.get("reason") or "",
            "start_date": request["start_date"],
            "end_date": request["end_date"],
            "start_time": None,
            "item_type": "info",
            "pin_color": "orange",
            "priority": "normal",
            "status": "not_started",
            "people": [],
            "_leave": True,
        }
        for request in requests
    ]


def leave_view(sb: Client, role: str) -> None:
    st.subheader("วันลา")
    with st.form("leave_request", clear_on_submit=True):
        leave_type = st.selectbox(
            "ประเภทการลา", ["ลาป่วย", "ลากิจ", "ลาพักร้อน", "อื่น ๆ"]
        )
        col1, col2 = st.columns(2)
        start = col1.date_input("วันเริ่มลา", format="DD/MM/YYYY")
        end = col2.date_input("วันสิ้นสุด", format="DD/MM/YYYY")
        reason = st.text_area("เหตุผล / หมายเหตุ")
        if st.form_submit_button("ส่งคำขออนุมัติ", use_container_width=True):
            if end < start:
                st.error("วันสิ้นสุดต้องไม่ก่อนวันเริ่มลา")
            else:
                sb.table("leave_requests").insert(
                    {
                        "member_id": actor_id(),
                        "member_name": actor_name(),
                        "leave_type": leave_type,
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                        "reason": reason.strip(),
                    }
                ).execute()
                st.success("ส่งคำขอแล้ว")
                st.rerun()
    query = sb.table("leave_requests").select("*").order("created_at", desc=True)
    if role != "admin":
        query = query.eq("member_id", actor_id())
    requests = query.execute().data or []
    for request in requests:
        st.markdown(
            f"**{request['member_name']} — {request['leave_type']}**  \n"
            f"{request['start_date']} ถึง {request['end_date']} • "
            f"{LEAVE_STATUS_LABELS[request['status']]}"
        )
        if role == "admin" and request["status"] == "pending":
            approve_col, reject_col = st.columns(2)
            for new_status, column, label in [
                ("approved", approve_col, "อนุมัติ"),
                ("rejected", reject_col, "ไม่อนุมัติ"),
            ]:
                if column.button(
                    label,
                    key=f"leave_{new_status}_{request['id']}",
                    use_container_width=True,
                ):
                    sb.table("leave_requests").update(
                        {
                            "status": new_status,
                            "reviewed_by": actor_id(),
                            "reviewed_by_name": actor_name(),
                            "reviewed_at": datetime.now(BANGKOK_TZ).isoformat(),
                        }
                    ).eq("id", request["id"]).execute()
                    log_action(
                        sb,
                        None,
                        f"leave_{new_status}",
                        {"member_name": request["member_name"]},
                    )
                    st.rerun()


def team_view(
    sb: Client,
    people: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    role: str,
) -> None:
    st.subheader("สมาชิกที่เข้าใช้งาน")
    members = load_members(sb)
    if role == "admin":
        with st.form("add_team_member", clear_on_submit=True):
            member_name = st.text_input("ชื่อสมาชิก")
            member_pin = st.text_input("PIN เริ่มต้น 4–8 หลัก", type="password")
            member_role = st.selectbox(
                "สิทธิ์",
                ["member", "admin"],
                format_func=lambda value: (
                    "สมาชิก" if value == "member" else "ผู้ดูแล"
                ),
            )
            if st.form_submit_button("เพิ่มสมาชิก", use_container_width=True):
                try:
                    sb.rpc(
                        "create_team_member",
                        {
                            "member_name": member_name.strip(),
                            "member_pin": member_pin,
                            "member_role": member_role,
                        },
                    ).execute()
                    st.success("เพิ่มสมาชิกแล้ว")
                    st.rerun()
                except Exception as exc:
                    st.error(f"เพิ่มสมาชิกไม่สำเร็จ: {exc}")
    for member in members:
        st.markdown(
            f"• **{html.escape(member['name'])}** — "
            f"{'ผู้ดูแล' if member['role'] == 'admin' else 'สมาชิก'}"
        )

    st.divider()
    st.subheader("ผู้รับผิดชอบ / ผู้เกี่ยวข้อง")
    with st.form("add_person", clear_on_submit=True):
        name = st.text_input("เพิ่มชื่อคนในแผนกหรือผู้เกี่ยวข้อง")
        if st.form_submit_button("เพิ่มรายชื่อ"):
            if name.strip():
                try:
                    sb.table("people").insert(
                        {"name": name.strip(), "created_by": actor_id()}
                    ).execute()
                    st.success("เพิ่มรายชื่อแล้ว")
                    st.rerun()
                except Exception as exc:
                    st.error(f"เพิ่มรายชื่อไม่สำเร็จ: {exc}")
    if people:
        for person in people:
            st.markdown(f"• {person['name']}")
    else:
        st.info("ยังไม่มีรายชื่อผู้เกี่ยวข้อง")


def activity_view(sb: Client) -> None:
    logs = (
        sb.table("audit_logs")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
        or []
    )
    labels = {
        "create": "เพิ่มรายการ",
        "update": "แก้ไขรายการ",
        "delete": "ย้ายเข้าถังขยะ",
        "restore": "กู้คืนรายการ",
        "delete_attachment": "ลบไฟล์แนบ",
        "leave_approved": "อนุมัติวันลา",
        "leave_rejected": "ไม่อนุมัติวันลา",
        "status": "เปลี่ยนสถานะ",
    }
    if not logs:
        st.info("ยังไม่มีประวัติการอัปเดต")
        return
    for log in logs:
        when = (
            isoparse(log["created_at"])
            .astimezone(BANGKOK_TZ)
            .strftime("%d/%m/%Y %H:%M")
        )
        st.markdown(
            f"**{html.escape(log.get('actor_name') or 'สมาชิก')}** "
            f"{labels.get(log['action'], log['action'])} · {when}"
        )


def export_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for event in events:
        rows.append(
            {
                "title": event["title"],
                "details": event.get("details", ""),
                "start_date": event["start_date"],
                "end_date": event["end_date"],
                "start_time": event.get("start_time") or "",
                "item_type": event["item_type"],
                "pin_color": event["pin_color"],
                "priority": event["priority"],
                "status": event["status"],
                "people": event_people_text(event),
                "created_at": event.get("created_at", ""),
                "updated_at": event.get("updated_at", ""),
            }
        )
    return rows


def export_markdown(events: list[dict[str, Any]]) -> str:
    lines = [
        "# กำหนดการของ DAILYLOOK.SM",
        "",
        f"ส่งออกเมื่อ {date.today().strftime('%d/%m/%Y')}",
        "",
    ]
    for event in events:
        status = (
            STATUS_LABELS[event["status"]]
            if event["item_type"] == "task"
            else "ไม่ต้องติ๊กเสร็จ"
        )
        lines.extend(
            [
                f"## {event['title']}",
                "",
                f"- วันที่: {format_range(event)}",
                f"- ลักษณะรายการ: {ITEM_LABELS[event['item_type']]}",
                f"- สีหมุด: {PIN_COLORS[event['pin_color']][0]}",
                f"- สถานะ: {status}",
                f"- ผู้เกี่ยวข้อง: {event_people_text(event)}",
                f"- รายละเอียด: {event.get('details') or '—'}",
                "",
            ]
        )
    return "\n".join(lines)


def backup_view(events: list[dict[str, Any]]) -> None:
    st.subheader("สำรองข้อมูลปฏิทิน")
    st.caption(
        "ไฟล์สำรองไม่มีกุญแจ Supabase หรือ Secret Key ของทีม "
        "และดาวน์โหลดได้เฉพาะผู้ใช้ที่ผ่านการอนุมัติแล้ว"
    )
    rows = export_rows(events)
    json_data = json.dumps(rows, ensure_ascii=False, indent=2, default=str)
    csv_buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(csv_buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    else:
        csv_buffer.write(
            "title,details,start_date,end_date,start_time,item_type,pin_color,"
            "priority,status,people,created_at,updated_at\n"
        )
    markdown_data = export_markdown(events)
    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "ดาวน์โหลด JSON",
        json_data.encode("utf-8"),
        file_name=f"dailylook-sm-calendar-{date.today().isoformat()}.json",
        mime="application/json",
        use_container_width=True,
    )
    col2.download_button(
        "ดาวน์โหลด CSV",
        ("\ufeff" + csv_buffer.getvalue()).encode("utf-8"),
        file_name=f"dailylook-sm-calendar-{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    col3.download_button(
        "ดาวน์โหลด Markdown",
        markdown_data.encode("utf-8"),
        file_name=f"dailylook-sm-calendar-{date.today().isoformat()}.md",
        mime="text/markdown",
        use_container_width=True,
    )


def sidebar_editor(
    sb: Client, events: list[dict[str, Any]], people: list[dict[str, Any]], role: str
) -> None:
    st.sidebar.markdown(
        '<div class="brand-kicker">DAILYLOOK.SM</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(f"### สวัสดี {actor_name()}")
    st.sidebar.caption("ผู้ดูแล" if role == "admin" else "สมาชิก")
    with st.sidebar.expander("เปลี่ยน PIN ของฉัน"):
        with st.form("change_my_pin"):
            new_pin = st.text_input("PIN ใหม่ 4–8 หลัก", type="password")
            confirm_pin = st.text_input("ยืนยัน PIN ใหม่", type="password")
            if st.form_submit_button("บันทึก PIN", use_container_width=True):
                if not new_pin.isdigit() or not 4 <= len(new_pin) <= 8:
                    st.error("PIN ต้องเป็นตัวเลข 4–8 หลัก")
                elif new_pin != confirm_pin:
                    st.error("PIN ทั้งสองช่องไม่ตรงกัน")
                else:
                    try:
                        sb.rpc(
                            "change_team_member_pin",
                            {"member_id": actor_id(), "new_pin": new_pin},
                        ).execute()
                        st.success("เปลี่ยน PIN แล้ว")
                    except Exception as exc:
                        st.error(f"เปลี่ยน PIN ไม่สำเร็จ: {exc}")
    if st.sidebar.button("ออกจากระบบ", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.sidebar.divider()
    mode = st.sidebar.radio(
        "จัดการรายการ", ["เพิ่มใหม่", "แก้ไข / ย้ายเข้าถังขยะ"]
    )
    if mode == "เพิ่มใหม่":
        with st.sidebar:
            event_form(sb, people)
        return
    editable = {
        f"{event['title']} | {format_range(event)}": event
        for event in events
        if can_manage_event(event, role)
    }
    if not editable:
        st.sidebar.info("ยังไม่มีรายการที่คุณแก้ไขหรือลบได้")
        return
    selected = st.sidebar.selectbox("เลือกรายการ", list(editable))
    event = editable[selected]
    with st.sidebar:
        event_form(sb, people, event)
        st.divider()
        confirm = st.checkbox("ยืนยันว่าต้องการย้ายรายการนี้เข้าถังขยะ")
        if st.button(
            "ย้ายเข้าถังขยะ",
            disabled=not confirm,
            use_container_width=True,
        ):
            try:
                delete_event(sb, event)
                st.success("ย้ายรายการเข้าถังขยะแล้ว")
                st.rerun()
            except Exception as exc:
                st.error(f"ลบไม่สำเร็จ: {exc}")


def main() -> None:
    inject_css()
    if not supabase_ready():
        st.title("DAILYLOOK.SM")
        st.warning("ยังไม่ได้เชื่อมฐานข้อมูล Supabase")
        st.markdown(
            """
            ตั้งค่าให้พร้อมใช้งานโดย:

            1. สร้าง Supabase Project
            2. รัน `supabase_schema.sql` และ `seed_2026.sql` ใน SQL Editor
            3. เพิ่ม `SUPABASE_URL`, `SUPABASE_ANON_KEY` และ
               `TEAM_ACCESS_CODE` ใน Streamlit Secrets
            """
        )
        return
    sb = get_supabase()
    if not current_user():
        login_screen(sb)
        return
    try:
        profile = {
            "display_name": actor_name(),
            "role": st.session_state.get("member_role", "member"),
            "approved": True,
        }
        people = load_people(sb)
        profiles = []
        events = load_events(sb)
        events.extend(load_leave_events(sb))
        events.sort(
            key=lambda event: (
                str(event["start_date"]),
                event.get("start_time") or "",
            )
        )
    except Exception:
        st.session_state.clear()
        st.error("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่")
        st.rerun()
        return

    sidebar_editor(sb, events, people, profile.get("role", "member"))
    st.markdown('<div class="brand-kicker">TEAM CALENDAR</div>', unsafe_allow_html=True)
    st.title("DAILYLOOK.SM")
    st.caption("ปฏิทินงานทีม • ทุกคนเห็นข้อมูลชุดเดียวกัน")

    today = date.today()
    real_tasks = [event for event in events if event["item_type"] == "task"]
    due_today = [event for event in real_tasks if event_covers(event, today)]
    next_7 = [
        event
        for event in real_tasks
        if parse_date(event["end_date"]) >= today
        and parse_date(event["start_date"]) <= today + timedelta(days=6)
    ]
    open_tasks = [event for event in real_tasks if event["status"] != "done"]
    holidays_month = [
        event
        for event in events
        if event["item_type"] == "holiday"
        and parse_date(event["start_date"]).month == today.month
        and parse_date(event["start_date"]).year == today.year
    ]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("งานวันนี้", len(due_today))
    m2.metric("งาน 7 วันข้างหน้า", len(next_7))
    m3.metric("งานที่ยังไม่เสร็จ", len(open_tasks))
    m4.metric("วันหยุดเดือนนี้", len(holidays_month))

    overdue = [
        event
        for event in open_tasks
        if parse_date(event["end_date"]) < today
    ]
    if overdue:
        st.error(f"🔔 มีงานเกินกำหนด {len(overdue)} รายการ")

    (
        calendar_tab,
        week_tab,
        timeline_tab,
        alerts_tab,
        dashboard_tab,
        leave_tab,
        team_tab,
        activity_tab,
        trash_tab,
        backup_tab,
    ) = st.tabs(
        [
            "ปฏิทิน",
            "รายสัปดาห์",
            "กำหนดการทั้งหมด",
            "แจ้งเตือน",
            "Dashboard",
            "วันลา",
            "ทีม",
            "ประวัติ",
            "ถังขยะ",
            "สำรองข้อมูล",
        ]
    )
    with calendar_tab:
        calendar_view(sb, people, events)
    with week_tab:
        week_view(events)
    with timeline_tab:
        timeline_view(sb, events, people)
    with alerts_tab:
        alerts_view(events)
    with dashboard_tab:
        dashboard_view(events, load_members(sb))
    with leave_tab:
        leave_view(sb, profile.get("role", "member"))
    with team_tab:
        team_view(sb, people, profiles, profile.get("role", "member"))
    with activity_tab:
        activity_view(sb)
    with trash_tab:
        trash_view(sb, profile.get("role", "member"))
    with backup_tab:
        backup_view(events)


if __name__ == "__main__":
    main()
