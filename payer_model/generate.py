"""Build the fake payer warehouse.

Reads assumptions/*.yml and writes data/payer.duckdb.
Harborline quarter totals are quotas. Other history uses the seed.
Nothing here is real PHI or a real Sprinter result.
"""

from __future__ import annotations

import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]
ASSUMPTIONS = ROOT / "assumptions"


def load_yaml(name: str) -> dict:
    with (ASSUMPTIONS / name).open() as handle:
        return yaml.safe_load(handle)


def parse_day(value: str) -> date:
    return date.fromisoformat(str(value))


def daterange(start: date, end: date) -> list[date]:
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def weekday_weight(day: date) -> float:
    if day.weekday() == 6:
        return 0.4
    if day.weekday() == 5:
        return 0.7
    return 1.0


def allocate(total: int, days: list[date]) -> list[int]:
    weights = [weekday_weight(day) for day in days]
    weight_sum = sum(weights)
    raw = [total * weight / weight_sum for weight in weights]
    floors = [int(value) for value in raw]
    leftover = total - sum(floors)
    order = sorted(range(len(raw)), key=lambda index: raw[index] - floors[index], reverse=True)
    for index in order[:leftover]:
        floors[index] += 1
    if sum(floors) != total:
        raise SystemExit("allocate failed to hit the quota")
    return floors


