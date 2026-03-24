import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_NAME = os.getenv("EMAIL_FROM_NAME", "BHK Invest Bot")


def _send(to_email: str, subject: str, html: str):
    if not SMTP_USER or not SMTP_PASS:
        logging.warning("SMTP credentials not set — skipping email.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        logging.info(f"Email sent to {to_email}")
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")


def send_lead_followup(name: str, email: str, interest: str = None):
    service_line = (
        f"<p>You expressed interest in: <strong>{interest}</strong>. "
        f"Our team will reach out to walk you through the process.</p>"
        if interest else
        "<p>Our team will be in touch to help you find the right solution.</p>"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;border:1px solid #eee;border-radius:8px;">
      <div style="background:#25D366;padding:20px;border-radius:6px 6px 0 0;text-align:center;">
        <h1 style="color:white;margin:0;font-size:20px;">BHK Investment (PTY) LTD</h1>
        <p style="color:white;margin:4px 0 0;font-size:13px;opacity:0.9;">Perseverance, Integrity and Honour</p>
      </div>

      <div style="padding:28px 24px;">
        <h2 style="color:#1a1a2e;margin-top:0;">Hi {name or 'there'}, thank you for reaching out!</h2>
        <p>We received your enquiry via our WhatsApp bot and a member of our team will be in touch with you shortly.</p>
        {service_line}

        <div style="background:#f9fff9;border-left:4px solid #25D366;padding:16px;margin:24px 0;border-radius:4px;">
          <p style="margin:0;font-weight:bold;">✅ Remember — NO UPFRONT FEES | 100% RISK-FREE</p>
          <p style="margin:8px 0 0;font-size:13px;color:#555;">We only succeed when you succeed.</p>
        </div>

        <p>In the meantime you can:</p>
        <ul style="line-height:2;">
          <li>Apply online: <a href="https://bhkinvest.co.za/apply" style="color:#25D366;">bhkinvest.co.za/apply</a></li>
          <li>Call us: <strong>012 002 5096</strong></li>
          <li>Email us: <a href="mailto:info@bhkinvest.co.za" style="color:#25D366;">info@bhkinvest.co.za</a></li>
        </ul>
      </div>

      <div style="background:#f8f9fa;padding:16px 24px;border-radius:0 0 6px 6px;text-align:center;">
        <p style="color:#aaa;font-size:12px;margin:0;">
          BHK Investment (PTY) LTD · Pretoria, South Africa<br>
          100% Success Rate · 580+ Clients Served
        </p>
      </div>
    </div>
    """
    _send(email, "BHK Invest — We've received your enquiry", html)


def send_new_lead_alert(name: str, phone: str, email: str, interest: str = None):
    alert_email = os.getenv("ALERT_EMAIL")
    if not alert_email:
        logging.warning("ALERT_EMAIL not set — skipping internal alert.")
        return

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;border:1px solid #eee;border-radius:8px;">
      <h2 style="color:#1a1a2e;margin-top:0;">🔔 New WhatsApp Lead</h2>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;color:#888;width:120px;">Name</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;font-weight:bold;">{name or '—'}</td>
        </tr>
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;color:#888;">Phone</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;">{phone or '—'}</td>
        </tr>
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;color:#888;">Email</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;">{email or '—'}</td>
        </tr>
        <tr>
          <td style="padding:10px 12px;color:#888;">Interest</td>
          <td style="padding:10px 12px;">
            <span style="background:#e8f5e9;color:#2e7d32;padding:3px 10px;border-radius:20px;font-size:13px;">
              {interest or 'Not specified'}
            </span>
          </td>
        </tr>
      </table>
      <div style="margin-top:20px;">
        <a href="https://bhkinvest.co.za/apply"
           style="background:#25D366;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;font-size:14px;">
          View Leads Dashboard
        </a>
      </div>
    </div>
    """
    _send(alert_email, f"New Lead: {name or 'Unknown'} — {interest or 'No service selected'}", html)
