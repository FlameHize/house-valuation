"""提前还贷分析模型

评估提前还贷对现金流的影响，缩短年限 vs 减少月供 vs 理财投资。
"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from valuation.prepayment import analyze_prepayment
plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "Noto Sans CJK SC",
                                    "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

st.markdown("""
<style>
div[data-testid="stNumberInput"] label p { text-align: center; width: 100%; }
div[data-testid="stNumberInput"] input { text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("💰 提前还贷分析")
st.markdown("评估提前还贷 vs 理财投资的财务影响。")

# ============================================================
# 参数输入
# ============================================================
with st.sidebar:
    st.header("📋 贷款参数")

    loan_balance = st.number_input("当前贷款余额（元）", value=1_200_000, step=100_000, format="%d")
    loan_rate = st.number_input("年利率", value=0.026, step=0.001, format="%.3f")
    remaining_years = st.slider("剩余还款年限", 10, 30, 30, 5)

    st.divider()
    st.header("💰 提前还款方案")
    prepay_amount = st.number_input("计划提前还款金额（元）", value=300_000, step=50_000, format="%d")

    st.divider()
    st.header("📈 对比参数")
    investment_return = st.number_input("预期理财年化收益率", value=0.04, step=0.005, format="%.3f")

# ============================================================
# 计算
# ============================================================
orig, plan_a, plan_b = analyze_prepayment(loan_balance, loan_rate, remaining_years, prepay_amount)

# ============================================================
# 结果展示
# ============================================================

col1, col2, col3 = st.columns(3)
col1.metric("原月供", f"{orig['monthly']:,.2f} 元",
            delta=f"剩余利息 {orig['total_interest']:,.2f} 元")
col2.metric("方案A：缩短年限", f"{plan_a['years']}年{plan_a['months']}个月",
            delta=f"省息 {plan_a['interest_saved']:,.2f} 元",
            delta_color="inverse")
col3.metric("方案B：减少月供", f"{plan_b['monthly']:,.2f} 元/月",
            delta=f"省息 {plan_b['interest_saved']:,.2f} 元",
            delta_color="inverse")

st.divider()

# ---------- 方案详情 ----------
tab1, tab2, tab3 = st.tabs(["📄 原贷款计划", "⚡ 方案A：缩短年限", "🔻 方案B：减少月供"])

with tab1:
    c1, c2 = st.columns(2)
    c1.markdown(f"**月供（等额本息）:** {orig['monthly']:,.2f} 元")
    c2.markdown(f"**剩余利息:** {orig['total_interest']:,.2f} 元")
    c1.markdown(f"**本息合计:** {orig['total_payment']:,.2f} 元")
    c2.markdown(f"**剩余期数:** {orig['total_months']} 期")

with tab2:
    st.markdown("**月供不变，更快还清**")
    c1, c2 = st.columns(2)
    c1.markdown(f"**新月供:** {plan_a['monthly']:,.2f} 元")
    c2.markdown(f"**剩余期数:** {plan_a['n_months']} 期（{plan_a['years']} 年 {plan_a['months']} 个月）")
    c1.markdown(f"**节省期限:** {orig['total_months'] - plan_a['n_months']} 期")
    c2.markdown(f"**节省利息:** {plan_a['interest_saved']:,.2f} 元")

with tab3:
    st.markdown("**年限不变，月供降低**")
    c1, c2 = st.columns(2)
    c1.markdown(f"**新月供:** {plan_b['monthly']:,.2f} 元")
    c2.markdown(f"**月供减少:** {plan_b['monthly_reduction']:,.2f} 元")
    c1.markdown(f"**剩余期数:** {orig['total_months']} 期（不变）")
    c2.markdown(f"**节省利息:** {plan_b['interest_saved']:,.2f} 元")

# ---------- 还贷 vs 理财 ----------
st.divider()
st.subheader("📊 还贷 vs 理财")

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**提前还贷等效年化收益率:** {loan_rate*100:.2f}%（无风险）")
    st.markdown(f"**理财预期年化收益率:** {investment_return*100:.2f}%（有风险）")

    if loan_rate > investment_return:
        st.success("结论：**提前还贷更划算**，还贷等效收益高于理财预期。")
    elif loan_rate < investment_return:
        st.warning("结论：**理财更划算**，但需注意市场风险。")
    else:
        st.info("结论：两者基本持平。")

with col2:
    invest_earning = prepay_amount * ((1 + investment_return) ** remaining_years - 1)
    st.markdown(f"**提前还贷省息（方案A）:** {plan_a['interest_saved']:,.2f} 元")
    st.markdown(f"**提前还贷省息（方案B）:** {plan_b['interest_saved']:,.2f} 元")
    st.markdown(f"**{prepay_amount:,} 元理财 {remaining_years} 年收益:** {invest_earning:,.2f} 元（预期）")

# ---------- 可视化 ----------
st.divider()
st.subheader("📈 月供与利息对比")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

labels = ["原计划", "缩短年限", "减少月供"]
monthly_vals = [orig["monthly"], orig["monthly"], plan_b["monthly"]]
colors_m = ["#3498db", "#e74c3c", "#2ecc71"]

bars1 = ax1.bar(labels, monthly_vals, color=colors_m, alpha=0.8, width=0.5)
for bar, val in zip(bars1, monthly_vals):
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 500,
             f"{val:,.0f}", ha="center", va="bottom", fontsize=10)
ax1.set_ylabel("月供（元）")
ax1.set_title("月供对比")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

interest_vals = [orig["total_interest"], plan_a["new_interest"], plan_b["new_interest"]]
bars2 = ax2.bar(labels, interest_vals, color=colors_m, alpha=0.8, width=0.5)
for bar, val in zip(bars2, interest_vals):
    ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2000,
             f"{val:,.0f}", ha="center", va="bottom", fontsize=10)
ax2.set_ylabel("利息总额（元）")
ax2.set_title("剩余利息对比")
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

plt.tight_layout()
st.pyplot(fig)

st.divider()
# ---------- 推荐 ----------
if plan_a["interest_saved"] > plan_b["interest_saved"]:
    st.success(f"**推荐：方案A（缩短年限）省息更多**，比方案B多省 "
               f"{plan_a['interest_saved'] - plan_b['interest_saved']:,.0f} 元。"
               + (" 注意：当前贷款利率低于理财预期，需综合考虑风险承受能力。"
                  if loan_rate < investment_return else ""))
else:
    st.info(f"**推荐：方案B（减少月供）**，每月可多 "
            f"{plan_b['monthly_reduction']:,.0f} 元现金流。"
            + (" 注意：当前贷款利率低于理财预期，需综合考虑风险承受能力。"
               if loan_rate < investment_return else ""))
