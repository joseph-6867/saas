# ============================================================
# dashboard.py  —  Post-Login Analytics Dashboard
# ============================================================
# Tabs:
#   1. 📤 Upload & Overview
#   2. 📈 User Growth
#   3. 💰 Revenue
#   4. 📉 Churn & Retention
#   5. 🛒 Subscriptions
#   6. 🎯 Engagement
#   7. 🤖 ML Predictions
#   8. 📋 Reports & History
#   9. ⚙️  Settings
# ============================================================

import json
import streamlit as st
import pandas as pd
from datetime import datetime

from database import (
    db_get_datasets, db_save_dataset_meta, db_delete_dataset,
    db_save_report, db_get_reports,
    db_save_prediction, db_get_predictions,
    db_get_notifications, db_mark_all_read, db_add_notification,
    db_get_login_history, db_get_profile
)
from analytics import (
    dataset_overview, analyse_user_growth, analyse_revenue,
    analyse_churn, analyse_retention,
    analyse_subscriptions, analyse_engagement,
    analyse_product_performance
)
from prediction import (
    predict_churn, forecast_revenue,
    predict_clv, analyse_trends, segment_users
)
from charts import (
    bar_chart, line_chart, area_chart, pie_chart,
    scatter_plot, heatmap, grouped_bar, multi_line,
    forecast_chart, segment_bar, gauge_chart, funnel_chart
)
from email_service import (
    email_analytics_report, email_prediction_report, email_login_alert
)
from utils import (
    load_uploaded_file, df_summary, num_cols, cat_cols,
    to_csv_bytes, to_excel_bytes, fmt_currency, fmt_number,
    fmt_pct, delta_pct, build_report_text, now_label, PALETTE
)
from auth import auth_sign_out


# ── Entry Point ───────────────────────────────────────────────

def render_dashboard():
    """Main dashboard — called from app.py when user is logged in."""
    uid      = st.session_state.user_id
    name     = st.session_state.full_name or "User"
    email    = st.session_state.email
    provider = st.session_state.provider or "email"

    _render_sidebar(uid, name, email)

    # ── Tab structure ──
    tabs = st.tabs([
        "📤 Upload & Overview",
        "📈 User Growth",
        "💰 Revenue",
        "📉 Churn & Retention",
        "🛒 Subscriptions",
        "🎯 Engagement",
        "🤖 ML Predictions",
        "📋 Reports & History",
        "⚙️ Settings",
    ])

    with tabs[0]: _tab_upload(uid, email, name)
    with tabs[1]: _tab_user_growth(uid, email, name)
    with tabs[2]: _tab_revenue(uid, email, name)
    with tabs[3]: _tab_churn_retention(uid, email, name)
    with tabs[4]: _tab_subscriptions(uid)
    with tabs[5]: _tab_engagement(uid)
    with tabs[6]: _tab_predictions(uid, email, name)
    with tabs[7]: _tab_reports(uid)
    with tabs[8]: _tab_settings(uid, email, name)


# ── Sidebar ───────────────────────────────────────────────────

def _render_sidebar(uid, name, email):
    with st.sidebar:
        st.markdown(f"## 📊 SaaS Analytics")
        st.markdown(f"**{name}**  \n`{email}`")
        st.divider()

        # Notifications
        notifs = db_get_notifications(uid, unread_only=True, limit=5)
        if notifs:
            st.warning(f"🔔 {len(notifs)} unread notification(s)")
            with st.expander("View Notifications"):
                for n in notifs:
                    icon = {"success":"✅","warning":"⚠️","error":"❌"}.get(n["type"],"ℹ️")
                    st.markdown(f"{icon} **{n['title']}**  \n{n['message']}")
                if st.button("Mark all read"):
                    db_mark_all_read(uid)
                    st.rerun()
        else:
            st.success("✅ No new notifications")

        st.divider()

        # Dataset loaded?
        df = st.session_state.get("active_df")
        if df is not None:
            st.success(f"📂 **{st.session_state.active_df_name}**  \n"
                       f"{len(df):,} rows × {len(df.columns)} cols")
        else:
            st.info("📤 Upload a dataset to begin analysis")

        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            auth_sign_out()
            st.rerun()


