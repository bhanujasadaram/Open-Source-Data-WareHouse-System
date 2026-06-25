#!/usr/bin/env python3

import json
import sys
import traceback
from datetime import date
from collections import defaultdict
import mysql.connector


def parse_date(d):
    if d is None:
        return None
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d)[:10])


def format_date(d):
    return d.strftime("%d-%b-%Y")


def format_boundary_intervals(intervals):
    if not intervals:
        return "[]"
    parts = []
    for start, end in intervals:
        parts.append(f"[{format_date(start)}\u2013{format_date(end)}]")
    return ", ".join(parts)


def merge_intervals(intervals):
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def compute_t_user(all_query_intervals):
    if not all_query_intervals:
        return 0
    merged = merge_intervals(all_query_intervals)
    return sum((end - start).days for start, end in merged)


def compute_t_member(queries_m, rec_m, t_start):
    has_queries = len(queries_m) > 0
    has_rec     = rec_m is not None

    # CASE 1: no queries, no recommendation
    if not has_queries and not has_rec:
        return 0, 1, []

    # CASE 3: no queries, recommendation exists
    if not has_queries and has_rec:
        return (rec_m - t_start).days, 0, [(t_start, rec_m)]

    queries_sorted = sorted(queries_m, key=lambda x: x[0])
    boundary = []
    idle     = 0

    # Idle before first query
    first_open = queries_sorted[0][0]
    if first_open > t_start:
        boundary.append((t_start, first_open))
        idle += max(0, (first_open - t_start).days)

    # Idle gaps between consecutive queries
    for k in range(1, len(queries_sorted)):
        prev_close = queries_sorted[k - 1][1]
        curr_open  = queries_sorted[k][0]
        if curr_open > prev_close:
            boundary.append((prev_close, curr_open))
            idle += max(0, (curr_open - prev_close).days)

    last_close = queries_sorted[-1][1]

    # CASE 2: queries, no recommendation
    if not has_rec:
        return idle, 0, boundary

    # CASE 4: queries and recommendation
    if rec_m > last_close:
        boundary.append((last_close, rec_m))
        idle += max(0, (rec_m - last_close).days)

    return idle, 0, boundary


def process_demand(demand, comments, recommendations, committee_members):
    demand_id     = demand["demand_id"]
    demand_number = demand.get("demand_number", "")
    t_start       = parse_date(demand["initialization_date"])
    t_end         = parse_date(demand["end_date"])

    if t_end is None:
        return None, []

    t_total = (t_end - t_start).days

    all_intervals     = []
    queries_by_member = defaultdict(list)

    for c in comments:
        open_d  = parse_date(c["requested_date"])
        close_d = parse_date(c["response_date"])
        if open_d and close_d:
            all_intervals.append((open_d, close_d))
            queries_by_member[c["member_id"]].append((open_d, close_d))

    t_user      = compute_t_user(all_intervals)
    t_committee = t_total - t_user

    rec_by_member = {
        r["member_id"]: parse_date(r["rec_date"])
        for r in recommendations
    }

    member_results = []
    for m in committee_members:
        mid       = m["member_id"]
        queries_m = queries_by_member.get(mid, [])
        rec_m     = rec_by_member.get(mid)
        t_member, passive, boundary_intervals = compute_t_member(
            queries_m, rec_m, t_start
        )
        member_results.append({
            "member_id":           mid,
            "member_name":         m["member_name"],
            "role":                m["role"],
            "t_member_days":       t_member,
            "passive_flag":        passive,
            "_boundary_intervals": boundary_intervals
        })

    member_results.sort(key=lambda x: x["t_member_days"], reverse=True)

    member_rows = []
    for rank, m in enumerate(member_results, start=1):
        raw_intervals = m.pop("_boundary_intervals")
        member_rows.append({
            "demand_id":           demand_id,
            "demand_number":       demand_number,
            "member_id":           m["member_id"],
            "member_name":         m["member_name"],
            "role":                m["role"],
            "t_member_days":       m["t_member_days"],
            "passive_flag":        m["passive_flag"],
            "accountability_rank": rank,
            "boundary_intervals":  format_boundary_intervals(raw_intervals)
        })

    delay_flag = 1 if t_user >= t_committee else 0

    demand_row = {
        "demand_id":           demand_id,
        "demand_number":       demand_number,
        "initialization_date": str(t_start),
        "end_date":            str(t_end),
        "t_total_days":        t_total,
        "t_user_days":         t_user,
        "t_committee_days":    t_committee,
        "delay_flag":          delay_flag
    }

    return demand_row, member_rows


