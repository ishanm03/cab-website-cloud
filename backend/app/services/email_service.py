# backend/app/services/email_service.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Dict, Any
import json
import urllib.request
import urllib.error

from app.core.config import settings

def _send_email_raw(to_email: str, subject: str, html_content: str, text_content: str) -> bool:
    """
    Deliver email via Resend API, SMTP, or simulated stdout logger fallback.
    Never raises an uncaught exception to ensure database operations are never blocked.
    """
    if not to_email or "@" not in to_email or to_email == "N/A":
        print(f"SethCabs Email Service: Skipping email dispatch. Invalid or missing recipient: {to_email}")
        return False

    # 1. Try Resend API if API Key is configured
    if settings.RESEND_API_KEY:
        try:
            req_data = {
                "from": f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "text": text_content
            }
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps(req_data).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    print(f"SethCabs Email Service: Successfully delivered email to {to_email} via Resend.")
                    return True
        except Exception as re:
            print(f"SethCabs Email Service: Resend dispatch failed ({str(re)}). Falling back...")

    # 2. Try SMTP if host configured
    if settings.SMTP_HOST:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = to_email

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            if settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                server.starttls()

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
            server.quit()
            print(f"SethCabs Email Service: Successfully delivered email to {to_email} via SMTP.")
            return True
        except Exception as se:
            print(f"SethCabs Email Service: SMTP dispatch failed ({str(se)}). Falling back...")

    # 3. Fallback: Log email details cleanly to stdout (Simulation Mode)
    print("=" * 60)
    print(f"📧 [SETHCABS EMAIL SIMULATOR / LOG]")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Body (Text Summary):")
    for line in text_content.strip().splitlines()[:15]:
        print(f"  {line}")
    print("=" * 60)
    return True


def _email_boilerplate(title: str, content_html: str) -> str:
    """Wraps body content in a responsive, branded HTML email template."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f1f5f9;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0b0f19; padding: 30px 10px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" style="max-width: 600px; background-color: #111827; border: 1px solid #1f2937; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5);" cellspacing="0" cellpadding="0">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 24px 30px; background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); border-bottom: 2px solid #f59e0b;">
                            <table width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td>
                                        <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">
                                            SETH<span style="color: #f59e0b;">CABS</span>
                                        </h1>
                                        <p style="margin: 4px 0 0; font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">
                                            Executive Chauffeur & Cab Services
                                        </p>
                                    </td>
                                    <td align="right">
                                        <span style="display: inline-block; padding: 6px 12px; background-color: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 20px; font-size: 11px; font-weight: 700; color: #fbbf24;">
                                            24x7 DISPATCH
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 30px;">
                            {content_html}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; background-color: #0d131f; border-top: 1px solid #1f2937; text-align: center;">
                            <p style="margin: 0 0 6px; font-size: 12px; color: #94a3b8;">
                                Need assistance? Call Dispatch Helpline: <a href="tel:{settings.DISPATCH_HELPLINE}" style="color: #f59e0b; text-decoration: none; font-weight: bold;">{settings.DISPATCH_HELPLINE}</a>
                            </p>
                            <p style="margin: 0; font-size: 11px; color: #64748b;">
                                &copy; 2026 SethCabs Services. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def send_booking_received_email(booking: Dict[str, Any]) -> bool:
    """Triggered immediately when customer creates a booking (Pending Review)."""
    cust_details = booking.get("customer_details", {})
    to_email = cust_details.get("email")
    if not to_email or to_email == "N/A":
        return False

    booking_id = booking.get("booking_id") or booking.get("id", "N/A")
    cust_name = cust_details.get("name") or "Rider"
    trip = booking.get("trip_details", {})
    fare = booking.get("fare_details", {})

    pickup_loc = trip.get("pickup_location", "Pickup Location")
    drop_loc = trip.get("drop_location", "Drop Location")
    date_str = trip.get("pickup_date", "--")
    time_str = trip.get("pickup_time", "--")
    tier = str(fare.get("vehicle_tier", "Sedan")).upper()
    est_fare = fare.get("estimated_fare", 0)

    subject = f"SethCabs: Booking Request Received [{booking_id}]"

    content_html = f"""
    <h2 style="margin: 0 0 12px; color: #ffffff; font-size: 20px;">Booking Request Under Review</h2>
    <p style="margin: 0 0 20px; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
        Dear <strong>{cust_name}</strong>,<br>
        Thank you for choosing SethCabs! We have received your booking request <strong>{booking_id}</strong>. Our dispatch team is currently reviewing driver availability and scheduling your chauffeur.
    </p>

    <div style="background-color: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 24px; border: 1px solid #334155;">
        <h3 style="margin: 0 0 14px; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #f59e0b;">
            Trip Specifications
        </h3>
        <table width="100%" cellspacing="0" cellpadding="6" style="font-size: 13px; color: #e2e8f0;">
            <tr>
                <td style="color: #94a3b8; width: 35%;">Booking ID:</td>
                <td style="font-weight: 700; color: #ffffff;">{booking_id}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Pickup Date & Time:</td>
                <td style="font-weight: 700;">{date_str} at {time_str}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Vehicle Class:</td>
                <td style="font-weight: 700; color: #f59e0b;">{tier}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Pickup Point:</td>
                <td style="font-weight: 500;">{pickup_loc}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Destination:</td>
                <td style="font-weight: 500;">{drop_loc}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Estimated Fare:</td>
                <td style="font-weight: 700; color: #10b981; font-size: 15px;">₹{est_fare}/-</td>
            </tr>
        </table>
    </div>

    <p style="margin: 0 0 20px; font-size: 13px; color: #94a3b8; line-height: 1.6;">
        ℹ️ <em>You will receive a WhatsApp message or phone call from our dispatch supervisor once your driver is assigned.</em>
    </p>
    """

    text_content = f"""SethCabs: Booking Request Received [{booking_id}]