# ── Helper: get active DataFrame ─────────────────────────────

def _get_df() -> pd.DataFrame | None:
    return st.session_state.get("active_df")


def _require_df() -> pd.DataFrame | None:
    """Show warning and return None if no dataset is loaded."""
    df = _get_df()
    if df is None:
        st.info("📤 Please upload a dataset in the **Upload & Overview** tab first.")
    return df


# ── TAB 1: Upload & Overview ──────────────────────────────────

def _tab_upload(uid, email, name):
    st.header("📤 Upload Dataset & Overview")

    col_up, col_hist = st.columns([2, 1])

    with col_up:
        st.subheader("Upload CSV or Excel File")
        uploaded = st.file_uploader(
            "Drag & drop or browse",
            type=["csv", "xlsx", "xls"],
            help="Supported: CSV, Excel (.xlsx, .xls)"
        )

        if uploaded:
            df, err = load_uploaded_file(uploaded)
            if err:
                st.error(f"❌ {err}")
            else:
                st.session_state.active_df      = df
                st.session_state.active_df_name = uploaded.name

                # Save metadata to Supabase
                db_save_dataset_meta(
                    uid, uploaded.name, len(df), len(df.columns),
                    json.dumps(list(df.columns))
                )
                db_add_notification(uid, "Dataset Uploaded",
                                    f"{uploaded.name} loaded ({len(df):,} rows)",
                                    "success")
                st.success(f"✅ Loaded **{uploaded.name}** — {len(df):,} rows × {len(df.columns)} columns")

    with col_hist:
        st.subheader("Previous Uploads")
        datasets = db_get_datasets(uid)
        if datasets:
            for ds in datasets[:6]:
                with st.expander(f"📄 {ds['name'][:30]}"):
                    st.caption(f"Rows: {ds['rows']}  Cols: {ds['cols']}")
                    st.caption(ds['created_at'][:16])
                    if st.button("🗑️ Delete", key=f"del_{ds['id']}"):
                        db_delete_dataset(ds['id'], uid)
                        st.rerun()
        else:
            st.caption("No uploads yet.")

    st.divider()
    df = _get_df()
    if df is None:
        return

    # ── Dataset Overview ──────────────────────────────────────
    st.subheader("📊 Dataset Summary")
    ov  = dataset_overview(df)
    smry = ov["summary"]

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Rows",        f"{smry['rows']:,}")
    c2.metric("Columns",     smry['columns'])
    c3.metric("Numeric",     smry['numeric'])
    c4.metric("Missing",     f"{smry['missing']:,}")
    c5.metric("Duplicates",  smry['duplicates'])

    # Tabs within overview
    ov_tabs = st.tabs(["📋 Sample Data","📐 Column Info","📊 Statistics","🔍 Missing Values"])

    with ov_tabs[0]:
        # Filters
        fc1, fc2, fc3 = st.columns([2,1,1])
        with fc1:
            search = st.text_input("🔍 Search columns", key="ov_search")
        with fc2:
            rows_show = st.slider("Rows to show", 5, 100, 20, key="ov_rows")

        display_df = df
        if search:
            cols_match = [c for c in df.columns if search.lower() in c.lower()]
            display_df = df[cols_match] if cols_match else df
        st.dataframe(display_df.head(rows_show), use_container_width=True)

        # Download
        col_dl1, col_dl2, _ = st.columns([1,1,3])
        col_dl1.download_button("⬇️ CSV", to_csv_bytes(df),
                                 file_name=f"{st.session_state.active_df_name}_export.csv",
                                 mime="text/csv")
        col_dl2.download_button("⬇️ Excel", to_excel_bytes(df),
                                  file_name=f"{st.session_state.active_df_name}_export.xlsx",
                                  mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with ov_tabs[1]:
        dtypes = ov["dtypes"]
        dtypes["dtype"] = dtypes["dtype"].astype(str)
        st.dataframe(dtypes, use_container_width=True)

    with ov_tabs[2]:
        if not ov["stats"].empty:
            st.dataframe(ov["stats"], use_container_width=True)
        else:
            st.info("No numeric columns found.")

    with ov_tabs[3]:
        if not ov["missing"].empty:
            st.dataframe(ov["missing"], use_container_width=True)
            # Bar chart of missing %
            st.plotly_chart(
                bar_chart(ov["missing"], "column", "missing_pct",
                          "Missing Value % by Column"),
                use_container_width=True
            )
        else:
            st.success("✅ No missing values in dataset!")

    # Correlation heatmap
    nc = num_cols(df)
    if len(nc) >= 2:
        st.subheader("🔥 Correlation Heatmap")
        corr = df[nc].corr()
        st.plotly_chart(heatmap(corr, "Numeric Feature Correlations"),
                        use_container_width=True)


# ── TAB 2: User Growth ────────────────────────────────────────

def _tab_user_growth(uid, email, name):
    st.header("📈 User Growth Analysis")
    df = _require_df()
    if df is None: return

    res = analyse_user_growth(df)

    if res["status"] != "ok":
        st.warning(f"⚠️ {res['message']}")
        if res["status"] == "error": return

    # KPI row
    kpis = res.get("kpis", {})
    cols = st.columns(len(kpis)) if kpis else []
    for i,(k,v) in enumerate(kpis.items()):
        cols[i].metric(k, v)

    st.divider()

    if not res["monthly"].empty:
        t1, t2, t3 = st.tabs(["Monthly Growth","Weekly Growth","Cumulative"])

        with t1:
            st.plotly_chart(
                bar_chart(res["monthly"], "period", "users",
                          "New Users per Month", PALETTE[0]),
                use_container_width=True
            )

        with t2:
            if not res["weekly"].empty:
                st.plotly_chart(
                    line_chart(res["weekly"], "period", "users",
                               "Weekly User Growth", PALETTE[2]),
                    use_container_width=True
                )

        with t3:
            if "cumulative" in res["monthly"].columns:
                st.plotly_chart(
                    area_chart(res["monthly"], "period", "cumulative",
                               "Cumulative Users", PALETTE[1]),
                    use_container_width=True
                )

    # Save report + email option
    _report_controls(uid, email, name, df, "User Growth", kpis)


# ── TAB 3: Revenue ────────────────────────────────────────────

def _tab_revenue(uid, email, name):
    st.header("💰 Revenue Analysis")
    df = _require_df()
    if df is None: return

    res = analyse_revenue(df)

    if res["status"] != "ok":
        st.warning(f"⚠️ {res['message']}")
        if res["status"] == "error": return

    kpis = res.get("kpis", {})
    cols = st.columns(len(kpis)) if kpis else []
    for i,(k,v) in enumerate(kpis.items()):
        cols[i].metric(k, v)

    st.divider()

    if not res["monthly"].empty:
        t1,t2,t3 = st.tabs(["Monthly Revenue","Area Chart","Raw Data"])

        with t1:
            st.plotly_chart(
                bar_chart(res["monthly"], "period", "revenue",
                          "Monthly Revenue", PALETTE[3]),
                use_container_width=True
            )
        with t2:
            st.plotly_chart(
                area_chart(res["monthly"], "period",
                           "cumulative" if "cumulative" in res["monthly"].columns else "revenue",
                           "Cumulative Revenue", PALETTE[2]),
                use_container_width=True
            )
        with t3:
            st.dataframe(res["monthly"], use_container_width=True)
            st.download_button("⬇️ Download Revenue Data",
                                to_csv_bytes(res["monthly"]),
                                "revenue_analysis.csv", "text/csv")

    _report_controls(uid, email, name, df, "Revenue Analysis", kpis)


# ── TAB 4: Churn & Retention ──────────────────────────────────

def _tab_churn_retention(uid, email, name):
    st.header("📉 Churn & Retention")
    df = _require_df()
    if df is None: return

    c_res = analyse_churn(df)
    r_res = analyse_retention(df)

    # Churn KPIs
    st.subheader("Churn Metrics")
    if c_res["status"] == "ok":
        kpis = c_res.get("kpis", {})
        cols = st.columns(len(kpis)) if kpis else []
        for i,(k,v) in enumerate(kpis.items()):
            delta_col = "inverse" if "Churn" in k else "normal"
            cols[i].metric(k, v)

        if not c_res["monthly"].empty:
            st.plotly_chart(
                line_chart(c_res["monthly"], "period", "churn",
                           "Monthly Churn Trend", PALETTE[4]),
                use_container_width=True
            )
    else:
        st.warning(c_res["message"])

    st.divider()

    # Retention KPIs
    st.subheader("Retention Metrics")
    if r_res["status"] == "ok":
        kpis_r = r_res.get("kpis", {})
        cols2 = st.columns(len(kpis_r)) if kpis_r else []
        for i,(k,v) in enumerate(kpis_r.items()):
            cols2[i].metric(k, v)

        if not r_res["monthly"].empty:
            st.plotly_chart(
                area_chart(r_res["monthly"], "period", "retention",
                           "Monthly Retention Rate %", PALETTE[2]),
                use_container_width=True
            )
    else:
        st.warning(r_res["message"])

    _report_controls(uid, email, name, df, "Churn & Retention",
                     {**c_res.get("kpis",{}), **r_res.get("kpis",{})})


# ── TAB 5: Subscriptions ──────────────────────────────────────

def _tab_subscriptions(uid):
    st.header("🛒 Subscription & Plan Breakdown")
    df = _require_df()
    if df is None: return

    sub_res = analyse_subscriptions(df)
    prod_res = analyse_product_performance(df)

    if sub_res["status"] != "ok":
        st.warning(sub_res["message"])
    else:
        kpis = sub_res.get("kpis", {})
        cols = st.columns(len(kpis)) if kpis else []
        for i,(k,v) in enumerate(kpis.items()):
            cols[i].metric(k, v)

        st.divider()
        c1, c2 = st.columns(2)

        with c1:
            if not sub_res["plan_counts"].empty:
                st.plotly_chart(
                    pie_chart(
                        list(sub_res["plan_counts"].index),
                        list(sub_res["plan_counts"].values),
                        "Users by Plan"
                    ),
                    use_container_width=True
                )

        with c2:
            if not sub_res["plan_revenue"].empty:
                rev_df = sub_res["plan_revenue"].reset_index()
                rev_df.columns = ["plan","revenue"]
                st.plotly_chart(
                    bar_chart(rev_df, "plan", "revenue",
                              "Revenue by Plan", PALETTE[1]),
                    use_container_width=True
                )

    if not prod_res["pivot"].empty:
        st.subheader("📦 Product Performance Table")
        st.dataframe(prod_res["pivot"], use_container_width=True)
        st.download_button("⬇️ Download", to_csv_bytes(prod_res["pivot"]),
                            "product_performance.csv", "text/csv")


# ── TAB 6: Engagement ────────────────────────────────────────

def _tab_engagement(uid):
    st.header("🎯 Engagement Metrics")
    df = _require_df()
    if df is None: return

    res = analyse_engagement(df)

    if res["status"] != "ok":
        st.warning(res["message"])
        return

    kpis = res.get("kpis", {})
    cols = st.columns(len(kpis)) if kpis else []
    for i,(k,v) in enumerate(kpis.items()):
        cols[i].metric(k, v)

    st.divider()

    if not res["monthly"].empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(
                line_chart(res["monthly"], "period", "engagement",
                           "Monthly Engagement Trend", PALETTE[5]),
                use_container_width=True
            )
        with c2:
            st.plotly_chart(
                area_chart(res["monthly"], "period", "engagement",
                           "Engagement Area Chart", PALETTE[6]),
                use_container_width=True
            )

    # Numeric scatter explorer
    nc = num_cols(df)
    if len(nc) >= 2:
        st.subheader("🔬 Scatter Plot Explorer")
        sc1, sc2, sc3 = st.columns(3)
        x_col = sc1.selectbox("X Axis", nc, index=0, key="eng_x")
        y_col = sc2.selectbox("Y Axis", nc, index=min(1,len(nc)-1), key="eng_y")
        cc    = cat_cols(df)
        color_opt = [None] + cc
        c_col = sc3.selectbox("Color by (optional)", color_opt, key="eng_c")
        st.plotly_chart(
            scatter_plot(df, x_col, y_col, c_col, title=f"{x_col} vs {y_col}"),
            use_container_width=True
        )


# ── TAB 7: ML Predictions ─────────────────────────────────────

def _tab_predictions(uid, email, name):
    st.header("🤖 Machine Learning Predictions")
    df = _require_df()
    if df is None: return

    pred_type = st.selectbox(
        "Select Prediction Type",
        ["Churn Prediction", "Revenue Forecast",
         "Customer Lifetime Value", "Trend Analysis", "User Segmentation"],
        key="pred_select"
    )

    st.divider()

    if pred_type == "Churn Prediction":
        _pred_churn(df, uid, email, name)
    elif pred_type == "Revenue Forecast":
        _pred_revenue(df, uid, email, name)
    elif pred_type == "Customer Lifetime Value":
        _pred_clv(df, uid, email, name)
    elif pred_type == "Trend Analysis":
        _pred_trends(df, uid, email, name)
    elif pred_type == "User Segmentation":
        _pred_segments(df, uid, email, name)


def _pred_churn(df, uid, email, name):
    st.subheader("📉 Churn Prediction — Random Forest")
    st.info(
        "**How it works:** Trains a Random Forest classifier on your data "
        "to predict which customers are likely to churn. "
        "Requires a column with 'churn' in the name as the target (0/1)."
    )

    if st.button("▶️ Run Churn Prediction", type="primary"):
        with st.spinner("Training model…"):
            res = predict_churn(df)

        if res["status"] == "error":
            st.error(res["message"]); return
        if res["status"] == "warn":
            st.warning(res["message"]); return

        acc = res["accuracy"]
        _show_accuracy(acc)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Feature Importance")
            if not res["feature_importance"].empty:
                st.plotly_chart(
                    bar_chart(res["feature_importance"], "feature", "importance",
                              "Top Features", horizontal=True),
                    use_container_width=True
                )
        with c2:
            if not res["predictions"].empty:
                st.subheader("Risk Distribution")
                risk_counts = res["predictions"]["risk_level"].value_counts()
                st.plotly_chart(
                    pie_chart(list(risk_counts.index), list(risk_counts.values),
                              "Churn Risk Levels"),
                    use_container_width=True
                )

        with st.expander("📋 Classification Report"):
            st.code(res["report"])

        if not res["predictions"].empty:
            st.subheader("Predictions (sample)")
            st.dataframe(res["predictions"].head(50), use_container_width=True)
            st.download_button("⬇️ Download All Predictions",
                                to_csv_bytes(res["predictions"]),
                                "churn_predictions.csv", "text/csv")

        # Save & email
        summary = build_report_text(df, "Churn Prediction",
                                     [f"Accuracy: {acc}%",
                                      f"High Risk: {(res['predictions']['risk_level']=='High').sum()}"])
        db_save_prediction(uid, "Churn Prediction", res["model_name"], acc, summary)
        db_add_notification(uid, "Churn Prediction Complete",
                             f"Model accuracy: {acc}%", "success")

        if st.button("📧 Email Results"):
            ok, msg = email_prediction_report(
                email, name, "Churn Prediction", res["model_name"], acc,
                [f"Model Accuracy: {acc}%",
                 f"High Risk Users: {(res['predictions']['risk_level']=='High').sum()}",
                 f"Features Used: {len(res['feature_importance'])}"]
            )
            st.success(msg) if ok else st.error(msg)


def _pred_revenue(df, uid, email, name):
    st.subheader("💰 Revenue Forecast — Polynomial Regression")
    st.info(
        "**How it works:** Uses Polynomial Regression (degree 2) on "
        "your monthly revenue history to forecast the next N months. "
        "Requires columns with 'date' and 'revenue'/'mrr' in their names."
    )

    periods = st.slider("Forecast periods (months)", 1, 12, 6, key="rev_periods")

    if st.button("▶️ Run Revenue Forecast", type="primary"):
        with st.spinner("Forecasting…"):
            res = forecast_revenue(df, periods)

        if res["status"] == "error":
            st.error(res["message"]); return
        if res["status"] == "warn":
            st.warning(res["message"]); return

        c1, c2, c3 = st.columns(3)
        c1.metric("Trend", res["trend"])
        c2.metric("Model R²", f"{res['model_score']}%")
        c3.metric("Forecast Periods", f"{periods} months")

        hist = res["historical"]
        fore = res["forecast"]

        st.plotly_chart(
            forecast_chart(
                list(hist["period"]), list(hist["revenue"]),
                list(fore["period"]), list(fore["revenue"]),
                "Revenue ($)", "Revenue Forecast"
            ),
            use_container_width=True
        )

        col_h, col_f = st.columns(2)
        with col_h:
            st.subheader("Historical Data")
            st.dataframe(hist[["period","revenue"]], use_container_width=True)
        with col_f:
            st.subheader("Forecast")
            st.dataframe(fore[["period","revenue"]], use_container_width=True)
            st.download_button("⬇️ Download Forecast",
                                to_csv_bytes(fore[["period","revenue"]]),
                                "revenue_forecast.csv", "text/csv")

        summary = build_report_text(df, "Revenue Forecast",
                                     [f"Trend: {res['trend']}",
                                      f"R² Score: {res['model_score']}%",
                                      f"Periods: {periods}"])
        db_save_prediction(uid, "Revenue Forecast", res["model_name"],
                            res["model_score"], summary)
        db_add_notification(uid, "Revenue Forecast Ready",
                             res["trend"], "info")


def _pred_clv(df, uid, email, name):
    st.subheader("💎 Customer Lifetime Value — Linear Regression")
    st.info(
        "**How it works:** Trains a Linear Regression model to predict "
        "the lifetime value of each customer. "
        "Requires a column with 'ltv', 'clv', or 'revenue' in its name as target."
    )

    if st.button("▶️ Run CLV Prediction", type="primary"):
        with st.spinner("Predicting CLV…"):
            res = predict_clv(df)

        if res["status"] in ("error","warn"):
            (st.error if res["status"]=="error" else st.warning)(res["message"]); return

        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Predicted CLV", fmt_currency(res["avg_predicted_clv"]))
        c2.metric("MAE", fmt_currency(res["mae"]))
        c3.metric("R² Score", f"{res['r2']}%")

        if not res["predictions"].empty:
            # CLV segment distribution
            if "clv_segment" in res["predictions"].columns:
                seg_counts = res["predictions"]["clv_segment"].value_counts()
                st.plotly_chart(
                    pie_chart(list(seg_counts.index), list(seg_counts.values),
                              "CLV Segments"),
                    use_container_width=True
                )

            st.subheader("CLV Predictions (sample)")
            disp_cols = [c for c in ["actual_clv","predicted_clv","clv_segment"]
                          if c in res["predictions"].columns]
            st.dataframe(res["predictions"][disp_cols].head(50),
                          use_container_width=True)
            st.download_button("⬇️ Download Predictions",
                                to_csv_bytes(res["predictions"]),
                                "clv_predictions.csv", "text/csv")

        summary = build_report_text(df, "CLV Prediction",
                                     [f"Avg CLV: {fmt_currency(res['avg_predicted_clv'])}",
                                      f"MAE: {fmt_currency(res['mae'])}",
                                      f"R²: {res['r2']}%"])
        db_save_prediction(uid, "Customer Lifetime Value",
                            res["model_name"], res["r2"], summary)


def _pred_trends(df, uid, email, name):
    st.subheader("📊 Trend Analysis — Linear Regression per Column")
    st.info(
        "**How it works:** Fits a linear model to each numeric column "
        "over time to detect whether values are increasing, decreasing, or stable."
    )

    if st.button("▶️ Analyse Trends", type="primary"):
        with st.spinner("Analysing trends…"):
            res = analyse_trends(df)

        if res["status"] != "ok":
            st.warning(res["message"]); return

        if not res["trends"].empty:
            st.dataframe(res["trends"], use_container_width=True)

        if res["summary"]:
            st.subheader("💡 Insights")
            for line in res["summary"]:
                icon = "📈" if "Increasing" in line else "📉" if "Decreasing" in line else "➡️"
                st.markdown(f"- {line}")

        summary = "\n".join(res["summary"][:10])
        db_save_prediction(uid, "Trend Analysis", "Linear Regression", 0, summary)


def _pred_segments(df, uid, email, name):
    st.subheader("👥 User Segmentation — K-Means Clustering")
    st.info(
        "**How it works:** Groups customers into segments using K-Means clustering. "
        "Each cluster is labelled by value level: Champions, Loyal, At Risk, Dormant."
    )

    k = st.slider("Number of segments", 2, 8, 4, key="kmeans_k")

    if st.button("▶️ Segment Users", type="primary"):
        with st.spinner("Clustering…"):
            res = segment_users(df, k)

        if res["status"] != "ok":
            st.warning(res["message"]); return

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(
                segment_bar(res["segment_counts"], "Segment Sizes"),
                use_container_width=True
            )
        with c2:
            st.plotly_chart(
                pie_chart(list(res["segment_counts"].index),
                          list(res["segment_counts"].values),
                          "Segment Distribution"),
                use_container_width=True
            )

        st.subheader("Segment Summary (mean values)")
        st.dataframe(res["cluster_summary"], use_container_width=True)

        if not res["segmented_df"].empty:
            st.subheader("Segmented Data (sample)")
            disp_cols = [c for c in res["segmented_df"].columns
                          if c in ["segment","cluster"] or c in num_cols(df)][:8]
            st.dataframe(res["segmented_df"][disp_cols].head(50),
                          use_container_width=True)
            st.download_button("⬇️ Download Segmented Data",
                                to_csv_bytes(res["segmented_df"]),
                                "user_segments.csv", "text/csv")

        summary = build_report_text(df, "User Segmentation",
                                     [f"k={k}",
                                      f"Segments: {', '.join(res['segment_counts'].index.astype(str)[:4])}"])
        db_save_prediction(uid, "User Segmentation", res["model_name"], 0, summary)
        db_add_notification(uid, "Segmentation Complete",
                             f"{k} segments created", "success")

        if st.button("📧 Email Segmentation Report"):
            ok, msg = email_prediction_report(
                email, name, "User Segmentation", res["model_name"], 0,
                [f"Segments: {k}",
                 f"Largest: {res['segment_counts'].idxmax()} ({res['segment_counts'].max():,} users)"]
            )
            st.success(msg) if ok else st.error(msg)


def _show_accuracy(acc: float):
    if acc >= 80:
        st.success(f"✅ Model Accuracy: **{acc}%** — Excellent!")
    elif acc >= 65:
        st.warning(f"⚠️ Model Accuracy: **{acc}%** — Moderate (add more data for better results)")
    else:
        st.error(f"❌ Model Accuracy: **{acc}%** — Low (check data quality)")


# ── TAB 8: Reports & History ──────────────────────────────────

def _tab_reports(uid):
    st.header("📋 Reports & History")

    r_tabs = st.tabs(["📄 Reports", "🤖 Predictions", "🔐 Login History", "🔔 Notifications"])

    with r_tabs[0]:
        reports = db_get_reports(uid)
        if reports:
            for r in reports:
                with st.expander(f"📄 {r['title']} — {r['created_at'][:10]}"):
                    st.markdown(f"**Type:** {r['report_type']}")
                    st.code(r['summary'])
        else:
            st.info("No reports yet. Run analytics and click 'Save Report'.")

    with r_tabs[1]:
        preds = db_get_predictions(uid)
        if preds:
            for p in preds:
                icon = "🤖"
                with st.expander(f"{icon} {p['prediction_type']} — {p['created_at'][:10]}"):
                    st.markdown(f"**Model:** {p['model_name']}")
                    if p['accuracy'] > 0:
                        st.metric("Accuracy / Score", f"{p['accuracy']*100:.1f}%")
                    st.code(p['summary'])
        else:
            st.info("No prediction history yet.")

    with r_tabs[2]:
        history = db_get_login_history(uid)
        if history:
            for h in history:
                ts = h.get("created_at","")[:16]
                st.markdown(f"🟢 **{ts}** — `{h.get('provider','').title()}` — {h.get('user_agent','')[:80]}")
        else:
            st.info("No login history found.")

    with r_tabs[3]:
        notifs = db_get_notifications(uid, limit=20)
        if notifs:
            for n in notifs:
                icon = {"success":"✅","warning":"⚠️","error":"❌","info":"ℹ️"}.get(n["type"],"ℹ️")
                read = "" if n["read"] else " 🆕"
                with st.expander(f"{icon} {n['title']}{read} — {n['created_at'][:10]}"):
                    st.write(n["message"])
            if st.button("✅ Mark All Read"):
                db_mark_all_read(uid)
                st.rerun()
        else:
            st.info("No notifications.")


# ── TAB 9: Settings ───────────────────────────────────────────

def _tab_settings(uid, email, name):
    st.header("⚙️ Settings & Account")

    s_tabs = st.tabs(["👤 Profile", "📧 Email", "🔧 SMTP Config"])

    with s_tabs[0]:
        profile = db_get_profile(uid)
        st.subheader("Account Information")
        st.markdown(f"**Name:** {name}")
        st.markdown(f"**Email:** {email}")
        st.markdown(f"**Provider:** {st.session_state.provider or 'email'}")
        st.markdown(f"**User ID:** `{uid}`")
        if profile:
            st.markdown(f"**Member since:** {profile.get('created_at','')[:10]}")

    with s_tabs[1]:
        st.subheader("Send Test Emails")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📧 Send Login Alert Email"):
                ok, msg = email_login_alert(email, name,
                                             st.session_state.provider or "email")
                st.success(msg) if ok else st.error(msg)

        with col2:
            df = _get_df()
            if df is not None:
                kpis = df_summary(df)
                kpis_fmt = {k: str(v) for k, v in kpis.items()}
                if st.button("📊 Send Analytics Report Email"):
                    ok, msg = email_analytics_report(
                        email, name, kpis_fmt,
                        st.session_state.active_df_name or "dataset",
                        now_label()
                    )
                    st.success(msg) if ok else st.error(msg)
            else:
                st.info("Upload a dataset to enable analytics email.")

    with s_tabs[2]:
        st.subheader("SMTP Email Configuration")
        with st.expander("📬 How to set up Gmail SMTP"):
            st.markdown("""
            1. Go to [myaccount.google.com](https://myaccount.google.com)
            2. **Security → 2-Step Verification** → Enable
            3. **Security → App Passwords** → Generate for "Mail"
            4. Copy the 16-character password
            5. Add to your `.env` file:
            ```
            SMTP_SERVER=smtp.gmail.com
            SMTP_PORT=587
            SMTP_EMAIL=your@gmail.com
            SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
            ```
            > ⚠️ Never commit your `.env` file to GitHub!
            """)


# ── Shared Report Controls ────────────────────────────────────

def _report_controls(uid, email, name, df, analysis_type, kpis):
    """Reusable Save Report + Email button row shown at bottom of each tab."""
    st.divider()
    c1, c2, _ = st.columns([1, 1, 2])

    with c1:
        if st.button(f"💾 Save Report", key=f"save_{analysis_type}"):
            summary = build_report_text(df, analysis_type,
                                         [f"{k}: {v}" for k, v in kpis.items()])
            db_save_report(uid, f"{analysis_type} Report", analysis_type, summary)
            db_add_notification(uid, f"{analysis_type} Report Saved",
                                 "Report saved to history.", "success")
            st.success("✅ Report saved!")

    with c2:
        if st.button(f"📧 Email Report", key=f"email_{analysis_type}"):
            ok, msg = email_analytics_report(
                email, name,
                {k: str(v) for k, v in kpis.items()},
                st.session_state.active_df_name or "dataset",
                now_label()
            )
            st.success(msg) if ok else st.error(msg)
