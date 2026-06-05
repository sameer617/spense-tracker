"""
Spense Tracker — main application entry point.

Architecture (planned):
    - Frontend: Streamlit  (this module)
    - Backend:  FastAPI    (separate service, see backend/ — TODO)

The Streamlit app talks to the FastAPI backend over HTTP. For now everything
below is a placeholder/scaffold so the structure is clear.
"""

import streamlit as st

from database.db import init_db, seed_db

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# TODO: move to a settings module / environment variables
API_BASE_URL = "http://localhost:8000"  # FastAPI backend (not yet running)


# ---------------------------------------------------------------------------
# Backend client (placeholders)
# ---------------------------------------------------------------------------
# These wrap calls to the FastAPI backend. Replace the stubbed returns with
# real `requests`/`httpx` calls once the backend endpoints exist.

def fetch_expenses():
    """GET {API_BASE_URL}/expenses — return a list of expense records."""
    # TODO: call backend; returning sample data for now
    return [
        {"id": 1, "date": "2026-06-01", "category": "Food", "amount": 12.50, "note": "Lunch"},
        {"id": 2, "date": "2026-06-02", "category": "Transport", "amount": 3.25, "note": "Bus"},
    ]


def add_expense(date, category, amount, note):
    """POST {API_BASE_URL}/expenses — create a new expense record."""
    # TODO: call backend
    st.info("add_expense() is a placeholder — backend not wired up yet.")


def fetch_summary():
    """GET {API_BASE_URL}/summary — return aggregated totals for charts."""
    # TODO: call backend
    return {"total": 15.75, "by_category": {"Food": 12.50, "Transport": 3.25}}


# ---------------------------------------------------------------------------
# UI sections (placeholders)
# ---------------------------------------------------------------------------

def render_sidebar():
    """Navigation / global filters."""
    st.sidebar.title("💸 Spense Tracker")
    return st.sidebar.radio("Navigate", ["Dashboard", "Add Expense", "Expenses"])


def render_dashboard():
    st.header("Dashboard")
    summary = fetch_summary()
    col1, col2 = st.columns(2)
    col1.metric("Total Spent", f"${summary['total']:.2f}")
    col2.metric("Categories", len(summary["by_category"]))
    st.subheader("Spending by category")
    st.bar_chart(summary["by_category"])  # TODO: replace with richer chart


def render_add_expense():
    st.header("Add Expense")
    with st.form("add_expense_form"):
        date = st.date_input("Date")
        category = st.selectbox("Category", ["Food", "Transport", "Bills", "Other"])
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        note = st.text_input("Note")
        submitted = st.form_submit_button("Add")
        if submitted:
            add_expense(date, category, amount, note)


def render_expenses():
    st.header("Expenses")
    expenses = fetch_expenses()
    st.dataframe(expenses, use_container_width=True)  # TODO: pagination/edit/delete


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Spense Tracker", page_icon="💸", layout="wide")

    # Ensure the database exists, has the schema, and is seeded once. Both calls
    # are idempotent/guarded, so they're safe to run on every Streamlit rerun.
    init_db()
    seed_db()

    page = render_sidebar()
    if page == "Dashboard":
        render_dashboard()
    elif page == "Add Expense":
        render_add_expense()
    elif page == "Expenses":
        render_expenses()


if __name__ == "__main__":
    main()
