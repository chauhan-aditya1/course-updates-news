import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, config):
        self.config = config
    
    def send_notification(self, updates):
        """Send notifications through all enabled channels"""
        if not updates:
            logger.info("No updates to notify")
            return
        
        if self.config.get('email', {}).get('enabled'):
            self.send_email(updates)
        
        if self.config.get('slack', {}).get('enabled'):
            self.send_slack(updates)
    
    def send_email(self, updates):
        """Send email notification"""
        try:
            email_config = self.config['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = f"🔔 Certification Updates - {datetime.now().strftime('%B %d, %Y')}"
            
            body = self._create_email_body(updates)
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                password = os.getenv('EMAIL_PASSWORD')
                if not password:
                    logger.error("EMAIL_PASSWORD environment variable not set")
                    return
                
                server.login(email_config['from_email'], password)
                server.send_message(msg)
            
            logger.info("✓ Email notification sent successfully")
        
        except Exception as e:
            logger.error(f"✗ Error sending email: {str(e)}")
    
   def _create_email_body(self, updates):
        """Create HTML email for certification changes"""
        from datetime import datetime
        
        # Group by provider
        by_provider = {}
        for update in updates:
            provider = update.get('provider', 'Other')
            by_provider.setdefault(provider, []).append(update)
        
        html = """
        <html>
        <head>
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    text-align: center;
                }
                .header h1 {
                    margin: 0 0 10px 0;
                    font-size: 28px;
                }
                .summary {
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin-bottom: 30px;
                    border-radius: 4px;
                }
                .provider-section {
                    margin-bottom: 30px;
                }
                .provider-header {
                    background-color: #667eea;
                    color: white;
                    padding: 12px 20px;
                    border-radius: 8px;
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 15px;
                }
                .cert-card {
                    background: white;
                    border-left: 4px solid #667eea;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .cert-title {
                    font-size: 18px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 8px;
                }
                .cert-code {
                    display: inline-block;
                    background-color: #e8f5e9;
                    color: #2e7d32;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: 600;
                    margin-bottom: 15px;
                }
                .change-item {
                    background-color: #fff9e6;
                    border-left: 3px solid #ff9800;
                    padding: 12px 15px;
                    margin: 8px 0;
                    border-radius: 4px;
                    font-size: 15px;
                }
                .change-item::before {
                    content: "▸ ";
                    color: #ff9800;
                    font-weight: bold;
                }
                .btn {
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #667eea;
                    color: white !important;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 10px;
                    font-weight: 500;
                }
                .btn:hover {
                    background-color: #5568d3;
                }
                .footer {
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 2px solid #ddd;
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 13px;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔔 Certification Updates Detected</h1>
                <p style="margin: 0; opacity: 0.95; font-size: 16px;">
                    """ + datetime.now().strftime('%B %d, %Y') + """
                </p>
            </div>
            
            <div class="summary">
                <strong>📊 Summary:</strong> """ + str(len(updates)) + """ certification(s) updated across """ + str(len(by_provider)) + """ provider(s)
            </div>
        """
        
        for provider, provider_updates in by_provider.items():
            html += f'<div class="provider-section">'
            html += f'<div class="provider-header">📚 {provider} ({len(provider_updates)} update{"s" if len(provider_updates) > 1 else ""})</div>'
            
            for update in provider_updates:
                html += '<div class="cert-card">'
                html += f'<div class="cert-title">{update["name"]}</div>'
                html += f'<span class="cert-code">{update["code"]}</span>'
                html += '<div style="margin-top: 15px;"><strong>Changes Detected:</strong></div>'
                
                for change in update['changes']:
                    html += f'<div class="change-item">{change}</div>'
                
                html += f'<a href="{update["url"]}" class="btn">View Certification Page →</a>'
                html += '</div>'
            
            html += '</div>'
        
        html += """
            <div class="footer">
                <p><strong>KodeKloud Certification Monitor</strong></p>
                <p>Automated monitoring for 49 certifications</p>
                <p style="margin-top: 10px; font-size: 11px;">
                    AWS • Azure • Kubernetes • CNCF • Google Cloud • HashiCorp • More
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
       
        for provider, provider_updates in by_provider.items():
            html += f'<div class="provider-section">'
            html += f'<div class="provider-header">📚 {provider}</div>'
            
            for update in provider_updates:
                html += '<div class="update-card">'
                html += f'<div class="update-title">{update.get("title", "No title")}</div>'
                
                html += '<div class="update-meta">'
                html += f'📍 {update.get("source", "Unknown")} | '
                html += f'📅 {update.get("published_date", "Recent")[:10]} | '
                html += f'⭐ {update.get("relevance_score", 0)}/100'
                html += '</div>'
                
                if update.get('keywords_matched'):
                    html += '<div class="keywords">'
                    for keyword in update['keywords_matched'][:5]:
                        html += f'<span class="keyword-tag">🏷️ {keyword}</span>'
                    html += '</div>'
                
                summary = update.get('summary', '')
                if summary:
                    # Clean and truncate summary
                    summary = summary.replace('\n', ' ').strip()
                    if len(summary) > 400:
                        summary = summary[:400] + '...'
                    html += f'<div class="update-summary">{summary}</div>'
                
                if update.get('url'):
                    html += f'<a href="{update["url"]}" class="btn">Read Full Article →</a>'
                
                html += '</div>'
            
            html += '</div>'
        
        html += """
            <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #7f8c8d; font-size: 12px;">
                <p>Automated Certification Monitor</p>
                <p>AWS | Azure | Kubernetes | Google Cloud | DevOps</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_slack(self, updates):
        """Send Slack notification"""
        try:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL') or self.config['slack'].get('webhook_url')
            if not webhook_url:
                logger.warning("Slack webhook URL not configured")
                return
            
            # Group by provider
            by_provider = {}
            for update in updates:
                provider = update.get('provider', 'Other').upper()
                if provider not in by_provider:
                    by_provider[provider] = []
                by_provider[provider].append(update)
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔔 {len(updates)} Certification Updates",
                        "emoji": True
                    }
                },
                {"type": "divider"}
            ]
            
            for provider, provider_updates in list(by_provider.items())[:5]:  # Limit providers
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📚 {provider}* - {len(provider_updates)} update(s)"
                    }
                })
                
                for update in provider_updates[:3]:  # Limit updates per provider
                    text = f"*{update.get('title', 'No title')[:100]}*\n"
                    text += f"_{update.get('source', 'Unknown')}_ • Score: {update.get('relevance_score', 0)}/100"
                    
                    block = {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": text}
                    }
                    
                    if update.get('url'):
                        block["accessory"] = {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Read"},
                            "url": update['url']
                        }
                    
                    blocks.append(block)
                
                blocks.append({"type": "divider"})
            
            response = requests.post(webhook_url, json={"blocks": blocks})
            response.raise_for_status()
            
            logger.info("✓ Slack notification sent successfully")
        
        except Exception as e:
            logger.error(f"✗ Error sending Slack notification: {str(e)}")
