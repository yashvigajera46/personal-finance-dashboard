import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from fpdf import FPDF
import os
import database as db

# Page Setup
st.set_page_config(
    page_title="FinPulse Pro | Financial Analytics",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VISIBLE CSS ANIMATIONS & CARD HOVER EFFECTS ---
st.markdown("""
<style>
    @keyframes floatGraphic {
        0% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-8px) rotate(2deg); }
        100% { transform: translateY(0px) rotate(0deg); }
    }

    @keyframes subtlePulse {
        0% { box-shadow: 0 4px 6px rgba(139, 92, 246, 0.08); }
        50% { box-shadow: 0 10px 20px rgba(139, 92, 246, 0.25); }
        100% { box-shadow: 0 4px 6px rgba(139, 92, 246, 0.08); }
    }

    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 2px solid #ede9fe !important;
        padding: 1.2rem !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 8px rgba(76, 29, 149, 0.06) !important;
        transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease !important;
        animation: subtlePulse 4s infinite ease-in-out;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-8px) scale(1.02) !important;
        box-shadow: 0 14px 28px rgba(124, 58, 237, 0.22) !important;
        border-color: #8b5cf6 !important;
    }
    div[data-testid="stMetricLabel"] > div {
        color: #6b7280 !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }
    div[data-testid="stMetricValue"] > div {
        color: #1e1b4b !important;
        font-weight: 800 !important;
    }

    div.stButton > button {
        background-color: #7c3aed !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease !important;
    }
    div.stButton > button:hover {
        background-color: #6d28d9 !important;
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow: 0 8px 18px rgba(124, 58, 237, 0.35) !important;
    }

    .floating-logo {
        animation: floatGraphic 3s ease-in-out infinite;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
db.init_db()

# Currency mapping
CURRENCY_SYMBOLS = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£"
}

# --- HELPER: SAFE PDF GENERATION ---
def generate_pdf_report(df, total_income, total_expense, net_savings, curr_code):
    pdf_label_map = {
        "INR": "Rs. ",
        "USD": "$ ",
        "EUR": "EUR ",
        "GBP": "GBP "
    }
    pdf_sym = pdf_label_map.get(curr_code, f"{curr_code} ")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 18)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 12, "FinPulse - Financial Statement Report", ln=True, align="C")
    
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, f"Generated on: {date.today().strftime('%B %d, %Y')} | Currency: {curr_code}", ln=True, align="C")
    pdf.ln(6)

    # Summary box
    pdf.set_fill_color(248, 247, 252)
    pdf.rect(10, 32, 190, 26, 'F')
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_text_color(30, 27, 75)
    pdf.text(15, 42, f"Total Inflow:  {pdf_sym}{total_income:,.2f}")
    pdf.text(80, 42, f"Total Outflow: {pdf_sym}{total_expense:,.2f}")
    pdf.text(145, 42, f"Net Balance:   {pdf_sym}{net_savings:,.2f}")
    pdf.ln(20)

    # Table Header
    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_fill_color(226, 224, 240)
    pdf.set_text_color(30, 27, 75)
    pdf.cell(24, 8, "Date", 1, 0, 'C', True)
    pdf.cell(18, 8, "Type", 1, 0, 'C', True)
    pdf.cell(38, 8, "Category", 1, 0, 'C', True)
    pdf.cell(28, 8, "Payment", 1, 0, 'C', True)
    pdf.cell(28, 8, "Amount", 1, 0, 'C', True)
    pdf.cell(54, 8, "Description", 1, 1, 'C', True)

    # Rows
    pdf.set_font("Helvetica", size=9)
    for _, row in df.head(30).iterrows():
        desc = str(row['description']) if row['description'] else "-"
        desc = desc.encode('ascii', 'ignore').decode('ascii')
        if len(desc) > 25:
            desc = desc[:22] + "..."
        pdf.cell(24, 7, str(row['date'])[:10], 1)
        pdf.cell(18, 7, str(row['type']), 1)
        pdf.cell(38, 7, str(row['category']), 1)
        pdf.cell(28, 7, str(row.get('payment_method', 'Cash')), 1)
        pdf.cell(28, 7, f"{pdf_sym}{row['amount']:,.2f}", 1, 0, 'R')
        pdf.cell(54, 7, desc, 1, 1)

    return bytes(pdf.output())

# --- SIDEBAR: ENTRY FORM WITH SEPARATE CURRENCY ---
with st.sidebar:
    st.header("➕ Log Transaction")

    trans_date = st.date_input("Date", value=date.today())
    trans_type = st.selectbox("Type", ["Expense", "Income"])

    base_cats = {
        "Expense": ["Food & Dining", "Rent & Utilities", "Transport", "Shopping", "Entertainment", "Health", "Education", "Other"],
        "Income": ["Salary", "Freelance", "Stipend", "Investment", "Other"]
    }
    custom_saved = db.get_custom_categories(trans_type)
    combined_cats = base_cats[trans_type] + [c for c in custom_saved if c not in base_cats[trans_type]]
    combined_cats.append("➕ Create New Category...")

    chosen_category = st.selectbox("Category", combined_cats)
    if chosen_category == "➕ Create New Category...":
        new_cat_input = st.text_input("Enter New Category Name")
        if st.button("Save New Category"):
            if new_cat_input.strip():
                db.add_custom_category(new_cat_input.strip(), trans_type)
                st.toast(f"Category added: {new_cat_input}", icon="✨")
                st.rerun()
        final_category = new_cat_input.strip() if new_cat_input.strip() else "Other"
    else:
        final_category = chosen_category

    # Transaction-specific currency
    entry_currency = st.selectbox("Currency for this transaction", ["INR", "USD", "EUR", "GBP"])
    entry_sym = CURRENCY_SYMBOLS[entry_currency]

    amount = st.number_input(f"Amount ({entry_sym})", min_value=0.01, step=5.0, format="%.2f")
    payment_mode = st.selectbox("Payment Method", ["UPI / Net Banking", "Cash", "Credit Card", "Debit Card"])
    selected_tags = st.multiselect("Tags", ["#Personal", "#Academic", "#Work", "#Trip", "#Bill", "#TaxDeductible"])
    description = st.text_input("Description / Notes")

    receipt_file = st.file_uploader("Attach Bill/Receipt (Optional)", type=["png", "jpg", "jpeg"])

    if st.button("Save Record", use_container_width=True):
        saved_receipt_path = ""
        if receipt_file is not None:
            filename = f"{int(datetime.now().timestamp())}_{receipt_file.name}"
            saved_receipt_path = os.path.join(db.RECEIPTS_DIR, filename)
            with open(saved_receipt_path, "wb") as f:
                f.write(receipt_file.getbuffer())

        tag_str = ", ".join(selected_tags)
        db.add_transaction(trans_date, trans_type, final_category, amount, entry_currency, description, payment_mode, tag_str, saved_receipt_path)
        
        if trans_type == "Income":
            st.balloons()
            st.toast(f"Inflow of {entry_sym}{amount:,.2f} recorded!", icon="🎉")
        else:
            st.toast(f"Expense of {entry_sym}{amount:,.2f} recorded.", icon="📝")
            
        st.rerun()

    st.markdown("---")
    st.header("🎯 Target Budget")
    budget_currency = st.selectbox("Budget Currency", ["INR", "USD", "EUR", "GBP"], key="budget_curr")
    budget_sym = CURRENCY_SYMBOLS[budget_currency]
    monthly_budget = st.number_input(f"Monthly Budget Cap ({budget_sym})", min_value=100.0, value=1500.0, step=100.0)

# --- HEADER SECTION WITH ANIMATED EMBLEM ---
head_col1, head_col2 = st.columns([5, 1])
with head_col1:
    st.title("FinPulse Financial Analytics")
    st.caption("Cash flow monitoring, separate currency ledgers, and budget intelligence.")
with head_col2:
    st.markdown("""
    <div class="floating-logo" style="text-align: right; padding-top: 10px;">
        <svg width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="4" width="20" height="16" rx="4"></rect>
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M6 12h.01M18 12h.01"></path>
        </svg>
    </div>
    """, unsafe_allow_html=True)

df = db.get_all_transactions()

if df.empty:
    st.info("👋 Database is empty. Use the left sidebar to add transactions.")
else:
    df["date"] = pd.to_datetime(df["date"])
    df["date_only"] = df["date"].dt.date
    if "currency" not in df.columns:
        df["currency"] = "INR"

    # --- ADVANCED FILTER BAR ---
    with st.expander("🔍 Filter Transactions & Currency View", expanded=True):
        f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
        with f_col1:
            available_currencies = list(df["currency"].dropna().unique())
            active_currency = st.selectbox("View Currency", available_currencies if available_currencies else ["INR"])
            active_sym = CURRENCY_SYMBOLS.get(active_currency, active_currency)
        with f_col2:
            all_types = ["All"] + list(df["type"].unique())
            selected_type = st.selectbox("Type Filter", all_types)
        with f_col3:
            all_cats = ["All"] + list(df["category"].unique())
            selected_cat = st.selectbox("Category Filter", all_cats)
        with f_col4:
            all_modes = ["All"] + list(df["payment_method"].dropna().unique())
            selected_mode = st.selectbox("Payment Mode", all_modes)
        with f_col5:
            min_date = df["date_only"].min()
            max_date = df["date_only"].max()
            date_range = st.date_input("Date Range", value=(min_date, max_date))

    # Currency filter scoping
    currency_scoped_df = df[df["currency"] == active_currency].copy()

    filtered_df = currency_scoped_df.copy()
    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["type"] == selected_type]
    if selected_cat != "All":
        filtered_df = filtered_df[filtered_df["category"] == selected_cat]
    if selected_mode != "All":
        filtered_df = filtered_df[filtered_df["payment_method"] == selected_mode]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[(filtered_df["date_only"] >= start_date) & (filtered_df["date_only"] <= end_date)]

    # --- TOP METRIC CARDS ---
    total_income = filtered_df[filtered_df["type"] == "Income"]["amount"].sum()
    total_expense = filtered_df[filtered_df["type"] == "Expense"]["amount"].sum()
    net_savings = total_income - total_expense
    savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Income", f"{active_sym}{total_income:,.2f}")
    kpi2.metric("Total Expenses", f"{active_sym}{total_expense:,.2f}")
    kpi3.metric("Net Savings", f"{active_sym}{net_savings:,.2f}", delta=f"{savings_rate:.1f}% rate")
    
    budget_usage = (total_expense / monthly_budget) * 100 if active_currency == budget_currency else 0.0
    if active_currency == budget_currency:
        kpi4.metric(
            f"Budget Used ({active_currency})",
            f"{budget_usage:.1f}%",
            delta=f"{active_sym}{monthly_budget - total_expense:,.2f} left",
            delta_color="normal" if budget_usage <= 100 else "inverse"
        )
        st.progress(min(budget_usage / 100.0, 1.0))
        if budget_usage > 100:
            st.error(f"⚠️ Budget Alert: Exceeded monthly target by {active_sym}{total_expense - monthly_budget:,.2f}!")
    else:
        kpi4.metric("Budget Scope", f"{budget_currency}", delta="Different currency selected")

    st.markdown("---")

    # --- WORKSPACE TABS ---
    tab_analytics, tab_budgets, tab_subs, tab_crud, tab_io = st.tabs([
        "📊 Analytics & Trends",
        "🎯 Category Budgets",
        "🔁 Subscriptions",
        "✏️ Transaction Manager & Receipts",
        "📁 Reports & Portability"
    ])

    # 1. ANALYTICS & TRENDS
    with tab_analytics:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"Expense by Category ({active_currency})")
            exp_df = filtered_df[filtered_df["type"] == "Expense"]
            if not exp_df.empty:
                cat_summary = exp_df.groupby("category")["amount"].sum().reset_index()
                fig_donut = px.pie(
                    cat_summary,
                    names="category",
                    values="amount",
                    hole=0.48,
                    color_discrete_sequence=["#c4b5fd", "#a78bfa", "#8b5cf6", "#7c3aed", "#f472b6", "#fb7185", "#cbd5e1"]
                )
                fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                fig_donut.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info(f"No expense data in {active_currency}.")

        with c2:
            st.subheader(f"Payment Channel Volume ({active_currency})")
            if not filtered_df.empty:
                pm_summary = filtered_df.groupby("payment_method")["amount"].sum().reset_index()
                fig_pm = px.bar(
                    pm_summary,
                    x="payment_method",
                    y="amount",
                    color="payment_method",
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    labels={"payment_method": "Channel", "amount": f"Volume ({active_sym})"}
                )
                fig_pm.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
                st.plotly_chart(fig_pm, use_container_width=True)

        st.subheader(f"Daily Inflow vs Outflow ({active_currency})")
        daily_df = filtered_df.copy()
        daily_df["date_str"] = daily_df["date"].dt.strftime('%b %d')
        daily_agg = daily_df.groupby(["date_str", "type"])["amount"].sum().reset_index()

        fig_bar = px.bar(
            daily_agg,
            x="date_str",
            y="amount",
            color="type",
            barmode="group",
            color_discrete_map={"Income": "#34d399", "Expense": "#f87171"},
            labels={"date_str": "Date", "amount": f"Amount ({active_sym})", "type": "Type"}
        )
        fig_bar.update_xaxes(type='category', showgrid=False)
        fig_bar.update_yaxes(showgrid=True, gridcolor="#ede9fe")
        fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10, b=10, l=10, r=10), legend_title_text="")
        st.plotly_chart(fig_bar, use_container_width=True)

    # 2. CATEGORY BUDGET GAUGES
    with tab_budgets:
        st.subheader(f"Category-Specific Budget Gauges ({active_currency})")
        b_col1, b_col2 = st.columns([1, 2])
        with b_col1:
            st.markdown("#### Set Limit")
            bud_cat = st.selectbox("Select Expense Category", base_cats["Expense"])
            bud_limit = st.number_input(f"Category Limit ({active_sym})", min_value=10.0, value=250.0, step=25.0)
            if st.button("Save Category Budget", use_container_width=True):
                db.set_category_budget(bud_cat, bud_limit)
                st.toast(f"Budget saved for {bud_cat}", icon="🎯")
                st.rerun()

        with b_col2:
            st.markdown("#### Budget Tracking Status")
            cat_budgets_df = db.get_category_budgets()
            exp_totals = currency_scoped_df[currency_scoped_df["type"] == "Expense"].groupby("category")["amount"].sum().to_dict()

            if cat_budgets_df.empty:
                st.info("No category budgets configured.")
            else:
                for _, b_row in cat_budgets_df.iterrows():
                    c_name = b_row["category"]
                    c_limit = b_row["budget_limit"]
                    c_spent = exp_totals.get(c_name, 0.0)
                    pct = (c_spent / c_limit) * 100
                    status_badge = "🟢 Normal" if pct < 75 else ("🟡 Warning" if pct <= 100 else "🔴 Exceeded")
                    st.write(f"**{c_name}** — {active_sym}{c_spent:,.2f} of {active_sym}{c_limit:,.2f} ({pct:.1f}%) | {status_badge}")
                    st.progress(min(pct / 100.0, 1.0))

    # 3. SUBSCRIPTIONS
    with tab_subs:
        st.subheader("Recurring Subscriptions")
        s_col1, s_col2 = st.columns([1, 2])
        with s_col1:
            st.markdown("#### Add Subscription")
            sub_name = st.text_input("Service Name (e.g., Spotify, Netflix)")
            sub_cat = st.selectbox("Category", base_cats["Expense"], key="sub_cat")
            sub_curr = st.selectbox("Currency", ["INR", "USD", "EUR", "GBP"], key="sub_curr")
            sub_sym = CURRENCY_SYMBOLS[sub_curr]
            sub_amt = st.number_input(f"Monthly Cost ({sub_sym})", min_value=1.0, value=15.0, step=5.0)
            sub_day = st.number_input("Billing Day (1-31)", min_value=1, max_value=31, value=1)
            
            if st.button("Add Subscription", use_container_width=True):
                if sub_name.strip():
                    db.add_subscription(sub_name, sub_cat, sub_amt, sub_curr, sub_day)
                    st.toast(f"Subscription added: {sub_name}", icon="🔁")
                    st.rerun()

        with s_col2:
            st.markdown("#### Active Subscriptions")
            subs_df = db.get_subscriptions()
            if subs_df.empty:
                st.info("No recurring expenses added.")
            else:
                st.dataframe(subs_df[["id", "name", "category", "amount", "currency", "billing_day"]], use_container_width=True, hide_index=True)
                del_sub_id = st.selectbox("Select Subscription ID to Cancel", options=subs_df["id"].tolist())
                if st.button("🗑️ Remove Subscription", use_container_width=True):
                    db.delete_subscription(del_sub_id)
                    st.toast("Subscription canceled", icon="🗑️")
                    st.rerun()

    # 4. CRUD & RECEIPTS
    with tab_crud:
        st.subheader("Full Ledger (All Currencies)")
        table_display = df[["id", "date_only", "type", "category", "amount", "currency", "payment_method", "tags", "description", "receipt_path"]].copy()
        table_display.rename(columns={"date_only": "date"}, inplace=True)
        st.dataframe(table_display, use_container_width=True, hide_index=True)

        st.markdown("---")
        manage_col1, manage_col2 = st.columns(2)

        with manage_col1:
            st.markdown("#### ✏️ Edit Transaction")
            edit_id = st.selectbox("Select ID to Edit", options=df["id"].tolist())
            row_to_edit = df[df["id"] == edit_id].iloc[0]

            with st.form(key=f"edit_form_{edit_id}"):
                new_date = st.date_input("Date", value=pd.to_datetime(row_to_edit["date"]).date())
                new_type = st.selectbox("Type", ["Expense", "Income"], index=0 if row_to_edit["type"] == "Expense" else 1)
                new_cat = st.selectbox("Category", base_cats[new_type], index=0)
                
                curr_list = ["INR", "USD", "EUR", "GBP"]
                default_curr_idx = curr_list.index(row_to_edit["currency"]) if row_to_edit["currency"] in curr_list else 0
                new_curr = st.selectbox("Currency", curr_list, index=default_curr_idx)
                
                new_amt = st.number_input(f"Amount", value=float(row_to_edit["amount"]), min_value=0.01, step=1.0, format="%.2f")
                new_mode = st.selectbox("Payment Method", ["UPI / Net Banking", "Cash", "Credit Card", "Debit Card"])
                new_tags = st.text_input("Tags", value=str(row_to_edit["tags"]) if row_to_edit["tags"] else "")
                new_desc = st.text_input("Description", value=str(row_to_edit["description"]) if row_to_edit["description"] else "")
                
                if st.form_submit_button("Update Transaction"):
                    db.update_transaction(edit_id, new_date, new_type, new_cat, new_amt, new_curr, new_desc, new_mode, new_tags)
                    st.toast(f"Record #{edit_id} updated!", icon="✏️")
                    st.rerun()

        with manage_col2:
            st.markdown("#### 🖼️ View Receipt Attachment")
            inspect_id = st.selectbox("Select ID to View Bill", options=df["id"].tolist(), key="inspect_box")
            inspected_row = df[df["id"] == inspect_id].iloc[0]
            r_path = inspected_row.get("receipt_path", "")
            if r_path and os.path.exists(r_path):
                st.image(r_path, caption=f"Receipt for Record #{inspect_id}", use_column_width=True)
            else:
                st.info("No receipt image attached to this transaction.")

            st.write("")
            if st.button("🗑️ Delete Transaction", type="primary", use_container_width=True):
                db.delete_transaction(inspect_id)
                st.toast(f"Record #{inspect_id} removed.", icon="🗑️")
                st.rerun()

    # 5. DATA PORTABILITY & PDF
    with tab_io:
        st.subheader("Reports & Data Portability")
        io_c1, io_c2 = st.columns(2)
        with io_c1:
            st.markdown(f"#### 📄 PDF Statement ({active_currency})")
            pdf_bytes = generate_pdf_report(filtered_df, total_income, total_expense, net_savings, active_currency)
            st.download_button(
                label=f"📄 Download {active_currency} Statement (PDF)",
                data=pdf_bytes,
                file_name=f"FinPulse_Statement_{active_currency}_{date.today()}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with io_c2:
            st.markdown("#### 📥 CSV Ledger")
            csv_export = df[["date", "type", "category", "amount", "currency", "payment_method", "tags", "description"]].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Full Ledger (CSV)",
                data=csv_export,
                file_name=f"finpulse_records_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )