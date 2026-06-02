# ============================================================
# analytics.py  —  SaaS Business Analytics Engine
# ============================================================
# Provides analysis functions for:
#   • Dataset overview & health check
#   • User growth & acquisition
#   • Revenue & MRR/ARR analysis
#   • Customer retention & cohorts
#   • Churn rate calculation
#   • Subscription & plan breakdown
#   • Engagement metrics
#   • Product performance
# ============================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils import (
    detect_col, coerce_datetime, num_cols, cat_cols,
    df_summary, safe_div, fmt_currency, fmt_pct, fmt_number
)


# ── Dataset Overview ──────────────────────────────────────────

def dataset_overview(df: pd.DataFrame) -> dict:
    """
    Return comprehensive dataset health information.
    Used in the "Dataset Overview" tab.
    """
    summary = df_summary(df)

    # Missing values per column
    missing_by_col = (
        df.isnull().sum()
          .reset_index()
          .rename(columns={"index": "column", 0: "missing_count"})
    )
    missing_by_col["missing_pct"] = (
        missing_by_col["missing_count"] / len(df) * 100
    ).round(1)
    missing_by_col = missing_by_col[missing_by_col["missing_count"] > 0]

    # Numeric column statistics
    stats_df = pd.DataFrame()
    nc = num_cols(df)
    if nc:
        stats_df = df[nc].describe().T.reset_index().rename(columns={"index": "column"})
        stats_df = stats_df.round(2)

    # Sample data
    sample = df.head(50)

    return {
        "summary":     summary,
        "missing":     missing_by_col,
        "stats":       stats_df,
        "sample":      sample,
        "dtypes":      df.dtypes.reset_index().rename(
                          columns={"index": "column", 0: "dtype"}),
    }


# ── User Growth ───────────────────────────────────────────────

def analyse_user_growth(df: pd.DataFrame) -> dict:
    """
    Analyse user sign-up growth over time.

    Auto-detects: date column, user count column.
    Returns monthly/weekly aggregates + growth rates.
    """
    result = {"status": "ok", "message": "", "monthly": pd.DataFrame(),
              "weekly": pd.DataFrame(), "total": 0, "growth_rate": 0.0,
              "new_this_month": 0, "kpis": {}}

    date_col = detect_col(df, "date")
    user_col = detect_col(df, "users")

    if not date_col:
        result["status"]  = "warn"
        result["message"] = "No date column detected. Add a column with 'date' in the name."
        return result

    df = coerce_datetime(df, date_col)
    if df.empty:
        result["status"]  = "error"
        result["message"] = "Date column could not be parsed."
        return result

    df["_month"] = df[date_col].dt.to_period("M").astype(str)
    df["_week"]  = df[date_col].dt.to_period("W").astype(str)

    if user_col and user_col in df.columns:
        # Aggregate numeric user counts
        monthly = df.groupby("_month", as_index=False)[user_col].sum()
        weekly  = df.groupby("_week",  as_index=False)[user_col].sum()
        monthly.rename(columns={"_month": "period", user_col: "users"}, inplace=True)
        weekly.rename( columns={"_week":  "period", user_col: "users"}, inplace=True)
    else:
        # Count rows per period (each row = one user sign-up)
        monthly = df.groupby("_month").size().reset_index(name="users")
        monthly.rename(columns={"_month": "period"}, inplace=True)
        weekly  = df.groupby("_week").size().reset_index(name="users")
        weekly.rename( columns={"_week":  "period"}, inplace=True)

    monthly = monthly.sort_values("period")
    weekly  = weekly.sort_values("period")

    # Cumulative growth
    monthly["cumulative"] = monthly["users"].cumsum()

    total = int(monthly["users"].sum())

    # Month-over-month growth rate (last 2 months)
    growth_rate = 0.0
    if len(monthly) >= 2:
        curr = monthly["users"].iloc[-1]
        prev = monthly["users"].iloc[-2]
        growth_rate = safe_div(curr - prev, prev) * 100

    new_this_month = int(monthly["users"].iloc[-1]) if not monthly.empty else 0

    result.update({
        "monthly":        monthly,
        "weekly":         weekly,
        "total":          total,
        "growth_rate":    round(growth_rate, 2),
        "new_this_month": new_this_month,
        "kpis": {
            "Total Users":       fmt_number(total),
            "New This Month":    fmt_number(new_this_month),
            "MoM Growth":        f"{growth_rate:+.1f}%",
            "Active Periods":    str(len(monthly)),
        }
    })
    return result


# ── Revenue Analysis ──────────────────────────────────────────

def analyse_revenue(df: pd.DataFrame) -> dict:
    """
    Analyse revenue trends: MRR, ARR, total, growth.

    Auto-detects: date column, revenue column.
    """
    result = {"status": "ok", "message": "", "monthly": pd.DataFrame(),
              "total": 0.0, "mrr": 0.0, "arr": 0.0, "kpis": {},
              "growth_rate": 0.0}

    date_col    = detect_col(df, "date")
    revenue_col = detect_col(df, "revenue")

    if not revenue_col:
        result["status"]  = "warn"
        result["message"] = ("No revenue column found. "
                             "Add a column with 'revenue', 'mrr', or 'amount' in its name.")
        return result

    df = df.copy()
    df[revenue_col] = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)

    if date_col:
        df = coerce_datetime(df, date_col)
        df["_month"] = df[date_col].dt.to_period("M").astype(str)
        monthly = df.groupby("_month", as_index=False)[revenue_col].sum()
        monthly.rename(columns={"_month": "period", revenue_col: "revenue"}, inplace=True)
        monthly = monthly.sort_values("period")
        monthly["cumulative"] = monthly["revenue"].cumsum()
    else:
        monthly = pd.DataFrame({"period": ["All Time"],
                                  "revenue": [df[revenue_col].sum()]})

    total = float(df[revenue_col].sum())
    mrr   = float(monthly["revenue"].iloc[-1]) if not monthly.empty else 0
    arr   = mrr * 12

    growth_rate = 0.0
    if len(monthly) >= 2:
        curr = monthly["revenue"].iloc[-1]
        prev = monthly["revenue"].iloc[-2]
        growth_rate = safe_div(curr - prev, prev) * 100

    result.update({
        "monthly":     monthly,
        "total":       total,
        "mrr":         mrr,
        "arr":         arr,
        "growth_rate": round(growth_rate, 2),
        "kpis": {
            "Total Revenue":  fmt_currency(total),
            "MRR":            fmt_currency(mrr),
            "ARR":            fmt_currency(arr),
            "Revenue Growth": f"{growth_rate:+.1f}%",
        }
    })
    return result


# ── Churn Analysis ────────────────────────────────────────────

def analyse_churn(df: pd.DataFrame) -> dict:
    """
    Calculate churn rate and churned user counts.

    Accepts either:
      a) A column with churn flag (0/1 or True/False)
      b) A column with churn_rate values
    """
    result = {"status": "ok", "message": "", "monthly": pd.DataFrame(),
              "overall_rate": 0.0, "churned_count": 0, "kpis": {}}

    churn_col = detect_col(df, "churn")
    date_col  = detect_col(df, "date")

    if not churn_col:
        result["status"]  = "warn"
        result["message"] = ("No churn column found. "
                             "Add a column with 'churn' or 'cancel' in its name.")
        return result

    df = df.copy()
    df[churn_col] = pd.to_numeric(df[churn_col], errors="coerce").fillna(0)

    # If values look like rates (all ≤ 1), treat as percentage directly
    is_rate = df[churn_col].max() <= 1.0

    if is_rate:
        overall_rate = float(df[churn_col].mean() * 100)
        churned      = 0
    else:
        churned      = int(df[churn_col].sum())
        total        = len(df)
        overall_rate = safe_div(churned, total) * 100

    # Monthly churn trend
    if date_col:
        df = coerce_datetime(df, date_col)
        df["_month"] = df[date_col].dt.to_period("M").astype(str)
        if is_rate:
            monthly = df.groupby("_month", as_index=False)[churn_col].mean()
            monthly[churn_col] = (monthly[churn_col] * 100).round(2)
        else:
            monthly = df.groupby("_month", as_index=False)[churn_col].sum()
        monthly.rename(columns={"_month": "period", churn_col: "churn"}, inplace=True)
        monthly = monthly.sort_values("period")
    else:
        monthly = pd.DataFrame()

    result.update({
        "monthly":      monthly,
        "overall_rate": round(overall_rate, 2),
        "churned_count":churned,
        "kpis": {
            "Churn Rate":     f"{overall_rate:.2f}%",
            "Churned Users":  fmt_number(churned) if churned else "N/A",
            "Retention Rate": f"{100 - overall_rate:.2f}%",
        }
    })
    return result


# ── Retention Analysis ────────────────────────────────────────

def analyse_retention(df: pd.DataFrame) -> dict:
    """
    Cohort retention table and average retention rate.
    """
    result = {"status": "ok", "message": "", "monthly": pd.DataFrame(),
              "avg_retention": 0.0, "kpis": {}}

    ret_col  = detect_col(df, "retention")
    date_col = detect_col(df, "date")

    if not ret_col:
        result["status"]  = "warn"
        result["message"] = "No retention column found (needs 'retention' or 'retained' in name)."
        return result

    df = df.copy()
    df[ret_col] = pd.to_numeric(df[ret_col], errors="coerce").fillna(0)
    # Normalise to 0-100 range
    if df[ret_col].max() <= 1:
        df[ret_col] = df[ret_col] * 100

    avg = float(df[ret_col].mean())

    if date_col:
        df = coerce_datetime(df, date_col)
        df["_month"] = df[date_col].dt.to_period("M").astype(str)
        monthly = (df.groupby("_month", as_index=False)[ret_col]
                     .mean().rename(
                         columns={"_month": "period", ret_col: "retention"}))
        monthly["retention"] = monthly["retention"].round(2)
        monthly = monthly.sort_values("period")
    else:
        monthly = pd.DataFrame()

    result.update({
        "monthly":       monthly,
        "avg_retention": round(avg, 2),
        "kpis": {
            "Avg Retention": f"{avg:.1f}%",
            "Churn (implied)": f"{100-avg:.1f}%",
        }
    })
    return result


