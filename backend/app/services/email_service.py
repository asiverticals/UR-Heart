import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
import ssl
from typing import Any, Dict, List, Optional
import httpx

from ..core.config import settings

logger = logging.getLogger("urheart.email")


def _mask_email(email: str) -> str:
    """Masks recipient email for DPDP/GDPR-compliant telemetry without logging raw PII."""
    if not email or "@" not in email:
        return "***"
    user_part, domain = email.split("@", 1)
    masked_user = (user_part[:2] + "***") if len(user_part) > 2 else "***"
    return f"{masked_user}@{domain}"


class EmailService:
    """Multi-engine transactional email waterfall: Resend -> Gmail SMTP -> Brevo API -> Brevo SMTP -> Mock/Testmail."""

    def __init__(self) -> None:
        self.resend_api_key = settings.RESEND_API_KEY
        self.resend_from = settings.RESEND_FROM
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from = settings.SMTP_FROM
        self.brevo_api_key = settings.BREVO_API_KEY
        self.brevo_smtp_host = settings.BREVO_SMTP_HOST
        self.brevo_smtp_port = settings.BREVO_SMTP_PORT
        self.brevo_smtp_user = settings.BREVO_SMTP_USER
        self.brevo_smtp_password = settings.BREVO_SMTP_PASSWORD

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Dispatches an email across the prioritized engine waterfall with failover."""
        # 1. Primary: Resend API
        if self.resend_api_key and not self.resend_api_key.startswith("placeholder_"):
            try:
                success = await self._send_via_resend(to_email, subject, html_content, text_content)
                if success:
                    logger.info("Email dispatched successfully via Resend to %s", _mask_email(to_email))
                    return True
            except Exception as e:
                logger.warning("Resend email dispatch failed (%s) for %s; failing over to SMTP relay", type(e).__name__, _mask_email(to_email))

        # 2. Secondary: Gmail SMTP Relay
        if self.smtp_user and self.smtp_password and not self.smtp_user.startswith("placeholder_"):
            try:
                success = await asyncio.to_thread(
                    self._send_via_smtp,
                    self.smtp_host,
                    self.smtp_port,
                    self.smtp_user,
                    self.smtp_password,
                    self.smtp_from,
                    to_email,
                    subject,
                    html_content,
                    text_content,
                )
                if success:
                    logger.info("Email dispatched successfully via Gmail SMTP to %s", _mask_email(to_email))
                    return True
            except Exception as e:
                logger.warning("Gmail SMTP dispatch failed (%s) for %s; failing over to Brevo", type(e).__name__, _mask_email(to_email))

        # 3. Tertiary: Brevo (Sendinblue) Engine - API or SMTP Relay
        if self.brevo_api_key and not self.brevo_api_key.startswith("placeholder_"):
            try:
                success = await self._send_via_brevo_api(to_email, subject, html_content)
                if success:
                    logger.info("Email dispatched successfully via Brevo to %s", _mask_email(to_email))
                    return True
            except Exception as e:
                logger.warning("Brevo API dispatch failed (%s) for %s; falling back to Brevo SMTP", type(e).__name__, _mask_email(to_email))

        if self.brevo_smtp_user and self.brevo_smtp_password and not self.brevo_smtp_user.startswith("placeholder_"):
            try:
                success = await asyncio.to_thread(
                    self._send_via_smtp,
                    self.brevo_smtp_host,
                    self.brevo_smtp_port,
                    self.brevo_smtp_user,
                    self.brevo_smtp_password,
                    self.smtp_from,
                    to_email,
                    subject,
                    html_content,
                    text_content,
                )
                if success:
                    logger.info("Email dispatched successfully via Brevo SMTP to %s", _mask_email(to_email))
                    return True
            except Exception as e:
                logger.warning("Brevo SMTP dispatch failed (%s) for %s; falling back to offline handler", type(e).__name__, _mask_email(to_email))

        # 4. Offline / Testmail Sandbox Fallback
        if settings.ENVIRONMENT in ("development", "test"):
            logger.info(
                "[EMAIL SANDBOX] Email to %s, Subject: '%s' (content length: %d bytes)",
                _mask_email(to_email),
                subject,
                len(html_content),
            )
            return True

        logger.error(
            "Failed to send email to %s across all configured providers in environment '%s'",
            _mask_email(to_email),
            settings.ENVIRONMENT,
        )
        return False

    async def _send_via_resend(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str],
    ) -> bool:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {self.resend_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": self.resend_from,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        if text_content:
            payload["text"] = text_content

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            return resp.status_code in (200, 201)

    def _send_via_smtp(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        recipient: str,
        subject: str,
        html_content: str,
        text_content: Optional[str],
    ) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient

        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as server:
                server.login(user, password)
                server.sendmail(sender, [recipient], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls(context=context)
                server.login(user, password)
                server.sendmail(sender, [recipient], msg.as_string())
        return True

    async def _send_via_brevo_api(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": self.brevo_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "sender": {"email": self.smtp_from.split("<")[-1].rstrip(">").strip() if "<" in self.smtp_from else self.smtp_from},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            return resp.status_code in (200, 201)

    async def send_magic_link(self, to_email: str, magic_link_url: str) -> bool:
        subject = "UR-Heart Sanctuary: Your Sacred Sign-In Link"
        html = f"""
        <div style="background-color: #0F1115; color: #F9F6F0; padding: 32px; font-family: sans-serif; border-radius: 12px; max-width: 500px; margin: auto;">
            <h2 style="color: #2E6F5E; text-align: center;">UR-Heart Sanctuary</h2>
            <p>A sacred sign-in link was requested for your seeker identity.</p>
            <div style="text-align: center; margin: 28px 0;">
                <a href="{magic_link_url}" style="background-color: #2E6F5E; color: #FFFFFF; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Enter Sanctuary</a>
            </div>
            <p style="font-size: 12px; color: #8A92A6; text-align: center;">This single-use cryptographic link expires in 15 minutes. If you did not request this, you may safely disregard it.</p>
        </div>
        """
        return await self.send_email(to_email, subject, html)

    async def send_incineration_confirmation(self, to_email: str, confirmation_url: str) -> bool:
        subject = "UR-Heart Sanctuary: Confirm Account Incineration (DPDP Act 2023)"
        html = f"""
        <div style="background-color: #0F1115; color: #F9F6F0; padding: 32px; font-family: sans-serif; border-radius: 12px; max-width: 500px; margin: auto;">
            <h2 style="color: #B23B3B; text-align: center;">Account Incineration Request</h2>
            <p>Pursuant to Section 12 of the Digital Personal Data Protection Act 2023, you have requested permanent erasure of your seeker account and all associated biometric and message data.</p>
            <div style="text-align: center; margin: 28px 0;">
                <a href="{confirmation_url}" style="background-color: #B23B3B; color: #FFFFFF; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Permanently Incinerate Account</a>
            </div>
            <p style="font-size: 12px; color: #8A92A6; text-align: center;">This action is permanent and irrevocable. Link expires in 15 minutes.</p>
        </div>
        """
        return await self.send_email(to_email, subject, html)


email_service = EmailService()

def get_email_service() -> EmailService:
    return email_service
