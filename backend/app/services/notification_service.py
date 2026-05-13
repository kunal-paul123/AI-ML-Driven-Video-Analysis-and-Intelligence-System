"""
Notification Service — Twilio SMS
──────────────────────────────────
Sends an SMS/WhatsApp alert when a security threat is detected.
"""
from app.core.config import settings


def send_sms_alert(title: str, description: str, severity: str) -> bool:
    """
    Send an SMS to the configured phone number via Twilio.
    Only sends for 'critical' or 'high' severity to avoid spam.
    Returns True if sent successfully, False otherwise.
    """
    if severity.lower() not in ("critical", "high"):
        print(f"ℹ️  Skipping SMS for severity='{severity}' (only critical/high trigger SMS)")
        return False

    # Debug: print current config values
    sid = settings.twilio_account_sid
    token = settings.twilio_auth_token
    from_num = settings.twilio_from_number
    to_num = settings.twilio_to_number

    print(f"📲 Attempting SMS | SID: {sid[:10]}... | From: {from_num} | To: {to_num}")

    if not sid or not token or not from_num or not to_num:
        print("❌ Twilio not configured — one or more credentials are missing in .env")
        return False

    try:
        from twilio.rest import Client

        client = Client(sid, token)

        message_body = (
            f"SECURITY ALERT - {severity.upper()}\n"
            f"{title}\n"
            f"{description}\n"
            f"-- VideoAI Intelligence System"
        )

        message = client.messages.create(
            body=message_body,
            from_=from_num,
            to=to_num,
        )

        print(f"✅ SMS sent successfully — SID: {message.sid} | Status: {message.status}")
        return True

    except Exception as e:
        print(f"❌ SMS FAILED — Reason: {e}")
        return False
