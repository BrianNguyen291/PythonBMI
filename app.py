import csv
import io
import math
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone

from flask import Flask, abort, render_template, request, send_file

app = Flask(__name__)
app.config.setdefault("DATABASE", os.path.join(app.instance_path, "bmi.sqlite3"))

MAX_NAME_LENGTH = 30
# Taiwan has no DST; a fixed offset avoids needing tzdata on Windows' embedded Python.
TAIPEI = timezone(timedelta(hours=8))
MILITARY_STANDARD = "國防部《體位區分標準》2023-06-01 施行"
CATEGORY_LINES = (18.5, 24, 27)
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


def bmi_guidance(bmi):
    if bmi < 18.5:
        return {
            "label": "體重過輕",
            "tone": "low",
            "advice": "留意是否攝取足夠且均衡的營養，規律進食並搭配適度肌力活動；若體重持續下降，建議諮詢醫師或營養師。",
        }
    if bmi < 24:
        return {
            "label": "健康體位",
            "tone": "healthy",
            "advice": "維持均衡飲食與規律運動，並持續留意睡眠及生活習慣，幫助保持健康體位。",
        }
    if bmi < 27:
        return {
            "label": "體重過重",
            "tone": "high",
            "advice": "可從減少含糖飲料、增加蔬菜與日常活動量開始，循序建立適合自己的健康習慣。",
        }
    return {
        "label": "肥胖",
        "tone": "obese",
        "advice": "建議與醫師或營養師討論適合自己的飲食及運動計畫，並留意血壓、血糖等健康指標。",
    }


def military_status(bmi):
    if 16.5 <= bmi <= 32:
        return "常備役"
    if 15 <= bmi <= 35:
        return "替代役"
    return "免役"


def trend(rows):
    """rows: (bmi, created_at) newest first -> points oldest first with delta vs previous."""
    points, prev = [], None
    for bmi_text, created_at in reversed(rows):
        bmi = float(bmi_text)
        delta = None if prev is None else round(bmi - prev, 1)
        points.append({"bmi": bmi_text, "value": bmi, "created_at": created_at,
                       "label": bmi_guidance(bmi)["label"], "delta": delta})
        prev = bmi
    return points


def format_delta(delta):
    if delta > 0:
        return f"▲ +{delta:.1f}"
    if delta < 0:
        return f"▼ −{-delta:.1f}"
    return "— 0.0"


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
            height_meters = height / 100
            height_squared = height_meters * height_meters
            if not math.isfinite(height_squared) or height_squared == 0:
                errors["height"] = "無法使用這組數值計算 BMI，請檢查身高與體重。"
            else:
                bmi = weight / height_squared
                if not math.isfinite(bmi) or bmi == 0:
                    errors["weight"] = "無法使用這組數值計算 BMI，請檢查身高與體重。"
                else:
                    displayed_bmi = round(bmi, 1)
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
