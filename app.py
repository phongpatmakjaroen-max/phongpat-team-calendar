from __future__ import annotations

import calendar
import csv
import hmac
import html
import io
import json
import os
from datetime import date, time, timedelta
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
    "red": ("แดง", "#D85C5C"),
}
STATUS_LABELS = {
    "not_started": "ยังไม่เริ่ม",
    "in_progress": "กำลังทำ",
    "waiting": "รอตรวจ/รอข้อมูล",
    "done": "เสร็จแล้ว",
}
ITEM_LABELS = {
    "task": "งานที่ต้องติดตาม",
    "info": "รายการแจ้งข้อมูล",
    "holiday": "วันหยุด",
}
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
        .calendar-cell.today { border: 2px solid #9bb9c2; background: var(--blue-soft); }
        .calendar-cell.outside { opacity: .44; }
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
        .timeline-card {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px 18px;
            margin: 9px 0 15px;
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
        div.stButton > button[kind="primary"] {
            background:var(--brown-soft);
            border-color:var(--brown-soft);
            color:#fff;
        }
        div.stButton > button {
            border-color:var(--line);
            color:var(--brown);
            border-radius:10px;
        }
        [data-baseweb="tab-list"] button[aria-selected="true"] {
            color:var(--brown);
            border-bottom-color:var(--brown-soft);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong,
        [data-testid="stSidebar"] h3 {
            color:var(--brown);
        }
        @media (max-width: 700px) {
            .block-container { padding: 1rem .7rem; }
            .calendar-cell { min-height: 105px; padding: 7px; }
            .event-chip { font-size: .68rem; padding: 4px; }
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
        and secret("TEAM_SECRET_KEY")
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
    return st.session_state.get("user")


def actor_name() -> str:
    return st.session_state.get("display_name") or current_user().email.split("@")[0]


def login_screen(sb: Client) -> None:
    st.markdown('<div class="brand-kicker">DAILYLOOK.SM</div>', unsafe_allow_html=True)
    st.title("ปฏิทินงานทีม")
    st.subheader("จัดการงานของทีมในที่เดียว")
    login_tab, signup_tab = st.tabs(["เข้าสู่ระบบ", "สร้างบัญชี"])
    with login_tab:
        with st.form("login"):
            email = st.text_input("อีเมล")
            password = st.text_input("รหัสผ่าน", type="password")
            if st.form_submit_button("เข้าสู่ระบบ", use_container_width=True):
                try:
                    result = sb.auth.sign_in_with_password(
                        {"email": email.strip(), "password": password}
                    )
                    st.session_state.user = result.user
                    st.session_state.access_token = result.session.access_token
                    st.rerun()
                except Exception as exc:
                    st.error(f"เข้าสู่ระบบไม่สำเร็จ: {exc}")
    with signup_tab:
        st.caption("สมาชิกใหม่อาจต้องยืนยันอีเมลก่อนเข้าสู่ระบบ")
        with st.form("signup"):
            name = st.text_input("ชื่อที่ใช้ในทีม")
            email = st.text_input("อีเมล", key="signup_email")
            password = st.text_input(
                "รหัสผ่าน (อย่างน้อย 6 ตัว)", type="password", key="signup_password"
            )
            invite_code = st.text_input(
                "Secret Key ของทีม", type="password", key="team_secret_key"
            )
            if st.form_submit_button("สร้างบัญชี", use_container_width=True):
                expected = secret("TEAM_SECRET_KEY") or ""
                if not hmac.compare_digest(invite_code, expected):
                    st.error("Secret Key ของทีมไม่ถูกต้อง")
                    return
                try:
                    sb.auth.sign_up(
                        {
                            "email": email.strip(),
                            "password": password,
                            "options": {"data": {"display_name": name.strip()}},
                        }
                    )
                    st.success("สร้างบัญชีแล้ว กรุณาตรวจอีเมลเพื่อยืนยันบัญชี")
                except Exception as exc:
                    st.error(f"สร้างบัญชีไม่สำเร็จ: {exc}")


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


def load_events(sb: Client) -> list[dict[str, Any]]:
    events = (
        sb.table("events")
        .select("*, event_people(person_id, people(id,name))")
        .order("start_date")
        .order("start_time")
        .execute()
        .data
        or []
    )
    for event in events:
        event["people"] = [
            link["people"]
            for link in event.get("event_people", [])
            if link.get("people")
        ]
    return events


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
            "actor_id": current_user().id,
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
        {"status": new_status, "updated_by": current_user().id}
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


def event_form(
    sb: Client,
    people: list[dict[str, Any]],
    event: dict[str, Any] | None = None,
) -> None:
    editing = event is not None
    title = "แก้ไขรายการ" if editing else "เพิ่มรายการ"
    person_by_name = {person["name"]: person["id"] for person in people}
    current_people = (
        [p["name"] for p in event.get("people", [])] if editing else []
    )
    with st.form("event_form", clear_on_submit=not editing):
        st.subheader(title)
        item_type = st.selectbox(
            "ลักษณะรายการ",
            list(ITEM_LABELS),
            format_func=ITEM_LABELS.get,
            index=list(ITEM_LABELS).index(event["item_type"]) if editing else 0,
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
            disabled=not has_time,
        )
        pin_color = st.selectbox(
            "สีหมุด",
            list(PIN_COLORS),
            format_func=lambda key: f"● {PIN_COLORS[key][0]}",
            index=list(PIN_COLORS).index(event["pin_color"]) if editing else 0,
        )
        priority = st.selectbox(
            "ความเร่งด่วน",
            ["normal", "urgent"],
            format_func=lambda key: "ด่วน" if key == "urgent" else "ปกติ",
            index=1 if editing and event.get("priority") == "urgent" else 0,
            disabled=item_type != "task",
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
            disabled=item_type != "task",
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
                "updated_by": current_user().id,
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
                else:
                    payload["created_by"] = current_user().id
                    result = sb.table("events").insert(payload).execute()
                    event_id = result.data[0]["id"]
                    action = "create"
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


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = year * 12 + month - 1 + delta
    return month_index // 12, month_index % 12 + 1


def calendar_view(events: list[dict[str, Any]]) -> None:
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

    header_cols = st.columns(7)
    for col, label in zip(
        header_cols, ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
    ):
        col.markdown(f"**{label}**")
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdatescalendar(int(year), month):
        cols = st.columns(7)
        for col, day in zip(cols, week):
            day_events = [event for event in events if event_covers(event, day)]
            chips = []
            for event in day_events[:3]:
                color = PIN_COLORS[event["pin_color"]][1]
                icon = (
                    "ℹ️ "
                    if event["item_type"] == "info"
                    else "🏖️ "
                    if event["item_type"] == "holiday"
                    else "✓ "
                )
                chips.append(
                    f'<span class="event-chip" style="background:{color}35;'
                    f'border-left:5px solid {color}">'
                    f'{icon}{html.escape(event["title"])}</span>'
                )
            if len(day_events) > 3:
                chips.append(
                    f'<span class="muted">+ อีก {len(day_events) - 3} รายการ</span>'
                )
            classes = ["calendar-cell"]
            if day == today:
                classes.append("today")
            if day.month != month:
                classes.append("outside")
            col.markdown(
                f'<div class="{" ".join(classes)}">'
                f'<div class="day-number">{day.day}</div>'
                f'{"".join(chips)}</div>',
                unsafe_allow_html=True,
            )


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


def team_view(
    sb: Client,
    people: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    role: str,
) -> None:
    st.subheader("ทีมและผู้เกี่ยวข้อง")
    with st.form("add_person", clear_on_submit=True):
        name = st.text_input("เพิ่มชื่อคนในแผนกหรือผู้เกี่ยวข้อง")
        if st.form_submit_button("เพิ่มรายชื่อ"):
            if name.strip():
                try:
                    sb.table("people").insert(
                        {"name": name.strip(), "created_by": current_user().id}
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
    st.divider()
    st.subheader("บัญชีที่เข้าใช้งาน")
    for profile in profiles:
        name = profile.get("display_name") or "ยังไม่ได้ตั้งชื่อ"
        current_role = profile.get("role", "member")
        approved = profile.get("approved", False)
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.markdown(
            f"**{html.escape(name)}**  \n"
            f"{'ผู้ดูแล' if current_role == 'admin' else 'สมาชิก'}"
            f" • {'อนุมัติแล้ว' if approved else 'รออนุมัติ'}"
        )
        if role == "admin" and profile["id"] != current_user().id:
            new_role = c2.selectbox(
                "สิทธิ์",
                ["member", "admin"],
                index=1 if current_role == "admin" else 0,
                format_func=lambda value: "ผู้ดูแล" if value == "admin" else "สมาชิก",
                key=f"role_{profile['id']}",
                label_visibility="collapsed",
            )
            if new_role != current_role:
                try:
                    sb.table("profiles").update({"role": new_role}).eq(
                        "id", profile["id"]
                    ).execute()
                    st.success(f"ปรับสิทธิ์ของ {name} แล้ว")
                    st.rerun()
                except Exception as exc:
                    st.error(f"ปรับสิทธิ์ไม่สำเร็จ: {exc}")
            new_approval = c3.selectbox(
                "การอนุมัติ",
                [False, True],
                index=1 if approved else 0,
                format_func=lambda value: "อนุมัติ" if value else "รออนุมัติ",
                key=f"approved_{profile['id']}",
                label_visibility="collapsed",
            )
            if new_approval != approved:
                try:
                    sb.table("profiles").update({"approved": new_approval}).eq(
                        "id", profile["id"]
                    ).execute()
                    st.success(f"อัปเดตการอนุมัติของ {name} แล้ว")
                    st.rerun()
                except Exception as exc:
                    st.error(f"ปรับการอนุมัติไม่สำเร็จ: {exc}")


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
        "delete": "ลบรายการ",
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
    with st.sidebar.expander("โปรไฟล์ของฉัน"):
        with st.form("profile_form"):
            display_name = st.text_input(
                "ชื่อที่แสดง",
                value=actor_name(),
                max_chars=60,
            )
            if st.form_submit_button("บันทึกชื่อ", use_container_width=True):
                clean_name = display_name.strip()
                if not clean_name:
                    st.error("กรุณาใส่ชื่อที่ต้องการแสดง")
                else:
                    try:
                        sb.table("profiles").update(
                            {"display_name": clean_name}
                        ).eq("id", current_user().id).execute()
                        st.session_state.display_name = clean_name
                        st.success("บันทึกชื่อแล้ว")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"บันทึกชื่อไม่สำเร็จ: {exc}")
    if st.sidebar.button("ออกจากระบบ", use_container_width=True):
        sb.auth.sign_out()
        st.session_state.clear()
        st.rerun()
    st.sidebar.divider()
    mode = st.sidebar.radio("จัดการรายการ", ["เพิ่มใหม่", "แก้ไขรายการ"])
    if mode == "เพิ่มใหม่":
        with st.sidebar:
            event_form(sb, people)
        return
    editable = {
        f"{event['title']} | {format_range(event)}": event for event in events
    }
    if not editable:
        st.sidebar.info("ยังไม่มีรายการให้แก้ไข")
        return
    selected = st.sidebar.selectbox("เลือกรายการ", list(editable))
    event = editable[selected]
    with st.sidebar:
        event_form(sb, people, event)
        if role == "admin":
            st.divider()
            confirm = st.checkbox("ยืนยันว่าต้องการลบรายการนี้")
            if st.button(
                "ลบรายการ",
                disabled=not confirm,
                use_container_width=True,
            ):
                try:
                    log_action(sb, event["id"], "delete", {"title": event["title"]})
                    sb.table("events").delete().eq("id", event["id"]).execute()
                    st.success("ลบรายการแล้ว")
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
            3. เพิ่ม `SUPABASE_URL`, `SUPABASE_ANON_KEY` และ `TEAM_SECRET_KEY`
               ใน Streamlit Secrets
            """
        )
        return
    sb = get_supabase()
    if not current_user():
        login_screen(sb)
        return
    try:
        profile = load_profile(sb, current_user().id)
        st.session_state.display_name = profile.get("display_name") or actor_name()
        if not profile.get("approved", False):
            st.title("รอผู้ดูแลอนุมัติบัญชี")
            st.info(
                "บัญชีถูกสร้างแล้ว แต่ยังเปิดดูข้อมูลปฏิทินไม่ได้ "
                "กรุณาให้ผู้ดูแลอนุมัติจากหน้า ทีม"
            )
            if st.button("ออกจากระบบ"):
                sb.auth.sign_out()
                st.session_state.clear()
                st.rerun()
            return
        people = load_people(sb)
        profiles = load_profiles(sb)
        events = load_events(sb)
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

    calendar_tab, timeline_tab, team_tab, activity_tab, backup_tab = st.tabs(
        ["ปฏิทิน", "กำหนดการทั้งหมด", "ทีม", "ประวัติอัปเดต", "สำรองข้อมูล"]
    )
    with calendar_tab:
        calendar_view(events)
    with timeline_tab:
        timeline_view(sb, events, people)
    with team_tab:
        team_view(sb, people, profiles, profile.get("role", "member"))
    with activity_tab:
        activity_view(sb)
    with backup_tab:
        backup_view(events)


if __name__ == "__main__":
    main()
