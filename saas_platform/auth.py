# ============================================================
# auth.py  —  Authentication: Email/Password + Google OAuth
# ============================================================
#
# Email/Password via Supabase Auth:
#   auth_sign_up()  → creates user in supabase.auth.users
#   auth_sign_in()  → validates credentials, returns JWT session
#
# Google OAuth (Authorization Code Flow):
#   Step 1: build_google_auth_url() → send user to Google
#   Step 2: Google redirects back → ?code=XYZ in URL
#   Step 3: handle_google_callback() → exchange code → user info
#   Step 4: upsert profile → set session state
#
# All user state is kept in st.session_state (Streamlit's
# built-in in-memory store — cleared on browser refresh).
# ============================================================

import os
import httpx
import streamlit as st
from urllib.parse import urlencode
from dotenv import load_dotenv
from database import get_client, db_upsert_profile, db_log_login

load_dotenv()

# ── Google OAuth Endpoints (fixed, never change) ─────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "https://sample--saas.streamlit.app/")
GOOGLE_AUTH_URL      = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL     = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"


# ── Session State Management ──────────────────────────────────

def init_session() -> None:
    """
    Set up all session_state keys on first run.
    Streamlit re-runs this file on every interaction;
    we only set defaults if the key doesn't already exist.
    """
    defaults = {
        "authenticated":  False,
        "user_id":        None,
        "email":          None,
        "full_name":      None,
        "avatar_url":     None,
        "provider":       None,       # 'email' | 'google'
        "current_page":   "home",
        "oauth_done":     False,      # prevents re-processing the OAuth code
        "active_df":      None,       # currently loaded pandas DataFrame
        "active_df_name": None,       # filename of the loaded dataset
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _set_session(user_id: str, email: str, full_name: str,
                 avatar_url: str, provider: str) -> None:
    """Populate session state after a successful login."""
    st.session_state.authenticated = True
    st.session_state.user_id       = user_id
    st.session_state.email         = email
    st.session_state.full_name     = full_name
    st.session_state.avatar_url    = avatar_url
    st.session_state.provider      = provider
    st.session_state.current_page  = "dashboard"


def clear_session() -> None:
    """
    Wipe all auth-related session state (logout).
    Keeps non-auth keys (e.g. current_page) reset to default.
    """
    keys = ["authenticated", "user_id", "email", "full_name",
            "avatar_url", "provider", "oauth_done",
            "active_df", "active_df_name"]
    for k in keys:
        st.session_state[k] = None
    st.session_state.authenticated = False
    st.session_state.current_page  = "home"


def is_authenticated() -> bool:
    """Returns True if user has a live authenticated session."""
    return bool(
        st.session_state.get("authenticated") and
        st.session_state.get("user_id")
    )


def require_auth() -> None:
    """
    Guard function: stop page rendering if not logged in.
    Place at the top of any protected page function.
    """
    if not is_authenticated():
        st.warning("🔒 Please log in to access this page.")
        st.stop()


# ── Email / Password Auth ─────────────────────────────────────

def auth_sign_up(email: str, password: str,
                 full_name: str) -> tuple[bool, str]:
    """
    Register a new user with Supabase Auth.

    What happens behind the scenes:
      1. Supabase creates a row in auth.users
      2. Sends a confirmation email to the user
      3. We also create a row in our own profiles table
    """
    client = get_client()
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    try:
        res = client.auth.sign_up({
            "email":    email.strip().lower(),
            "password": password,
            "options":  {"data": {"full_name": full_name.strip()}}
        })
        if res.user:
            db_upsert_profile(res.user.id, email.lower(), full_name,
                              provider="email")
            return True, (
                "✅ Account created! Check your email to confirm "
                "your address, then log in."
            )
        return False, "Sign-up failed — please try again."
    except Exception as e:
        msg = str(e).lower()
        if "already registered" in msg:
            return False, "Email already registered. Please log in."
        return False, f"Sign-up error: {e}"


def auth_sign_in(email: str, password: str) -> tuple[bool, str]:
    """
    Sign in with email + password.
    Supabase validates credentials and returns a JWT session.
    """
    client = get_client()
    try:
        res = client.auth.sign_in_with_password({
            "email":    email.strip().lower(),
            "password": password
        })
        user = res.user
        if not user:
            return False, "Invalid credentials."

        meta       = user.user_metadata or {}
        full_name  = meta.get("full_name", email.split("@")[0])
        avatar_url = meta.get("avatar_url", "")

        # Keep profile fresh
        db_upsert_profile(user.id, user.email, full_name,
                          avatar_url, provider="email")
        db_log_login(user.id, user.email, "email", "Streamlit/Browser")
        _set_session(user.id, user.email, full_name, avatar_url, "email")
        return True, f"Welcome back, {full_name}! 👋"

    except Exception as e:
        msg = str(e).lower()
        if "invalid" in msg or "credentials" in msg or "password" in msg:
            return False, "Incorrect email or password."
        if "confirm" in msg or "not confirmed" in msg or "unconfirmed" in msg:
            return False, (
                "Your email is not confirmed yet. "
                "Please check your inbox for the confirmation link and try again."
            )
        return False, f"Login error: {e}"


def auth_sign_out() -> None:
    """Sign out from Supabase and clear local session."""
    client = get_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass   # local clear happens regardless
    clear_session()


# ── Google OAuth 2.0 ──────────────────────────────────────────

def build_google_auth_url() -> str:
    """
    Build the redirect URL to Google's consent screen.

    Parameters:
      client_id     — our app's ID (from Google Console)
      redirect_uri  — where Google sends the user after login
      response_type — 'code' (Authorization Code Flow)
      scope         — openid + email + profile
      prompt        — 'select_account' shows account picker
    """
    if not GOOGLE_CLIENT_ID:
        st.error("❌ GOOGLE_CLIENT_ID missing from .env — see .env.example")
        st.stop()

    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "online",
        "prompt":        "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def _exchange_code_for_token(code: str) -> dict | None:
    """
    POST to Google's token endpoint to exchange the auth code
    for an access_token.  Must include client_secret (server-side only).
    Returns the token JSON or None on failure.
    """
    try:
        r = httpx.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri":  GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        }, timeout=10)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        st.error(f"❌ Token exchange failed: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"❌ Token request error: {e}")
        return None


