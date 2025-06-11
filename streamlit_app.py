
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import numpy_financial as npf

# Function definitions (from the model you've built)
def calculate_reet(purchase_price):
    brackets = [(525_000, 0.011), (1_525_000, 0.0128), (3_025_000, 0.0275), (float('inf'), 0.030)]
    tax, prev_limit = 0, 0
    for limit, rate in brackets:
        if purchase_price > limit:
            tax += (limit - prev_limit) * rate
            prev_limit = limit
        else:
            tax += (purchase_price - prev_limit) * rate
            break
    return round(tax, 2)

def calculate_mortgage_payment(loan_amount, annual_rate, term_years):
    monthly_rate = annual_rate / 12
    n_payments = term_years * 12
    return loan_amount * monthly_rate / (1 - (1 + monthly_rate) ** -n_payments)

def calculate_mortgage_schedule(loan_amount, annual_rate, term_years):
    monthly_rate = annual_rate / 12
    n_payments = term_years * 12
    monthly_payment = calculate_mortgage_payment(loan_amount, annual_rate, term_years)
    schedule, balance = [], loan_amount
    for month in range(1, n_payments + 1):
        interest_payment = balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        balance -= principal_payment
        schedule.append({
            "Month": month,
            "Interest": interest_payment,
            "Principal": principal_payment,
            "Remaining Balance": balance
        })
    return pd.DataFrame(schedule)

def simulate_stay_full(home_value, mortgage_balance, rate, term_remaining, annual_tax,
                       monthly_ins, appreciation_rate, tax_rate, years):
    monthly_pmt = calculate_mortgage_payment(mortgage_balance, rate, term_remaining)
    schedule = calculate_mortgage_schedule(mortgage_balance, rate, term_remaining)
    cash_flows = [-600_000]
    for year in range(1, years + 1):
        sched_year = schedule[schedule['Month'].between((year - 1) * 12 + 1, year * 12)]
        interest = sched_year['Interest'].sum()
        mortgage_interest_deduction = interest * tax_rate
        annual_piti = (monthly_pmt + (annual_tax / 12) + monthly_ins) * 12
        net_cash_flow = -annual_piti + mortgage_interest_deduction
        cash_flows.append(net_cash_flow)
    appreciated_value = home_value * (1 + appreciation_rate) ** years
    remaining_balance = schedule[schedule['Month'] == years * 12]['Remaining Balance'].values[0]
    net_sale_proceeds = appreciated_value - remaining_balance - calculate_reet(appreciated_value)
    cash_flows.append(net_sale_proceeds)
    return cash_flows

def simulate_home_ownership(purchase_price, equity, existing_mortgage, existing_rate,
                             existing_term, rate, term_years, tax, ins, down_pct,
                             appreciation, tax_rate, years):
    down_payment = purchase_price * down_pct
    loan_amount = purchase_price - down_payment
    monthly_pmt = calculate_mortgage_payment(loan_amount, rate, term_years)
    schedule = calculate_mortgage_schedule(loan_amount, rate, term_years)
    reet = calculate_reet(purchase_price)
    closing_costs = purchase_price * 0.015
    net_proceeds = equity
    cash_flows = [net_proceeds - down_payment - closing_costs - reet]
    deductible_interest = min(750_000, loan_amount) * rate
    annual_tax_savings = deductible_interest * tax_rate
    for _ in range(years):
        annual_piti = (monthly_pmt + tax + ins) * 12
        cash_flows.append(-annual_piti + annual_tax_savings)
    appreciated_value = purchase_price * (1 + appreciation) ** years
    remaining_balance = schedule[schedule['Month'] == years * 12]['Remaining Balance'].values[0]
    net_sale_proceeds = appreciated_value - remaining_balance - calculate_reet(appreciated_value)
    cash_flows.append(net_sale_proceeds)
    return cash_flows

# Streamlit UI
st.title("🏠 Home Ownership Scenario Model")

st.sidebar.header("Global Inputs")
holding_years = st.sidebar.slider("Holding Period (Years)", 5, 30, 10)
appreciation_rate = st.sidebar.slider("Home Appreciation Rate", 0.0, 0.08, 0.04)
discount_rate = st.sidebar.slider("Discount Rate", 0.02, 0.08, 0.05)
tax_rate = st.sidebar.slider("Marginal Tax Rate", 0.0, 0.50, 0.35)

st.sidebar.header("Current Home Inputs")
home_value = st.sidebar.number_input("Current Home Value", value=1_000_000)
mortgage_balance = st.sidebar.number_input("Current Mortgage Balance", value=400_000)
current_rate = st.sidebar.number_input("Current Mortgage Rate", value=0.0475)
current_term = st.sidebar.number_input("Years Remaining on Mortgage", value=24)
current_tax = st.sidebar.number_input("Annual Property Tax", value=8800)
current_ins = st.sidebar.number_input("Monthly Insurance", value=800)

st.sidebar.header("New Home Inputs")
price_29 = st.sidebar.number_input("Purchase Price: Option 1", value=2_900_000)
price_35 = st.sidebar.number_input("Purchase Price: Option 2", value=3_500_000)
tax_29 = st.sidebar.number_input("Monthly Tax (2.9M)", value=1993)
tax_35 = st.sidebar.number_input("Monthly Tax (3.5M)", value=2392)
ins_29 = st.sidebar.number_input("Monthly Insurance (2.9M)", value=1078)
ins_35 = st.sidebar.number_input("Monthly Insurance (3.5M)", value=1167)
annual_rate = st.sidebar.number_input("New Mortgage Rate", value=0.065)
term_years = st.sidebar.number_input("New Mortgage Term", value=30)
down_pct = st.sidebar.slider("Down Payment %", 0.1, 0.5, 0.20)

# Run model
cf_stay = simulate_stay_full(home_value, mortgage_balance, current_rate, current_term,
                             current_tax, current_ins, appreciation_rate, tax_rate, holding_years)
cf_29 = simulate_home_ownership(price_29, home_value - mortgage_balance, mortgage_balance, current_rate,
                                current_term, annual_rate, term_years, tax_29, ins_29, down_pct,
                                appreciation_rate, tax_rate, holding_years)
cf_35 = simulate_home_ownership(price_35, home_value - mortgage_balance, mortgage_balance, current_rate,
                                current_term, annual_rate, term_years, tax_35, ins_35, down_pct,
                                appreciation_rate, tax_rate, holding_years)

# Display results
def show_results(cash_flows, label):
    irr = npf.irr(cash_flows)
    npv = npf.npv(discount_rate, cash_flows)
    st.subheader(f"{label}")
    st.markdown(f"**IRR:** {irr * 100:.2f}%")
    st.markdown(f"**NPV:** ${npv:,.0f}")

st.header("📊 Financial Results")
show_results(cf_stay, "Stay in Current Home")
show_results(cf_29, "Buy $2.9M Home")
show_results(cf_35, "Buy $3.5M Home")

# Chart
df = pd.DataFrame({
    "Year": list(range(len(cf_stay))),
    "Stay": cf_stay,
    "2.9M": cf_29,
    "3.5M": cf_35
})
df.set_index("Year").cumsum().plot(figsize=(10, 6), title="Cumulative Net Cash Flow")
st.pyplot(plt.gcf())
