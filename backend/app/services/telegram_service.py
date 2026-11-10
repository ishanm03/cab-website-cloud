# backend/app/services/telegram_service.py
import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from app.core.config import settings

def format_clean_phone(phone_str: str) -> str:
    """Format an Indian phone number for wa.me links."""
    clean = "".join(filter(str.isdigit, str(phone_str or "")))
    if len(clean) == 10:
        return f"91{clean}"
    return clean

def send_telegram_booking_alert(booking: Dict[str, Any]) -> bool:
    """
    Dispatch a real-time notification to the Admin Telegram channel with an inline
    1-Click WhatsApp Holding Reply button.
    Gracefully logs if bot token or chat ID is not configured.
    """
    booking_id = booking.get("booking_id") or booking.get("id", "N/A")
    cust_details = booking.get("customer_details", {})
    cust_name = cust_details.get("name") or "Rider"
    cust_phone = cust_details.get("phone") or "N/A"
    clean_phone = format_clean_phone(cust_phone)

    trip = booking.get("trip_details", {})
    fare = booking.get("fare_details", {})

    pickup_loc = trip.get("pickup_location", "Not specified")
    drop_loc = trip.get("drop_location", "Not specified")
    pickup_date = trip.get("pickup_date", "--")
    pickup_time = trip.get("pickup_time", "--")
    veh_tier = str(fare.get("vehicle_tier", "Sedan")).upper()
    est_fare = fare.get("estimated_fare", 0)

    # 1. Telegram Message Text
    msg_lines = [
        "🚖 *NEW BOOKING REQUEST RECEIVED*",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📋 *ID:* `{booking_id}`",
        f"👤 *Customer:* {cust_name} ({cust_phone})",
        f"📅 *Schedule:* {pickup_date} at {pickup_time}",
        f"📍 *Pickup:* {pickup_loc}",
        f"🎯 *Drop:* {drop_loc}",
        f"🚘 *Tier:* {veh_tier}",
        f"💵 *Estimated Fare:* ₹{est_fare}/-",
        "━━━━━━━━━━━━━━━━━━━━",
        "⚡ _Tap below to send an instant 1-Click WhatsApp holding reply to customer:_"
    ]
    telegram_text = "\n".join(msg_lines)

    # 2. WhatsApp Pre-filled Holding Reply Text
    holding_text = (
        f"🚖 *SETHCABS: BOOKING UNDER REVIEW*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Dear *{cust_name}*,\n"
        f"We have received your booking request *{booking_id}* for *{pickup_date} at {pickup_time}*.\n"
        f"📍 *Route:* {pickup_loc} ➔ {drop_loc}\n\n"
        f"Our dispatch team is currently reviewing driver availability and will get back to you shortly with full confirmation details.\n\n"
        f"📞 Helpline: {settings.DISPATCH_HELPLINE}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    encoded_holding_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(holding_text)}"
    admin_dashboard_url = f"{settings.FRONTEND_BASE_URL}/modules/admin/admin.html"

    # 3. Telegram Inline Buttons
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "💬 WhatsApp Holding Reply (1-Click)", "url": encoded_holding_url}
            ],
            [
                {"text": "🖥️ Open Admin Dashboard", "url": admin_dashboard_url}
            ]
        ]
    }

    # 4. Deliver via Telegram API if configured
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        try:
            telegram_api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": telegram_text,
                "parse_mode": "Markdown",
                "reply_markup": reply_markup,
                "disable_web_page_preview": True
            }
            req = urllib.request.Request(
                telegram_api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    print(f"SethCabs Telegram Service: Successfully sent booking alert for {booking_id}")
                    return True
        except Exception as te:
            print(f"SethCabs Telegram Service: Dispatch failed ({str(te)}). Falling back...")

    # 5. Fallback Simulator / Logger
    print("=" * 60)
    print("🤖 [SETHCABS TELEGRAM BOT SIMULATOR / LOG]")
    print(telegram_text)
    print("Inline Buttons:")
    print(f"  [1] 💬 WhatsApp Holding Reply -> {encoded_holding_url}")
    print(f"  [2] 🖥️ Open Admin Dashboard -> {admin_dashboard_url}")
    print("=" * 60)
    return True
