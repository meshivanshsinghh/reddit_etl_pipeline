import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from datetime import datetime

class EmailAlerter:
    """Send email alerts for critical anomalies"""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv('GMAIL_USER')
        self.sender_password = os.getenv('GMAIL_APP_PASSWORD')
        self.recipient_email = os.getenv('ALERT_EMAIL_TO')
        
        if not all([self.sender_email, self.sender_password, self.recipient_email]):
            print("⚠️ Warning: Email credentials not set. Skipping email alerts.")
            print("   Set GMAIL_USER, GMAIL_APP_PASSWORD, ALERT_EMAIL_TO to enable.")
            self.enabled = False
        else:
            self.enabled = True
    
    def send_alert(self, anomalies: List[Dict]):
        """Send email for critical/high severity anomalies
        
        Args:
            anomalies: List of anomaly dicts with alert_type, severity, message, etc.
        """
        if not self.enabled:
            print("📧 Email alerts disabled (credentials not configured)")
            return
        
        # Filter for CRITICAL and HIGH only
        critical_anomalies = [a for a in anomalies if a['severity'] in ['CRITICAL', 'HIGH']]
        
        if not critical_anomalies:
            print("📧 No critical/high severity alerts to send")
            return
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[{critical_anomalies[0]['severity']}] Tesla Energy Alert - {len(critical_anomalies)} Issue(s) Detected"
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        
        # Create HTML body
        html = self._create_html_body(critical_anomalies)
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            print(f"✅ Email alert sent: {len(critical_anomalies)} anomalies to {self.recipient_email}")
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
    
    def _create_html_body(self, anomalies: List[Dict]) -> str:
        """Create HTML email body"""
        severity_colors = {
            'CRITICAL': '#dc2626',
            'HIGH': '#ea580c',
            'MEDIUM': '#f59e0b',
            'LOW': '#3b82f6'
        }
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #1f2937; color: white; padding: 20px; }}
                .alert {{ padding: 15px; margin: 10px 0; border-left: 4px solid #ccc; background: #f9f9f9; }}
                .critical {{ border-left-color: {severity_colors['CRITICAL']}; background: #fee; }}
                .high {{ border-left-color: {severity_colors['HIGH']}; background: #fef3e7; }}
                .severity {{ font-weight: bold; font-size: 1.1em; }}
                .timestamp {{ color: #666; font-size: 0.9em; }}
                .post-link {{ color: #0066cc; text-decoration: none; }}
                .post-link:hover {{ text-decoration: underline; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ccc; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 Tesla Energy Sentiment Alert</h2>
            </div>
            <p style="padding: 15px;"><strong>{len(anomalies)} anomal{'y' if len(anomalies) == 1 else 'ies'} detected</strong> at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        for anomaly in anomalies:
            severity_class = anomaly['severity'].lower()
            html += f"""
            <div class="alert {severity_class}">
                <div class="severity" style="color: {severity_colors[anomaly['severity']]};">
                    {anomaly['severity']} - {anomaly['alert_type']}
                </div>
                <p><strong>Subreddit:</strong> r/{anomaly.get('subreddit', 'multiple')}</p>
                <p><strong>Message:</strong> {anomaly['message']}</p>
            """
            
            # Add post links if available
            metadata = anomaly.get('metadata', {})
            if metadata and 'post_links' in metadata and metadata['post_links']:
                html += "<p><strong>Related Posts:</strong><ul>"
                for i, link in enumerate(metadata['post_links'][:5]):  # Max 5 posts
                    title = metadata.get('post_titles', [])[i] if i < len(metadata.get('post_titles', [])) else 'View post'
                    html += f'<li><a href="https://reddit.com{link}" class="post-link">{title}</a></li>'
                html += "</ul></p>"
            elif metadata and 'post_id' in metadata:
                # Single post (EXTREME_POST type)
                post_title = metadata.get('title', 'View post')
                html += f'<p><strong>Related Post:</strong> {post_title}</p>'
            
            html += "</div>"
        
        html += """
            <div class="footer">
                <p>
                    This is an automated alert from the <strong>Tesla Energy Sentiment Pipeline</strong>.<br>
                    To investigate further, check the PostgreSQL alerts table or run <code>./verify_pipeline.sh</code>
                </p>
            </div>
        </body>
        </html>
        """
        
        return html


# Test function
if __name__ == "__main__":
    alerter = EmailAlerter()
    
    test_anomalies = [
        {
            'alert_type': 'EXTREME_POST',
            'severity': 'CRITICAL',
            'subreddit': 'teslaenergy',
            'message': 'Fire hazard recall detected',
            'metadata': {
                'post_id': 'abc123',
                'title': 'Tesla Recalls Powerwall 2 AC Battery Systems Due to Fire Hazards'
            }
        }
    ]
    
    alerter.send_alert(test_anomalies)