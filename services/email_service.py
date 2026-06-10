"""
NEXUS-14: Email Service
Handles all email communications including production reports.
Supports: SendGrid, SMTP
Reports sent to: talalnewjersey@gmail.com
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service for NEXUS-14 production reports.
    
    Sends:
    - Morning Production Report (09:45 UTC)
    - Executive Daily Report (18:30 UTC)
    - Error alerts
    - Article publication notifications
    
    Primary recipient: talalnewjersey@gmail.com
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.sendgrid_api_key = config.get("sendgrid_api_key", "")
        self.from_email = config.get("email_from", "noreply@moneyabroadguide.com")
        self.from_name = config.get("email_from_name", "NEXUS-14 Newsroom")
        self.recipient = config.get("email_recipient", "talalnewjersey@gmail.com")
        self.subject_prefix = config.get("email_subject_prefix", "[NEXUS-14]")
        
        logger.info(f"EmailService initialized. Recipient: {self.recipient}")
    
    async def send(self, to: str, subject: str, body: str, 
                   html_body: str = None, attachments: List = None) -> bool:
        """Send an email."""
        try:
            if self.sendgrid_api_key:
                return await self._send_sendgrid(to, subject, body, html_body, attachments)
            else:
                return await self._send_smtp(to, subject, body, html_body)
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False
    
    async def send_html(self, to: str, subject: str, html_body: str, 
                        text_body: str = None) -> bool:
        """Send an HTML email."""
        return await self.send(to, subject, text_body or "", html_body)
    
    async def send_morning_report(self, metrics: Dict, errors: List) -> bool:
        """Send the morning production report."""
        subject = f"{self.subject_prefix} Morning Production Report - {datetime.utcnow().strftime('%B %d, %Y')}"
        
        body = self._build_morning_report_text(metrics, errors)
        html = self._build_morning_report_html(metrics, errors)
        
        logger.info(f"Sending morning report to {self.recipient}")
        return await self.send(self.recipient, subject, body, html)
    
    async def send_executive_report(self, report_html: str, metrics: Dict) -> bool:
        """Send the executive daily report."""
        subject = f"{self.subject_prefix} Executive Daily Report - {datetime.utcnow().strftime('%B %d, %Y')}"
        
        text_body = (
            f"NEXUS-14 Daily Report\n"
            f"Articles Produced: {metrics.get('total_articles_produced', 0)}\n"
            f"Articles Validated: {metrics.get('articles_validated', 0)}\n"
            f"Articles Rejected: {metrics.get('articles_rejected', 0)}\n"
        )
        
        logger.info(f"Sending executive report to {self.recipient}")
        return await self.send(self.recipient, subject, text_body, report_html)
    
    async def send_error_alert(self, error_message: str, agent_id: str = None) -> bool:
        """Send an error alert."""
        subject = f"{self.subject_prefix} ERROR ALERT - {agent_id or 'System'}"
        body = f"Error detected in NEXUS-14:\n\n{error_message}\n\nTime: {datetime.utcnow().isoformat()}"
        
        return await self.send(self.recipient, subject, body)
    
    async def _send_sendgrid(self, to: str, subject: str, body: str, 
                              html_body: str = None, attachments: List = None) -> bool:
        """Send email via SendGrid API."""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
            
            sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to),
                subject=subject
            )
            
            message.add_content(Content("text/plain", body))
            if html_body:
                message.add_content(Content("text/html", html_body))
            
            response = await asyncio.to_thread(sg.send, message)
            
            if response.status_code in [200, 202]:
                logger.info(f"Email sent successfully via SendGrid. Status: {response.status_code}")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"SendGrid sending failed: {e}")
            return False
    
    async def _send_smtp(self, to: str, subject: str, body: str, html_body: str = None) -> bool:
        """Send email via SMTP."""
        import aiosmtplib
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to
        
        msg.attach(MIMEText(body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))
        
        smtp_config = self.config.get("smtp", {})
        
        try:
            await aiosmtplib.send(
                msg,
                hostname=smtp_config.get("host", "smtp.gmail.com"),
                port=smtp_config.get("port", 587),
                username=smtp_config.get("username"),
                password=smtp_config.get("password"),
                use_tls=smtp_config.get("use_tls", True)
            )
            logger.info(f"Email sent via SMTP to {to}")
            return True
        except Exception as e:
            logger.error(f"SMTP sending failed: {e}")
            return False
    
    def _build_morning_report_text(self, metrics: Dict, errors: List) -> str:
        """Build plain text morning report."""
        lines = [
            "=" * 50,
            "NEXUS-14 MORNING PRODUCTION REPORT",
            f"Date: {datetime.utcnow().strftime('%B %d, %Y')}",
            f"Time: {datetime.utcnow().strftime('%H:%M UTC')}",
            "=" * 50,
            "",
            "PRODUCTION SUMMARY",
            f"  Articles Produced:    {metrics.get('total_articles_produced', 0)}",
            f"  Articles Validated:   {metrics.get('articles_validated', 0)}",
            f"  Articles Rejected:    {metrics.get('articles_rejected', 0)}",
            f"  Needs Correction:     {metrics.get('articles_need_correction', 0)}",
            "",
            "QUALITY METRICS",
            f"  Avg Word Count:       {metrics.get('avg_word_count', 0):,}",
            f"  Avg SEO Score:        {metrics.get('avg_seo_score', 0)}/100",
            f"  Avg EEAT Score:       {metrics.get('avg_eeat_score', 0)}/100",
            "",
            "SYSTEM STATUS",
            f"  Agents Completed:     {metrics.get('agents_completed', 0)}/14",
            "",
        ]
        
        if errors:
            lines.append(f"ERRORS ({len(errors)})")
            for error in errors[:5]:
                lines.append(f"  - {error.get('message', 'Unknown error')}")
            lines.append("")
        
        lines.extend([
            "SCHEDULE",
            "  Batch #1 Ready:       10:00 UTC",
            "  Audit #2:             16:30 UTC",
            "  Executive Report:     18:30 UTC",
            "",
            "--",
            "NEXUS-14 Autonomous Newsroom",
            "MoneyAbroadGuide.com"
        ])
        
        return "\n".join(lines)
    
    def _build_morning_report_html(self, metrics: Dict, errors: List) -> str:
        """Build HTML morning report."""
        error_html = ""
        if errors:
            error_items = "".join([f"<li>{e.get('message', '')}</li>" for e in errors[:5]])
            error_html = f"<h3 style='color: #dc3545;'>Errors ({len(errors)})</h3><ul>{error_items}</ul>"
        
        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #1a1a2e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 22px;">🤖 NEXUS-14 Morning Report</h1>
        <p style="margin: 5px 0 0; opacity: 0.8;">{datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}</p>
    </div>
    
    <div stemail_service.pyyle="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h2 style="color: #1a1a2e; margin-top: 0;">Production Summary</h2>
        <table width="100%" cellpadding="8">
            <tr><td>Articles Produced</td><td><strong>{metrics.get('total_articles_produced', 0)}</strong></td></tr>
            <tr><td>Articles Validated</td><td><strong style="color: #28a745;">{metrics.get('articles_validated', 0)}</strong></td></tr>
            <tr><td>Articles Rejected</td><td><strong style="color: #dc3545;">{metrics.get('articles_rejected', 0)}</strong></td></tr>
            <tr><td>Avg SEO Score</td><td><strong>{metrics.get('avg_seo_score', 0)}/100</strong></td></tr>
            <tr><td>Avg EEAT Score</td><td><strong>{metrics.get('avg_eeat_score', 0)}/100</strong></td></tr>
        </table>
    </div>
    
    {error_html}
    
    <p style="color: #666; font-size: 12px; text-align: center; margin-top: 30px;">
        NEXUS-14 Autonomous Newsroom | MoneyAbroadGuide.com
    </p>
</body>
</html>"""