# ── Subscription / Plan Breakdown ────────────────────────────

def analyse_subscriptions(df: pd.DataFrame) -> dict:
    """
    Break down users and revenue by subscription plan/tier.
    """
    result = {"status": "ok", "message": "", "plan_counts": pd.Series(),
              "plan_revenue": pd.Series(), "kpis": {}}

    plan_col    = detect_col(df, "plan")
    revenue_col = detect_col(df, "revenue")

    if not plan_col:
        result["status"]  = "warn"
        result["message"] = ("No plan/tier column found. "
                             "Add a column with 'plan', 'tier', or 'subscription' in its name.")
        return result

    plan_counts = df[plan_col].value_counts()
    top_plan    = plan_counts.idxmax() if not plan_counts.empty else "N/A"

    plan_revenue = pd.Series(dtype=float)
    if revenue_col:
        df_copy = df.copy()
        df_copy[revenue_col] = pd.to_numeric(df_copy[revenue_col], errors="coerce").fillna(0)
        plan_revenue = df_copy.groupby(plan_col)[revenue_col].sum().sort_values(ascending=False)

    result.update({
        "plan_counts":  plan_counts,
        "plan_revenue": plan_revenue,
        "kpis": {
            "Total Plans":   str(len(plan_counts)),
            "Top Plan":      top_plan,
            "Top Plan Users":fmt_number(plan_counts.max() if not plan_counts.empty else 0),
        }
    })
    return result


# ── Engagement Analysis ───────────────────────────────────────

def analyse_engagement(df: pd.DataFrame) -> dict:
    """
    Analyse user engagement metrics (sessions, logins, DAU/MAU).
    """
    result = {"status": "ok", "message": "", "monthly": pd.DataFrame(),
              "avg_engagement": 0.0, "kpis": {}}

    eng_col  = detect_col(df, "engagement")
    date_col = detect_col(df, "date")

    if not eng_col:
        result["status"]  = "warn"
        result["message"] = ("No engagement column found. "
                             "Add a column with 'engagement', 'sessions', or 'logins'.")
        return result

    df = df.copy()
    df[eng_col] = pd.to_numeric(df[eng_col], errors="coerce").fillna(0)
    avg = float(df[eng_col].mean())
    total = float(df[eng_col].sum())

    if date_col:
        df = coerce_datetime(df, date_col)
        df["_month"] = df[date_col].dt.to_period("M").astype(str)
        monthly = (df.groupby("_month", as_index=False)[eng_col]
                     .sum().rename(
                         columns={"_month": "period", eng_col: "engagement"}))
        monthly = monthly.sort_values("period")
    else:
        monthly = pd.DataFrame()

    result.update({
        "monthly":        monthly,
        "avg_engagement": round(avg, 2),
        "kpis": {
            "Total Sessions":   fmt_number(total),
            "Avg per Record":   fmt_number(avg, decimals=1),
        }
    })
    return result


# ── Product Performance ────────────────────────────────────────

def analyse_product_performance(df: pd.DataFrame) -> dict:
    """
    Compare metrics across product / plan categories.
    Builds a pivot-style summary.
    """
    result = {"status": "ok", "message": "", "pivot": pd.DataFrame(), "kpis": {}}

    plan_col    = detect_col(df, "plan")
    revenue_col = detect_col(df, "revenue")
    user_col    = detect_col(df, "users")

    if not plan_col:
        result["status"]  = "warn"
        result["message"] = "No product/plan column detected for performance breakdown."
        return result

    agg = {}
    df_copy = df.copy()

    if revenue_col:
        df_copy[revenue_col] = pd.to_numeric(df_copy[revenue_col], errors="coerce").fillna(0)
        agg["Revenue"] = (revenue_col, "sum")

    if user_col:
        df_copy[user_col] = pd.to_numeric(df_copy[user_col], errors="coerce").fillna(0)
        agg["Users"] = (user_col, "sum")

    if not agg:
        # Just count rows per plan
        pivot = df_copy[plan_col].value_counts().reset_index()
        pivot.columns = ["Plan", "Count"]
    else:
        pivot = df_copy.groupby(plan_col).agg(**agg).reset_index()
        pivot.rename(columns={plan_col: "Plan"}, inplace=True)
        pivot = pivot.sort_values("Revenue" if "Revenue" in pivot.columns else pivot.columns[1],
                                  ascending=False)

    result["pivot"] = pivot
    return result