Dear {cust_name},
We have received your booking request {booking_id}. Our dispatch team is reviewing driver availability.

Trip Details:
- Pickup: {pickup_loc}
- Destination: {drop_loc}
- Date & Time: {date_str} at {time_str}
- Vehicle Class: {tier}
- Estimated Fare: ₹{est_fare}/-

Helpline: {settings.DISPATCH_HELPLINE}
"""
    return _send_email_raw(to_email, subject, _email_boilerplate("Booking Received", content_html), text_content)


def send_booking_confirmed_email(booking: Dict[str, Any]) -> bool:
    """Triggered when Admin assigns driver and confirms booking."""
    cust_details = booking.get("customer_details", {})
    to_email = cust_details.get("email")
    if not to_email or to_email == "N/A":
        return False

    booking_id = booking.get("booking_id") or booking.get("id", "N/A")
    cust_name = cust_details.get("name") or "Rider"
    trip = booking.get("trip_details", {})
    fare = booking.get("fare_details", {})
    driver = booking.get("driver_assignment", {})

    driver_name = driver.get("driver_name", "Assigned Chauffeur")
    driver_phone = driver.get("driver_phone", "N/A")
    veh_number = driver.get("vehicle_number", "N/A")

    date_str = trip.get("pickup_date", "--")
    time_str = trip.get("pickup_time", "--")
    pickup_loc = trip.get("pickup_location", "Pickup Location")
    est_fare = fare.get("estimated_fare", 0)

    subject = f"SethCabs: Ride Confirmed! Driver Details for [{booking_id}]"

    content_html = f"""
    <div style="background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 16px; margin-bottom: 20px; text-align: center;">
        <h2 style="margin: 0; color: #10b981; font-size: 20px; font-weight: 800;">✓ RIDE CONFIRMED</h2>
        <p style="margin: 6px 0 0; color: #a7f3d0; font-size: 13px;">Your driver and car have been assigned!</p>
    </div>

    <p style="margin: 0 0 20px; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
        Dear <strong>{cust_name}</strong>,<br>
        Great news! Your ride <strong>{booking_id}</strong> is confirmed. Please find your chauffeur and vehicle details below:
    </p>

    <!-- Driver Card -->
    <div style="background-color: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155;">
        <h3 style="margin: 0 0 14px; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #f59e0b;">
            Chauffeur & Fleet Details
        </h3>
        <table width="100%" cellspacing="0" cellpadding="6" style="font-size: 13px; color: #e2e8f0;">
            <tr>
                <td style="color: #94a3b8; width: 35%;">Chauffeur Name:</td>
                <td style="font-weight: 700; color: #ffffff;">{driver_name}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Driver Contact:</td>
                <td><a href="tel:{driver_phone}" style="color: #f59e0b; text-decoration: none; font-weight: 700;">{driver_phone}</a></td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Vehicle Plate No:</td>
                <td style="font-weight: 700; color: #38bdf8; text-transform: uppercase;">{veh_number}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Pickup Date & Time:</td>
                <td style="font-weight: 700;">{date_str} at {time_str}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Pickup Location:</td>
                <td style="font-weight: 500;">{pickup_loc}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Total Fare:</td>
                <td style="font-weight: 700; color: #10b981; font-size: 15px;">₹{est_fare}/-</td>
            </tr>
        </table>
    </div>

    <p style="margin: 0; font-size: 13px; color: #94a3b8; line-height: 1.6;">
        Your chauffeur will arrive 10-15 minutes prior to the pickup time. Have a pleasant trip!
    </p>
    """

    text_content = f"""SethCabs: Ride Confirmed! Driver Details for [{booking_id}]

