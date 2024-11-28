from flask import Flask, render_template_string
import pandas as pd
from datetime import datetime
from odds_arbitrage_finder import OddsArbitrageFinder

app = Flask(__name__)

# Assume this is your existing class with the URL generator
class URLGenerator:
    def parse_existing_url(self, url):
        """
        Parse an existing betslip URL to extract book and parameters
        Returns tuple of (book_name, params_dict)
        """
        if not url:
            return None, {}
            
        url = url.lower()
        params = {}
        
        if 'betrivers.com' in url:
            parts = url.split('#event/')
            if len(parts) > 1:
                event_id = parts[1].split('?')[0]
                params['event_id'] = event_id
                if 'market=' in url and 'outcome=' in url:
                    params['market_id'] = url.split('market=')[1].split('&')[0]
                    params['outcome_id'] = url.split('outcome=')[1].split('&')[0]
            return 'betrivers', params
            
        elif 'fanduel.com' in url:
            if '/selection/' in url:
                selection_parts = url.split('/selection/')[1].split('?')[0].split('-')
                if len(selection_parts) > 1:
                    params['event_id'] = selection_parts[0]
                    params['market_id'] = selection_parts[1]
                if 'btag=' in url:
                    params['outcome_id'] = url.split('btag=')[1].split('&')[0]
            return 'fanduel', params
            
        elif 'betmgm.com' in url:
            if '/event/' in url:
                params['event_id'] = url.split('/event/')[1].split('?')[0]
                if 'market=' in url and 'selection=' in url:
                    params['market_id'] = url.split('market=')[1].split('&')[0]
                    params['outcome_id'] = url.split('selection=')[1].split('&')[0]
            return 'betmgm', params
            
        elif 'caesars.com' in url:
            if 'id=' in url and 'market=' in url and 'selection=' in url:
                params['event_id'] = url.split('id=')[1].split('&')[0]
                params['market_id'] = url.split('market=')[1].split('&')[0]
                params['outcome_id'] = url.split('selection=')[1].split('&')[0]
            return 'caesars', params
            
        elif 'draftkings.com' in url:
            if '/event/' in url:
                params['event_id'] = url.split('/event/')[1].split('?')[0]
                if 'category=' in url and 'subcategory=' in url:
                    params['market_id'] = url.split('category=')[1].split('&')[0]
                    params['outcome_id'] = url.split('subcategory=')[1].split('&')[0]
            return 'draftkings', params
            
        return None, {}
    
    def generate_betrivers_url(self, market_id, selection_id, state):
        return f"https://betrivers.com/{state}/..."
    
    def generate_fanduel_url(self, market_id, selection_id, state):
        return f"https://fanduel.com/{state}/..."
    
    def generate_betmgm_url(self, event_id, selection_id, state):
        return f"https://betmgm.com/{state}/..."
    
    def generate_caesars_url(self, selection_id, state):
        return f"https://caesars.com/{state}/..."
    
    def generate_draftkings_url(self, event_id, outcome_id, state):
        return f"https://draftkings.com/{state}/..."

