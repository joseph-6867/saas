# ============================================================
# utils.py  —  Shared Utilities, Constants & Helpers
# ============================================================
# Used by: analytics.py, prediction.py, charts.py, dashboard.py
# ============================================================

import io
import json
import numpy as np
import pandas as pd
from datetime import datetime

# ── App Meta ──────────────────────────────────────────────────
APP_NAME    = "SaaS Analytics Platform"
APP_VERSION = "1.0.0"
APP_ICON    = "📊"

# ── Chart colour palette ──────────────────────────────────────
PALETTE = [
    "#6366F1", "#8B5CF6", "#10B981", "#F59E0B",
    "#EF4444", "#3B82F6", "#EC4899", "#14B8A6",
    "#F97316", "#84CC16", "#06B6D4", "#A78BFA",
]

COLOR = {
    "primary":   "#6366F1",
    "success":   "#10B981",
    "warning":   "#F59E0B",
    "danger":    "#EF4444",
    "info":      "#3B82F6",
    "bg_dark":   "#0F172A",
    "bg_card":   "#1E293B",
    "text":      "#F1F5F9",
    "muted":     "#94A3B8",
}

# ── Auto-detection keyword maps ───────────────────────────────
# The analytics engine tries to guess which columns hold which
# SaaS metrics by checking if these keywords appear in the name.

COL_KEYWORDS = {
    "date":        ["date", "created_at", "signup", "month", "week",
                    "period", "timestamp", "time", "day"],
    "revenue":     ["revenue", "mrr", "arr", "amount", "sales",
                    "income", "gmv", "payment", "price", "value"],
    "users":       ["user", "customer", "account", "subscriber",
                    "client", "member", "count"],
    "churn":       ["churn", "cancel", "attrition", "left", "quit"],
    "retention":   ["retention", "retained", "keep", "renew"],
    "plan":        ["plan", "tier", "subscription", "product",
                    "package", "segment", "category"],
    "engagement":  ["engagement", "session", "login", "active",
                    "dau", "mau", "visit", "pageview"],
    "ltv":         ["ltv", "clv", "lifetime", "lv"],
}


def detect_col(df: pd.DataFrame, col_type: str) -> str | None:
    """
    Find the first column in df whose name contains any keyword
    for the given col_type.  Returns column name or None.

    Example:
        detect_col(df, "revenue")
        # returns "monthly_revenue" if that column exists
    """
    keywords = COL_KEYWORDS.get(col_type, [])
    cols_lower = {c.lower(): c for c in df.columns}
    for kw in keywords:
        for col_lower, col_orig in cols_lower.items():
            if kw in col_lower:
                return col_orig
    return None


# ── File I/O ──────────────────────────────────────────────────

def load_uploaded_file(uploaded) -> tuple[pd.DataFrame | None, str]:
    """
    Read a Streamlit UploadedFile (CSV or Excel) → pandas DataFrame.
    Returns (df, error_string).  error_string is "" on success.

    Also normalises column names:
      spaces → underscores, all lowercase.
    """
    if uploaded is None:
        return None, "No file provided."
    try:
        name = uploaded.name.lower()
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded)
        else:
            return None, "Only CSV and Excel (.xlsx/.xls) files are supported."

        if df.empty:
            return None, "The uploaded file is empty."

        # Normalise column names
        df.columns = [
            str(c).strip().lower().replace(" ", "_").replace("-", "_")
            for c in df.columns
        ]
        return df, ""
    except Exception as e:
        return None, f"Could not read file: {e}"


def coerce_datetime(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Parse a column as datetime; drop rows where parsing fails."""
    df = df.copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    before = len(df)
    df = df.dropna(subset=[col])
    dropped = before - len(df)
    if dropped > 0:
        print(f"[utils] coerce_datetime: dropped {dropped} unparseable rows in '{col}'")
    return df


def num_cols(df: pd.DataFrame) -> list[str]:
    """Return list of numeric column names."""
    return df.select_dtypes(include=[np.number]).columns.tolist()


def cat_cols(df: pd.DataFrame) -> list[str]:
    """Return list of categorical / object column names."""
    return df.select_dtypes(include=["object", "category"]).columns.tolist()


def df_summary(df: pd.DataFrame) -> dict:
    """
    Return a compact dataset summary dict.
    Used in the Dataset Overview tab.
    """
    return {
        "rows":        len(df),
        "columns":     len(df.columns),
        "numeric":     len(num_cols(df)),
        "categorical": len(cat_cols(df)),
        "missing":     int(df.isnull().sum().sum()),
        "duplicates":  int(df.duplicated().sum()),
        "memory_kb":   round(df.memory_usage(deep=True).sum() / 1024, 1),
    }


# ── Number Formatters ─────────────────────────────────────────

def fmt_number(n: float, decimals: int = 0) -> str:
    """Format large numbers with K / M suffix.  e.g. 1500 → '1.5K'"""
    try:
        n = float(n)
        if n >= 1_000_000:  return f"{n/1_000_000:.1f}M"
        if n >= 1_000:       return f"{n/1_000:.1f}K"
        return f"{n:,.{decimals}f}"
    except Exception:
        return str(n)


def fmt_currency(n: float, symbol: str = "$") -> str:
    """Format as currency string.  e.g. 2500.0 → '$2.5K'"""
    try:
        n = float(n)
        if n >= 1_000_000: return f"{symbol}{n/1_000_000:.2f}M"
        if n >= 1_000:      return f"{symbol}{n/1_000:.1f}K"
        return f"{symbol}{n:,.2f}"
    except Exception:
        return f"{symbol}{n}"


def fmt_pct(n: float, decimals: int = 1) -> str:
    """Format as percentage.  e.g. 0.1234 → '12.3%' or 12.34 → '12.3%'"""
    try:
        n = float(n)
        # If value looks like a ratio (0-1), multiply
        if 0 <= n <= 1:
            n *= 100
        return f"{n:.{decimals}f}%"
    except Exception:
        return str(n)


def delta_pct(curr: float, prev: float) -> tuple[str, str]:
    """
    Calculate % change between two values.
    Returns (label_string, delta_color_for_st_metric).
    delta_color: 'normal' (green for +), 'inverse' (red for +).
    """
    try:
        curr, prev = float(curr), float(prev)
        if prev == 0:
            return "N/A", "off"
        pct  = (curr - prev) / abs(prev) * 100
        sign = "+" if pct >= 0 else ""
        col  = "normal" if pct >= 0 else "inverse"
        return f"{sign}{pct:.1f}%", col
    except Exception:
        return "N/A", "off"


# ── Export ────────────────────────────────────────────────────

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to CSV bytes for st.download_button."""
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel bytes for st.download_button."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return buf.getvalue()


# ── Misc ──────────────────────────────────────────────────────

def now_label() -> str:
    """Return current UTC time as a readable string."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Division that returns `default` instead of ZeroDivisionError."""
    return a / b if b != 0 else default


def build_report_text(df: pd.DataFrame, analysis_type: str,
                      extra_lines: list[str] | None = None) -> str:
    """
    Build a plain-text summary string to save in the reports table.
    """
    lines = [
        f"Type     : {analysis_type}",
        f"Dataset  : {len(df)} rows × {len(df.columns)} columns",
        f"Numeric  : {', '.join(num_cols(df)[:6])}",
        f"Generated: {now_label()}",
    ]
    if extra_lines:
        lines += extra_lines
    return "\n".join(lines)