Dear {cust_name},
Your ride {booking_id} is confirmed!

Chauffeur: {driver_name}
Contact: {driver_phone}
Vehicle: {veh_number}
Pickup: {pickup_loc}
Time: {date_str} at {time_str}
Total Fare: ₹{est_fare}/-

Helpline: {settings.DISPATCH_HELPLINE}
"""
    return _send_email_raw(to_email, subject, _email_boilerplate("Ride Confirmed", content_html), text_content)


def send_booking_rejected_email(booking: Dict[str, Any], reason: str = "") -> bool:
    """Triggered when Admin rejects / cancels a booking."""
    cust_details = booking.get("customer_details", {})
    to_email = cust_details.get("email")
    if not to_email or to_email == "N/A":
        return False

    booking_id = booking.get("booking_id") or booking.get("id", "N/A")
    cust_name = cust_details.get("name") or "Rider"
    trip = booking.get("trip_details", {})
    date_str = trip.get("pickup_date", "--")
    time_str = trip.get("pickup_time", "--")
    reason_text = reason or booking.get("rejection_reason") or "Operational unavailability on this route/time."

    subject = f"SethCabs: Booking Update for [{booking_id}]"

    content_html = f"""
    <div style="background-color: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 12px; padding: 16px; margin-bottom: 20px; text-align: center;">
        <h2 style="margin: 0; color: #f43f5e; font-size: 20px; font-weight: 800;">BOOKING CANCELLED</h2>
        <p style="margin: 6px 0 0; color: #fecdd3; font-size: 13px;">We are unable to fulfill this request at this time.</p>
    </div>

    <p style="margin: 0 0 20px; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
        Dear <strong>{cust_name}</strong>,<br>
        We regret to inform you that we are unable to accept your booking request <strong>{booking_id}</strong> scheduled for <strong>{date_str} at {time_str}</strong>.
    </p>

    <div style="background-color: #1e293b; border-radius: 12px; padding: 16px; margin-bottom: 20px; border-left: 4px solid #f43f5e;">
        <strong style="color: #f43f5e; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 6px;">Reason:</strong>
        <p style="margin: 0; font-size: 13px; color: #e2e8f0; font-style: italic;">"{reason_text}"</p>
    </div>

    <p style="margin: 0 0 16px; font-size: 13px; color: #94a3b8; line-height: 1.6;">
        If you have questions or require an urgent custom booking arrangement, please reach our 24x7 priority dispatch desk directly at <a href="tel:{settings.DISPATCH_HELPLINE}" style="color: #f59e0b; font-weight: bold;">{settings.DISPATCH_HELPLINE}</a>.
    </p>
    """

    text_content = f"""SethCabs: Booking Update for [{booking_id}]

Dear {cust_name},
We regret to inform you that booking {booking_id} for {date_str} at {time_str} could not be fulfilled.

Reason: {reason_text}

For immediate assistance or alternate vehicle arrangement, please contact our dispatch team at {settings.DISPATCH_HELPLINE}.
"""
    return _send_email_raw(to_email, subject, _email_boilerplate("Booking Update", content_html), text_content)


def send_ride_started_email(booking: Dict[str, Any]) -> bool:
    """Triggered when Admin clicks Start Ride (status: active / On-Going)."""
    cust_details = booking.get("customer_details", {})
    to_email = cust_details.get("email")
    if not to_email or to_email == "N/A":
        return False

    booking_id = booking.get("booking_id") or booking.get("id", "N/A")
    cust_name = cust_details.get("name") or "Rider"
    trip = booking.get("trip_details", {})
    driver = booking.get("driver_assignment", {})

    driver_name = driver.get("driver_name", "Assigned Chauffeur")
    driver_phone = driver.get("driver_phone", "N/A")
    veh_number = driver.get("vehicle_number", "N/A")
    drop_loc = trip.get("drop_location", "Destination")

    subject = f"SethCabs: Your Ride Has Started [{booking_id}] - Safe Journey!"

    content_html = f"""
    <div style="background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 12px; padding: 16px; margin-bottom: 20px; text-align: center;">
        <h2 style="margin: 0; color: #38bdf8; font-size: 20px; font-weight: 800;">🚀 RIDE IN PROGRESS</h2>
        <p style="margin: 6px 0 0; color: #bae6fd; font-size: 13px;">Your journey with SethCabs has officially begun!</p>
    </div>

    <p style="margin: 0 0 20px; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
        Dear <strong>{cust_name}</strong>,<br>
        Your journey for booking <strong>{booking_id}</strong> is now on-going. Relax and enjoy your travel with our professional chauffeur service.
    </p>

    <div style="background-color: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155;">
        <table width="100%" cellspacing="0" cellpadding="6" style="font-size: 13px; color: #e2e8f0;">
            <tr>
                <td style="color: #94a3b8; width: 35%;">Chauffeur:</td>
                <td style="font-weight: 700; color: #ffffff;">{driver_name} (<a href="tel:{driver_phone}" style="color: #f59e0b; text-decoration: none;">{driver_phone}</a>)</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Vehicle Plate:</td>
                <td style="font-weight: 700; color: #f59e0b; text-transform: uppercase;">{veh_number}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Destination:</td>
                <td style="font-weight: 500;">{drop_loc}</td>
            </tr>
        </table>
    </div>

    <p style="margin: 0; font-size: 13px; color: #94a3b8; line-height: 1.6;">
        🛡️ In case of any mid-route assistance, our 24x7 control room is reachable at <a href="tel:{settings.DISPATCH_HELPLINE}" style="color: #f59e0b; font-weight: bold;">{settings.DISPATCH_HELPLINE}</a>.
    </p>
    """

    text_content = f"""SethCabs: Your Ride Has Started [{booking_id}] - Safe Journey!