def duration_pool(count: int, low: int, high: int, median: int) -> list[int]:
    if count % 2 != 0:
        raise SystemExit("duration pool expects an even count so the median is the middle pair")
    half = (count // 2) - 1
    below = [low + (index % (median - low)) for index in range(half)]
    above = [median + 1 + (index % (high - median)) for index in range(half)]
    pool = below + [median, median] + above
    if len(pool) != count:
        raise SystemExit("duration pool size drifted")
    ordered = sorted(pool)
    left = ordered[(count // 2) - 1]
    right = ordered[count // 2]
    if (left + right) / 2 != median:
        raise SystemExit("duration pool median is not locked")
    return pool


class MemberPool:
    def __init__(self, ranges: list[tuple[int, int]]):
        self.flat: list[int] = []
        for start, end in ranges:
            self.flat.extend(range(start, end + 1))
        self.cursor = 0

    def take(self, count: int) -> list[int]:
        if count < 0 or self.cursor + count > len(self.flat):
            raise SystemExit("member pool exhausted")
        picked = self.flat[self.cursor : self.cursor + count]
        self.cursor += count
        return picked


class IdFactory:
    def __init__(self) -> None:
        self.source_row = 0

    def next_source_row(self) -> int:
        self.source_row += 1
        return self.source_row


def member_id(payer_id: str, index: int) -> str:
    return f"{payer_id}_m{index:05d}"


def at_hour(day: date, hour: int = 15) -> datetime:
    return datetime(day.year, day.month, day.day, hour, 0, 0)


class PayerBuilder:
    def __init__(self, payer: dict, population: dict, ids: IdFactory, rng: random.Random):
        self.payer = payer
        self.population = population
        self.ids = ids
        self.rng = rng
        self.payer_id = payer["id"]
        self.referrals: list[dict] = []
        self.visits: list[dict] = []
        self.gaps: list[dict] = []
        self.er_events: list[dict] = []
        self.referral_n = 0
        self.visit_n = 0
        self.gap_n = 0
        self.er_n = 0

    def add_referral(self, index: int, when: datetime, visit_type: str) -> str:
        self.referral_n += 1
        referral_id = f"{self.payer_id}_r{self.referral_n:06d}"
        sources = self.population["sources"]
        self.referrals.append(
            {
                "referral_id": referral_id,
                "member_id": member_id(self.payer_id, index),
                "payer_id": self.payer_id,
                "referred_at": when,
                "visit_type": visit_type,
                "referral_source": sources[index % len(sources)],
            }
        )
        return referral_id

    def add_visit(
        self,
        index: int,
        visit_type: str,
        status: str,
        day: date,
        referred_days_before: int,
    ) -> dict:
        self.visit_n += 1
        visit_id = f"{self.payer_id}_v{self.visit_n:06d}"
        scheduled_at = at_hour(day)
        referred_at = scheduled_at - timedelta(days=referred_days_before)
        referral_id = self.add_referral(index, referred_at, visit_type)
        completed_at = scheduled_at if status == "completed" else None
        outcome_at = None if status in ("completed", "scheduled") else scheduled_at
        if status == "completed":
            outcome_at = None
        row = {
            "visit_id": visit_id,
            "referral_id": referral_id,
            "member_id": member_id(self.payer_id, index),
            "payer_id": self.payer_id,
            "visit_type": visit_type,
            "status": status,
            "scheduled_at": scheduled_at,
            "completed_at": completed_at,
            "outcome_at": outcome_at,
            "ingest_at": datetime(2026, 11, 6, 18, 0, 0),
            "source_row": self.ids.next_source_row(),
            "member_index": index,
            "day": day,
        }
        self.visits.append(row)
        return row

    def add_gap(self, index: int, gap_type: str, due_on: date, closed_on: date | None) -> None:
        self.gap_n += 1
        self.gaps.append(
            {
                "gap_id": f"{self.payer_id}_g{self.gap_n:06d}",
                "member_id": member_id(self.payer_id, index),
                "payer_id": self.payer_id,
                "gap_type": gap_type,
                "due_on": due_on,
                "closed_on": closed_on,
            }
        )

    def add_er(self, index: int, missed_visit_id: str, event_day: date) -> None:
        self.er_n += 1
        self.er_events.append(
            {
                "event_id": f"{self.payer_id}_e{self.er_n:06d}",
                "member_id": member_id(self.payer_id, index),
                "payer_id": self.payer_id,
                "missed_visit_id": missed_visit_id,
                "event_at": at_hour(event_day, 11),
            }
        )


def cycle_types(preventive: int, chronic: int, post_discharge: int) -> list[str]:
    return (["preventive"] * preventive) + (["chronic"] * chronic) + (["post_discharge"] * post_discharge)


def build_harborline(population: dict, ids: IdFactory, rng: random.Random) -> PayerBuilder:
    payer = next(item for item in population["payers"] if item["id"] == population["example_payer_id"])
    builder = PayerBuilder(payer, population, ids, rng)
    quarter = population["harborline_quarter"]
    overdue = population["overdue"]
    er_cfg = population["er_after_miss"]
    waiting = population["waiting_referrals"]
    history = population["history"]
    future = population["future"]

    as_of = parse_day(population["as_of"])
    period_start = parse_day(population["period_start"])
    period_end = parse_day(population["period_end"])
    history_start = parse_day(population["history_start"])
    elapsed_days = daterange(period_start, as_of)
    closing_days = daterange(period_start, parse_day(quarter["closing_gap_last_day"]))
    missed_days = daterange(period_start, parse_day(quarter["missed_last_day"]))

    open_preventive = overdue["open_preventive_count"]
    open_chronic = overdue["open_chronic_count"]
    closed_count = overdue["closed_count"]
    if closed_count != quarter["closing_gap_visits"]:
        raise SystemExit("closed gaps must match closing visits")

    # Members 0-719 are overdue and get no completed visit.
    for index in range(open_preventive):
        builder.add_gap(index, "preventive", parse_day(overdue["open_preventive_due"]), None)
    for offset in range(open_chronic):
        builder.add_gap(
            open_preventive + offset,
            "chronic",
            parse_day(overdue["open_chronic_due"]),
            None,
        )

    other_completed = quarter["completed_visits"] - closed_count
    if other_completed <= 0:
        raise SystemExit("completed quota is smaller than closing visits")
    type_list = cycle_types(138, 256, 96)
    if len(type_list) != other_completed:
        raise SystemExit("visit type mix does not match the remaining completed quota")
    rng.shuffle(type_list)

    closing_counts = allocate(closed_count, closing_days)
    other_counts = allocate(other_completed, elapsed_days)
    completed_rows: list[dict] = []

    closing_index = open_preventive + open_chronic
    type_cursor = 0
    other_index = closing_index + closed_count

    for day, count in zip(closing_days, closing_counts):
        for _ in range(count):
            row = builder.add_visit(closing_index, "preventive", "completed", day, referred_days_before=1)
            builder.add_gap(closing_index, "preventive", parse_day(overdue["closed_due"]), day)
            completed_rows.append(row)
            closing_index += 1

    if closing_index != open_preventive + open_chronic + closed_count:
        raise SystemExit("closing member index drifted")

    for day, count in zip(elapsed_days, other_counts):
        for _ in range(count):
            visit_type = type_list[type_cursor]
            type_cursor += 1
            completed_rows.append(
                builder.add_visit(other_index, visit_type, "completed", day, referred_days_before=1)
            )
            other_index += 1

    if len(completed_rows) != quarter["completed_visits"]:
        raise SystemExit("completed quota missed")

    pool = duration_pool(
        quarter["completed_visits"],
        quarter["duration_low"],
        quarter["duration_high"],
        quarter["duration_median"],
    )
    rng.shuffle(pool)
    for row, days_to_complete in zip(completed_rows, pool):
        row["referred_at_override"] = row["completed_at"] - timedelta(days=days_to_complete)
        referral = next(item for item in builder.referrals if item["referral_id"] == row["referral_id"])
        referral["referred_at"] = row["referred_at_override"]

    missed_total = quarter["canceled_visits"] + quarter["no_show_visits"]
    missed_counts = allocate(missed_total, missed_days)
    missed_index = other_index
    missed_rows: list[dict] = []
    missed_statuses = (["canceled"] * quarter["canceled_visits"]) + (["no_show"] * quarter["no_show_visits"])
    status_cursor = 0
    for day, count in zip(missed_days, missed_counts):
        for _ in range(count):
            status = missed_statuses[status_cursor]
            status_cursor += 1
            visit_type = ["preventive", "chronic", "post_discharge"][missed_index % 3]
            missed_rows.append(
                builder.add_visit(missed_index, visit_type, status, day, referred_days_before=3)
            )
            missed_index += 1

    if len(missed_rows) != missed_total:
        raise SystemExit("missed quota missed")

    er_members = er_cfg["members"]
    span = er_cfg["max_days_after"] - er_cfg["min_days_after"] + 1
    for offset, row in enumerate(missed_rows[:er_members]):
        event_day = row["day"] + timedelta(days=er_cfg["min_days_after"] + (offset % span))
        if event_day > as_of:
            raise SystemExit("ER date fell after the as-of date")
        builder.add_er(row["member_index"], row["visit_id"], event_day)

    history_pool = MemberPool([(missed_index, 5999), (7090, payer["members"] - 1)])
    history_days = daterange(history_start, period_start - timedelta(days=1))
    for day in history_days:
        for index in history_pool.take(history["completed_per_day"]):
            visit_type = ["preventive", "chronic", "post_discharge"][index % 3]
            row = builder.add_visit(index, visit_type, "completed", day, referred_days_before=4 + (index % 6))
            referral = next(item for item in builder.referrals if item["referral_id"] == row["referral_id"])
            referral["referred_at"] = row["completed_at"] - timedelta(days=4 + (index % 6))
        for index in history_pool.take(history["missed_per_day"]):
            status = "canceled" if index % 2 == 0 else "no_show"
            visit_type = ["preventive", "chronic", "post_discharge"][index % 3]
            builder.add_visit(index, visit_type, status, day, referred_days_before=2)

    future_days = daterange(as_of + timedelta(days=1), period_end)
    future_index = 6000
    per_day = future["scheduled_per_day"]
    if future_index + per_day * len(future_days) - 1 > 6799:
        raise SystemExit("future visits collide with waiting referrals")
    for day in future_days:
        for _ in range(per_day):
            visit_type = ["preventive", "chronic", "post_discharge"][future_index % 3]
            builder.add_visit(future_index, visit_type, "scheduled", day, referred_days_before=6)
            future_index += 1

    waiting_day = as_of - timedelta(days=waiting["age_days"])
    for offset in range(waiting["count"]):
        index = 6800 + offset
        visit_type = ["preventive", "chronic", "post_discharge"][offset % 3]
        builder.add_referral(index, at_hour(waiting_day, 9), visit_type)

    return builder


def build_background(payer: dict, population: dict, ids: IdFactory, rng: random.Random) -> PayerBuilder:
    builder = PayerBuilder(payer, population, ids, rng)
    background = population["background"]
    history_start = parse_day(population["history_start"])
    as_of = parse_day(population["as_of"])
    open_gaps = background["open_gaps"]
    due_on = parse_day(background["open_gap_due"])
    for index in range(open_gaps):
        gap_type = "preventive" if index % 2 == 0 else "chronic"
        builder.add_gap(index, gap_type, due_on, None)

    next_index = open_gaps
    for day in daterange(history_start, as_of):
        for _ in range(background["completed_per_day"]):
            visit_type = ["preventive", "chronic", "post_discharge"][next_index % 3]
            days_before = 3 + (next_index % 8)
            row = builder.add_visit(next_index, visit_type, "completed", day, referred_days_before=days_before)
            referral = next(item for item in builder.referrals if item["referral_id"] == row["referral_id"])
            referral["referred_at"] = row["completed_at"] - timedelta(days=days_before)
            next_index += 1
        if next_index >= payer["members"]:
            raise SystemExit(f"{payer['id']} ran out of members")
        index = next_index
        status = "canceled" if day.day % 2 == 0 else "no_show"
        builder.add_visit(index, "chronic", status, day, referred_days_before=2)
        next_index += 1

    missed = [row for row in builder.visits if row["status"] in ("canceled", "no_show")]
    for offset, row in enumerate(missed[: background["er_events"]]):
        event_day = row["day"] + timedelta(days=6)
        if event_day <= as_of:
            builder.add_er(row["member_index"], row["visit_id"], event_day)
    return builder


def apply_northwind_mess(builder: PayerBuilder, population: dict, ids: IdFactory) -> None:
    mess = population["mess"]
    completed = [row for row in builder.visits if row["status"] == "completed"]
    if len(completed) < 20:
        raise SystemExit("Northwind does not have enough completed visits to mess up")

    for row in completed[: mess["duplicate_visits"]]:
        bad = dict(row)
        bad["status"] = "canceled"
        bad["completed_at"] = None
        bad["outcome_at"] = row["scheduled_at"]
        bad["ingest_at"] = datetime(2026, 11, 5, 18, 0, 0)
        bad["source_row"] = ids.next_source_row()
        bad["visit_type"] = row["visit_type"]
        builder.visits.append(bad)

    for row in completed[mess["duplicate_visits"] : mess["duplicate_visits"] + mess["blank_visit_types"]]:
        row["visit_type"] = None

    skew_start = mess["duplicate_visits"] + mess["blank_visit_types"]
    for row in completed[skew_start : skew_start + mess["clock_skew_visits"]]:
        referral = next(item for item in builder.referrals if item["referral_id"] == row["referral_id"])
        referral["referred_at"] = row["completed_at"] + timedelta(hours=2)

    upper_start = skew_start + mess["clock_skew_visits"]
    for row in completed[upper_start : upper_start + mess["uppercase_status"]]:
        row["status"] = "COMPLETED"


def member_rows(payer: dict, population: dict) -> list[dict]:
    states = population["states"]
    lines = population["lines_of_business"]
    rows = []
    enrolled = parse_day(population["history_start"])
    for index in range(payer["members"]):
        rows.append(
            {
                "member_id": member_id(payer["id"], index),
                "payer_id": payer["id"],
                "state_code": states[index % len(states)],
                "line_of_business": lines[index % len(lines)],
                "enrolled_on": enrolled,
                "has_chronic": 1 if index % 5 == 0 else 0,
            }
        )
    return rows


def week_rows(as_of: date, weeks: int = 12) -> list[dict]:
    days_since_sunday = (as_of.weekday() + 1) % 7
    last_sunday = as_of - timedelta(days=days_since_sunday)
    rows = []
    for offset in range(weeks):
        week_end = last_sunday - timedelta(days=7 * offset)
        week_start = week_end - timedelta(days=6)
        rows.append(
            {
                "week_start": week_start,
                "week_end": week_end,
                "sort_order": weeks - offset,
            }
        )
    rows.sort(key=lambda item: item["week_start"])
    for index, row in enumerate(rows, start=1):
        row["sort_order"] = index
    return rows


def drop_helper_keys(rows: list[dict], columns: list[str]) -> list[tuple]:
    return [tuple(row[column] for column in columns) for row in rows]


def create_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("create schema if not exists raw")
    statements = [
        """
        create table raw.payers (
            payer_id varchar,
            payer_name varchar,
            is_example integer
        )
        """,
        """
        create table raw.members (
            member_id varchar,
            payer_id varchar,
            state_code varchar,
            line_of_business varchar,
            enrolled_on date,
            has_chronic integer
        )
        """,
        """
        create table raw.referrals (
            referral_id varchar,
            member_id varchar,
            payer_id varchar,
            referred_at timestamp,
            visit_type varchar,
            referral_source varchar
        )
        """,
        """
        create table raw.visits (
            visit_id varchar,
            referral_id varchar,
            member_id varchar,
            payer_id varchar,
            visit_type varchar,
            status varchar,
            scheduled_at timestamp,
            completed_at timestamp,
            outcome_at timestamp,
            ingest_at timestamp,
            source_row integer
        )
        """,
        """
        create table raw.care_gaps (
            gap_id varchar,
            member_id varchar,
            payer_id varchar,
            gap_type varchar,
            due_on date,
            closed_on date
        )
        """,
        """
        create table raw.er_events (
            event_id varchar,
            member_id varchar,
            payer_id varchar,
            missed_visit_id varchar,
            event_at timestamp
        )
        """,
        """
        create table raw.goals (
            goal_id varchar,
            label varchar,
            subtitle varchar,
            spark_caption varchar,
            unit varchar,
            unit_singular varchar,
            unit_plural varchar,
            metric_kind varchar,
            direction varchar,
            target_value double,
            sort_order integer
        )
        """,
        """
        create table raw.calendar (
            period_start date,
            period_end date,
            quarter_label varchar,
            on_track_ratio double,
            at_risk_ratio double,
            example_payer_id varchar
        )
        """,
        """
        create table raw.generation_meta (
            seed integer,
            as_of date,
            history_start date,
            example_payer_id varchar
        )
        """,
        """
        create table raw.weeks (
            week_start date,
            week_end date,
            sort_order integer
        )
        """,
    ]
    for statement in statements:
        con.execute(statement)


def insert_rows(con: duckdb.DuckDBPyConnection, table: str, columns: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    placeholders = ", ".join(["?"] * len(columns))
    con.executemany(
        f"insert into raw.{table} ({', '.join(columns)}) values ({placeholders})",
        drop_helper_keys(rows, columns),
    )


def assert_harborline(con: duckdb.DuckDBPyConnection, population: dict) -> None:
    payer_id = population["example_payer_id"]
    quarter = population["harborline_quarter"]
    as_of = population["as_of"]
    period_start = population["period_start"]
    completed = con.execute(
        """
        select count(*)
        from raw.visits
        where payer_id = ?
          and lower(status) = 'completed'
          and cast(completed_at as date) between cast(? as date) and cast(? as date)
        """,
        [payer_id, period_start, as_of],
    ).fetchone()[0]
    if completed != quarter["completed_visits"]:
        raise SystemExit(f"expected {quarter['completed_visits']} completed visits, found {completed}")

    median = con.execute(
        """
        select median(
            date_diff(
                'day',
                cast(referrals.referred_at as date),
                cast(visits.completed_at as date)
            )
        )
        from raw.visits as visits
        inner join raw.referrals as referrals
            on visits.referral_id = referrals.referral_id
        where visits.payer_id = ?
          and lower(visits.status) = 'completed'
          and cast(visits.completed_at as date) between cast(? as date) and cast(? as date)
        """,
        [payer_id, period_start, as_of],
    ).fetchone()[0]
    if median != quarter["duration_median"]:
        raise SystemExit(f"expected median {quarter['duration_median']}, found {median}")

    open_gaps = con.execute(
        """
        select count(distinct member_id)
        from raw.care_gaps
        where payer_id = ?
          and gap_type in ('preventive', 'chronic')
          and due_on <= cast(? as date)
          and closed_on is null
        """,
        [payer_id, as_of],
    ).fetchone()[0]
    expected_open = population["overdue"]["open_preventive_count"] + population["overdue"]["open_chronic_count"]
    if open_gaps != expected_open:
        raise SystemExit(f"expected {expected_open} overdue members, found {open_gaps}")


def main() -> None:
    population = load_yaml("population.yml")
    goals = load_yaml("goals.yml")
    rng = random.Random(population["seed"])
    ids = IdFactory()

    harbor = build_harborline(population, ids, rng)
    backgrounds = []
    for payer in population["payers"]:
        if payer["id"] == population["example_payer_id"]:
            continue
        backgrounds.append(build_background(payer, population, ids, rng))

    northwind = next(item for item in backgrounds if item.payer_id == "payer_northwind")
    apply_northwind_mess(northwind, population, ids)

    path = Path(os.environ.get("PAYER_DB_PATH", ROOT / "data" / "payer.duckdb"))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    create_tables(con)

    insert_rows(
        con,
        "payers",
        ["payer_id", "payer_name", "is_example"],
        [
            {
                "payer_id": payer["id"],
                "payer_name": payer["name"],
                "is_example": payer["is_example"],
            }
            for payer in population["payers"]
        ],
    )

    members: list[dict] = []
    builders = [harbor, *backgrounds]
    for payer in population["payers"]:
        members.extend(member_rows(payer, population))
    insert_rows(
        con,
        "members",
        ["member_id", "payer_id", "state_code", "line_of_business", "enrolled_on", "has_chronic"],
        members,
    )

    referrals: list[dict] = []
    visits: list[dict] = []
    gaps: list[dict] = []
    events: list[dict] = []
    for builder in builders:
        referrals.extend(builder.referrals)
        visits.extend(builder.visits)
        gaps.extend(builder.gaps)
        events.extend(builder.er_events)

    insert_rows(
        con,
        "referrals",
        ["referral_id", "member_id", "payer_id", "referred_at", "visit_type", "referral_source"],
        referrals,
    )
    insert_rows(
        con,
        "visits",
        [
            "visit_id",
            "referral_id",
            "member_id",
            "payer_id",
            "visit_type",
            "status",
            "scheduled_at",
            "completed_at",
            "outcome_at",
            "ingest_at",
            "source_row",
        ],
        visits,
    )
    insert_rows(
        con,
        "care_gaps",
        ["gap_id", "member_id", "payer_id", "gap_type", "due_on", "closed_on"],
        gaps,
    )
    insert_rows(
        con,
        "er_events",
        ["event_id", "member_id", "payer_id", "missed_visit_id", "event_at"],
        events,
    )

    goal_rows = []
    for goal in goals["goals"]:
        goal_rows.append(
            {
                "goal_id": goal["id"],
                "label": goal["label"],
                "subtitle": goal["subtitle"],
                "spark_caption": goal["spark_caption"],
                "unit": goal["unit"],
                "unit_singular": goal["unit_singular"],
                "unit_plural": goal["unit_plural"],
                "metric_kind": goal["metric_kind"],
                "direction": goal["direction"],
                "target_value": goal["target"],
                "sort_order": goal["sort_order"],
            }
        )
    insert_rows(
        con,
        "goals",
        [
            "goal_id",
            "label",
            "subtitle",
            "spark_caption",
            "unit",
            "unit_singular",
            "unit_plural",
            "metric_kind",
            "direction",
            "target_value",
            "sort_order",
        ],
        goal_rows,
    )
    insert_rows(
        con,
        "calendar",
        [
            "period_start",
            "period_end",
            "quarter_label",
            "on_track_ratio",
            "at_risk_ratio",
            "example_payer_id",
        ],
        [
            {
                "period_start": parse_day(population["period_start"]),
                "period_end": parse_day(population["period_end"]),
                "quarter_label": population["quarter_label"],
                "on_track_ratio": population["on_track_ratio"],
                "at_risk_ratio": population["at_risk_ratio"],
                "example_payer_id": population["example_payer_id"],
            }
        ],
    )
    insert_rows(
        con,
        "generation_meta",
        ["seed", "as_of", "history_start", "example_payer_id"],
        [
            {
                "seed": population["seed"],
                "as_of": parse_day(population["as_of"]),
                "history_start": parse_day(population["history_start"]),
                "example_payer_id": population["example_payer_id"],
            }
        ],
    )
    insert_rows(
        con,
        "weeks",
        ["week_start", "week_end", "sort_order"],
        week_rows(parse_day(population["as_of"])),
    )

    assert_harborline(con, population)
    payers = con.execute("select count(*) from raw.payers").fetchone()[0]
    visit_count = con.execute("select count(*) from raw.visits").fetchone()[0]
    print(f"Wrote {path}")
    print(f"Payers {payers}. Visit rows {visit_count}. Seed {population['seed']}.")
    con.close()


if __name__ == "__main__":
    main()
