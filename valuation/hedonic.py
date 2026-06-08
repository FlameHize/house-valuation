"""特征价格调价模型 — 纯计算逻辑"""

# ============================================================
# 系数表
# ============================================================

FLOOR_ADJ = {
    "bottom": -0.06,
    "low": -0.02,
    "mid": 0.04,
    "high": 0.01,
    "top": -0.04,
}

ORIENT_ADJ = {
    "南": 0.00,
    "东南": -0.01,
    "西南": -0.015,
    "东": -0.02,
    "西": -0.025,
    "东北": -0.025,
    "西北": -0.03,
    "北": -0.03,
}

SOUTH_ROOMS_ADJ = {0: -0.01, 1: 0.00, 2: 0.01, 3: 0.02, 4: 0.03}

CROSS_VENT_ADJ = {True: 0.02, False: 0.00}

DECO_ADJ = {"精装": 0.05, "简装": 0.02, "毛坯": 0.00}

AGE_RATE = -0.005
AGE_CAP = -0.25

AREA_EFFICIENCY_K = 0.4
AREA_EFFICIENCY_BASE = 0.80

VIEW_ADJ = {"一线无遮挡": 0.05, "一般": 0.00, "有遮挡": -0.02}

NOISE_ADJ = {"安静": 0.00, "一般": 0.00, "临街": -0.03}

LAYOUT_ADJ = {"方正全明": 0.02, "普通": 0.00, "异形": -0.02}

ELEVATOR_ADJ = {"一梯一户": 0.02, "一梯两户": 0.01, "两梯四户": 0.00, "三梯六户+": -0.02}

ELEVATOR_ORDER = ["一梯一户", "一梯两户", "两梯四户", "三梯六户+"]


def calc_floor_adj(floor, total):
    if floor == 1:
        return FLOOR_ADJ["bottom"]
    if floor == total:
        return FLOOR_ADJ["top"]
    rel = floor / total
    if rel < 0.25:
        return FLOOR_ADJ["low"]
    if rel <= 0.75:
        return FLOOR_ADJ["mid"]
    return FLOOR_ADJ["high"]


def calc_age_adj(age):
    return max(AGE_RATE * age, AGE_CAP)


def calc_area_eff_adj(rate):
    return (rate / 100 - AREA_EFFICIENCY_BASE) * AREA_EFFICIENCY_K


def calc_adjustments(floor, total, orient, south_rm, cross, deco, age,
                     area_eff, view, noise, layout, elevator):
    return {
        "楼层": calc_floor_adj(floor, total),
        "主朝向": ORIENT_ADJ.get(orient, 0),
        "南向开间": SOUTH_ROOMS_ADJ.get(south_rm, 0),
        "通透性": CROSS_VENT_ADJ.get(cross, 0),
        "装修": DECO_ADJ.get(deco, 0),
        "房龄": calc_age_adj(age),
        "得房率": calc_area_eff_adj(area_eff),
        "景观视野": VIEW_ADJ.get(view, 0),
        "噪音": NOISE_ADJ.get(noise, 0),
        "户型格局": LAYOUT_ADJ.get(layout, 0),
        "梯户比": ELEVATOR_ADJ.get(elevator, 0),
    }


def calc_final_value(base, adjustments):
    val = base
    for adj in adjustments.values():
        val *= (1 + adj)
    return val
