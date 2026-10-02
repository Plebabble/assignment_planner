import json
import html
import math
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

import streamlit as st

DATA_FILE = Path("assignments.json")
CALENDAR_FILE = Path("calendar.ics")
DEFAULT_WAKE_START = time(7, 0)
DEFAULT_WAKE_END = time(23, 0)


COURSES = ["Math 131", "Phys 151", "CompLit 335", "FYS 191", "Engin 112", "Other"]
COURSE_COLORS = {
    "Math 131": "#173B73",
    "Phys 151": "#58A6D6",
    "CompLit 335": "#C66A25",
    "FYS 191": "#7043A5",
    "Engin 112": "#155B3B",
    "Other": "#41464F",
}


def infer_course(name):
    text = name.lower()
    if "phys" in text or "physics" in text:
        return "Phys 151"
    if "math" in text or __import__("re").search(r"\\b\\d+\\.\\d+\\b", text):
        return "Math 131"
    if "complit" in text or "contract with god" in text or "comic" in text:
        return "CompLit 335"
    if "fys" in text:
        return "FYS 191"
    if "engin" in text or "engineering" in text:
        return "Engin 112"
    return "Other"

st.set_page_config(page_title="Assignment Planner", page_icon="📚", layout="wide")


st.markdown("""
<style>
    .stApp { background: #0d1118; }
    [data-testid="stHeader"] { background: rgba(13,17,24,0.88); }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px; }
    h1, h2, h3 { letter-spacing: -0.035em; }
    div[data-testid="stMetric"] {
        background: #171e29; border: 1px solid #293344;
        padding: 16px 18px; border-radius: 14px;
    }
    div[data-testid="stMetricLabel"] { color: #aebbd0; }
    div[data-testid="stMetricValue"] { font-weight: 750; }
    div[data-testid="stTabs"] button { font-weight: 650; }
    div[data-testid="stForm"] {
        background: #141a24; border: 1px solid #293344;
        border-radius: 14px; padding: 14px 16px;
    }
    div[data-testid="stNumberInput"] input { text-align: center; }
    .assignment-card {
        border: 1px solid #293344; border-radius: 16px;
        background: linear-gradient(145deg, #171e29, #121821);
        padding: 17px 18px; margin: 0 0 8px 0; min-height: 220px;
    }
    .assignment-card.due-today {
        border: 2px solid #e05252;
        box-shadow: 0 0 0 1px rgba(224,82,82,.12), 0 8px 24px rgba(160,35,35,.10);
    }
    .due-today-tag {
        display: inline-block; color: #ff8585; border: 1px solid #a83d45;
        background: rgba(168,61,69,.16); border-radius: 999px;
        padding: 3px 9px; font-size: .72rem; font-weight: 800;
        letter-spacing: .06em; text-transform: uppercase; margin-left: 8px;
        vertical-align: middle;
    }
    .target-line { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }

    .assignment-title {
        display: inline-block; color: #fff; font-size: 1.22rem;
        line-height: 1.35; font-weight: 750; padding: 9px 15px;
        border-radius: 10px; margin-bottom: 12px;
        overflow-wrap: anywhere;
    }
    .target-label {
        color: #aab8ca; text-transform: uppercase; letter-spacing: .11em;
        font-size: .78rem; font-weight: 750; margin-top: 2px;
    }
    .target-number {
        color: #fff; font-size: 2.65rem; line-height: 1.12;
        font-weight: 850; letter-spacing: -.05em; margin: 4px 0 5px 0;
    }
    .target-unit { color: #d4dce8; font-size: 1.35rem; font-weight: 700; letter-spacing: -.02em; }
    .assignment-meta { color: #9aa8ba; font-size: .9rem; margin-top: 7px; }
    .today-progress-label { color: #aab8ca; font-size: .88rem; font-weight: 650; }
    div[data-testid="stVerticalBlock"] > div:has(> .assignment-card) { gap: .35rem; }
    @media (max-width: 700px) {
        .target-number { font-size: 2.1rem; }
        .assignment-card { padding: 14px; }
    }
</style>
""", unsafe_allow_html=True)


