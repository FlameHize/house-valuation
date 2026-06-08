"""提前还贷分析模型 — 纯计算逻辑"""

import math


def calc_monthly_payment(principal, monthly_rate, n_months):
    if monthly_rate == 0:
        return principal / n_months
    return principal * monthly_rate * (1 + monthly_rate) ** n_months / ((1 + monthly_rate) ** n_months - 1)


def calc_total_interest(principal, monthly_rate, n_months):
    monthly = calc_monthly_payment(principal, monthly_rate, n_months)
    return monthly * n_months - principal


def analyze_prepayment(loan_balance, loan_rate, remaining_years, prepay_amount):
    """分析提前还贷，返回 (orig, plan_a, plan_b)"""
    monthly_rate = loan_rate / 12
    total_months = remaining_years * 12
    orig_monthly = calc_monthly_payment(loan_balance, monthly_rate, total_months)
    orig_total_interest = calc_total_interest(loan_balance, monthly_rate, total_months)

    new_balance = loan_balance - prepay_amount

    # 方案A：缩短年限
    if monthly_rate > 0:
        if orig_monthly > new_balance * monthly_rate:
            n_new_a = math.log(orig_monthly / (orig_monthly - new_balance * monthly_rate)) / math.log(1 + monthly_rate)
            n_new_a = math.ceil(n_new_a)
        else:
            n_new_a = 1
    else:
        n_new_a = math.ceil(new_balance / orig_monthly)

    if monthly_rate > 0:
        remaining_a = (new_balance * (1 + monthly_rate) ** n_new_a -
                       orig_monthly * ((1 + monthly_rate) ** n_new_a - 1) / monthly_rate)
        if remaining_a < 0:
            remaining_a = 0
    else:
        remaining_a = 0

    new_interest_a = orig_monthly * (n_new_a - 1) + remaining_a - new_balance
    interest_saved_a = max(0, orig_total_interest - new_interest_a)

    years_new_a = n_new_a // 12
    months_new_a = n_new_a % 12

    # 方案B：减少月供
    new_monthly_b = calc_monthly_payment(new_balance, monthly_rate, total_months)
    new_interest_b = calc_total_interest(new_balance, monthly_rate, total_months)
    interest_saved_b = orig_total_interest - new_interest_b

    orig = {
        "monthly": orig_monthly,
        "total_interest": orig_total_interest,
        "total_payment": loan_balance + orig_total_interest,
        "total_months": total_months,
    }

    plan_a = {
        "new_balance": new_balance,
        "monthly": orig_monthly,
        "n_months": n_new_a,
        "years": years_new_a,
        "months": months_new_a,
        "new_interest": new_interest_a,
        "interest_saved": interest_saved_a,
    }

    plan_b = {
        "new_balance": new_balance,
        "monthly": new_monthly_b,
        "monthly_reduction": orig_monthly - new_monthly_b,
        "new_interest": new_interest_b,
        "interest_saved": interest_saved_b,
    }

    return orig, plan_a, plan_b
