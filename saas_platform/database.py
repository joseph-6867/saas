# ============================================================
# database.py  —  All Supabase Database Operations
# ============================================================
# Every table gets its own set of clearly-named functions.
# Each function does ONE thing and handles its own exceptions.
#
# Tables: profiles, login_history, datasets,
#         reports, predictions, notifications
# ============================================================

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase.client import create_client, Client
import streamlit as st

load_dotenv()


# ── Client (cached — only one connection per session) ─────────

@st.cache_resource
def get_client() -> Client:
    """
    Create and cache the Supabase client.
    @st.cache_resource means it's created only ONCE and reused
    across all reruns (very important for performance).
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not key:
        st.error(
            "❌ Supabase credentials not found!\n"
            "Copy .env.example → .env and fill in your values."
        )
        st.stop()
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Supabase connection failed: {e}")
        st.stop()


# ── PROFILES ──────────────────────────────────────────────────

def db_upsert_profile(user_id: str, email: str, full_name: str,
                      avatar_url: str = "", provider: str = "email") -> dict | None:
    """
    Insert OR update (upsert) a profile row.
    Called after every successful login so the profile stays fresh.
    """
    client = get_client()
    try:
        res = client.table("profiles").upsert({
            "id":         user_id,
            "email":      email,
            "full_name":  full_name,
            "avatar_url": avatar_url,
            "provider":   provider,
            "updated_at": datetime.utcnow().isoformat()
        }, on_conflict="id").execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DB] upsert_profile: {e}")
        return None


def db_get_profile(user_id: str) -> dict | None:
    """Fetch a single profile by user UUID."""
    client = get_client()
    try:
        res = (client.table("profiles").select("*")
               .eq("id", user_id).single().execute())
        return res.data
    except Exception:
        return None


# ── LOGIN HISTORY ─────────────────────────────────────────────

def db_log_login(user_id: str, email: str,
                 provider: str, user_agent: str = "") -> None:
    """Record a login event. Non-blocking — errors are just printed."""
    client = get_client()
    try:
        client.table("login_history").insert({
            "user_id":    user_id,
            "email":      email,
            "provider":   provider,
            "user_agent": user_agent[:200]
        }).execute()
    except Exception as e:
        print(f"[DB] log_login: {e}")


def db_get_login_history(user_id: str, limit: int = 10) -> list[dict]:
    """Return the N most recent logins for a user."""
    client = get_client()
    try:
        res = (client.table("login_history").select("*")
               .eq("user_id", user_id)
               .order("created_at", desc=True)
               .limit(limit).execute())
        return res.data or []
    except Exception:
        return []


# ── DATASETS ──────────────────────────────────────────────────

def db_save_dataset_meta(user_id: str, name: str, rows: int,
                         cols: int, columns_json: str) -> dict | None:
    """
    Save metadata about an uploaded dataset.
    We don't store the actual file bytes — just the shape and column names.
    The real data stays in Streamlit session_state.
    """
    client = get_client()
    try:
        res = client.table("datasets").insert({
            "user_id":      user_id,
            "name":         name,
            "rows":         rows,
            "cols":         cols,
            "columns_json": columns_json
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DB] save_dataset: {e}")
        return None


def db_get_datasets(user_id: str) -> list[dict]:
    """Return all dataset metadata rows for a user."""
    client = get_client()
    try:
        res = (client.table("datasets").select("*")
               .eq("user_id", user_id)
               .order("created_at", desc=True).execute())
        return res.data or []
    except Exception:
        return []


def db_delete_dataset(dataset_id: str, user_id: str) -> bool:
    """Delete a dataset metadata row (ownership-checked by user_id)."""
    client = get_client()
    try:
        client.table("datasets").delete() \
            .eq("id", dataset_id).eq("user_id", user_id).execute()
        return True
    except Exception:
        return False


# ── REPORTS ───────────────────────────────────────────────────

def db_save_report(user_id: str, title: str,
                   report_type: str, summary: str) -> dict | None:
    """Save a generated analytics report summary."""
    client = get_client()
    try:
        res = client.table("reports").insert({
            "user_id":     user_id,
            "title":       title,
            "report_type": report_type,
            "summary":     summary[:3000]
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DB] save_report: {e}")
        return None


def db_get_reports(user_id: str, limit: int = 20) -> list[dict]:
    """Return the N most recent reports for a user."""
    client = get_client()
    try:
        res = (client.table("reports").select("*")
               .eq("user_id", user_id)
               .order("created_at", desc=True)
               .limit(limit).execute())
        return res.data or []
    except Exception:
        return []


# ── PREDICTIONS ───────────────────────────────────────────────

def db_save_prediction(user_id: str, pred_type: str, model_name: str,
                       accuracy: float, summary: str) -> dict | None:
    """Save a machine learning prediction result."""
    client = get_client()
    try:
        res = client.table("predictions").insert({
            "user_id":         user_id,
            "prediction_type": pred_type,
            "model_name":      model_name,
            "accuracy":        round(float(accuracy), 4),
            "summary":         summary[:3000]
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DB] save_prediction: {e}")
        return None


def db_get_predictions(user_id: str, limit: int = 20) -> list[dict]:
    """Return the N most recent ML predictions for a user."""
    client = get_client()
    try:
        res = (client.table("predictions").select("*")
               .eq("user_id", user_id)
               .order("created_at", desc=True)
               .limit(limit).execute())
        return res.data or []
    except Exception:
        return []


# ── NOTIFICATIONS ─────────────────────────────────────────────

def db_add_notification(user_id: str, title: str,
                        message: str, notif_type: str = "info") -> None:
    """
    Push a notification for the user.
    notif_type: 'info' | 'success' | 'warning' | 'error'
    """
    client = get_client()
    try:
        client.table("notifications").insert({
            "user_id": user_id,
            "title":   title,
            "message": message,
            "type":    notif_type,
            "read":    False
        }).execute()
    except Exception as e:
        print(f"[DB] add_notification: {e}")


def db_get_notifications(user_id: str,
                         unread_only: bool = False,
                         limit: int = 10) -> list[dict]:
    """Return recent notifications for a user."""
    client = get_client()
    try:
        q = (client.table("notifications").select("*")
             .eq("user_id", user_id))
        if unread_only:
            q = q.eq("read", False)
        res = q.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception:
        return []


def db_mark_all_read(user_id: str) -> None:
    """Mark all notifications as read for a user."""
    client = get_client()
    try:
        client.table("notifications").update({"read": True}) \
            .eq("user_id", user_id).execute()
    except Exception:
        pass