def identify_array(arr):
    if not arr or not isinstance(arr, list):
        return None
    keys = set(arr[0].keys())
    if "initialization_date" in keys:
        return "demands"
    if "requested_date" in keys:
        return "comments"
    if "rec_date" in keys:
        return "recommendations"
    if "member_name" in keys:
        return "committee"
    return None


def parse_and_identify(raw):
    parts = []
    remaining = (
        raw
        .replace('\\n', '')
        .replace('\n', '')
        .replace('\r', '')
        .strip()
    )

    while remaining:
        remaining = remaining.lstrip()
        if not remaining:
            break
        depth = 0
        end   = -1
        for i, c in enumerate(remaining):
            if c in ('[', '{'):
                depth += 1
            elif c in (']', '}'):
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end == -1:
            break
        piece = remaining[:end + 1].strip()
        if piece:
            parts.append(json.loads(piece))
        remaining = remaining[end + 1:]

    result = {
        "demands":         [],
        "comments":        [],
        "recommendations": [],
        "committee":       []
    }

    for arr in parts:
        table = identify_array(arr)
        if table:
            result[table] = arr

    return result


def transform(input_data):
    demands         = input_data["demands"]
    comments        = input_data["comments"]
    recommendations = input_data["recommendations"]
    committee       = input_data["committee"]

    comments_by_demand = defaultdict(list)
    for c in comments:
        comments_by_demand[c["demand_id"]].append(c)

    recs_by_demand = defaultdict(list)
    for r in recommendations:
        recs_by_demand[r["demand_id"]].append(r)

    demand_rows = []
    member_rows = []

    for demand in demands:
        did = demand["demand_id"]
        demand_row, m_rows = process_demand(
            demand,
            comments_by_demand[did],
            recs_by_demand[did],
            committee
        )
        if demand_row:
            demand_rows.append(demand_row)
            member_rows.extend(m_rows)

    return demand_rows, member_rows


if __name__ == "__main__":
    raw = ""
    try:
        raw_bytes = sys.stdin.buffer.read()

        if raw_bytes.startswith(b'\xef\xbb\xbf'):
            raw_bytes = raw_bytes[3:]

        raw = raw_bytes.decode('utf-8', errors='replace').strip()

        while raw and raw[0] not in '[{':
            raw = raw[1:]

        if not raw:
            raise ValueError(
                "Empty input received from NiFi. "
                "Ensure Ignore STDIN = false in ExecuteStreamCommand."
            )

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                input_data = parsed
            elif isinstance(parsed, list):
                input_data = {
                    "demands":         [],
                    "comments":        [],
                    "recommendations": [],
                    "committee":       []
                }
                table = identify_array(parsed)
                if table:
                    input_data[table] = parsed
        except json.JSONDecodeError:
            input_data = parse_and_identify(raw)

        if not input_data["demands"]:
            raise ValueError(
                "demands array empty or not identified. "
                "Check that MergeContent is combining all four QueryDatabaseTable "
                "outputs before ExecuteStreamCommand."
            )

        if not input_data["committee"]:
            try:
                conn = mysql.connector.connect(
                    host="localhost",
                    port=3306,
                    user="root",
                    password="Warehouse",
                    database="demand_db"
                )
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT member_id, member_name, role FROM committee")
                input_data["committee"] = cursor.fetchall()
                cursor.close()
                conn.close()
                sys.stderr.write(
                    "WARNING: committee missing from batch — "
                    "fetched directly from MySQL\n"
                )
            except Exception as db_err:
                raise ValueError(
                    f"committee array empty and MySQL fallback failed: {db_err}"
                )

        demand_rows, member_rows = transform(input_data)

        print(json.dumps(demand_rows, default=str))
        print(json.dumps(member_rows, default=str))

        sys.exit(0)

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.stderr.write("\n=== RAW INPUT (first 2000 chars) ===\n")
        sys.stderr.write(raw[:2000])
        sys.stderr.write("\n=====================================\n")
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)
