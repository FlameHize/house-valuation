"""Hedonic 特征价格调价模型

从 DCF 页面自动获取公允价值作为基准价，输入房源特征后计算调价估值。
"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import io
import base64
import os
import datetime

from valuation.hedonic import (
    calc_adjustments, calc_final_value, ELEVATOR_ORDER,
)
from valuation.report_utils import md_to_png, fig_to_html
plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "Noto Sans CJK SC",
                                    "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

st.markdown("""
<style>
div[data-testid="stNumberInput"] label p { text-align: center; width: 100%; }
div[data-testid="stNumberInput"] input { text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("📐 特征价格调价模型")
st.markdown("在 DCF 小区公允价值的基础上，逐项调整房源特征得到最终估值。")

# ============================================================
# 侧边栏 — 基准价 + 房源特征
# ============================================================
with st.sidebar:
    st.header("📋 基准价")
    default_base = st.session_state.get("dcf_fair_value", 1_354_580)
    st.info(f"DCF 公允价值：**{default_base:,.0f} 元**"
            + ("（已同步）" if "dcf_fair_value" in st.session_state else ""))
    override = st.checkbox("手动覆盖基准价")
    if override:
        base_price = st.number_input("基准价（元）", value=int(default_base), step=100_000, format="%d")
    else:
        base_price = default_base

    st.divider()
    st.header("🏠 房源特征")

    floor_num = st.number_input("所在楼层", value=2, step=1, min_value=1)
    total_floors = st.number_input("楼栋总层数", value=11, step=1, min_value=1)
    main_orient = st.selectbox("主朝向", ["南", "东南", "西南", "东", "西", "东北", "西北", "北"])
    south_rooms = st.selectbox("南向开间数", [0, 1, 2, 3, 4])
    cross_vent = st.selectbox("通透性", ["南北通透", "非通透"])
    decoration = st.selectbox("装修", ["精装", "简装", "毛坯"], index=2)
    building_age = st.slider("房龄（年）", 0, 70, 7, 1)
    area_efficiency = st.slider("得房率（%）", 60, 120, 75, 1, format="%d%%")
    view_level = st.selectbox("景观视野", ["一线无遮挡", "一般", "有遮挡"], index=1)
    noise_level = st.selectbox("噪音", ["安静", "一般", "临街"], index=1)
    layout_type = st.selectbox("户型格局", ["方正全明", "普通", "异形"], index=1)
    elevator_ratio = st.selectbox("梯户比", ELEVATOR_ORDER, index=1)

    st.divider()
    generate_report = st.button("📄 生成报告", use_container_width=True)

# ============================================================
# 计算
# ============================================================
cross_bool = cross_vent == "南北通透"

adj_map = calc_adjustments(
    floor_num, total_floors, main_orient, south_rooms, cross_bool,
    decoration, building_age, area_efficiency, view_level,
    noise_level, layout_type, elevator_ratio,
)

final_value = calc_final_value(base_price, adj_map)

# ============================================================
# 结果展示
# ============================================================
st.divider()
st.subheader("📊 估值结果")

col1, col2, col3 = st.columns(3)
col1.metric("基准价", f"{base_price:,.0f} 元")
col2.metric("最终估值", f"{final_value:,.0f} 元")
col3.metric("调整幅度", f"{(final_value / base_price - 1) * 100:+.2f}%")

# ---------- 调整明细 ----------
st.subheader("📋 调整明细")
rows = []
for name, adj in adj_map.items():
    amt = base_price * adj
    rows.append({"因子": name, "调整率": f"{adj*100:+.2f}%", "调整金额": f"{amt:+,.0f} 元"})
st.table(rows)

# ---------- 瀑布图 ----------
st.subheader("📈 各因子贡献瀑布图")

amounts = [base_price * r for r in adj_map.values()]
cumsum = [base_price]
for a in amounts:
    cumsum.append(cumsum[-1] + a)

colors = []
for r in adj_map.values():
    if r >= 0:
        colors.append("#e74c3c" if r > 0.03 else "#f39c12")
    else:
        colors.append("#2ecc71" if r > -0.03 else "#27ae60")

fig, ax = plt.subplots(figsize=(10, 6))
labels = list(adj_map.keys())
bar_container = ax.bar(range(len(labels)), amounts, color=colors, alpha=0.8, edgecolor="white", linewidth=0.5)
ax.axhline(y=0, color="gray", linewidth=0.5)

for i, (amt, rate) in enumerate(zip(amounts, adj_map.values())):
    y = cumsum[i] + amt / 2
    ax.text(i, y, f"{rate*100:+.1f}%" + "\n" + f"{amt:+,.0f}",
            ha="center", va="center", fontsize=8, fontweight="bold",
            color="white" if abs(amt) > base_price * 0.03 else "black")

for i in range(len(labels)):
    bot = cumsum[i]
    top = cumsum[i + 1]
    lo, hi = min(bot, top), max(bot, top)
    ax.plot([i - 0.4, i + 0.4], [bot, bot], color="gray", linewidth=0.5)

ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("调整金额（元）")
ax.set_title("各因子调整贡献")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
plt.tight_layout()
st.pyplot(fig)

# ---------- 系数参考 ----------
with st.expander("📖 各因子系数参考"):
    from valuation.hedonic import (
        FLOOR_ADJ, ORIENT_ADJ, SOUTH_ROOMS_ADJ, CROSS_VENT_ADJ,
        DECO_ADJ, VIEW_ADJ, NOISE_ADJ, LAYOUT_ADJ, ELEVATOR_ADJ,
        AGE_RATE, AGE_CAP, AREA_EFFICIENCY_K, AREA_EFFICIENCY_BASE,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**楼层**")
        for k, v in FLOOR_ADJ.items():
            st.markdown(f"- {k}: {v*100:+.1f}%")
        st.markdown("**主朝向**")
        for k, v in ORIENT_ADJ.items():
            st.markdown(f"- {k}: {v*100:+.1f}%")
        st.markdown("**南向开间**")
        for k, v in SOUTH_ROOMS_ADJ.items():
            st.markdown(f"- {k} 间: {v*100:+.0f}%")
        st.markdown("**通透性**")
        st.markdown(f"- 南北通透: {CROSS_VENT_ADJ[True]*100:+.0f}%")
        st.markdown(f"- 非通透: {CROSS_VENT_ADJ[False]*100:+.0f}%")
        st.markdown("**装修**")
        for k, v in DECO_ADJ.items():
            st.markdown(f"- {k}: {v*100:+.0f}%")
    with c2:
        st.markdown("**房龄**")
        st.markdown(f"- 每年 {AGE_RATE*100:.1f}%，上限 {AGE_CAP*100:.0f}%")
        st.markdown("**得房率**")
        st.markdown(f"- (输入值 - {AREA_EFFICIENCY_BASE*100:.0f}%) × {AREA_EFFICIENCY_K}")
        st.markdown("**景观视野**")
        for k, v in VIEW_ADJ.items():
            st.markdown(f"- {k}: {v*100:+.0f}%")
        st.markdown("**噪音**")
        for k, v in NOISE_ADJ.items():
            st.markdown(f"- {k}: {v*100:+.0f}%")
        st.markdown("**户型格局**")
        for k, v in LAYOUT_ADJ.items():
            st.markdown(f"- {k}: {v*100:+.0f}%")
        st.markdown("**梯户比**")
        for k in ELEVATOR_ORDER:
            st.markdown(f"- {k}: {ELEVATOR_ADJ[k]*100:+.0f}%")

st.divider()
st.success(f"**最终估值：{base_price:,.0f} 元 → {final_value:,.0f} 元**")

# ============================================================
# 报告生成
# ============================================================
if generate_report:
    with st.spinner("正在生成图文报告..."):
        waterfall_html = fig_to_html(fig)

        adj_rows = ""
        for name, adj in adj_map.items():
            amt = base_price * adj
            adj_rows += f"| {name} | {adj*100:+.2f}% | {amt:+,.0f} 元 |\n"

        report_md = f"""# 特征价格调价报告

**生成时间：** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 一、输入参数

**基准价：** {base_price:,.0f} 元

| 特征 | 值 |
|---|---|
| 所在楼层 | {floor_num} / {total_floors} 层 |
| 主朝向 | {main_orient} |
| 南向开间 | {south_rooms} 间 |
| 通透性 | {cross_vent} |
| 装修 | {decoration} |
| 房龄 | {building_age} 年 |
| 得房率 | {area_efficiency}% |
| 景观视野 | {view_level} |
| 噪音 | {noise_level} |
| 户型格局 | {layout_type} |
| 梯户比 | {elevator_ratio} |

---

## 二、调整明细

| 因子 | 调整率 | 调整金额 |
|---|---|---|
{adj_rows}
---

## 三、瀑布图

{waterfall_html}

---

## 四、估值结果

| 项目 | 金额 |
|---|---|
| 基准价 | {base_price:,.0f} 元 |
| 最终估值 | {final_value:,.0f} 元 |
| 调整幅度 | {(final_value / base_price - 1) * 100:+.2f}% |
| 调整总金额 | {final_value - base_price:+,.0f} 元 |

---

## 五、方法说明

Hedonic 特征价格调价模型基于市场比较法原理，逐项评估房源各特征与基准小区平均水平的差异，通过调整系数修正得到个性化估值。各因子调整率基于市场经验数据，反映了不同特征对房产价值的影响程度。

> **免责声明：** 本报告仅供参考，不构成投资建议。调整系数基于一般市场规律，实际交易价格可能因市场情绪、谈判能力、政策变化等因素产生偏差。
"""
        fname, png_bytes = md_to_png(report_md, f"hedonic_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

        st.success("报告生成完成！")
        st.download_button("📥 下载 PNG", data=png_bytes,
                         file_name=fname,
                         mime="image/png", use_container_width=True)

        with st.expander("📄 报告预览"):
            st.image(png_bytes)