class OpportunitiesGenerator:
    def __init__(self, state='NY'):
        self.state = state
        self.url_generator = URLGenerator()
    
    def generate_opportunities_html(self, df):
        if df.empty:
            return """<div class="no-opps">No opportunities found.</div>"""
        
        df['display_market'] = df.apply(
            lambda x: x.get('prop_description', x['market_type']) 
            if x['market_type'] == 'player_prop' 
            else x['market_type'], 
            axis=1
        )
        
        df['commence_time'] = pd.to_datetime(df['commence_time']).dt.strftime('%Y-%m-%d %H:%M')
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
        df = df.sort_values('hold_percentage', ascending=True)
        
        html = """
        <div class="container">
            <table id="opportunities-table">
                <tr>
                    <th>Type</th>
                    <th>Hold%</th>
                    <th>Sport</th>
                    <th>Market</th>
                    <th>Point</th>
                    <th>Game</th>
                    <th>Time</th>
                    <th>Team1</th>
                    <th>Book1</th>
                    <th>Odds1</th>
                    <th>Stake1</th>
                    <th>Team2</th>
                    <th>Book2</th>
                    <th>Odds2</th>
                    <th>Stake2</th>
                    <th>Profit%</th>
                </tr>"""
        
        for _, row in df.iterrows():
            row_class = 'arbitrage' if row['opportunity_type'] == 'Arbitrage' else 'low-hold'
            badge_class = 'arbitrage-badge' if row['opportunity_type'] == 'Arbitrage' else 'low-hold-badge'
            profit_class = 'profit-positive' if row['profit_percentage'] > 0 else 'profit-zero'
            
            team1_point = f"({row['team1_point']:+g})" if pd.notna(row['team1_point']) else ""
            team2_point = f"({row['team2_point']:+g})" if pd.notna(row['team2_point']) else ""
            
            odds1_class = 'odds-negative' if row['team1_odds'] < 0 else 'odds-positive'
            odds2_class = 'odds-negative' if row['team2_odds'] < 0 else 'odds-positive'
            
            book1_name, params1 = self.url_generator.parse_existing_url(row['team1_link'])
            book2_name, params2 = self.url_generator.parse_existing_url(row['team2_link'])
            
            book1_link = row['team1_link']
            book2_link = row['team2_link']
            
            # Process URLs with the state parameter
            if book1_name:
                if book1_name == 'betrivers' and params1.get('market_id') and params1.get('selection_id'):
                    book1_link = self.url_generator.generate_betrivers_url(params1['market_id'], params1['selection_id'], self.state)
                elif book1_name == 'fanduel' and params1.get('market_id') and params1.get('selection_id'):
                    book1_link = self.url_generator.generate_fanduel_url(params1['market_id'], params1['selection_id'], self.state)
                elif book1_name == 'betmgm' and params1.get('event_id') and params1.get('selection_id'):
                    book1_link = self.url_generator.generate_betmgm_url(params1['event_id'], params1['selection_id'], self.state)
                elif book1_name == 'caesars' and params1.get('selection_id'):
                    book1_link = self.url_generator.generate_caesars_url(params1['selection_id'], self.state)
                elif book1_name == 'draftkings' and params1.get('event_id') and params1.get('outcome_id'):
                    book1_link = self.url_generator.generate_draftkings_url(params1['event_id'], params1['outcome_id'], self.state)
            
            if book2_name:
                if book2_name == 'betrivers' and params2.get('market_id') and params2.get('selection_id'):
                    book2_link = self.url_generator.generate_betrivers_url(params2['market_id'], params2['selection_id'], self.state)
                elif book2_name == 'fanduel' and params2.get('market_id') and params2.get('selection_id'):
                    book2_link = self.url_generator.generate_fanduel_url(params2['market_id'], params2['selection_id'], self.state)
                elif book2_name == 'betmgm' and params2.get('event_id') and params2.get('selection_id'):
                    book2_link = self.url_generator.generate_betmgm_url(params2['event_id'], params2['selection_id'], self.state)
                elif book2_name == 'caesars' and params2.get('selection_id'):
                    book2_link = self.url_generator.generate_caesars_url(params2['selection_id'], self.state)
                elif book2_name == 'draftkings' and params2.get('event_id') and params2.get('outcome_id'):
                    book2_link = self.url_generator.generate_draftkings_url(params2['event_id'], params2['outcome_id'], self.state)
            
            html += f"""
                <tr class="{row_class}">
                    <td><span class="type-badge {badge_class}">{row['opportunity_type']}</span></td>
                    <td>{row['hold_percentage']:.2f}%</td>
                    <td>{row['sport']}</td>
                    <td>{row['display_market']}</td>
                    <td>{row['market_point']}</td>
                    <td>{row['game']}</td>
                    <td>{row['commence_time']}</td>
                    <td>{row['team1_name']} {team1_point}</td>
                    <td><a href="{book1_link}" target="_blank" class="betslip-link">{row['team1_book']}</a></td>
                    <td class="{odds1_class}">{row['team1_odds']}</td>
                    <td class="stake">{row['team1_stake']:.1f}%</td>
                    <td>{row['team2_name']} {team2_point}</td>
                    <td><a href="{book2_link}" target="_blank" class="betslip-link">{row['team2_book']}</a></td>
                    <td class="{odds2_class}">{row['team2_odds']}</td>
                    <td class="stake">{row['team2_stake']:.1f}%</td>
                    <td class="{profit_class}">{row['profit_percentage']:.2f}%</td>
                </tr>"""
        
        html += f"""
            </table>
            <div class="timestamp">
                Last updated: {df['timestamp'].iloc[0]}
            </div>
        </div>"""
        
        return html

# Assume you have a function to get the opportunities data
def get_opportunities_data():
    with open('key.txt', 'r') as file:
        api_key = file.read().strip()
    
    arbitrage_finder = OddsArbitrageFinder(api_key)
    arbitrage_table = arbitrage_finder.generate_arbitrage_table()
    arbitrage_table.to_csv("arbitrage_opps.csv")
    return arbitrage_table

# Initialize the opportunities generator
opportunities_generator = OpportunitiesGenerator()

@app.route('/')
def index():
    df = get_opportunities_data()
    table_html = opportunities_generator.generate_opportunities_html(df)
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Betting Opportunities</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 100%;
                overflow-x: auto;
            }
            #opportunities-table {
                width: 100%;
                border-collapse: collapse;
                background-color: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            }
            #opportunities-table th, #opportunities-table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            #opportunities-table th {
                background-color: #f8f9fa;
                font-weight: bold;
            }
            .type-badge {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            .arbitrage-badge {
                background-color: #d4edda;
                color: #155724;
            }
            .low-hold-badge {
                background-color: #cce5ff;
                color: #004085;
            }
            .odds-negative { color: #dc3545; }
            .odds-positive { color: #28a745; }
            .profit-positive { color: #28a745; }
            .profit-zero { color: #6c757d; }
            .stake { font-weight: bold; }
            .timestamp {
                margin-top: 20px;
                color: #6c757d;
                font-size: 14px;
            }
            .betslip-link {
                color: #007bff;
                text-decoration: none;
            }
            .betslip-link:hover {
                text-decoration: underline;
            }
            .refresh-button {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                margin-bottom: 20px;
                font-size: 16px;
            }
            .refresh-button:hover {
                background-color: #0056b3;
            }
            .no-opps {
                text-align: center;
                padding: 20px;
                color: #6c757d;
                font-size: 18px;
            }
        </style>
        <script>
            function refreshData() {
                location.reload();
            }
        </script>
    </head>
    <body>
        <button class="refresh-button" onclick="refreshData()">Refresh Data</button>
        {{ table_html | safe }}
    </body>
    </html>
    """, table_html=table_html)

if __name__ == '__main__':
    app.run(debug=True)