def _fetch_google_profile(access_token: str) -> dict | None:
    """Call Google's userinfo API to get email, name, picture."""
    try:
        r = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Google profile fetch failed: {e}")
        return None


def handle_google_callback(code: str) -> tuple[bool, str]:
    """
    Full OAuth callback: code → token → profile → session.
    Called from app.py when ?code= appears in query params.
    """
    token_data = _exchange_code_for_token(code)
    if not token_data or "access_token" not in token_data:
        return False, "Could not obtain access token from Google."

    profile = _fetch_google_profile(token_data["access_token"])
    if not profile:
        return False, "Could not fetch user profile from Google."

    email      = profile.get("email", "").lower().strip()
    full_name  = profile.get("name", email.split("@")[0])
    avatar_url = profile.get("picture", "")
    verified   = profile.get("email_verified", False)
    sub        = profile.get("sub", "")       # Google's stable user ID

    if not email:
        return False, "No email returned from Google."
    if not verified:
        return False, "Google email address is not verified."

    # Try Supabase sign-in via id_token; fall back to using Google sub as ID
    client = get_client()
    user_id = sub   # default fallback
    try:
        id_token = token_data.get("id_token", "")
        if id_token:
            res = client.auth.sign_in_with_id_token({
                "provider": "google",
                "token":    id_token
            })
            if res.user:
                user_id = res.user.id
    except Exception:
        pass   # fallback to sub already set above

    db_upsert_profile(user_id, email, full_name, avatar_url, provider="google")
    db_log_login(user_id, email, "google", f"Google OAuth | {email}")
    _set_session(user_id, email, full_name, avatar_url, "google")
    return True, f"Welcome, {full_name}! 👋"


def process_oauth_redirect() -> None:
    """
    Called at the very top of app.py on every Streamlit run.
    Detects ?code= in the URL (set by Google after user approves),
    processes it once (oauth_done flag), then clears the URL.
    """
    params = st.query_params

    # Google sends ?error= if user denies access
    error = params.get("error")
    if error:
        if isinstance(error, list):
            error = error[0]
        st.error(f"Google login was cancelled: {error}")
        st.query_params.clear()
        return

    code = params.get("code")
    if isinstance(code, list):
        code = code[0]
    if not code:
        return   # normal page load — nothing to do

    if is_authenticated() or st.session_state.get("oauth_done"):
        st.query_params.clear()
        return

    # Process the code exactly once
    st.session_state.oauth_done = True
    with st.spinner("🔄 Completing Google sign-in…"):
        ok, msg = handle_google_callback(code)

    st.query_params.clear()   # remove ?code= from URL

    if ok:
        st.rerun()
    else:
        st.error(f"Google sign-in failed: {msg}")
        st.session_state.oauth_done = False
