"""Write site/data.json, site/data.js, and the architecture diagram.

Every number on the page comes from this file. The export also checks
that the published marts contain only the example payer.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
EXAMPLE_PAYER = "payer_harborline"
NAVY = (27, 42, 65)
POWDER = (167, 199, 231)
PAPER = (244, 247, 251)
WHITE = (255, 255, 255)


def connect():
    path = os.environ.get("PAYER_DB_PATH", str(ROOT / "data" / "payer.duckdb"))
    return duckdb.connect(path, read_only=True)


def plain(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise SystemExit("Non-finite number in the page export")
        return value
    return value


def table(con, sql: str) -> list[dict]:
    cursor = con.execute(sql)
    names = [item[0] for item in cursor.description]
    rows = []
    for record in cursor.fetchall():
        rows.append({name: plain(value) for name, value in zip(names, record)})
    return rows


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def format_value(unit: str, value: float) -> str:
    if unit == "percent":
        return f"{int(round(value * 100))}%"
    if unit == "days":
        number = int(round(value))
        word = "day" if number == 1 else "days"
        return f"{number} {word}"
    return str(int(round(value)))


def percent_label(ratio: float) -> str:
    return f"{ratio * 100:.1f}%"


def month_day(iso_day: str) -> str:
    parsed = date.fromisoformat(iso_day[:10])
    return f"{parsed.strftime('%b')} {parsed.day}"


def long_day(iso_day: str) -> str:
    parsed = date.fromisoformat(iso_day[:10])
    return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"


def assert_tenant(con) -> None:
    leaked = table(
        con,
        """
        select 'fct_visits' as model_name, payer_id from marts.fct_visits
        where payer_id <> 'payer_harborline'
        union all
        select 'fct_members', payer_id from marts.fct_members
        where payer_id <> 'payer_harborline'
        union all
        select 'mart_goal_status', payer_id from marts.mart_goal_status
        where payer_id <> 'payer_harborline'
        union all
        select 'mart_actions_this_week', payer_id from marts.mart_actions_this_week
        where payer_id <> 'payer_harborline'
        """,
    )
    if leaked:
        raise SystemExit(f"Export refused rows for another payer: {leaked[:3]}")
    dim = table(con, "select payer_id from marts.dim_payer")
    if dim != [{"payer_id": EXAMPLE_PAYER}]:
        raise SystemExit(f"dim_payer is not the example payer: {dim}")


def load_goals(con) -> list[dict]:
    rows = table(
        con,
        """
        select
            goal_id as id,
            payer_id as payerId,
            label,
            subtitle,
            spark_caption as sparkCaption,
            unit,
            metric_kind as kind,
            direction,
            tile_role as tileRole,
            current_value as currentValue,
            target_value as targetValue,
            progress_ratio as progressRatio,
            pace_ratio as paceRatio,
            pct_of_pace as pctOfPace,
            status,
            status_label as statusLabel,
            delta_label as deltaLabel,
            sort_order as sortOrder
        from marts.mart_goal_status
        where payer_id = 'payer_harborline'
        order by sort_order
        """,
    )
    if len(rows) != 4:
        raise SystemExit(f"Expected 4 goals, found {len(rows)}")
    for goal in rows:
        if goal["payerId"] != EXAMPLE_PAYER:
            raise SystemExit("Goal row failed the payer filter")
        goal["currentLabel"] = format_value(goal["unit"], goal["currentValue"])
        goal["targetLabel"] = format_value(goal["unit"], goal["targetValue"])
        if goal["tileRole"] == "primary":
            goal["quarterShareLabel"] = percent_label(goal["progressRatio"]) + " of the quarter goal"
            goal["paceShareLabel"] = percent_label(goal["pctOfPace"]) + " of pace"
        for field in ("deltaLabel", "label", "subtitle"):
            text = goal.get(field) or ""
            if ";" in text or "—" in text or "Down from" in text:
                raise SystemExit(f"Page copy is not plain: {text}")
    return rows


def attach_sparklines(con, goals: list[dict]) -> None:
    rows = table(
        con,
        """
        select
            goal_id as goalId,
            cast(week_start as varchar) as weekStart,
            trend_value as value
        from marts.mart_weekly_trend
        where payer_id = 'payer_harborline'
        order by goal_id, week_start
        """,
    )
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["goalId"], []).append(
            {"label": month_day(row["weekStart"]), "value": row["value"]}
        )
    for goal in goals:
        goal["sparkline"] = grouped.get(goal["id"], [])


def load_pace(con) -> list[dict]:
    rows = table(
        con,
        """
        select
            cast(date_day as varchar) as day,
            cumulative_actual as actual,
            cumulative_pace as pace
        from marts.mart_visit_pace
        where payer_id = 'payer_harborline'
        order by date_day
        """,
    )
    if len(rows) != 92:
        raise SystemExit(f"Expected 92 pace days, found {len(rows)}")
    previous = None
    for row in rows:
        row["label"] = month_day(row["day"])
        if row["actual"] is not None:
            if previous is not None and row["actual"] < previous:
                raise SystemExit("Cumulative visits fell. The chart would look like a drop.")
            previous = row["actual"]
    return rows


def load_actions(con) -> list[dict]:
    rows = table(
        con,
        """
        select
            action_id as id,
            sort_order as sortOrder,
            title,
            metric_value as metricValue,
            sentence
        from marts.mart_actions_this_week
        where payer_id = 'payer_harborline'
        order by sort_order
        """,
    )
    if not 3 <= len(rows) <= 5:
        raise SystemExit(f"Expected 3 to 5 actions, found {len(rows)}")
    for row in rows:
        if ";" in row["sentence"] or "—" in row["sentence"]:
            raise SystemExit(f"Action copy is not plain: {row['sentence']}")
        if str(int(round(row["metricValue"]))) not in row["sentence"]:
            raise SystemExit(f"Action sentence is missing its number: {row['sentence']}")
    return rows


def load_context(con, company: dict) -> dict:
    payers = table(
        con,
        """
        select payer_id as id, payer_name as name, is_example as isExample
        from staging.stg_payers
        order by payer_name
        """,
    )
    example = next(row for row in payers if row["id"] == EXAMPLE_PAYER)
    others = [row["name"] for row in payers if row["id"] != EXAMPLE_PAYER]
    counts = table(
        con,
        """
        select
            (select count(*) from marts.fct_members) as members,
            (select count(*) from marts.fct_visits) as visits
        """,
    )[0]
    calendar = table(
        con,
        """
        select
            cast(as_of as varchar) as asOf,
            quarter_label as quarterLabel,
            days_elapsed as daysElapsed,
            days_in_period as daysInPeriod,
            on_track_ratio as onTrackRatio,
            at_risk_ratio as atRiskRatio
        from intermediate.int_calendar
        """,
    )[0]
    on_track = int(round(calendar["onTrackRatio"] * 100))
    at_risk = int(round(calendar["atRiskRatio"] * 100))
    other_names = " and ".join(others)
    warehouse_sentence = (
        f"The warehouse has {len(payers)} payers. "
        f"This page keeps {example['name']} only. "
        f"{other_names} stay upstream and are dropped from the marts. "
        f"{example['name']} has {int(counts['members'])} members and "
        f"{int(counts['visits'])} visits in the published facts."
    )
    calendar["asOfLabel"] = long_day(calendar["asOf"])
    calendar["line"] = (
        f"Through {calendar['asOfLabel']}. "
        f"Day {int(calendar['daysElapsed'])} of {int(calendar['daysInPeriod'])} "
        f"in {calendar['quarterLabel']}."
    )
    calendar["statusRule"] = (
        f"On track means {on_track}% of pace or better. "
        f"At risk means from {at_risk}% up to {on_track}%. "
        f"Behind means under {at_risk}%. "
        "Snapshot goals use the same cutoffs against the full target. "
        "When a lower number is better, on track means the value is at or under "
        "the target divided by the on-track cutoff."
    )
    return {
        "payer": {
            "id": example["id"],
            "name": example["name"],
            "note": company["exampleNote"],
        },
        "calendar": calendar,
        "warehouseSentence": warehouse_sentence,
    }


def load_build() -> dict:
    results = json.loads((ROOT / "dbt" / "target" / "run_results.json").read_text())["results"]
    manifest = json.loads((ROOT / "dbt" / "target" / "manifest.json").read_text())
    allowed = {"pass", "success"}
    bad = [row["unique_id"] for row in results if row["status"] not in allowed]
    if bad:
        raise SystemExit(f"dbt build has failures: {bad[:5]}")
    data_tests = [row for row in results if row["unique_id"].startswith("test.")]
    layers = {"staging": [], "intermediate": [], "spine": [], "marts": []}
    for node in manifest["nodes"].values():
        if node.get("resource_type") != "model":
            continue
        path = node.get("path") or ""
        if "/" in path:
            layer = path.split("/")[0]
        elif node["name"] == "metric_time_spine":
            layer = "spine"
        else:
            layer = "marts"
        if layer not in layers:
            continue
        description = " ".join((node.get("description") or "").split())
        layers[layer].append({"name": node["name"], "description": description})
    for items in layers.values():
        items.sort(key=lambda item: item["name"])
    semantic = yaml.safe_load((ROOT / "dbt" / "models" / "semantic.yml").read_text())
    metrics = []
    for metric in semantic["metrics"]:
        metrics.append(
            {
                "name": metric["name"],
                "label": metric["label"],
                "description": " ".join(metric["description"].split()),
            }
        )
    return {
        "checks": len(results),
        "dataTests": len(data_tests),
        "passed": len(results),
        "modelCount": sum(len(items) for items in layers.values()),
        "layers": layers,
        "metrics": metrics,
    }


def draw_diagram(path: Path) -> None:
    regular = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    bold = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    title_font = ImageFont.truetype(bold, 32)
    box_font = ImageFont.truetype(bold, 22)
    body_font = ImageFont.truetype(regular, 18)
    image = Image.new("RGB", (1200, 560), PAPER)
    draw = ImageDraw.Draw(image)
    draw.text((48, 36), "How the goals are built", font=title_font, fill=NAVY)
    boxes = [
        ("Generator", "Fake rows from the\nassumption files"),
        ("Raw", "DuckDB tables\nbefore cleanup"),
        ("Staging", "Latest row kept\nStatus cleaned"),
        ("Intermediate", "Clocks and gaps\nEvery payer stays"),
        ("Marts", "Payer filter\nGoals and actions"),
        ("Page", "Reads the export\nNo second math"),
    ]
    # Two rows. The path goes across the top, down, then back across the bottom.
    slots = [(0, 0), (0, 1), (0, 2), (1, 2), (1, 1), (1, 0)]
    width = 300
    height = 132
    gap_x = 36
    origin_x = 48
    rows_y = (120, 340)
    boxes_xy = []
    for title, body in boxes:
        row, col = slots[len(boxes_xy)]
        x = origin_x + col * (width + gap_x)
        y = rows_y[row]
        draw.rounded_rectangle((x, y, x + width, y + height), radius=18, fill=NAVY, outline=POWDER, width=4)
        draw.text((x + 22, y + 24), title, font=box_font, fill=WHITE)
        draw.multiline_text((x + 22, y + 64), body, font=body_font, fill=POWDER, spacing=6)
        boxes_xy.append((x, y))

    def center(index: int) -> tuple[float, float]:
        x, y = boxes_xy[index]
        return x + width / 2, y + height / 2

    def arrow(start: tuple[float, float], end: tuple[float, float]) -> None:
        draw.line((start[0], start[1], end[0], end[1]), fill=NAVY, width=4)
        if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
            sign = 1 if end[0] > start[0] else -1
            tip = (end[0] + sign * 2, end[1])
            draw.polygon(
                [(tip[0], tip[1]), (tip[0] - sign * 12, tip[1] - 7), (tip[0] - sign * 12, tip[1] + 7)],
                fill=NAVY,
            )
        else:
            tip = (end[0], end[1] + 2)
            draw.polygon([(tip[0], tip[1]), (tip[0] - 7, tip[1] - 12), (tip[0] + 7, tip[1] - 12)], fill=NAVY)

    for left, right in ((0, 1), (1, 2), (3, 4), (4, 5)):
        x1, y1 = center(left)
        x2, y2 = center(right)
        direction = 1 if x2 > x1 else -1
        arrow((x1 + direction * (width / 2 + 4), y1), (x2 - direction * (width / 2 + 10), y2))
    x1, y1 = center(2)
    x2, y2 = center(3)
    arrow((x1, y1 + height / 2 + 4), (x2, y2 - height / 2 - 10))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")


def main() -> None:
    company = load_json(ROOT / "config" / "company.json")
    profile = load_json(ROOT / "config" / "profile.json")
    con = connect()
    assert_tenant(con)
    goals = load_goals(con)
    attach_sparklines(con, goals)
    payload = {
        "company": company,
        "profile": profile,
        "goals": goals,
        "pace": load_pace(con),
        "actions": load_actions(con),
        "build": load_build(),
    }
    payload.update(load_context(con, company))
    con.close()
    SITE.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2)
    (SITE / "data.json").write_text(encoded + "\n")
    (SITE / "data.js").write_text("window.SITE_DATA = " + encoded + ";\n")
    draw_diagram(SITE / "architecture.png")
    primary = next(goal for goal in goals if goal["tileRole"] == "primary")
    print(f"Exported {SITE / 'data.js'}")
    print(
        f"Primary {primary['currentLabel']} of {primary['targetLabel']}. "
        f"{primary['paceShareLabel']}. {primary['statusLabel']}. {primary['deltaLabel']}."
    )
    print(
        f"Checks {payload['build']['checks']}. "
        f"Data tests {payload['build']['dataTests']}."
    )


if __name__ == "__main__":
    main()
