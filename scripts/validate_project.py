from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "app.py",
    "requirements.txt",
    "supabase_schema.sql",
    "seed_2026.sql",
    ".streamlit/secrets.toml.example",
    "PROJECT_CONTEXT.md",
    "FEATURES.md",
    "CHANGELOG.md",
    "DATABASE_SCHEMA.md",
    "DEPLOYMENT.md",
    "TODO.md",
    "docs/decisions/0001-storage-and-secrets.md",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    require(not missing, f"Missing files: {', '.join(missing)}")

    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    ast.parse(app_source, filename="app.py")
    require("@st.cache_resource" not in app_source, "Supabase auth client must not be global")
    require("st.session_state.supabase_client" in app_source, "Session client missing")
    require("TEAM_SECRET_KEY" in app_source, "Team invite key check missing")
    require("def backup_view" in app_source, "Backup export missing")
    require("def update_task_status" in app_source, "Task status action missing")

    schema = (ROOT / "supabase_schema.sql").read_text(encoding="utf-8")
    for table in ("profiles", "people", "events", "event_people", "audit_logs"):
        require(
            f"alter table public.{table} enable row level security;" in schema,
            f"RLS missing for {table}",
        )
    require("public.is_team_member()" in schema, "Team member guard missing")
    require("public.is_admin()" in schema, "Admin guard missing")

    seed = (ROOT / "seed_2026.sql").read_text(encoding="utf-8")
    holiday_rows = re.findall(r"'holiday'", seed)
    require(len(holiday_rows) == 15, f"Expected 15 holidays, found {len(holiday_rows)}")
    require(
        "'ส่ง Mycloud ไม่ได้'" in seed
        and "'2026-08-06'" in seed
        and "'2026-08-07'" in seed
        and "'info'" in seed,
        "Mycloud info notice is missing or has the wrong dates",
    )

    secrets_example = (ROOT / ".streamlit/secrets.toml.example").read_text(
        encoding="utf-8"
    )
    require("service_role" not in secrets_example.casefold(), "Unsafe key in example")
    require(
        all(
            key in secrets_example
            for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "TEAM_SECRET_KEY")
        ),
        "Secrets example is incomplete",
    )

    print("Project validation passed.")


if __name__ == "__main__":
    main()
