"""DCF 现金流贴现模型 — 计算小区居住公允价值"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import io
import base64
import os
import datetime

from valuation.dcf import (
    calc_monthly_payment, calc_purchase_fees, calc_fair_value,
    calc_npv, calc_sensitivity_matrix, find_breakeven,
    calc_annual_cashflow,
)
from valuation.report_utils import md_to_png, fig_to_html

plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "Noto Sans CJK SC",
                                    "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 输入框文字居中
st.markdown("""
<style>
div[data-testid="stNumberInput"] label p { text-align: center; width: 100%; }
div[data-testid="stNumberInput"] input { text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🏠 房产现金流估值模型")
st.markdown("计算小区居住公允价值，作为 Hedonic 调价模型的基准价。")

# ============================================================
# 侧边栏 — 所有参数
# ============================================================
with st.sidebar:
    st.header("📋 购房方案参数")
    house_price = st.number_input("总房价（元）", value=1_500_000, step=100_000, format="%d")
    down_payment_ratio = st.slider("首付比例", 15, 100, 20, 5, format="%d%%") / 100
    loan_rate = st.slider("贷款利率（年化）", 0.0, 10.0, 2.6, 0.1, format="%.1f%%") / 100
    loan_term_years = st.slider("贷款年限", 10, 30, 30, 5)

    st.divider()
    st.header("📈 估值假设")

    monthly_rent = st.number_input("同户型月租金（元）", value=3_000, step=500, format="%d")
    annual_holding_cost = st.number_input("年持有成本（元）", value=2_000, step=500, format="%d")
    real_growth_rate = st.slider("租金/成本实际增长率", 0.0, 10.0, 1.5, 0.1, format="%.1f%%") / 100
    inflation = st.slider("通胀率", -10.0, 10.0, 1.0, 0.1, format="%.1f%%") / 100
    discount_rate = st.slider("实际折现率", 0.0, 10.0, 4.0, 0.1, format="%.1f%%") / 100
    depreciation_rate = st.slider("年折旧率（物理老化）", 0.0, 5.0, 1.0, 0.1, format="%.1f%%") / 100
    terminal_pop_ratio = st.slider("终值人口比例（30年后）", 30, 100, 60, 5, format="%d%%") / 100
    holding_years = st.slider("持有期（年）", 1, 70, 30, 5)

    st.divider()
    st.header("💰 税费参数")
    col1, col2 = st.columns(2)
    with col1:
        deed_tax_rate = st.slider("契税比例", 0.0, 3.0, 1.0, 0.1, format="%.1f%%",
            help="首套 ≤140m²=1%，>140m²=1.5%；二套 ≤140m²=1%，>140m²=2%；三套及以上=3%") / 100
        agency_fee_rate = st.slider("中介费比例", 0.0, 3.0, 1.0, 0.1, format="%.1f%%") / 100
    with col2:
        vat_rate = st.slider("增值税率", 0.0, 5.0, 0.0, 0.1, format="%.1f%%", help="满二免征（持有满2年免增值税）") / 100
        iit_rate = st.slider("个人所得税率", 0.0, 5.0, 0.0, 0.1, format="%.1f%%", help="满五唯一免征（持有满5年且唯一住房免个税）") / 100
    other_purchase_fees = st.number_input("其他杂费（元）", value=0, step=500, format="%d")

    st.divider()
    generate_report = st.button("📄 生成报告", use_container_width=True)

# ============================================================
# 计算核心
# ============================================================

down_payment = house_price * down_payment_ratio
loan_amount = house_price - down_payment
purchase_fees = calc_purchase_fees(house_price, deed_tax_rate, agency_fee_rate, other_purchase_fees)
annual_payment = calc_monthly_payment(loan_amount, loan_rate, loan_term_years) * 12

fair_value, pv_rent_sum, terminal_value = calc_fair_value(
    house_price, monthly_rent, annual_holding_cost, real_growth_rate,
    discount_rate, depreciation_rate, terminal_pop_ratio, holding_years)

npv, npv_annual_pv_sum, cumulative_npv = calc_npv(
    house_price, down_payment_ratio, loan_rate, loan_term_years,
    purchase_fees, monthly_rent, annual_holding_cost, real_growth_rate,
    inflation, discount_rate, holding_years, terminal_value)

years, net_cf, rent_saved_real, holding_costs_real, loan_payment_real = calc_annual_cashflow(
    house_price, down_payment_ratio, loan_rate, loan_term_years,
    purchase_fees, monthly_rent, annual_holding_cost, real_growth_rate,
    inflation, holding_years, terminal_value)

discount_rates = [0.03, 0.04, 0.05]
growth_rates = [0.00, 0.015, 0.03]
sensitivity_matrix = calc_sensitivity_matrix(
    house_price, down_payment_ratio, loan_rate, loan_term_years,
    purchase_fees, monthly_rent, annual_holding_cost, inflation,
    holding_years, terminal_value, discount_rates, growth_rates)

be_matrix = {}
for gr in growth_rates:
    for dr in discount_rates:
        be_matrix[(dr, gr)] = find_breakeven(
            house_price, down_payment_ratio, loan_rate, loan_term_years,
            purchase_fees, monthly_rent, annual_holding_cost, inflation,
            holding_years, terminal_value, deed_tax_rate, agency_fee_rate,
            other_purchase_fees, dr, gr)
be_base = be_matrix[(discount_rate, real_growth_rate)]

# 存入 session_state 供调价页面取用
st.session_state["dcf_fair_value"] = fair_value
st.session_state["dcf_house_price"] = house_price

# ============================================================
# 展示结果
# ============================================================

col1, col2, col3 = st.columns(3)
col1.metric("居住公允价值", f"{fair_value:,.0f} 元",
            delta=f"{fair_value - house_price:+,.0f} 元 vs 售价")
col2.metric("净现值 (NPV)", f"{npv:,.0f} 元",
            delta="买房划算" if npv > 0 else "租房划算")
col3.metric("期末残值", f"{terminal_value:,} 元",
            delta=f"原价 {house_price:,} 元")

# ---------- 月供摘要 ----------
with st.expander("📄 月供与费用明细", expanded=False):
    m, c = st.columns(2)
    total_repayment = annual_payment * loan_term_years
    total_interest = total_repayment - loan_amount
    monthly_payment = annual_payment / 12
    with m:
        st.markdown(f"**月供（等额本息）:** {monthly_payment:,.0f} 元/月")
        st.markdown(f"**年供:** {annual_payment:,.0f} 元/年")
        st.markdown(f"**首付:** {down_payment:,.0f} 元")
        st.markdown(f"**贷款金额:** {loan_amount:,.0f} 元")
    with c:
        st.markdown(f"**{loan_term_years}年总还款:** {total_repayment:,.0f} 元")
        st.markdown(f"**其中利息:** {total_interest:,.0f} 元")
        st.markdown(f"**买房一次性费用:** {purchase_fees:,.0f} 元")

# ---------- 公允价值分析 ----------
st.divider()
st.subheader("📊 公允价值分析")

col1, col2 = st.columns(2)
col1.markdown(f"**省租金现值总计:** {pv_rent_sum:,.0f} 元")
col1.markdown(f"**期末残值（不折现）:** {terminal_value:,} 元")
col1.markdown(f"**居住公允价值:** {fair_value:,.0f} 元")
col1.markdown(f"**当前售价:** {house_price:,.0f} 元")

premium_ratio = (house_price - fair_value) / house_price * 100
col2.markdown(f"**价差:** {house_price - fair_value:+,.0f} 元")
if fair_value > house_price:
    col2.success(f"公允价值高于售价，居住价值上值得购买。")
else:
    col2.warning(f"公允价值低于售价（{-premium_ratio:.1f}%），"
                 f"溢价部分反映地段、供需等市场因素。")

# ---------- NPV 决策分析 ----------
st.divider()
st.subheader("📊 NPV 决策分析（买 vs 租）")

discount_rate_pct = discount_rate * 100
st.markdown(f"""
NPV 从**买房 vs 租房+理财投资**两个角度，比较哪种方式在财务上更划算：

- **买房：** 付出首付 + 月供，省下房租，持有期满卖出获得残值
- **租房：** 付出房租，将首付和税费差额投入年化 {discount_rate_pct:.0f}% 的理财

**NPV = -首付 - 税费 + Σ(省租金 - 月供 - 持有成本)/ (1+折现率)^t + 期末残值**

当 NPV > 0 → 买房划算（省下的租金和残值超过首付和月供的成本）
当 NPV < 0 → 租房划算（理财收益超过买房带来的财务回报）
""")

col1, col2 = st.columns(2)
col1.markdown(f"**首付现金流出:** {down_payment:,.0f} 元")
col1.markdown(f"**买房税费:** {purchase_fees:,.0f} 元")
col1.markdown(f"**年度现金流现值总和:** {npv_annual_pv_sum:,.0f} 元")
col1.markdown(f"**期末残值（不折现）:** {terminal_value:,.0f} 元")
col2.markdown(f"**净现值 (NPV):** {npv:,.0f} 元")
if npv > 0:
    col2.success(f"NPV > 0，当前参数下**买房比租房更划算**。")
else:
    col2.warning(f"NPV < 0，租房并将资金用于投资（年化{discount_rate*100:.0f}%）更划算。"
                 f"但需考虑居住体验、稳定性等非财务价值。")

# ---------- 敏感性分析 ----------
st.divider()
st.subheader("📋 敏感性分析")

st.markdown("观察**折现率**和**租金/成本增长率**两个关键参数变化对 NPV 的影响。"
            "如果你的判断与基准参数不同，可以在这里看到结果的变化范围。")

dr_labels = [f"{dr*100:.0f}%" for dr in discount_rates]
gr_labels = [f"{g*100:.1f}%" for g in growth_rates]

# 热力图
sensitivity_array = np.array(sensitivity_matrix)
fig_heat, ax_heat = plt.subplots(figsize=(6, 4))
im = ax_heat.imshow(sensitivity_array, cmap="RdYlGn", aspect="auto")
ax_heat.set_xticks(range(len(growth_rates)))
ax_heat.set_yticks(range(len(discount_rates)))
ax_heat.set_xticklabels(gr_labels)
ax_heat.set_yticklabels(dr_labels)
ax_heat.set_xlabel("租金/成本增长率")
ax_heat.set_ylabel("折现率")
ax_heat.set_title("NPV 敏感性矩阵")
for i in range(len(discount_rates)):
    for j in range(len(growth_rates)):
        val = sensitivity_array[i, j]
        ax_heat.text(j, i, f"{val:,.0f}", ha="center", va="center",
                color="black", fontsize=9, fontweight="bold")
plt.colorbar(im, ax=ax_heat, label="NPV（元）")
plt.tight_layout()
st.pyplot(fig_heat)

# 敏感性表格
rows = []
for i, dr in enumerate(discount_rates):
    rows.append({"折现率": dr_labels[i],
                 **{gr_labels[j]: f"{sensitivity_matrix[i][j]:,.0f}" for j in range(3)}})
st.table(rows)

# 盈亏平衡
st.subheader("📋 盈亏平衡房价（NPV=0）")
st.markdown("给定所有假设，房价卖到多少 NPV 才会归零？低于这个价格→财务上划算，高于→不划算。")

be_rows = []
for gr in growth_rates:
    be_rows.append({"增长率": f"{gr*100:.1f}%",
                    **{dr_labels[i]: f"{be_matrix[(dr, gr)]:,.0f}" for i, dr in enumerate(discount_rates)}})
st.table(be_rows)
st.caption(f"基准场景：折现率 {discount_rate*100:.0f}%、增长率 {real_growth_rate*100:.1f}% → 盈亏平衡房价 **{be_base:,.0f} 元**")

# ---------- 可视化：现金流 + 累积 NPV ----------
st.divider()
st.subheader("📈 现金流与累积 NPV")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# 图1: 年度净现金流
plot_years = years[1:]
plot_cf = net_cf[1:]
colors = ["#2ecc71" if v > 0 else "#e74c3c" for v in plot_cf]
ax1.bar(plot_years, plot_cf, color=colors, alpha=0.7)
ax1.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
ax1.set_xlabel("年份")
ax1.set_ylabel("净现金流（元）")
ax1.set_title("年度净现金流（t=1~30）")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

# 图2: 累积 NPV
ax2.plot(years, cumulative_npv, "b-o", markersize=3, linewidth=1.5)
ax2.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
ax2.set_xlabel("年份")
ax2.set_ylabel("累积 NPV（元）")
ax2.set_title("累积 NPV 曲线")
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax2.grid(True, alpha=0.3)

plt.tight_layout()
st.pyplot(fig)

# ---------- 联动提示 ----------
st.divider()
st.info("👉 切换到侧边栏 **房源调整** 页面，DCF 计算的公允价值会自动填入基准价。")

# 底部参数确认
with st.expander("📝 当前所有参数（供截图/记录）"):
    st.json({
        "购房方案": {"总房价": house_price, "首付比例": f"{down_payment_ratio*100:.0f}%",
                     "贷款利率": f"{loan_rate*100:.1f}%", "贷款年限": loan_term_years},
        "估值假设": {"月租金": monthly_rent, "持有成本": annual_holding_cost,
                     "增长率": f"{real_growth_rate*100:.1f}%", "通胀率": f"{inflation*100:.0f}%",
                     "折现率": f"{discount_rate*100:.0f}%",
                     "折旧率": f"{depreciation_rate*100:.0f}%",
                     "人口比例": f"{terminal_pop_ratio*100:.0f}%",
                     "持有期": holding_years},
        "税费": {"契税": f"{deed_tax_rate*100:.1f}%", "中介费": f"{agency_fee_rate*100:.0f}%",
                 "其他": other_purchase_fees},
        "结果": {"公允价值": f"{fair_value:,.0f}", "NPV": f"{npv:,.0f}",
                 "终值": f"{terminal_value:,}"},
    })

# ============================================================
# 报告生成
# ============================================================
if generate_report:
    with st.spinner("正在生成图文报告..."):
        # 重新生成热力图
        fig_h, ax_h = plt.subplots(figsize=(6, 4))
        im = ax_h.imshow(sensitivity_array, cmap="RdYlGn", aspect="auto")
        ax_h.set_xticks(range(len(growth_rates)))
        ax_h.set_yticks(range(len(discount_rates)))
        ax_h.set_xticklabels(gr_labels)
        ax_h.set_yticklabels(dr_labels)
        ax_h.set_xlabel("租金/成本增长率")
        ax_h.set_ylabel("折现率")
        ax_h.set_title("NPV 敏感性矩阵")
        for i in range(len(discount_rates)):
            for j in range(len(growth_rates)):
                ax_h.text(j, i, f"{sensitivity_matrix[i][j]:,.0f}", ha="center", va="center",
                        color="black", fontsize=9, fontweight="bold")
        plt.colorbar(im, ax=ax_h, label="NPV（元）")
        plt.tight_layout()
        heat_html = fig_to_html(fig_h)
        plt.close(fig_h)

        # 重新生成现金流图
        fig_cf, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        colors_bar = ["#2ecc71" if v > 0 else "#e74c3c" for v in plot_cf]
        ax1.bar(plot_years, plot_cf, color=colors_bar, alpha=0.7)
        ax1.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
        ax1.set_xlabel("年份")
        ax1.set_ylabel("净现金流（元）")
        ax1.set_title("年度净现金流")
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax2.plot(years, cumulative_npv, "b-o", markersize=3, linewidth=1.5)
        ax2.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
        ax2.set_xlabel("年份")
        ax2.set_ylabel("累积 NPV（元）")
        ax2.set_title("累积 NPV 曲线")
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax2.grid(True, alpha=0.3)
        plt.tight_layout()
        cf_html = fig_to_html(fig_cf)
        plt.close(fig_cf)

        # 预计算结论
        fv_conc = (
            f"公允价值高于售价（{fair_value - house_price:+,.0f} 元），居住价值上值得购买。"
            if fair_value > house_price
            else f"公允价值低于售价（{-premium_ratio:.1f}%），溢价部分反映地段、供需等市场因素。"
        )
        npv_conc = (
            "NPV > 0，当前参数下买房比租房更划算。"
            if npv > 0
            else f"NPV < 0，租房并将资金用于投资（年化{discount_rate*100:.0f}%）更划算。但需考虑居住体验、稳定性等非财务价值。"
        )

        report_md = f"""# 房产现金流估值报告

**生成时间：** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 一、参数假设

### 购房方案
| 参数 | 值 |
|---|---|
| 总房价 | {house_price:,.0f} 元 |
| 首付比例 | {down_payment_ratio*100:.0f}% |
| 首付金额 | {down_payment:,.0f} 元 |
| 贷款金额 | {loan_amount:,.0f} 元 |
| 贷款利率 | {loan_rate*100:.1f}% |
| 贷款年限 | {loan_term_years} 年 |

### 估值假设
| 参数 | 值 |
|---|---|
| 月租金 | {monthly_rent:,} 元 |
| 年持有成本 | {annual_holding_cost:,} 元 |
| 租金/成本增长率 | {real_growth_rate*100:.1f}% |
| 通胀率 | {inflation*100:.0f}% |
| 折现率 | {discount_rate*100:.0f}% |
| 折旧率 | {depreciation_rate*100:.0f}% |
| 终值人口比例 | {terminal_pop_ratio*100:.0f}% |
| 持有期 | {holding_years} 年 |

### 税费参数
| 参数 | 值 |
|---|---|
| 契税比例 | {deed_tax_rate*100:.1f}% |
| 中介费比例 | {agency_fee_rate*100:.0f}% |
| 增值税率 | {vat_rate*100:.1f}% |
| 个人所得税率 | {iit_rate*100:.1f}% |
| 其他杂费 | {other_purchase_fees:,.0f} 元 |

---

## 二、公允价值分析

| 项目 | 金额 |
|---|---|
| 省租金现值总计 | {pv_rent_sum:,.0f} 元 |
| 期末残值（不折现） | {terminal_value:,} 元 |
| **居住公允价值** | **{fair_value:,.0f} 元** |
| 当前售价 | {house_price:,.0f} 元 |
| 价差 | {house_price - fair_value:+,.0f} 元 |

**结论：** {fv_conc}

---

## 三、NPV 决策分析

**NPV = -首付 - 税费 + Σ(省租金 - 月供 - 持有成本) / (1+折现率)^t + 期末残值**

| 项目 | 金额 |
|---|---|
| 首付现金流出 | {down_payment:,.0f} 元 |
| 买房税费 | {purchase_fees:,.0f} 元 |
| 年度现金流现值总和 | {npv_annual_pv_sum:,.0f} 元 |
| 期末残值（不折现） | {terminal_value:,.0f} 元 |
| **净现值 (NPV)** | **{npv:,.0f} 元** |

**结论：** {npv_conc}

---

## 四、敏感性分析

### NPV 敏感性矩阵（折现率 × 增长率）

| 折现率 | {gr_labels[0]} | {gr_labels[1]} | {gr_labels[2]} |
|---|---|---|---|
| {dr_labels[0]} | {sensitivity_matrix[0][0]:,.0f} | {sensitivity_matrix[0][1]:,.0f} | {sensitivity_matrix[0][2]:,.0f} |
| {dr_labels[1]} | {sensitivity_matrix[1][0]:,.0f} | {sensitivity_matrix[1][1]:,.0f} | {sensitivity_matrix[1][2]:,.0f} |
| {dr_labels[2]} | {sensitivity_matrix[2][0]:,.0f} | {sensitivity_matrix[2][1]:,.0f} | {sensitivity_matrix[2][2]:,.0f} |

{heat_html}

### 盈亏平衡房价（NPV=0）

| 增长率 | {dr_labels[0]} | {dr_labels[1]} | {dr_labels[2]} |
|---|---|---|---|
| {gr_labels[0]} | {be_matrix[(discount_rates[0], growth_rates[0])]:,.0f} | {be_matrix[(discount_rates[1], growth_rates[0])]:,.0f} | {be_matrix[(discount_rates[2], growth_rates[0])]:,.0f} |
| {gr_labels[1]} | {be_matrix[(discount_rates[0], growth_rates[1])]:,.0f} | {be_matrix[(discount_rates[1], growth_rates[1])]:,.0f} | {be_matrix[(discount_rates[2], growth_rates[1])]:,.0f} |
| {gr_labels[2]} | {be_matrix[(discount_rates[0], growth_rates[2])]:,.0f} | {be_matrix[(discount_rates[1], growth_rates[2])]:,.0f} | {be_matrix[(discount_rates[2], growth_rates[2])]:,.0f} |

基准场景：折现率 {discount_rate*100:.0f}%、增长率 {real_growth_rate*100:.1f}% → 盈亏平衡房价 **{be_base:,.0f} 元**

---

## 五、现金流与累积 NPV

{cf_html}

---

## 六、总结

- **居住公允价值：** {fair_value:,.0f} 元
- **净现值（NPV）：** {npv:,.0f} 元
- **盈亏平衡房价：** {be_base:,.0f} 元
- **持有期：** {holding_years} 年

> **免责声明：** 本报告仅供参考，不构成投资建议。估值结果基于用户输入的假设参数，实际市场情况可能存在偏差。房产投资需综合考虑地理位置、政策变化、市场供需等多方面因素。
"""
        fname, png_bytes = md_to_png(report_md, f"dcf_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

        st.success("报告生成完成！")
        st.download_button("📥 下载 PNG", data=png_bytes,
                         file_name=fname,
                         mime="image/png", use_container_width=True)

        with st.expander("📄 报告预览"):
            st.image(png_bytes)
