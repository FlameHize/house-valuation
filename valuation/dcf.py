"""DCF 估值模型 — 纯计算逻辑"""

import math


def calc_monthly_payment(principal, annual_rate, term_years):
    """等额本息月供"""
    monthly_rate = annual_rate / 12
    n = term_years * 12
    if monthly_rate == 0:
        return principal / n
    return principal * monthly_rate * (1 + monthly_rate) ** n / ((1 + monthly_rate) ** n - 1)


def calc_purchase_fees(house_price, deed_tax_rate, agency_fee_rate, other_fees):
    return house_price * (deed_tax_rate + agency_fee_rate) + other_fees


def calc_fair_value(house_price, monthly_rent, annual_holding_cost, real_growth_rate,
                    discount_rate, depreciation_rate, terminal_pop_ratio, holding_years):
    """计算公允价值"""
    annual_rent = monthly_rent * 12
    fair_value_pv = []
    for t in range(1, holding_years + 1):
        rent = annual_rent * (1 + real_growth_rate) ** (t - 1)
        cost = annual_holding_cost * (1 + real_growth_rate) ** (t - 1)
        cf = rent - cost
        pv = cf / (1 + discount_rate) ** t
        fair_value_pv.append(pv)

    terminal_value = int(house_price * (1 - depreciation_rate) ** holding_years * terminal_pop_ratio)
    fair_value = sum(fair_value_pv) + terminal_value
    return fair_value, sum(fair_value_pv), terminal_value


def calc_npv(house_price, down_payment_ratio, loan_rate, loan_term_years,
             purchase_fees, monthly_rent, annual_holding_cost, real_growth_rate,
             inflation, discount_rate, holding_years, terminal_value):
    """计算 NPV"""
    down_payment = house_price * down_payment_ratio
    loan_amount = house_price - down_payment
    annual_rent = monthly_rent * 12
    annual_payment = calc_monthly_payment(loan_amount, loan_rate, loan_term_years) * 12

    npv = -down_payment - purchase_fees
    npv_cf_pv = []
    cumulative_npv = [npv]

    for t in range(1, holding_years + 1):
        rent = annual_rent * (1 + real_growth_rate) ** (t - 1)
        cost = annual_holding_cost * (1 + real_growth_rate) ** (t - 1)
        loan_real = annual_payment / (1 + inflation) ** (t - 1)
        cf = rent - cost - loan_real
        pv = cf / (1 + discount_rate) ** t
        npv_cf_pv.append(pv)
        npv += pv
        cumulative_npv.append(npv)

    npv += terminal_value
    cumulative_npv[-1] = npv
    return npv, sum(npv_cf_pv), cumulative_npv


def calc_sensitivity_matrix(house_price, down_payment_ratio, loan_rate, loan_term_years,
                            purchase_fees, monthly_rent, annual_holding_cost, inflation,
                            holding_years, terminal_value,
                            discount_rates, growth_rates):
    """敏感性矩阵"""
    matrix = []
    annual_rent = monthly_rent * 12
    for dr in discount_rates:
        row = []
        for gr in growth_rates:
            down_payment = house_price * down_payment_ratio
            loan_amount = house_price - down_payment
            annual_payment = calc_monthly_payment(loan_amount, loan_rate, loan_term_years) * 12
            npv_val = -down_payment - purchase_fees
            for t in range(1, holding_years + 1):
                rent = annual_rent * (1 + gr) ** (t - 1)
                cost = annual_holding_cost * (1 + gr) ** (t - 1)
                loan_real = annual_payment / (1 + inflation) ** (t - 1)
                cf = rent - cost - loan_real
                npv_val += cf / (1 + dr) ** t
            npv_val += terminal_value
            row.append(npv_val)
        matrix.append(row)
    return matrix


def find_breakeven(house_price, down_payment_ratio, loan_rate, loan_term_years,
                   purchase_fees, monthly_rent, annual_holding_cost, inflation,
                   holding_years, terminal_value,
                   deed_tax_rate, agency_fee_rate, other_purchase_fees,
                   dr, gr):
    """在给定折现率和增长率下，二分法找 NPV=0 的房价"""
    annual_rent = monthly_rent * 12
    lo, hi = 10_000, 10_000_000
    for _ in range(50):
        mid = (lo + hi) / 2
        dp = mid * down_payment_ratio
        fees = mid * (deed_tax_rate + agency_fee_rate) + other_purchase_fees
        la = mid - dp
        ap = calc_monthly_payment(la, loan_rate, loan_term_years) * 12
        npv_val = -dp - fees
        for t in range(1, holding_years + 1):
            rent = annual_rent * (1 + gr) ** (t - 1)
            cost = annual_holding_cost * (1 + gr) ** (t - 1)
            loan_real = ap / (1 + inflation) ** (t - 1)
            cf = rent - cost - loan_real
            npv_val += cf / (1 + dr) ** t
        npv_val += terminal_value
        if npv_val > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def calc_annual_cashflow(house_price, down_payment_ratio, loan_rate, loan_term_years,
                         purchase_fees, monthly_rent, annual_holding_cost, real_growth_rate,
                         inflation, holding_years, terminal_value):
    """逐年现金流表"""
    down_payment = house_price * down_payment_ratio
    loan_amount = house_price - down_payment
    annual_rent = monthly_rent * 12
    annual_payment = calc_monthly_payment(loan_amount, loan_rate, loan_term_years) * 12

    years = list(range(holding_years + 1))
    net_cf = []
    rent_saved_real = []
    holding_costs_real = []
    loan_payment_real = []

    for t in years:
        if t == 0:
            rent_saved_real.append(0)
            holding_costs_real.append(0)
            loan_payment_real.append(0)
            net_cf.append(-down_payment - purchase_fees)
        else:
            rent = annual_rent * (1 + real_growth_rate) ** (t - 1)
            cost = annual_holding_cost * (1 + real_growth_rate) ** (t - 1)
            loan_real = annual_payment / (1 + inflation) ** (t - 1)
            rent_saved_real.append(rent)
            holding_costs_real.append(cost)
            loan_payment_real.append(loan_real)
            net_cf.append(rent - cost - loan_real)

    net_cf[holding_years] += terminal_value
    return years, net_cf, rent_saved_real, holding_costs_real, loan_payment_real
