"""BMI business rules, kept free of Flask so they can be unit tested on their own."""
import math

MILITARY_STANDARD = "國防部《體位區分標準》2023-06-01 施行"
CATEGORY_LINES = (18.5, 24, 27)


class BmiInputError(ValueError):
    """The inputs cannot produce a BMI; `field` names the input to blame."""

    def __init__(self, field):
        super().__init__(field)
        self.field = field


def calculate_bmi(height_cm, weight_kg):
    """Return BMI rounded to one decimal, or raise BmiInputError."""
    height_meters = height_cm / 100
    height_squared = height_meters * height_meters
    if not math.isfinite(height_squared) or height_squared == 0:
        raise BmiInputError("height")
    bmi = weight_kg / height_squared
    if not math.isfinite(bmi) or bmi == 0:
        raise BmiInputError("weight")
    return round(bmi, 1)


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
