import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Gmail SMTP Settings
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

SMTP_USER = os.getenv("USEREMAIL")
SMTP_PASSWORD = os.getenv("USERPASSWORD")


def send_invitation_email(
    recipient_email: str,
    recipient_name: str,
    invite_link: str
):
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError("Email credentials (USEREMAIL / USERPASSWORD) not found in environment variables")

    message = MIMEMultipart("alternative")

    message["From"] = f"FinSight <{SMTP_USER}>"
    message["To"] = recipient_email
    message["Subject"] = "You're invited to FinSight"

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f6f8fb;font-family:Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td align="center" style="padding:40px 20px;">
                    <table width="600" cellpadding="0" cellspacing="0" 
                           style="background:#ffffff;border-radius:16px;padding:40px;">
                        <tr>
                            <td align="center">
                                <h1 style="margin:0;color:#111827;">FinSight</h1>
                                <p style="color:#6b7280;margin-top:8px;">Financial Intelligence Platform</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding-top:30px;">
                                <h2 style="color:#111827;">Welcome {recipient_name},</h2>
                                <p style="font-size:16px;color:#4b5563;line-height:28px;">
                                    You have been invited to join your company's FinSight workspace.
                                </p>
                                <p style="font-size:16px;color:#4b5563;line-height:28px;">
                                    Click below to create your account and access financial reporting, KPI dashboards and analytics.
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" style="padding:30px 0;">
                                <a href="{invite_link}" 
                                   style="background:#111827;color:white;text-decoration:none;padding:14px 30px;border-radius:10px;display:inline-block;font-weight:bold;">
                                    Accept Invitation
                                </a>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <p style="color:#6b7280;font-size:14px;">This invitation expires in 7 days.</p>
                                <p style="color:#6b7280;font-size:14px;">If you did not expect this invitation, you can safely ignore this email.</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
        
        print(f"✅ Email sent successfully to {recipient_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {e}")
        return False