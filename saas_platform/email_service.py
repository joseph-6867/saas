# ============================================================
# email_service.py  —  SMTP Email Notification Service
# ============================================================
# Sends HTML emails for:
#   • Login alerts
#   • Analytics reports
#   • Prediction summaries
#   • Budget / KPI alerts
#
# Uses Python's built-in smtplib — no external library.
# For Gmail: use an App Password (not your real password).
# ============================================================

import os
import smtplib
from email.mime.text       import MIMEText
from email.mime.multipart  import MIMEMultipart
from datetime              import datetime
from dotenv                import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT", 587))
SMTP_EMAIL  = os.getenv("SMTP_EMAIL", "")
SMTP_PASS   = os.getenv("SMTP_PASSWORD", "")


# ── Core Sender ───────────────────────────────────────────────

def send_email(to: str, subject: str, html: str) -> tuple[bool, str]:
    """
    Send an HTML email via SMTP TLS.
    Returns (success, message).

    HOW SMTP TLS WORKS:
      1. Connect to server on port 587
      2. EHLO handshake
      3. STARTTLS  → upgrade to encrypted channel
      4. LOGIN with credentials
      5. Send MIME message
      6. QUIT
    """
    if not SMTP_EMAIL or not SMTP_PASS:
        return False, "SMTP credentials not configured. Add SMTP_EMAIL and SMTP_PASSWORD to .env"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"SaaS Analytics <{SMTP_EMAIL}>"
        msg["To"]      = to
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASS)
            server.sendmail(SMTP_EMAIL, to, msg.as_string())

        return True, "Email sent successfully!"

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Authentication failed. For Gmail, use an App Password "
            "(Account → Security → App Passwords)."
        )
    except Exception as e:
        return False, f"Email error: {e}"


# ── HTML Base Template ────────────────────────────────────────

def _wrap(title: str, body: str) -> str:
    """Wrap body content in a clean responsive HTML email shell."""
    year = datetime.now().year
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#0F172A;margin:0;padding:20px;color:#CBD5E1}}
  .card{{background:#1E293B;border-radius:12px;padding:32px;max-width:600px;margin:0 auto;
         box-shadow:0 8px 32px rgba(0,0,0,0.4)}}
  .header{{background:linear-gradient(135deg,#6366F1,#8B5CF6);border-radius:8px;
            padding:24px;text-align:center;margin-bottom:24px}}
  .header h1{{margin:0;color:#fff;font-size:22px}}
  .header p{{margin:6px 0 0;color:rgba(255,255,255,0.75);font-size:13px}}
  .kpi{{display:inline-block;background:#0F172A;border-radius:8px;padding:12px 20px;
         margin:6px;text-align:center;min-width:120px}}
  .kpi .val{{font-size:22px;font-weight:700;color:#6366F1}}
  .kpi .lbl{{font-size:11px;color:#94A3B8;margin-top:4px}}
  .alert-ok{{background:#064E3B;border-left:4px solid #10B981;padding:12px 16px;
              border-radius:6px;margin:12px 0;color:#A7F3D0}}
  .alert-warn{{background:#451A03;border-left:4px solid #F59E0B;padding:12px 16px;
               border-radius:6px;margin:12px 0;color:#FDE68A}}
  table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:13px}}
  th{{background:#334155;color:#94A3B8;padding:8px 12px;text-align:left;font-weight:600}}
  td{{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,0.05);color:#CBD5E1}}
  .footer{{text-align:center;color:#475569;font-size:11px;margin-top:24px}}
</style></head><body>
<div class="card">
  <div class="header"><h1>📊 SaaS Analytics Platform</h1><p>{title}</p></div>
  {body}
  <div class="footer">© {year} SaaS Analytics · Automated Notification</div>
</div></body></html>"""


# ── Email Templates ────────────────────────────────────────────

def email_login_alert(to: str, name: str, provider: str) -> tuple[bool, str]:
    """Security alert on new login."""
    body = f"""
    <p>Hi <strong>{name}</strong>,</p>
    <p>A new login to your SaaS Analytics account was detected.</p>
    <div class="alert-ok">
      🔐 <strong>Provider:</strong> {provider.title()}<br>
      🕐 <strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
    </div>
    <p>If this wasn't you, please secure your account immediately.</p>
    """
    return send_email(to, "🔐 New Login Detected — SaaS Analytics", _wrap("Login Alert", body))


def email_analytics_report(to: str, name: str, kpis: dict,
                            dataset_name: str, period: str) -> tuple[bool, str]:
    """Monthly/weekly analytics summary email."""
    kpi_html = "".join(
        f'<div class="kpi"><div class="val">{v}</div><div class="lbl">{k}</div></div>'
        for k, v in kpis.items()
    )

    status_class = "alert-ok" if "growth" in str(kpis).lower() else "alert-warn"

    body = f"""
    <p>Hi <strong>{name}</strong>,</p>
    <p>Here is your analytics report for <strong>{period}</strong>
       on dataset <em>{dataset_name}</em>.</p>
    <div style="margin:20px 0">{kpi_html}</div>
    <div class="{status_class}">
      ✅ Report generated successfully at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
    </div>
    <p style="color:#64748B;font-size:12px">
      Log in to the platform for interactive charts and ML predictions.
    </p>
    """
    return send_email(
        to,
        f"📊 Analytics Report — {period}",
        _wrap(f"Analytics Report · {dataset_name}", body)
    )


def email_prediction_report(to: str, name: str, pred_type: str,
                             model_name: str, accuracy: float,
                             summary_lines: list[str]) -> tuple[bool, str]:
    """ML prediction results email."""
    lines_html = "".join(f"<li>{l}</li>" for l in summary_lines)
    acc_class  = "alert-ok" if accuracy >= 70 else "alert-warn"

    body = f"""
    <p>Hi <strong>{name}</strong>,</p>
    <p>Your <strong>{pred_type}</strong> prediction model has finished running.</p>
    <div class="{acc_class}">
      🤖 <strong>Model:</strong> {model_name}<br>
      🎯 <strong>Accuracy / Score:</strong> {accuracy:.1f}%
    </div>
    <h3 style="color:#94A3B8;font-size:14px;margin-top:20px">Key Findings</h3>
    <ul style="line-height:2;color:#CBD5E1">{lines_html}</ul>
    <p style="color:#64748B;font-size:12px">
      Log in to view full predictions, charts, and download reports.
    </p>
    """
    return send_email(
        to,
        f"🤖 {pred_type} Prediction Report — SaaS Analytics",
        _wrap(f"ML Prediction · {pred_type}", body)
    )


def email_kpi_alert(to: str, name: str, metric: str,
                    value: str, threshold: str,
                    is_warning: bool = True) -> tuple[bool, str]:
    """Alert when a KPI crosses a threshold."""
    cls  = "alert-warn" if is_warning else "alert-ok"
    icon = "⚠️" if is_warning else "✅"
    body = f"""
    <p>Hi <strong>{name}</strong>,</p>
    <div class="{cls}">
      {icon} <strong>{metric}</strong> is now <strong>{value}</strong>
      (threshold: {threshold}).
    </div>
    <p>Review your dashboard for details and recommended actions.</p>
    """
    subject = f"{'⚠️ KPI Alert' if is_warning else '✅ KPI Target Met'} — {metric}"
    return send_email(to, subject, _wrap("KPI Alert", body))
