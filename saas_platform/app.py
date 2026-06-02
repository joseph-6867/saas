# ============================================================
# app.py  —  Main Streamlit Entry Point
# ============================================================
# Run with:  streamlit run app.py
#
# Routing logic:
#   Not logged in → Home page (features + login/signup)
#   OAuth redirect → handle ?code= → set session → dashboard
#   Logged in      → Dashboard
# ============================================================

import streamlit as st

# ── Page config — MUST be the very first Streamlit call ──────
st.set_page_config(
    page_title="SaaS Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "# SaaS Analytics Platform\nBuilt with Streamlit, Supabase & ML"
    }
)

from auth       import init_session, is_authenticated, process_oauth_redirect
from auth       import auth_sign_in, auth_sign_up, build_google_auth_url
from dashboard  import render_dashboard

# ── Initialise session state keys ────────────────────────────
init_session()

# ── Handle Google OAuth redirect (?code=...) ─────────────────
# Must run before any page render
process_oauth_redirect()


# =============================================================
#  HOME PAGE
# =============================================================

def render_home():
    """
    Landing page shown to unauthenticated visitors.
    Left column: features overview.
    Right column: login / register forms.
    """

    # ── Hero ─────────────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center;padding:48px 20px 24px">
          <h1 style="font-size:2.8rem;margin-bottom:0.2em">
            📊 SaaS Analytics Platform
          </h1>
          <p style="font-size:1.15rem;color:#94A3B8;max-width:640px;margin:0 auto">
            Upload your SaaS data, explore interactive analytics, and get
            AI-powered predictions — all in one place.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Two-column layout: Features | Auth ───────────────────
    feat_col, auth_col = st.columns([3, 2], gap="large")

    # ── LEFT: Feature cards ───────────────────────────────────
    with feat_col:
        st.subheader("✨ What you can do")

        f1, f2 = st.columns(2)
        with f1:
            st.info(
                "**📤 Upload Datasets**\n\n"
                "CSV or Excel files. Auto-detects SaaS metrics columns, "
                "shows summary stats, missing values, and correlations."
            )
            st.info(
                "**💰 Revenue Analytics**\n\n"
                "MRR, ARR, monthly trends, cumulative growth, "
                "and month-over-month comparison charts."
            )
            st.info(
                "**🛒 Subscription Breakdown**\n\n"
                "Plan distribution, per-tier revenue, "
                "product performance pivot tables."
            )
        with f2:
            st.info(
                "**📈 User Growth**\n\n"
                "Monthly & weekly new users, cumulative growth curves, "
                "MoM growth rate KPI cards."
            )
            st.info(
                "**📉 Churn & Retention**\n\n"
                "Churn rate trends, retention curves, "
                "cohort-style monthly breakdown."
            )
            st.info(
                "**🎯 Engagement Metrics**\n\n"
                "Sessions, logins, DAU/MAU trends, "
                "interactive scatter plot explorer."
            )

        st.subheader("🤖 ML Predictions")
        m1, m2, m3 = st.columns(3)
        m1.success("**Churn Prediction**\nRandom Forest classifier with feature importance")
        m2.success("**Revenue Forecast**\nPolynomial Regression — 1–12 month outlook")
        m3.success("**User Segmentation**\nK-Means clustering: Champions → Dormant")

        m4, m5, _ = st.columns(3)
        m4.success("**CLV Prediction**\nLinear Regression per-customer lifetime value")
        m5.success("**Trend Analysis**\nPer-column slope & direction detection")

        st.divider()
        st.subheader("🛠️ Built With")
        t1,t2,t3,t4,t5 = st.columns(5)
        t1.info("**Streamlit**\nUI")
        t2.info("**Supabase**\nAuth + DB")
        t3.info("**Plotly**\nCharts")
        t4.info("**scikit-learn**\nML")
        t5.info("**Google OAuth**\nSSO")

    # ── RIGHT: Auth forms ─────────────────────────────────────
    with auth_col:

        # ── Google OAuth button ───────────────────────────────
        try:
            google_url = build_google_auth_url()
            st.markdown(
                f"""
                <div style="margin-bottom:20px">
                  <a href="{google_url}" target="_self" style="text-decoration:none">
                    <div style="
                      display:flex;align-items:center;gap:12px;justify-content:center;
                      background:#fff;color:#3c4043;border:1px solid #dadce0;
                      border-radius:8px;padding:12px 24px;font-size:15px;
                      font-family:'Google Sans',Roboto,Arial,sans-serif;font-weight:500;
                      box-shadow:0 2px 8px rgba(0,0,0,0.15);cursor:pointer">
                      <svg width="20" height="20" viewBox="0 0 48 48">
                        <path fill="#EA4335" d="M24 9.5c3.2 0 5.9 1.1 8.1 2.9l6-6C34.5 3.1 29.6 1 24 1
                          14.8 1 7 6.7 3.7 14.7l7 5.4C12.4 13.7 17.7 9.5 24 9.5z"/>
                        <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7
                          c-.6 3-2.3 5.5-4.8 7.2l7.4 5.7c4.3-4 6.8-9.9 6.8-16.9z"/>
                        <path fill="#FBBC05" d="M10.7 28.6A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.7-4.6
                          l-7-5.4A23.9 23.9 0 0 0 .5 24c0 3.9.9 7.5 2.7 10.7l7.5-6.1z"/>
                        <path fill="#34A853" d="M24 47c5.9 0 10.9-1.9 14.5-5.2l-7.4-5.7
                          c-2 1.4-4.6 2.2-7.1 2.2-6.3 0-11.6-4.2-13.5-10l-7.5 6.1
                          C7 41.3 14.9 47 24 47z"/>
                      </svg>
                      Continue with Google
                    </div>
                  </a>
                </div>
                """,
                unsafe_allow_html=True,
            )
        except Exception:
            st.warning("⚠️ Google OAuth not configured — add GOOGLE_CLIENT_ID to .env")

        st.markdown(
            "<div style='text-align:center;color:#475569;margin:4px 0 16px'>"
            "— or use email —</div>",
            unsafe_allow_html=True,
        )

        # ── Email auth tabs ───────────────────────────────────
        login_tab, signup_tab = st.tabs(["🔑 Log In", "📝 Sign Up"])

        with login_tab:
            with st.form("login_form"):
                email_in    = st.text_input("Email", placeholder="you@company.com",
                                             key="li_email")
                password_in = st.text_input("Password", type="password",
                                             key="li_pass")
                submitted   = st.form_submit_button(
                    "Log In", use_container_width=True, type="primary"
                )

            if submitted:
                if not email_in or not password_in:
                    st.error("Please fill in both fields.")
                else:
                    with st.spinner("Signing in…"):
                        ok, msg = auth_sign_in(email_in, password_in)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with signup_tab:
            with st.form("signup_form"):
                su_name  = st.text_input("Full Name",  placeholder="Jane Smith",
                                          key="su_name")
                su_email = st.text_input("Email",       placeholder="you@company.com",
                                          key="su_email")
                su_pass  = st.text_input("Password (min 6 chars)", type="password",
                                          key="su_pass")
                su_pass2 = st.text_input("Confirm Password",       type="password",
                                          key="su_pass2")
                su_sub   = st.form_submit_button(
                    "Create Account", use_container_width=True, type="primary"
                )

            if su_sub:
                if not all([su_name, su_email, su_pass, su_pass2]):
                    st.error("Please fill in all fields.")
                elif su_pass != su_pass2:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating account…"):
                        ok, msg = auth_sign_up(su_email, su_pass, su_name)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        # ── Demo hint ─────────────────────────────────────────
        with st.expander("💡 No data? Use our sample CSV"):
            st.markdown(
                "Download a sample SaaS dataset to explore all features:\n\n"
                "The platform auto-detects columns for date, revenue, users, "
                "churn, plan, and engagement — so any SaaS CSV should work out of the box."
            )
            # Generate a small sample dataset for download
            import pandas as pd, io, numpy as np
            rng = np.random.default_rng(42)
            n   = 120
            months = pd.date_range("2023-01-01", periods=n, freq="D")
            sample = pd.DataFrame({
                "date":       months.strftime("%Y-%m-%d"),
                "users":      rng.integers(10, 80, n),
                "revenue":    (rng.random(n) * 4000 + 500).round(2),
                "churn":      rng.choice([0,1], n, p=[0.85,0.15]),
                "retention":  (rng.random(n) * 0.3 + 0.65).round(3),
                "plan":       rng.choice(["Starter","Pro","Enterprise"], n),
                "engagement": rng.integers(1, 50, n),
                "ltv":        (rng.random(n) * 3000 + 200).round(2),
            })
            csv_bytes = sample.to_csv(index=False).encode()
            st.download_button(
                "⬇️ Download sample_saas_data.csv",
                data=csv_bytes,
                file_name="sample_saas_data.csv",
                mime="text/csv",
            )


# =============================================================
#  ROUTER
# =============================================================

def main():
    """
    Main router — decides which screen to render.
    1. Always run OAuth intercept first (process_oauth_redirect called above)
    2. Authenticated → Dashboard
    3. Otherwise     → Home page
    """
    if is_authenticated():
        render_dashboard()
    else:
        render_home()


if __name__ == "__main__":
    main()
else:
    main()
