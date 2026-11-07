import csv
import io
import math
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone

from flask import Flask, abort, render_template, request, send_file

from bmi_logic import (
    CATEGORY_LINES,
    MILITARY_STANDARD,
    BmiInputError,
    bmi_guidance,
    calculate_bmi,
    format_delta,
    military_status,
    trend,
)

app = Flask(__name__)
app.config.setdefault("DATABASE", os.path.join(app.instance_path, "bmi.sqlite3"))

MAX_NAME_LENGTH = 30
# Taiwan has no DST; a fixed offset avoids needing tzdata on Windows' embedded Python.
TAIPEI = timezone(timedelta(hours=8))
CHART_WIDTH, CHART_HEIGHT, CHART_PAD = 600, 220, 24


@contextmanager
def db():
    path = app.config["DATABASE"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS records ("
            "id INTEGER PRIMARY KEY, name TEXT NOT NULL, bmi TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        yield conn


def save_record(name, bmi):
    created_at = datetime.now(TAIPEI).strftime("%Y-%m-%d %H:%M:%S")
    with db() as conn:
        conn.execute("INSERT INTO records (name, bmi, created_at) VALUES (?, ?, ?)", (name, bmi, created_at))


def chart(points):
    values = [p["value"] for p in points]
    low = min(min(values), CATEGORY_LINES[0]) - 2
    high = max(max(values), CATEGORY_LINES[-1]) + 2
    inner_w, inner_h = CHART_WIDTH - 2 * CHART_PAD, CHART_HEIGHT - 2 * CHART_PAD

    def y(v):
        return round(CHART_PAD + (high - v) / (high - low) * inner_h, 1)

    step = inner_w / (len(points) - 1)
    dots = [{"x": round(CHART_PAD + i * step, 1), "y": y(p["value"]), **p} for i, p in enumerate(points)]
    edges = [high, *reversed(CATEGORY_LINES), low]
    tones = ["obese", "high", "healthy", "low"]
    bands = [{"tone": t, "y": y(top), "h": round(y(bottom) - y(top), 1)} for t, top, bottom in zip(tones, edges, edges[1:])]
    lines = [{"value": v, "y": y(v)} for v in CATEGORY_LINES]
    return {"width": CHART_WIDTH, "height": CHART_HEIGHT, "pad": CHART_PAD, "dots": dots, "bands": bands, "lines": lines,
            "polyline": " ".join(f"{d['x']},{d['y']}" for d in dots)}


def history_rows(name):
    with db() as conn:
        rows = conn.execute(
            "SELECT bmi, created_at FROM records WHERE name = ? ORDER BY id DESC", (name,)
        ).fetchall()
    if not rows:
        abort(404)
    return rows


def parse_positive_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


@app.route("/", methods=["GET", "POST"])
def index():
    name_input = ""
    height_input = ""
    weight_input = ""
    errors = {}
    result = None

    if request.method == "POST":
        name_input = request.form.get("name", "").strip()[:MAX_NAME_LENGTH]
        height_input = request.form.get("height", "").strip()
        weight_input = request.form.get("weight", "").strip()
        height = parse_positive_number(height_input)
        weight = parse_positive_number(weight_input)

        if height is None:
            errors["height"] = "請輸入大於 0 的有效身高（公分）。"
        if weight is None:
            errors["weight"] = "請輸入大於 0 的有效體重（公斤）。"

        if not errors:
            try:
                displayed_bmi = calculate_bmi(height, weight)
            except BmiInputError as error:
                errors[error.field] = "無法使用這組數值計算 BMI，請檢查身高與體重。"
            else:
                result = {
                    "bmi": f"{displayed_bmi:.1f}",
                    "military": military_status(displayed_bmi),
                    "military_standard": MILITARY_STANDARD,
                    **bmi_guidance(displayed_bmi),
                }
                if name_input:
                    save_record(name_input, result["bmi"])

    return render_template(
        "index.html",
        name_input=name_input,
        height_input=height_input,
        weight_input=weight_input,
        errors=errors,
        result=result,
    )


@app.route("/users")
def users():
    with db() as conn:
        rows = conn.execute(
            "SELECT name, COUNT(*), MAX(created_at) FROM records GROUP BY name ORDER BY MAX(id) DESC"
        ).fetchall()
    return render_template("users.html", users=rows)


@app.route("/users/<path:name>")
def user_history(name):
    points = trend(history_rows(name))
    for p in points:
        p["delta_text"] = None if p["delta"] is None else format_delta(p["delta"])
    summary = None
    if len(points) > 1:
        first, last = points[0], points[-1]
        summary = {"first": first, "last": last, "delta_text": format_delta(round(last["value"] - first["value"], 1))}
    return render_template("users.html", name=name, records=list(reversed(points)), summary=summary,
                           chart=chart(points) if summary else None)


@app.route("/export/<path:name>")
def export_csv(name):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["量測時間", "BMI", "體位"])
    # Cells are server-generated (timestamp, number, fixed label), so no CSV formula injection is possible.
    writer.writerows([p["created_at"], p["bmi"], p["label"]] for p in trend(history_rows(name)))
    data = io.BytesIO(buffer.getvalue().encode("utf-8-sig"))  # BOM so Excel reads Chinese correctly
    filename = f"bmi-{name}-{datetime.now(TAIPEI):%Y%m%d}.csv"
    return send_file(data, mimetype="text/csv", as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(debug=True)