def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            st.error("Could not read assignments.json. Make a backup before replacing it.")
    return {"assignments": [], "calendar_events": [], "calendar_name": None}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def parse_ics(uploaded_file):
    """Return busy event intervals as local-naive datetimes."""
    try:
        from icalendar import Calendar
    except ImportError as exc:
        raise RuntimeError("The 'icalendar' package is missing. Run: pip install -r requirements.txt") from exc

    calendar = Calendar.from_ical(uploaded_file.getvalue())
    events = []
    for component in calendar.walk():
        if component.name != "VEVENT":
            continue

        # Ignore events explicitly marked FREE.
        transp = str(component.get("TRANSP", "OPAQUE")).upper()
        if transp == "TRANSPARENT":
            continue

        start_prop = component.get("DTSTART")
        end_prop = component.get("DTEND")
        if not start_prop:
            continue

        start_value = start_prop.dt
        if isinstance(start_value, date) and not isinstance(start_value, datetime):
            start_dt = datetime.combine(start_value, time.min)
            end_value = end_prop.dt if end_prop else start_value + timedelta(days=1)
            if isinstance(end_value, datetime):
                end_dt = end_value.replace(tzinfo=None)
            else:
                end_dt = datetime.combine(end_value, time.min)
        else:
            start_dt = start_value
            end_value = end_prop.dt if end_prop else start_value + timedelta(hours=1)
            end_dt = end_value
            if start_dt.tzinfo is not None:
                start_dt = start_dt.astimezone().replace(tzinfo=None)
            if end_dt.tzinfo is not None:
                end_dt = end_dt.astimezone().replace(tzinfo=None)

        if end_dt > start_dt:
            events.append({
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "summary": str(component.get("SUMMARY", "Busy")),
            })
    return events


def normalize_imported_assignments(payload, today):
    """Accept either a list of assignments or an object containing an assignments list."""
    rows = payload.get("assignments", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("JSON must be a list of assignments or an object with an 'assignments' list.")

    normalized = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Assignment #{index} must be an object.")
        name = str(row.get("name", "")).strip()
        if not name:
            raise ValueError(f"Assignment #{index} is missing a name.")

        total = int(row.get("total_units", row.get("questions", 0)))
        completed = int(row.get("completed_units", row.get("done", 0)))
        due_raw = row.get("due_date", row.get("due"))
        if not due_raw:
            raise ValueError(f"Assignment '{name}' is missing due_date (YYYY-MM-DD).")
        if isinstance(due_raw, date):
            due_iso = due_raw.isoformat()
        else:
            due_iso = date.fromisoformat(str(due_raw)).isoformat()

        unit = str(row.get("unit", "Questions")).strip() or "Questions"
        if total < 1 or completed < 0 or completed > total:
            raise ValueError(f"Assignment '{name}' has invalid total/completed values.")

        course = str(row.get("course", infer_course(name))).strip()
        if course not in COURSES:
            course = "Other"

        normalized.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "course": course,
            "total_units": total,
            "unit": unit,
            "due_date": due_iso,
            "completed_units": completed,
            "today_completed": 0,
            "today_date": today.isoformat(),
        })
    return normalized


