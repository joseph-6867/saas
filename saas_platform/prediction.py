# ============================================================
# prediction.py  —  Machine Learning Prediction Modules
# ============================================================
#
# Models included:
#   1. Churn Prediction        — RandomForest classifier
#   2. Revenue Forecasting     — Polynomial Regression
#   3. Customer Lifetime Value — Linear Regression
#   4. Trend Analysis          — Linear trend on time series
#   5. User Segmentation       — K-Means clustering
#
# Every function returns a standardised result dict so the
# dashboard can display results uniformly.
# ============================================================

import numpy as np
import pandas as pd
from sklearn.ensemble         import RandomForestClassifier
from sklearn.linear_model     import LinearRegression
from sklearn.cluster          import KMeans
from sklearn.preprocessing    import StandardScaler, PolynomialFeatures, LabelEncoder
from sklearn.pipeline         import make_pipeline
from sklearn.model_selection  import train_test_split
from sklearn.metrics          import (accuracy_score, classification_report,
                                       mean_absolute_error, r2_score)
import calendar
from utils import detect_col, coerce_datetime, num_cols, safe_div


# ── 1. Churn Prediction ───────────────────────────────────────

def predict_churn(df: pd.DataFrame) -> dict:
    """
    Binary classification: will this customer churn? (Yes/No)

    Algorithm: Random Forest Classifier
    Why Random Forest?
    - Handles mixed feature types (numbers + categories)
    - Resistant to overfitting (ensemble of many decision trees)
    - Gives feature importance scores for explainability

    Input requirements:
    - A column with 'churn' in its name (target: 0 or 1)
    - At least 3 numeric feature columns

    Returns:
      accuracy, report, feature_importance, predictions_df
    """
    result = {
        "status": "ok", "message": "",
        "accuracy": 0.0, "report": "",
        "feature_importance": pd.DataFrame(),
        "predictions": pd.DataFrame(),
        "model_name": "Random Forest Classifier"
    }

    # Find target column
    churn_col = detect_col(df, "churn")
    if not churn_col:
        result["status"]  = "error"
        result["message"] = "No churn column found (needs 'churn' or 'cancel' in name)."
        return result

    df = df.copy()
    df[churn_col] = pd.to_numeric(df[churn_col], errors="coerce")
    df = df.dropna(subset=[churn_col])

    # Encode categorical columns
    for c in df.select_dtypes(include=["object"]).columns:
        if c != churn_col:
            le = LabelEncoder()
            df[c] = le.fit_transform(df[c].astype(str))

    # Features = all numeric except target
    features = [c for c in num_cols(df) if c != churn_col]
    if len(features) < 2:
        result["status"]  = "warn"
        result["message"] = ("Need at least 2 numeric feature columns "
                             "besides the churn column.")
        return result

    X = df[features].fillna(df[features].median())
    y = (df[churn_col] > 0).astype(int)

    if len(y.unique()) < 2:
        result["status"]  = "warn"
        result["message"] = ("Target column has only one class — "
                             "need both churned and non-churned rows.")
        return result

    if len(X) < 20:
        result["status"]  = "warn"
        result["message"] = "Need at least 20 rows for churn prediction."
        return result

    test_size = max(0.2, min(0.4, 20 / len(X)))
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42,
                                    class_weight="balanced")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    report   = classification_report(y_test, y_pred,
                                     target_names=["Retained", "Churned"])

    # Feature importance
    fi = pd.DataFrame({
        "feature":    features,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)

    # Predictions on full dataset
    df_out = df[features].fillna(df[features].median()).copy()
    df_out["churn_probability"] = model.predict_proba(df_out)[:, 1].round(3)
    df_out["predicted_churn"]   = (df_out["churn_probability"] >= 0.5).astype(int)
    df_out["risk_level"]        = pd.cut(
        df_out["churn_probability"],
        bins=[0, 0.3, 0.6, 1.0],
        labels=["Low", "Medium", "High"]
    )

    result.update({
        "accuracy":           round(accuracy * 100, 2),
        "report":             report,
        "feature_importance": fi,
        "predictions":        df_out.head(200)
    })
    return result


# ── 2. Revenue Forecasting ────────────────────────────────────

def forecast_revenue(df: pd.DataFrame, periods: int = 6) -> dict:
    """
    Predict future revenue for the next `periods` months.

    Algorithm: Polynomial Regression (degree 2)
    Why? Better captures non-linear growth trends than simple
    linear regression, without overfitting like higher degrees.

    Input: date column + revenue column.
    """
    result = {
        "status": "ok", "message": "",
        "historical": pd.DataFrame(), "forecast": pd.DataFrame(),
        "model_score": 0.0, "model_name": "Polynomial Regression (deg 2)",
        "trend": "Stable"
    }

    date_col    = detect_col(df, "date")
    revenue_col = detect_col(df, "revenue")

    if not date_col or not revenue_col:
        result["status"]  = "error"
        result["message"] = ("Need both a date column and a revenue column. "
                             "Check column names contain 'date' and 'revenue'/'mrr'.")
        return result

    df = coerce_datetime(df, date_col)
    df = df.copy()
    df[revenue_col] = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)

    # Aggregate to monthly totals
    df["_month"] = df[date_col].dt.to_period("M")
    monthly = (df.groupby("_month", as_index=False)[revenue_col]
                 .sum().rename(columns={"_month": "period", revenue_col: "revenue"}))
    monthly = monthly.sort_values("period").reset_index(drop=True)
    monthly["t"] = range(1, len(monthly) + 1)   # sequential time index

    if len(monthly) < 3:
        result["status"]  = "warn"
        result["message"] = "Need at least 3 months of data for revenue forecasting."
        return result

    X = monthly["t"].values.reshape(-1, 1)
    y = monthly["revenue"].values

    # Polynomial degree 2 pipeline
    degree = 2 if len(monthly) >= 5 else 1
    model  = make_pipeline(PolynomialFeatures(degree), LinearRegression())
    model.fit(X, y)
    score = r2_score(y, model.predict(X))

    # Future periods
    last_t = int(monthly["t"].max())
    last_period = monthly["period"].iloc[-1]
    future_rows = []
    curr_period  = last_period
    for i in range(1, periods + 1):
        curr_period  = curr_period + 1
        pred_val = max(0.0, float(model.predict([[last_t + i]])[0]))
        future_rows.append({
            "period": str(curr_period),
            "revenue": round(pred_val, 2),
            "t": last_t + i
        })

    forecast_df  = pd.DataFrame(future_rows)
    monthly["period"] = monthly["period"].astype(str)

    # Trend direction
    if len(monthly) >= 3:
        first_half  = monthly["revenue"].iloc[:len(monthly)//2].mean()
        second_half = monthly["revenue"].iloc[len(monthly)//2:].mean()
        diff_pct    = safe_div(second_half - first_half, first_half) * 100
        trend = "📈 Increasing" if diff_pct > 5 else ("📉 Decreasing" if diff_pct < -5 else "➡️ Stable")
    else:
        trend = "➡️ Stable"

    result.update({
        "historical":   monthly,
        "forecast":     forecast_df,
        "model_score":  round(score * 100, 1),
        "trend":        trend
    })
    return result


# ── 3. Customer Lifetime Value ────────────────────────────────

def predict_clv(df: pd.DataFrame) -> dict:
    """
    Predict Customer Lifetime Value (CLV/LTV) for each customer.

    Algorithm: Linear Regression on available numeric features.
    Target: existing LTV column OR revenue column.

    CLV represents the total revenue a business can expect
    from a single customer account.
    """
    result = {
        "status": "ok", "message": "",
        "predictions": pd.DataFrame(),
        "mae": 0.0, "r2": 0.0,
        "avg_predicted_clv": 0.0,
        "model_name": "Linear Regression"
    }

    ltv_col = detect_col(df, "ltv") or detect_col(df, "revenue")
    if not ltv_col:
        result["status"]  = "error"
        result["message"] = ("No LTV/revenue column found. "
                             "Column name should contain 'ltv', 'clv', or 'revenue'.")
        return result

    df = df.copy()
    # Encode categoricals
    for c in df.select_dtypes(include=["object"]).columns:
        le = LabelEncoder()
        df[c] = le.fit_transform(df[c].astype(str))

    df[ltv_col] = pd.to_numeric(df[ltv_col], errors="coerce")
    df = df.dropna(subset=[ltv_col])

    features = [c for c in num_cols(df) if c != ltv_col]
    if len(features) < 1:
        result["status"]  = "warn"
        result["message"] = "Need at least 1 numeric feature column besides the target."
        return result

    X = df[features].fillna(df[features].median())
    y = df[ltv_col]

    if len(X) < 10:
        result["status"]  = "warn"
        result["message"] = "Need at least 10 rows for CLV prediction."
        return result

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)

    # Predict on all rows
    df_out = X.copy()
    df_out["actual_clv"]    = y.values
    df_out["predicted_clv"] = np.maximum(0, model.predict(X)).round(2)
    df_out["clv_segment"]   = pd.cut(
        df_out["predicted_clv"],
        bins=3,
        labels=["Low Value", "Mid Value", "High Value"]
    )

    result.update({
        "predictions":       df_out.head(200),
        "mae":               round(mae, 2),
        "r2":                round(r2 * 100, 1),
        "avg_predicted_clv": round(float(df_out["predicted_clv"].mean()), 2)
    })
    return result


# ── 4. Trend Analysis ─────────────────────────────────────────

def analyse_trends(df: pd.DataFrame) -> dict:
    """
    Detect trends in all numeric time-series columns.
    For each numeric column, fits a linear model and reports
    whether the trend is Increasing, Decreasing, or Stable.
    """
    result = {
        "status": "ok", "message": "",
        "trends": pd.DataFrame(),
        "summary": []
    }

    date_col = detect_col(df, "date")
    if not date_col:
        result["status"]  = "warn"
        result["message"] = "No date column found for trend analysis."
        return result

    df = coerce_datetime(df, date_col)
    df["_t"] = (df[date_col] - df[date_col].min()).dt.days.astype(float)

    numeric = [c for c in num_cols(df) if c != "_t"]
    if not numeric:
        result["status"]  = "warn"
        result["message"] = "No numeric columns to analyse."
        return result

    rows = []
    for col in numeric:
        series = df[["_t", col]].dropna()
        if len(series) < 3:
            continue
        X = series["_t"].values.reshape(-1, 1)
        y = series[col].values
        reg = LinearRegression().fit(X, y)
        slope = reg.coef_[0]
        r2    = r2_score(y, reg.predict(X))

        # Normalise slope by mean to get % change per day
        mean_val = np.mean(y)
        pct_per_day = safe_div(slope, mean_val) * 100

        direction = ("Increasing 📈" if pct_per_day > 0.01
                     else "Decreasing 📉" if pct_per_day < -0.01
                     else "Stable ➡️")

        rows.append({
            "Column":        col,
            "Trend":         direction,
            "Slope/Day":     round(slope, 4),
            "% Change/Day":  round(pct_per_day, 4),
            "R² Score":      round(r2 * 100, 1)
        })
        result["summary"].append(f"{col}: {direction} ({pct_per_day:+.3f}%/day)")

    result["trends"] = pd.DataFrame(rows)
    return result


# ── 5. User Segmentation ──────────────────────────────────────

def segment_users(df: pd.DataFrame, n_clusters: int = 4) -> dict:
    """
    Group users into segments using K-Means clustering.

    Algorithm: K-Means Clustering
    Why K-Means?
    - Unsupervised (no labels needed)
    - Fast and scalable
    - Produces clear, interpretable segments

    Segments are labelled by their average spending/engagement:
    Champions, Loyal Customers, At Risk, Needs Attention.
    """
    result = {
        "status": "ok", "message": "",
        "segmented_df": pd.DataFrame(),
        "cluster_summary": pd.DataFrame(),
        "segment_counts": pd.Series(dtype=int),
        "model_name": f"K-Means (k={n_clusters})"
    }

    # Encode categoricals
    df_enc = df.copy()
    for c in df_enc.select_dtypes(include=["object"]).columns:
        le = LabelEncoder()
        df_enc[c] = le.fit_transform(df_enc[c].astype(str))

    features = num_cols(df_enc)
    # Remove likely ID columns (very high cardinality integers)
    features = [f for f in features if df_enc[f].nunique() > 2]

    if len(features) < 2:
        result["status"]  = "warn"
        result["message"] = "Need at least 2 numeric columns for segmentation."
        return result

    X = df_enc[features].fillna(df_enc[features].median())

    # Scale features (K-Means is distance-based — scaling is critical!)
    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Clamp k to avoid errors with small datasets
    k = min(n_clusters, len(X) - 1, 8)
    if k < 2:
        result["status"]  = "warn"
        result["message"] = "Need at least 3 rows for segmentation."
        return result

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    df_out = df.copy()
    df_out["cluster"] = labels

    # Label segments by mean of first numeric feature (e.g., revenue)
    ref_col = detect_col(df_enc, "revenue") or features[0]
    cluster_means = df_out.groupby("cluster")[ref_col if ref_col in df_out.columns
                                               else features[0]].mean()

    # Sort clusters by mean value → assign human-readable labels
    label_map = _label_clusters(cluster_means.sort_values(ascending=False))
    df_out["segment"] = df_out["cluster"].map(label_map)

    # Summary per segment
    summary_cols = [c for c in features[:5] if c in df_out.columns]
    if summary_cols:
        summary = (
            df_out[summary_cols]
            .apply(pd.to_numeric, errors="coerce")
            .groupby(df_out["segment"]).mean()
            .round(2)
            .reset_index()
        )
    else:
        summary = pd.DataFrame(columns=["segment"])

    result.update({
        "segmented_df":   df_out.head(300),
        "cluster_summary": summary,
        "segment_counts": df_out["segment"].value_counts(),
        "model_name":     f"K-Means (k={k})"
    })
    return result


def _label_clusters(sorted_means: pd.Series) -> dict:
    """
    Assign segment labels to cluster indices based on their rank.
    Highest mean → 'Champions', lowest → 'At Risk / Dormant'
    """
    labels = ["🏆 Champions", "💛 Loyal Customers",
              "⚠️ At Risk", "😴 Dormant / Lost"]
    mapping = {}
    for rank, cluster_id in enumerate(sorted_means.index):
        label = labels[rank] if rank < len(labels) else f"Cluster {rank+1}"
        mapping[cluster_id] = label
    return mapping