Dear {cust_name},
Your trip {booking_id} is in progress.

Chauffeur: {driver_name} ({driver_phone})
Vehicle: {veh_number}
Destination: {drop_loc}

Control Room: {settings.DISPATCH_HELPLINE}
"""
    return _send_email_raw(to_email, subject, _email_boilerplate("Ride Started", content_html), text_content)


def send_ride_completed_email(booking: Dict[str, Any]) -> bool:
    """Triggered when Admin marks ride as Completed (status: completed)."""
    cust_details = booking.get("customer_details", {})
    to_email = cust_details.get("email")
    if not to_email or to_email == "N/A":
        return False

    booking_id = booking.get("booking_id") or booking.get("id", "N/A")
    cust_name = cust_details.get("name") or "Rider"
    trip = booking.get("trip_details", {})
    fare = booking.get("fare_details", {})

    pickup_loc = trip.get("pickup_location", "Pickup Location")
    drop_loc = trip.get("drop_location", "Drop Location")
    final_fare = fare.get("estimated_fare", 0)

    invoice_url = f"{settings.FRONTEND_BASE_URL}/modules/booking/invoice.html?id={booking_id}"
    activity_url = f"{settings.FRONTEND_BASE_URL}/modules/booking/activity.html"

    subject = f"SethCabs: Trip Completed & Official Tax Invoice [{booking_id}]"

    content_html = f"""
    <div style="background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 16px; margin-bottom: 20px; text-align: center;">
        <h2 style="margin: 0; color: #10b981; font-size: 20px; font-weight: 800;">✓ TRIP COMPLETED</h2>
        <p style="margin: 6px 0 0; color: #a7f3d0; font-size: 13px;">Thank you for choosing SethCabs!</p>
    </div>

    <p style="margin: 0 0 20px; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
        Dear <strong>{cust_name}</strong>,<br>
        Your journey for booking <strong>{booking_id}</strong> has been successfully completed. We hope you had a safe and comfortable ride with our chauffeur.
    </p>

    <!-- Trip Summary Box -->
    <div style="background-color: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 24px; border: 1px solid #334155;">
        <table width="100%" cellspacing="0" cellpadding="6" style="font-size: 13px; color: #e2e8f0;">
            <tr>
                <td style="color: #94a3b8; width: 35%;">Route:</td>
                <td style="font-weight: 500;">{pickup_loc} ➔ {drop_loc}</td>
            </tr>
            <tr>
                <td style="color: #94a3b8;">Total Fare:</td>
                <td style="font-weight: 800; color: #10b981; font-size: 16px;">₹{final_fare}/-</td>
            </tr>
        </table>
    </div>

    <!-- Actions -->
    <div style="text-align: center; margin-bottom: 24px;">
        <a href="{invoice_url}" target="_blank" style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #0b0f19; font-weight: 800; text-decoration: none; border-radius: 10px; font-size: 14px; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);">
            📄 View / Download Tax Invoice
        </a>
    </div>

    <p style="margin: 0; font-size: 12px; color: #94a3b8; text-align: center;">
        Please take a moment to rate your chauffeur in your <a href="{activity_url}" style="color: #f59e0b; text-decoration: none;">Activity Dashboard</a>!
    </p>
    """

    text_content = f"""SethCabs: Trip Completed & Official Tax Invoice [{booking_id}]

Dear {cust_name},
Thank you for traveling with SethCabs! Your trip {booking_id} has completed.

Route: {pickup_loc} -> {drop_loc}
Total Fare: ₹{final_fare}/-

Download Tax Invoice:
{invoice_url}

Rate your trip:
{activity_url}
"""
    return _send_email_raw(to_email, subject, _email_boilerplate("Trip Completed", content_html), text_content)
