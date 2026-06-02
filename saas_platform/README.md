# 📊 SaaS Business Analytics & Prediction Platform

> **Final-Year Project / Portfolio Showcase**  
> Built with Python · Streamlit · Supabase · scikit-learn · Plotly · Google OAuth

---

## 🚀 Features

| Module | What it does |
|---|---|
| 🔐 Auth | Email/Password + Google OAuth via Supabase Auth |
| 📤 Upload | CSV / Excel dataset upload with auto-detection of SaaS columns |
| 📈 User Growth | Monthly/weekly new users, cumulative growth, MoM rate |
| 💰 Revenue | MRR, ARR, monthly trends, cumulative revenue |
| 📉 Churn & Retention | Churn rate trends, retention curves |
| 🛒 Subscriptions | Plan breakdown, per-tier revenue, product performance |
| 🎯 Engagement | Sessions/logins trends, scatter plot explorer |
| 🤖 ML — Churn | Random Forest classifier + feature importance |
| 🤖 ML — Revenue | Polynomial Regression forecast (1–12 months) |
| 🤖 ML — CLV | Linear Regression per-customer lifetime value |
| 🤖 ML — Trends | Per-column slope & direction detection |
| 🤖 ML — Segments | K-Means clustering → Champions / Loyal / At Risk / Dormant |
| 📧 Email | SMTP notifications: login alerts, reports, prediction summaries |
| 📋 History | Reports, prediction history, login history, notifications |

---

## 🗂️ Project Structure

```
saas_platform/
├── app.py              ← Entry point  (streamlit run app.py)
├── auth.py             ← Email/password + Google OAuth auth
├── dashboard.py        ← Full post-login dashboard (9 tabs)
├── analytics.py        ← SaaS analytics computations
├── prediction.py       ← 5 ML models
├── charts.py           ← Plotly chart generators
├── database.py         ← All Supabase CRUD operations
├── email_service.py    ← SMTP email templates
├── utils.py            ← Shared helpers, formatters, constants
├── supabase_setup.sql  ← Run once in Supabase SQL Editor
├── requirements.txt    ← pip dependencies
├── .env.example        ← Copy → .env and fill in values
└── README.md
```

---

## ⚡ Quick Start (5 steps)

### 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### 2 — Set up Supabase (free)
1. Go to [supabase.com](https://supabase.com) → New Project
2. **SQL Editor → New Query** → paste `supabase_setup.sql` → **Run**
3. Go to **Settings → API** → copy:
   - Project URL  
   - anon/public key

### 3 — Set up Google OAuth (optional but recommended)
1. [console.cloud.google.com](https://console.cloud.google.com) → New Project
2. **APIs & Services → OAuth consent screen** → External → fill app name
3. **APIs & Services → Credentials → Create → OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Authorised redirect URI: `http://localhost:8501/`  ← exact, with trailing slash
4. Copy Client ID and Client Secret

### 4 — Configure environment
```bash
cp .env.example .env
# Open .env and fill in all values
```

`.env` should look like:
```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...

GOOGLE_CLIENT_ID=123-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_REDIRECT_URI=http://localhost:8501/

SMTP_EMAIL=your@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

### 5 — Run
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) 🎉

---

## 📊 Sample Dataset

The app ships with a **built-in sample CSV generator** on the home page.  
Click **"Download sample_saas_data.csv"** and upload it to explore all features instantly.

The platform auto-detects columns by keyword matching:

| Column keyword | Detected as |
|---|---|
| `date`, `created_at`, `timestamp` | Date axis |
| `revenue`, `mrr`, `arr`, `amount` | Revenue metric |
| `user`, `customer`, `subscriber` | User count |
| `churn`, `cancel`, `attrition` | Churn target |
| `retention`, `retained` | Retention rate |
| `plan`, `tier`, `subscription` | Plan/segment |
| `engagement`, `session`, `login` | Engagement metric |
| `ltv`, `clv`, `lifetime_value` | CLV target |

---

## 🗄️ Database Schema

```
profiles          — user info (linked to Supabase Auth)
login_history     — every login event with provider + device
datasets          — uploaded file metadata (name, rows, cols)
reports           — saved analytics report summaries
predictions       — ML model results (type, accuracy, summary)
notifications     — in-app alerts (info / success / warning / error)
```

All tables have **Row Level Security (RLS)** enabled.

---

## 🤖 ML Models Explained

### 1. Churn Prediction — Random Forest
- **What**: Classifies each customer as "will churn" or "won't churn"
- **Why Random Forest**: Handles mixed data types, resistant to overfitting, provides feature importance
- **Input needed**: Column with `churn` in name (0/1 values) + numeric features

### 2. Revenue Forecasting — Polynomial Regression
- **What**: Predicts next 1–12 months of revenue
- **Why Polynomial**: Captures non-linear growth better than plain linear regression
- **Input needed**: `date` column + `revenue`/`mrr` column

### 3. Customer Lifetime Value — Linear Regression
- **What**: Predicts the total expected revenue per customer
- **Input needed**: `ltv`/`clv`/`revenue` column as target + numeric features

### 4. Trend Analysis — Linear Regression per Column
- **What**: Fits a line to each numeric column over time → Increasing / Decreasing / Stable
- **Input needed**: `date` column + any numeric columns

### 5. User Segmentation — K-Means Clustering
- **What**: Groups customers into k clusters → labelled Champions, Loyal, At Risk, Dormant
- **Why K-Means**: Fast, unsupervised, produces clear actionable segments
- **Input needed**: 2+ numeric columns (no labels required)

---

## 📧 Email Setup (Gmail)

1. Enable **2-Factor Authentication** on your Gmail account
2. Go to [myaccount.google.com](https://myaccount.google.com) → Security → **App Passwords**
3. Generate password for **Mail**
4. Use the 16-character code as `SMTP_PASSWORD` in `.env`

> ⚠️ Never commit your `.env` file to Git. Add it to `.gitignore`.

---

## 🚢 Deployment (Streamlit Cloud)

1. Push code to a **private** GitHub repo (`.env` in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New App
3. Select your repo and `app.py`
4. Add all `.env` values under **Advanced → Secrets** (TOML format):
```toml
SUPABASE_URL = "https://..."
SUPABASE_ANON_KEY = "eyJ..."
GOOGLE_CLIENT_ID = "..."
GOOGLE_CLIENT_SECRET = "..."
GOOGLE_REDIRECT_URI = "https://your-app.streamlit.app/"
SMTP_EMAIL = "..."
SMTP_PASSWORD = "..."
```
5. Update `GOOGLE_REDIRECT_URI` in Google Console to your deployed URL

---

## 🐛 Common Issues

| Problem | Fix |
|---|---|
| `Supabase credentials not found` | Check `.env` exists and has correct values |
| `Google login not working` | Verify redirect URI matches exactly (including trailing `/`) |
| `SMTP Authentication failed` | Use App Password, not Gmail password. Enable 2FA first. |
| `No churn column found` | Column name must contain `churn` or `cancel` |
| `Need more data for predictions` | Add more rows — ML needs at least 10–20 records |
| Charts show "No data" | Upload a dataset first in the Upload tab |

---

## 📝 License

MIT — free for educational and portfolio use.