def merge_intervals(intervals, max_gap_minutes=30):
    """Merge overlapping/nearby busy events. Short gaps are not counted as free."""
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda item: item[0])
    merged = [list(intervals[0])]
    for start, end in intervals[1:]:
        previous_end = merged[-1][1]
        gap = (start - previous_end).total_seconds() / 60
        if gap <= max_gap_minutes:
            merged[-1][1] = max(previous_end, end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def daily_calendar_free_hours(day, events, wake_start, wake_end, ignore_gap_minutes):
    day_start = datetime.combine(day, wake_start)
    day_end = datetime.combine(day, wake_end)
    intervals = []
    for event in events:
        start = datetime.fromisoformat(event["start"])
        end = datetime.fromisoformat(event["end"])
        if end > day_start and start < day_end:
            intervals.append((max(start, day_start), min(end, day_end)))

    merged = merge_intervals(intervals, ignore_gap_minutes)
    free_minutes = 0
    cursor = day_start
    for start, end in merged:
        if start > cursor:
            free_minutes += (start - cursor).total_seconds() / 60
        cursor = max(cursor, end)
    if cursor < day_end:
        free_minutes += (day_end - cursor).total_seconds() / 60
    return max(0.0, free_minutes / 60)


def get_daily_availability_hours(day, settings, events, has_calendar):
    """Return usable waking-hour availability; used only to weight work across days."""
    if has_calendar:
        return daily_calendar_free_hours(
            day, events, settings["wake_start"], settings["wake_end"],
            settings["ignore_gap_minutes"]
        )
    return settings["weekday_fallback"] if day.weekday() < 5 else settings["weekend_fallback"]


def build_schedule(assignments, settings, events, has_calendar, today=None):
    """Allocate whole units by relative free-time availability, prioritizing deadlines."""
    today = today or date.today()
    active_assignments = [a for a in assignments if int(a.get("remaining_units", 0)) > 0]
    end_date = max(
        [date.fromisoformat(a["due_date"]) for a in active_assignments] or [today]
    )

    days = []
    current = today
    while current <= end_date:
        hours = get_daily_availability_hours(current, settings, events, has_calendar)
        # Logarithmic weighting prevents very open days (often weekends) from
        # absorbing a disproportionate share of the workload.
        weight = math.log1p(max(0.0, hours))
        days.append({"date": current, "availability_weight": weight})
        current += timedelta(days=1)

    plan = {d["date"].isoformat(): [] for d in days}

    # Assign earlier deadlines first. Rounding each day's share UP deliberately
    # creates a small buffer and tends to finish work before its due date.
    for assignment in sorted(assignments, key=lambda a: (a["due_date"], a["name"].lower())):
        remaining = max(0, int(assignment.get("remaining_units", 0)))
        due = date.fromisoformat(assignment["due_date"])

        # Once progress is recorded today, don't assign more of this assignment
        # to today; put its remaining units on future days instead.
        first_day = today + timedelta(days=1) if int(assignment.get("today_completed", 0)) > 0 else today
        eligible = [
            d for d in days
            if first_day <= d["date"] <= due and d["availability_weight"] > 0
        ]
        total_weight = sum(d["availability_weight"] for d in eligible)

        if remaining > 0 and eligible and total_weight > 0:
            for day_info in eligible:
                if remaining <= 0:
                    break
                ideal_share = int(assignment["remaining_units"]) * day_info["availability_weight"] / total_weight
                target = min(remaining, max(1, math.ceil(ideal_share)))
                plan[day_info["date"].isoformat()].append({
                    "assignment_id": assignment["id"],
                    "name": assignment["name"],
                    "units": target,
                    "unit": assignment["unit"],
                })
                remaining -= target

        assignment["unscheduled_units"] = remaining

    return plan, days


data = load_data()
data.setdefault("assignments", [])
data.setdefault("calendar_events", [])
data.setdefault("calendar_name", None)

st.title("Assignment Planner")
st.caption("A local study planner that uses your exported calendar and dynamically redistributes work.")

with st.sidebar:
    st.header("Calendar")
    calendar_upload = st.file_uploader("Upload Google Calendar export (.ics)", type=["ics"])
    if calendar_upload is not None:
        try:
            parsed = parse_ics(calendar_upload)
            data["calendar_events"] = parsed
            data["calendar_name"] = calendar_upload.name
            save_data(data)
            st.success(f"Imported {len(parsed)} calendar events.")
        except Exception as exc:
            st.error(str(exc))

    if data["calendar_name"]:
        st.caption(f"Current calendar: {data['calendar_name']}")
        if st.button("Remove imported calendar"):
            data["calendar_events"] = []
            data["calendar_name"] = None
            save_data(data)
            st.rerun()
    else:
        st.info("No calendar imported. The app will use your fallback availability settings.")

    st.divider()
    st.header("Scheduling settings")
    weekday_fallback = st.number_input("Assumed free hours on weekdays (if no calendar)", 0.0, 16.0, 4.0, 0.5)
    weekend_fallback = st.number_input("Assumed free hours on weekends (if no calendar)", 0.0, 16.0, 16.0, 0.5)
    ignore_gap = st.number_input("Ignore calendar gaps up to (minutes)", 0, 120, 30, 5)
    wake_start = st.time_input("Waking day starts", DEFAULT_WAKE_START)
    wake_end = st.time_input("Waking day ends", DEFAULT_WAKE_END)

settings = {
    "weekday_fallback": weekday_fallback,
    "weekend_fallback": weekend_fallback,
    "ignore_gap_minutes": ignore_gap,
    "wake_start": wake_start,
    "wake_end": wake_end,
}

if wake_end <= wake_start:
    st.error("The waking-day end must be later than the waking-day start.")
    st.stop()

today = date.today()

# Bulk assignment import
with st.expander("Import assignments in bulk (JSON)", expanded=False):
    st.write("Upload a JSON file or paste a JSON list. Required fields: name, total_units, due_date. Optional: completed_units, unit.")
    json_upload = st.file_uploader("Choose assignments JSON", type=["json"], key="bulk_json_upload")
    pasted_json = st.text_area(
        "Or paste JSON here",
        height=140,
        placeholder='[{"name":"Physics HW 3","total_units":12,"completed_units":4,"unit":"Questions","due_date":"2026-10-06"}]',
        key="bulk_json_text",
    )
    if st.button("Import assignments", type="primary", key="bulk_import_button"):
        try:
            if json_upload is not None:
                payload = json.loads(json_upload.getvalue().decode("utf-8-sig"))
            elif pasted_json.strip():
                payload = json.loads(pasted_json)
            else:
                raise ValueError("Choose a JSON file or paste JSON first.")

            incoming = normalize_imported_assignments(payload, today)
            existing_keys = {
                (a.get("name", "").strip().casefold(), a.get("due_date"))
                for a in data["assignments"]
            }
            added = 0
            skipped = 0
            for assignment in incoming:
                key = (assignment["name"].casefold(), assignment["due_date"])
                if key in existing_keys:
                    skipped += 1
                    continue
                data["assignments"].append(assignment)
                existing_keys.add(key)
                added += 1
            save_data(data)
            st.success(f"Imported {added} assignment(s)." + (f" Skipped {skipped} duplicate(s)." if skipped else ""))
            st.rerun()
        except Exception as exc:
            st.error(f"Import failed: {exc}")

# Assignment creation
with st.expander("＋ Add an assignment", expanded=not data["assignments"]):
    with st.form("new_assignment", clear_on_submit=True):
        name = st.text_input("Assignment name")
        course = st.selectbox("Course / category", COURSES, key="new_course")
        col1, col2, col3 = st.columns(3)
        total_units = col1.number_input("Total units", min_value=1, value=10, step=1)
        unit = col2.selectbox("Unit type", ["Questions", "Pages", "Chapters", "Problems", "Other"])
        due_date = col3.date_input("Due date", value=today + timedelta(days=7), min_value=today)
        col4, col5 = st.columns(2)
        completed_before = col4.number_input("Units completed before today", min_value=0, value=0, step=1)
        completed_today = col5.number_input("Units completed today", min_value=0, value=0, step=1)
        submitted = st.form_submit_button("Save assignment", type="primary")
        if submitted:
            if not name.strip():
                st.error("Enter an assignment name.")
            elif completed_before + completed_today > total_units:
                st.error("Completed units cannot exceed total units.")
            else:
                assignment = {
                    "id": str(uuid.uuid4()),
                    "name": name.strip(),
                    "course": course,
                    "total_units": int(total_units),
                    "unit": unit,
                    "due_date": due_date.isoformat(),
                    "completed_units": int(completed_before + completed_today),
                    "today_completed": int(completed_today),
                    "today_date": today.isoformat(),
                }
                data["assignments"].append(assignment)
                save_data(data)
                st.success("Assignment saved.")
                st.rerun()

# Progress rollover and remaining work
for assignment in data["assignments"]:
    if assignment.get("today_date") != today.isoformat():
        assignment["today_completed"] = 0
        assignment["today_date"] = today.isoformat()
    assignment["remaining_units"] = max(0, assignment["total_units"] - assignment["completed_units"])

if data["assignments"]:
    plan, day_rows = build_schedule(
        data["assignments"], settings, data["calendar_events"], bool(data["calendar_name"]), today
    )
else:
    plan, day_rows = {}, []

# Top-level summary
remaining_assignments = [a for a in data["assignments"] if a["remaining_units"] > 0]
today_items = plan.get(today.isoformat(), [])

tab_today, tab_assignments, tab_schedule, tab_settings = st.tabs(
    ["Today", "Assignments", "Schedule", "Data"]
)

with tab_today:
    st.subheader(f"Today's plan · {today.strftime('%A, %B') + f' {today.day}'}")
    if not today_items:
        st.info("Nothing is scheduled for today. Add assignments or check your calendar availability.")

    # Two assignments per row.
    for row_start in range(0, len(today_items), 2):
        row_cols = st.columns(2, gap="medium")
        for col_index, item in enumerate(today_items[row_start:row_start + 2]):
            with row_cols[col_index]:
                assignment = next((a for a in data["assignments"] if a["id"] == item["assignment_id"]), None)
                if not assignment:
                    continue

                course_name = assignment.get("course", infer_course(assignment["name"]))
                if course_name not in COURSE_COLORS:
                    course_name = "Other"
                course_color = COURSE_COLORS[course_name]
                due_date = date.fromisoformat(assignment["due_date"])
                is_due_today = due_date == today
                card_class = "assignment-card due-today" if is_due_today else "assignment-card"
                due_tag = '<span class="due-today-tag">Due today</span>' if is_due_today else ""
                unit_label = item["unit"].lower()
                if int(item["units"]) == 1 and unit_label.endswith("s"):
                    unit_label = unit_label[:-1]
                elif int(item["units"]) != 1 and not unit_label.endswith("s"):
                    unit_label += "s"

                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div class="assignment-title" style="background:{course_color};">{html.escape(item['name'])}</div>{due_tag}
                        <div class="target-label">Today's target</div>
                        <div class="target-line">
                            <div class="target-number">{item['units']}</div>
                            <div class="target-unit">{html.escape(unit_label)}</div>
                        </div>
                        <div class="assignment-meta">{html.escape(course_name)} &nbsp;·&nbsp; Due {due_date.strftime('%b %d')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with st.form(f"progress_{assignment['id']}"):
                    progress_col, action_col = st.columns([1, 1.15], vertical_alignment="bottom")
                    progress_col.markdown('<div class="today-progress-label">Completed today</div>', unsafe_allow_html=True)
                    amount = progress_col.number_input(
                        "Completed",
                        min_value=0,
                        max_value=max(0, int(assignment["total_units"]) - (
                            int(assignment["completed_units"]) - int(assignment.get("today_completed", 0))
                        )),
                        value=int(assignment.get("today_completed", 0)),
                        step=1, key=f"today_{assignment['id']}", label_visibility="collapsed"
                    )
                    if action_col.form_submit_button("Update", use_container_width=True):
                        previous_today = int(assignment.get("today_completed", 0))
                        delta = int(amount) - previous_today
                        assignment["completed_units"] = max(
                            0, min(assignment["total_units"], assignment["completed_units"] + delta)
                        )
                        assignment["today_completed"] = int(amount)
                        assignment["today_date"] = today.isoformat()
                        save_data(data)
                        st.rerun()

with tab_assignments:
    st.subheader("Your assignments")
    if not data["assignments"]:
        st.info("No assignments yet.")
    for assignment in data["assignments"]:
        remaining = max(0, assignment["total_units"] - assignment["completed_units"])
        due = date.fromisoformat(assignment["due_date"])
        overdue = due < today and remaining > 0
        with st.container(border=True):
            left, right = st.columns([4, 1])
            course_name = assignment.get("course", infer_course(assignment["name"]))
            if course_name not in COURSE_COLORS:
                course_name = "Other"
            left.markdown(
                f'<div class="assignment-title" style="background:{COURSE_COLORS[course_name]};">{html.escape(assignment["name"])}</div>',
                unsafe_allow_html=True,
            )
            left.caption(
                f"{assignment['completed_units']}/{assignment['total_units']} {assignment['unit'].lower()} completed"
                f" · Due {due.strftime('%b %d, %Y')}"
            )
            left.progress(assignment["completed_units"] / assignment["total_units"])
            if overdue:
                right.error("Overdue")
            elif remaining == 0:
                right.success("Complete")
            else:
                right.info(f"{remaining} left")
            with st.expander("Edit or delete"):
                with st.form(f"edit_{assignment['id']}"):
                    edit_name = st.text_input("Name", assignment["name"])
                    current_course = assignment.get("course", infer_course(assignment["name"]))
                    if current_course not in COURSES:
                        current_course = "Other"
                    edit_course = st.selectbox("Course / category", COURSES, index=COURSES.index(current_course), key=f"course_{assignment['id']}")
                    edit_total = st.number_input("Total units", min_value=1, value=int(assignment["total_units"]), key=f"total_{assignment['id']}")
                    edit_completed = st.number_input("Total completed units", min_value=0, max_value=int(edit_total), value=min(int(assignment["completed_units"]), int(edit_total)), key=f"completed_{assignment['id']}")
                    edit_due = st.date_input("Due date", value=due, key=f"due_{assignment['id']}")
                    edit_unit = st.selectbox("Unit", ["Questions", "Pages", "Chapters", "Problems", "Other"], index=["Questions", "Pages", "Chapters", "Problems", "Other"].index(assignment["unit"]) if assignment["unit"] in ["Questions", "Pages", "Chapters", "Problems", "Other"] else 0, key=f"unit_{assignment['id']}")
                    save_edit = st.form_submit_button("Save changes")
                    delete = st.form_submit_button("Delete assignment")
                    if save_edit:
                        assignment.update({
                            "name": edit_name.strip(), "course": edit_course, "total_units": int(edit_total),
                            "completed_units": int(edit_completed), "due_date": edit_due.isoformat(),
                            "unit": edit_unit,
                            "today_completed": min(int(assignment.get("today_completed", 0)), int(edit_completed))
                        })
                        save_data(data)
                        st.rerun()
                    if delete:
                        data["assignments"] = [a for a in data["assignments"] if a["id"] != assignment["id"]]
                        save_data(data)
                        st.rerun()

with tab_schedule:
    st.subheader("Upcoming daily workload")
    if not day_rows:
        st.info("Add an assignment to generate a schedule.")
    else:
        for day_info in day_rows[:21]:
            day = day_info["date"]
            items = plan.get(day.isoformat(), [])
            planned = sum(item["units"] for item in items)
            if planned <= 0 and day > today + timedelta(days=6):
                continue
            with st.container(border=True):
                st.write(f"**{day.strftime('%A, %b %d')}**")
                st.caption(f"Total planned: {planned} units")
                for item in items:
                    linked_assignment = next(
                        (a for a in data["assignments"] if a["id"] == item["assignment_id"]), None
                    )
                    item_is_due = bool(
                        linked_assignment
                        and date.fromisoformat(linked_assignment["due_date"]) == day
                    )
                    item_unit = item["unit"].lower()
                    if int(item["units"]) == 1 and item_unit.endswith("s"):
                        item_unit = item_unit[:-1]
                    elif int(item["units"]) != 1 and not item_unit.endswith("s"):
                        item_unit += "s"
                    if item_is_due:
                        st.markdown(
                            f'<div style="color:#ff7777;font-weight:750;">• {html.escape(item["name"])}: {item["units"]} {html.escape(item_unit)} — DUE TODAY</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.write(f"• {item['name']}: {item['units']} {item_unit}")

    overloaded = []
    for assignment in data["assignments"]:
        if assignment.get("unscheduled_units", 0) > 0:
            overloaded.append(assignment)
    if overloaded:
        st.warning("Some units could not be scheduled before the deadline. Check whether the calendar has any free time on those days.")
        for assignment in overloaded:
            st.write(f"• {assignment['name']}: {assignment['unscheduled_units']} units unscheduled")

with tab_settings:
    st.subheader("How scheduling works")
    st.markdown(
        "- Calendar events are treated as busy time.\n"
        "- Gaps of 30 minutes or less between events are merged into the busy block.\n"
        "- Free time is measured only inside your waking hours.\n"
        "- Calendar availability determines the relative share of work assigned to each day; it does not cap the number of units.\n"
        "- Logarithmic weighting gives diminishing scheduling preference to days with lots of free time, so weekends do not dominate.\n"
        "- Daily targets are whole units and are rounded up to build in a small early-completion buffer.\n"
        "- Earlier deadlines are scheduled first.\n"
        "- The plan is recalculated whenever you change progress, assignments, calendar, or settings."
    )
    st.caption("Calendar data and assignment data stay in this folder on your computer.")
    export_json = json.dumps(data, indent=2)
    st.download_button("Download assignment backup (JSON)", export_json, "assignments_backup.json", "application/json")
    if st.button("Export assignments as CSV"):
        import csv
        import io
        buffer = io.StringIO()
        fields = ["name", "total_units", "completed_units", "remaining_units", "unit", "due_date"]
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        for a in data["assignments"]:
            writer.writerow({field: a.get(field, "") for field in fields})
        st.download_button("Download CSV", buffer.getvalue(), "assignments.csv", "text/csv")

save_data(data)
