from flask import Flask, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time
import pytz

app = Flask(__name__)
finder = OddsArbitrageFinder('1e926844efc2bdb47a3552415b65b3cd')
tracker = OddsTracker('1e926844efc2bdb47a3552415b65b3cd', email_settings)

def update_data():
    global current_data
    try:
        current_data = finder.generate_arbitrage_table()
        if not current_data.empty:
            tracker.send_email(current_data)
    except Exception as e:
        print(f"Error updating data: {e}")

@app.route('/')
def index():
    df = finder.generate_arbitrage_table()
    html_content = finder.generate_html(df)
    return render_template_string(html_content)

if __name__ == '__main__':
    scheduler = BackgroundScheduler(timezone=pytz.timezone('America/New_York'))
    
    # Schedule updates every 30 minutes between 12:30 PM and 9 PM
    for hour in range(12, 21):  # 12 PM to 9 PM
        scheduler.add_job(update_data, 'cron', hour=hour, minute='0,30')
    
    scheduler.start()
    app.run(host='0.0.0.0', port=5000)