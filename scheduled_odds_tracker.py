import schedule
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from datetime import datetime, timezone
import pandas as pd
from odds_arbitrage_finder import OddsArbitrageFinder

class OddsTracker:
    def __init__(self, api_key, email_settings):
        self.api_key = api_key
        self.email_settings = email_settings
        self.finder = OddsArbitrageFinder(api_key)

    def send_email(self, df, individual_emails=True):
        """
        Send email with arbitrage opportunities to multiple recipients
        individual_emails: If True, sends separate emails to each recipient (BCC style)
                         If False, sends one email to all recipients (CC style)
        """
        # Filter for arbitrage opportunities only and sort by profit percentage
        arb_df = df[df['opportunity_type'] == 'Arbitrage'].sort_values('profit_percentage', ascending=False)
        
        if arb_df.empty:
            return  # Don't send email if no arbitrage opportunities

        # Create HTML email body
        html_body = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .opportunity {
                    background-color: #f8f9fa;
                    border-left: 4px solid #28a745;
                    margin: 15px 0;
                    padding: 15px;
                    border-radius: 4px;
                }
                .profit {
                    color: #28a745;
                    font-size: 18px;
                    font-weight: bold;
                }
                .game-info {
                    color: #495057;
                    font-size: 16px;
                    margin: 10px 0;
                }
                .bet-info {
                    margin: 10px 0;
                    padding: 10px;
                    background-color: white;
                    border-radius: 4px;
                }
                .book-link {
                    color: #007bff;
                    text-decoration: none;
                }
                .time-stamp {
                    color: #6c757d;
                    font-size: 12px;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
        """

        for _, row in arb_df.iterrows():
            html_body += f"""
            <div class="opportunity">
                <div class="profit">Profit: {row['profit_percentage']:.2f}%</div>
                <div class="game-info">
                    {row['sport']} | {row['game']}
                    <br>
                    Market: {row['market_type']}
                    {f" ({row['market_point']:g})" if pd.notna(row['market_point']) else ""}
                </div>
                <div class="bet-info">
                    Bet 1 ({row['team1_stake']:.1f}%): 
                    <a href="{row['team1_link']}" class="book-link">{row['team1_book']}</a>
                    - {row['team1_name']} 
                    {f"({row['team1_point']:+g})" if pd.notna(row['team1_point']) else ""} 
                    @ {row['team1_odds']}
                </div>
                <div class="bet-info">
                    Bet 2 ({row['team2_stake']:.1f}%): 
                    <a href="{row['team2_link']}" class="book-link">{row['team2_book']}</a>
                    - {row['team2_name']} 
                    {f"({row['team2_point']:+g})" if pd.notna(row['team2_point']) else ""} 
                    @ {row['team2_odds']}
                </div>
            </div>
            """

        html_body += f"""
            <div class="time-stamp">
                Generated at {datetime.now().strftime('%I:%M %p %Z')}
            </div>
        </body>
        </html>
        """

        try:
            with smtplib.SMTP(self.email_settings['smtp_server'], self.email_settings['smtp_port']) as server:
                server.starttls()
                server.login(self.email_settings['sender'], self.email_settings['password'])
                
                if individual_emails:
                    # Send individual emails (BCC style)
                    for recipient in self.email_settings['recipients']:
                        msg = MIMEMultipart('alternative')
                        msg['From'] = self.email_settings['sender']
                        msg['To'] = recipient
                        msg['Subject'] = f"Arbitrage Opportunities Alert - {datetime.now().strftime('%I:%M %p')}"
                        msg.attach(MIMEText(html_body, 'html'))
                        server.send_message(msg)
                else:
                    # Send single email to all recipients (CC style)
                    msg = MIMEMultipart('alternative')
                    msg['From'] = self.email_settings['sender']
                    msg['To'] = ', '.join(self.email_settings['recipients'])
                    msg['Subject'] = f"🎯 Arbitrage Opportunities Alert - {datetime.now().strftime('%I:%M %p')}"
                    msg.attach(MIMEText(html_body, 'html'))
                    server.send_message(msg)
                
            print(f"Email(s) sent successfully at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def check_opportunities(self):
        """Check for opportunities and send email"""
        current_hour = datetime.now().hour
        
        # Only run between 12 PM and 10 PM
        if 12 <= current_hour <= 22:
            print(f"\nChecking opportunities at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            try:
                df = self.finder.generate_arbitrage_table()
                self.send_email(df, individual_emails=True)  # Set to False if you want CC style
            except Exception as e:
                print(f"Error during opportunity check: {e}")
        else:
            print(f"Outside operating hours ({current_hour}:00) - skipping check")

def main():
    # API key for odds API
    api_key = '1e926844efc2bdb47a3552415b65b3cd'
    
    # Email settings with multiple recipients
    email_settings = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender': 'bollapranav05@gmail.com',
        'password': 'ycck cfax jvfp rdjc',  
        'recipients': [
            'samreznik8@gmail.com',
            'mattmueller.m215@gmail.com'
        ]
    }
    
    # Initialize tracker
    tracker = OddsTracker(api_key, email_settings)
    
    # Schedule hourly checks
    schedule.every().hour.at(":00").do(tracker.check_opportunities)
    
    # Run initial check immediately
    tracker.check_opportunities()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute for scheduled tasks

if __name__ == "__main__":
    main()