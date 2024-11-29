from flask import Flask, render_template_string
import pandas as pd
from datetime import datetime
from odds_arbitrage_finder import OddsArbitrageFinder
import os

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
    
    def generate_bookmaker_filter(self):
        """Generate HTML for bookmaker filter section"""
        bookmakers = ['betmgm', 'betrivers', 'caesars', 'draftkings', 'fanduel']
        
        html = """
        <div class="filters">
            <h3>Filter Bookmakers</h3>
            <div class="filter-group">
        """
        
        for book in sorted(bookmakers):
            html += f"""
                <label class="filter-checkbox">
                    <input type="checkbox" class="book-filter" value="{book.lower()}" checked>
                    {book.title()}
                </label>
            """
            
        html += """
            </div>
        </div>
        """
        
        return html
    
    def generate_plus_ev_cards(self, opportunities):
        if not opportunities:
            return """<div class="no-opportunities">No +EV opportunities found</div>"""
        
        html = """
        <table class="opportunities-table">
            <thead>
                <tr>
                    <th class="table-header">EV %</th>
                    <th class="table-header">Game</th>
                    <th class="table-header">Type</th>
                    <th class="table-header" colspan="6">Selection</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for opp in sorted(opportunities, key=lambda x: x['ev_percentage'], reverse=True):
            odds_class = 'odds-negative' if opp['odds'] < 0 else 'odds-positive'
            
            # Handle various bet types and ensure points are displayed correctly
            team_text = opp['team']
            # If it's not already formatted and contains 'Over' or 'Under'
            if ('Over' in team_text or 'Under' in team_text) and '(' not in team_text:
                if opp.get('market_point'):
                    team_text = f"{team_text} ({opp['market_point']})"
                    
            html += f"""
                <tr class="opportunity-row">
                    <td class="profit-cell">+{opp['ev_percentage']:.2f}%</td>
                    <td class="game-cell">
                        <div class="game-details">
                            <div class="game-time">{opp['commence_time']}</div>
                            <div class="game-title">{opp['game']}</div>
                            <div class="game-league">{opp['sport']}</div>
                        </div>
                    </td>
                    <td class="market-type">{opp['market_type']}</td>
                    <td colspan="6" class="bets-cell">
                        <div class="bet-row">
                            <div class="bet-number">1</div>
                            <div class="bet-selection">{team_text}</div>
                            <div class="{odds_class}">{opp['odds']}</div>
                            <img src="{self.get_book_logo(opp['bookmaker'])}" alt="{opp['bookmaker']}" class="book-logo">
                            <div class="stake-amount">$100</div>
                            <a href="{opp['link']}" target="_blank" class="bet-button">BET ↗</a>
                        </div>
                    </td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        return html

    def get_prop_description(self, prop_type, sport_name):
        """Convert prop type to readable format"""
        prop_map = {
            'pass_yds': 'Passing Yards',
            'pass_tds': 'Passing TDs',
            'pass_completions': 'Completions',
            'rush_attempts': 'Rush Attempts',
            'receptions': 'Receptions',
            'reception_yds': 'Receiving Yards',
            'points': 'Points',
            'rebounds': 'Rebounds',
            'assists': 'Assists',
            'threes': '3-Pointers Made',
            'blocks': 'Blocks',
            'steals': 'Steals',
            'blocks_steals': 'Blocks + Steals',
            'turnovers': 'Turnovers',
            'points_rebounds_assists': 'PRA',
            'points_rebounds': 'Points + Rebounds',
            'points_assists': 'Points + Assists',
            'rebounds_assists': 'Rebounds + Assists',
            'power_play_points': 'Power Play Points',
            'blocked_shots': 'Blocked Shots',
            'shots_on_goal': 'Shots on Goal',
            'goals': 'Goals',
            'total_saves': 'Saves'
        }
        return prop_map.get(prop_type, prop_type.replace('_', ' ').title())

    def generate_arbitrage_cards(self, df):
        if df.empty:
            return """<div class="no-opportunities">No arbitrage opportunities found</div>"""
        
        df = df.sort_values('profit_percentage', ascending=False)
        
        html = """
        <table class="opportunities-table">
            <thead>
                <tr>
                    <th class="table-header">Profit</th>
                    <th class="table-header">Game</th>
                    <th class="table-header">Type</th>
                    <th class="table-header" colspan="6">Selections</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for _, row in df.iterrows():
            odds1_class = 'odds-negative' if row['team1_odds'] < 0 else 'odds-positive'
            odds2_class = 'odds-negative' if row['team2_odds'] < 0 else 'odds-positive'
            
            profit_display = f"+{row['profit_percentage']:.2f}%"
            
            # Format the bet selections based on market type
            if row['market_type'] == 'player_prop':
                player_name = row.get('prop_description', '').split(' - ')[0] if row.get('prop_description') else ''
                bet1_text = f"{player_name} Over ({row['team1_point']})"
                bet2_text = f"{player_name} Under ({row['team2_point']})"
                prop_type = row.get('prop_description', '').split(' - ')[1] if row.get('prop_description') else 'Player Prop'
                market_display = prop_type
            elif 'alternate_spreads' in row['market_type']:
                team1_point = f"{row['team1_point']:+g}" if pd.notna(row['team1_point']) else ""
                team2_point = f"{row['team2_point']:+g}" if pd.notna(row['team2_point']) else ""
                bet1_text = f"{row['team1_name']} ({team1_point})"
                bet2_text = f"{row['team2_name']} ({team2_point})"
                market_display = "Alternate Spread" if 'alternate' in row['market_type'].lower() else "Spread"
            elif 'alternate_totals' in row['market_type'] or 'totals' in row['market_type']:
                bet1_text = f"Over ({row['team1_point']})"
                bet2_text = f"Under ({row['team2_point']})"
                market_display = "Alternate Total" if 'alternate' in row['market_type'].lower() else "Total"
            else:
                bet1_text = row['team1_name']
                bet2_text = row['team2_name']
                market_display = row['market_type'].replace('_', ' ').title()

            html += f"""
                <tr class="opportunity-row">
                    <td class="profit-cell">{profit_display}</td>
                    <td class="game-cell">
                        <div class="game-details">
                            <div class="game-time">{row['commence_time']}</div>
                            <div class="game-title">{row['game']}</div>
                            <div class="game-league">{row['sport']}</div>
                        </div>
                    </td>
                    <td class="market-type">{market_display}</td>
                    <td colspan="6" class="bets-cell">
                        <div class="bet-row">
                            <div class="bet-number">1</div>
                            <div class="bet-selection">{bet1_text}</div>
                            <div class="{odds1_class}">{row['team1_odds']}</div>
                            <img src="{self.get_book_logo(row['team1_book'])}" alt="{row['team1_book']}" class="book-logo">
                            <div class="stake-amount">${row['team1_stake']:.0f}</div>
                            <a href="{row['team1_link']}" target="_blank" class="bet-button">BET ↗</a>
                        </div>
                        <div class="bet-row">
                            <div class="bet-number">2</div>
                            <div class="bet-selection">{bet2_text}</div>
                            <div class="{odds2_class}">{row['team2_odds']}</div>
                            <img src="{self.get_book_logo(row['team2_book'])}" alt="{row['team2_book']}" class="book-logo">
                            <div class="stake-amount">${row['team2_stake']:.0f}</div>
                            <a href="{row['team2_link']}" target="_blank" class="bet-button">BET ↗</a>
                        </div>
                    </td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        return html
    
    def get_book_logo(self, bookmaker):
        """Return the appropriate logo URL for each bookmaker"""
        # You'll need to set up proper paths to your logo images
        book_logos = {
            'fanduel': '/static/images/fanduel-logo.png',
            'draftkings': '/static/images/draftkings-logo.png',
            'betmgm': '/static/images/betmgm-logo.png',
            'caesars': '/static/images/caesars-logo.png',
            'betrivers': '/static/images/betrivers-logo.png',
            'pinnacle': '/statoc/images/pinnacle-logo.png'
        }
        return book_logos.get(bookmaker.lower(), '/static/images/default-logo.png')

# Assume you have a function to get the opportunities data
def get_data():
    with open('key.txt', 'r') as file:
        api_key = file.read().strip()
    
    arbitrage_finder = OddsArbitrageFinder(api_key)
    arbitrage_table = arbitrage_finder.generate_arbitrage_table()
    return arbitrage_table, arbitrage_finder.all_plus_ev


# Initialize the opportunities generator
opportunities_generator = OpportunitiesGenerator()

@app.route('/')
def index():
    # Get the data
    arbitrage_table, plus_ev_data = get_data()
    
    # Initialize generator
    opportunities_generator = OpportunitiesGenerator()
    
    # Generate HTML components
    arb_cards_html = opportunities_generator.generate_arbitrage_cards(arbitrage_table)
    plus_ev_cards_html = opportunities_generator.generate_plus_ev_cards(plus_ev_data)
    bookmaker_filter_html = opportunities_generator.generate_bookmaker_filter()
    
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>IcyPicks</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                :root {
                    --primary-bg: #1a1e2d;
                    --secondary-bg: #242b3d;
                    --text-primary: #ffffff;
                    --text-secondary: #8b8f9a;
                    --accent-green: #4cd964;
                    --profit-green: #1cb954;
                    --button-green: #2c4c3b;
                }

                body {
                    font-family: 'Consolas', 'Monaco', monospace;
                    margin: 0;
                    padding: 16px;
                    background-color: var(--primary-bg);
                    color: var(--text-primary);
                    min-width: 1000px;
                }
                                  
                .opportunities-table {
                    width: 100%;
                    max-width: 1400px; /* Limit max width */
                    border-spacing: 0 4px;
                    margin: 0 auto; /* Center the table */
                }
                                  
                .table-header {
                    color: var(--text-secondary);
                    font-size: 0.85rem;
                    text-align: left;
                    padding: 8px 12px;
                    font-weight: normal;
                }

                .opportunity-row {
                    background-color: var(--secondary-bg);
                }
                
                .opportunity-row > td {
                    padding: 16px 12px; /* Increased vertical padding */
                }

                .profit-cell {
                    color: var(--profit-green);
                    font-size: 0.9rem;
                    width: 80px;
                    vertical-align: middle;
                }
                                  
                .profit-badge {
                    width: 48px;
                    font-size: 0.6rem;
                    color: var(--accent-green);
                    font-weight: 200;
                }
                                  
                .game-cell {
                    width: 300px;
                    vertical-align: middle;
                }

                .game-details {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }
                                  
                .game-info {
                    width: 300px;
                    padding: 0 16px;
                }

                

                .game-title {
                    font-weight: 500;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
               

                .bets-container {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }


                .bet-number {
                    width: 24px;
                    color: var(--text-secondary);
                }

                .bet-details {
                    display: flex; /* Changed from grid to flex */
                    align-items: center;
                    gap: 12px;
                    width: 100%;
                }

                .book-logo {
                    width: 24px;
                    height: 24px;
                    border-radius: 4px;
                    background-color: white;
                    padding: 2px;
                }

                .bet-selection {
                    white-space: normal; /* Allow text to wrap */
                    line-height: 1.3;
                    min-height: 20px;
                }

                .bet-odds {
                    width: 80px;
                    text-align: right;
                }
                                  
            
                .odds-positive {
                    color: var(--accent-green);
                }

                .odds-negative {
                    color: #ff3b30;
                }

                .stake-info {
                    width: 60px;
                    text-align: right;
                }
                                  
                .stake-amount {
                    color: var(--text-secondary);
                    text-align: right;
                }

                .bet-button {
                    background-color: var(--button-green);
                    color: var(--text-primary);
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    text-decoration: none;
                    font-size: 0.85rem;
                    text-align: center;
                    display: inline-block;
                }

                .bet-button:hover {
                    filter: brightness(1.2);
                }

                .bet-button.green {
                    background-color: var(--button-green);
                }

               

                .filters {
                    background-color: var(--secondary-bg);
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 16px;
                }

                .filter-group {
                    display: flex;
                    gap: 12px;
                    flex-wrap: wrap;
                }

                .filter-checkbox {
                    background-color: rgba(255, 255, 255, 0.05);
                    padding: 8px 12px;
                    border-radius: 6px;
                    cursor: pointer;
                }

                .filter-checkbox:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }

                .tabs {
                    display: flex;
                    gap: 8px;
                    margin-bottom: 16px;
                }

                .tab-button {
                    background-color: var(--secondary-bg);
                    border: none;
                    color: var(--text-primary);
                    padding: 12px 24px;
                    border-radius: 8px;
                    cursor: pointer;
                }

                .tab-button.active {
                    background-color: var(--accent-green);
                }

                .tab-content {
                    display: none;
                }

                .tab-content.active {
                    display: block;
                }

                .no-opportunities {
                    text-align: center;
                    padding: 24px;
                    color: var(--text-secondary);
                }
                .opportunities-wrapper {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 0 16px;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                

                .profit-badge {
                    font-size: 1.1rem;
                    font-weight: 500;
                }
                                  
                .profit-positive {
                    color: var(--accent-green);
                }

                .profit-negative {
                    color: #ff3b30;  /* Red color for negative profit */
                }

                .market-type {
                    color: #9f7aea;
                    width: 180px;
                    vertical-align: middle;
                    padding-left: 24px;
                    padding-right: 24px;
                }

                .game-info {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }

                .game-time {
                    color: var(--text-secondary);
                    font-size: 0.8rem;
                }

                .game-title {
                    font-weight: 500;
                }

                .game-league {
                    color: var(--text-secondary);
                    font-size: 0.8rem;
                }

                .bets-cell {
                    vertical-align: middle;
                }

                .bets-container {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                
                .bet-row {
                    display: grid;
                    grid-template-columns: 20px minmax(200px, 300px) 80px 40px 80px 100px 40px; /* Added column for calculator */
                    align-items: center;
                    gap: 12px;
                    min-height: 40px; /* Increased minimum height */
                    height: auto; /* Allow height to grow */
                }

                .bet-number {
                    color: var(--text-secondary);
                }


                .bet-odds {
                    font-weight: 600;
                    text-align: right;
                }

                .book-logo {
                    width: 24px;
                    height: 24px;
                    border-radius: 4px;
                    background-color: white;
                    padding: 2px;
                }

                .stake-info {
                    color: var(--text-secondary);
                    font-size: 0.9rem;
                    text-align: right;
                }

                .calculator {
                    background-color: var(--secondary-bg);
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }

                .calc-title {
                    color: var(--text-primary);
                    margin-bottom: 20px;
                    font-size: 1.5em;
                }

                .input-group {
                    margin-bottom: 15px;
                }

                .calculator label {
                    display: block;
                    margin-bottom: 5px;
                    font-weight: bold;
                    color: var(--text-primary);
                }

                .calculator input {
                    width: 100%;
                    padding: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                    background-color: rgba(255, 255, 255, 0.05);
                    color: var(--text-primary);
                }

                .calculator input::placeholder {
                    color: var(--text-secondary);
                }

                .results {
                    margin-top: 20px;
                    padding: 15px;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 4px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    color: var(--text-primary);
                }

                .result-row {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 10px;
                    padding: 8px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                }

                .result-row:last-child {
                    border-bottom: none;
                }

                .result-label {
                    font-weight: bold;
                    color: var(--text-secondary);
                }

                .profit-section {
                    background-color: rgba(76, 217, 100, 0.1);
                    padding: 15px;
                    border-radius: 4px;
                    margin-top: 15px;
                }

                .calculator button {
                    width: 100%;
                    padding: 10px;
                    background-color: var(--button-green);
                    color: var(--text-primary);
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 0.85rem;
                }

                .calculator button:hover {
                    filter: brightness(1.2);
                }
                                  
                .refresh-button {
                    background-color: var(--button-green);
                    color: var(--text-primary);
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 0.9rem;
                }

                .refresh-button:hover {
                    filter: brightness(1.2);
                }

                .refresh-icon {
                    display: inline-block;
                    font-size: 1.2rem;
                }

                .refresh-button.loading .refresh-icon {
                    animation: spin 1s linear infinite;
                }

                .loading-overlay {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background-color: rgba(26, 30, 45, 0.8);
                    justify-content: center;
                    align-items: center;
                    z-index: 1000;
                }

                .loading-spinner {
                    width: 50px;
                    height: 50px;
                    border: 3px solid transparent;
                    border-radius: 50%;
                    border-top-color: var(--accent-green);
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    from {
                        transform: rotate(0deg);
                    }
                    to {
                        transform: rotate(360deg);
                    }
                }
                
            </style>
        </head>
        <body>
            <div class="container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h1 style="color: var(--text-primary); margin: 0;">IcyPicks</h1>
                    <button id="refreshButton" class="refresh-button">
                        <span class="refresh-icon">↻</span>
                        Refresh
                    </button>
                </div>
                <div id="loadingOverlay" class="loading-overlay">
                    <div class="loading-spinner"></div>
                </div>
                {{ bookmaker_filter_html | safe }}
                
                <div class="tabs">
                    <button class="tab-button" data-tab="promos">Promos</button>
                    <button class="tab-button active" data-tab="arbitrage">Arbitrage</button>
                    <button class="tab-button" data-tab="plus-ev">+EV Bets</button>
                </div>
                                  
                <div id="promos" class="tab-content">
                    <div class="calculators-container" style="display: flex; gap: 20px; justify-content: center;">
                        <div style="width: 600px;">
                            <h2 class="calc-title">Initial Risk-Free Bet Hedge</h2>
                            <div class="calculator">
                                <div class="input-group">
                                    <label for="odds1">Odds 1 (+)</label>
                                    <input type="number" id="odds1" placeholder="e.g., 200">
                                </div>
                                
                                <div class="input-group">
                                    <label for="odds2">Odds 2 (-)</label>
                                    <input type="number" id="odds2" placeholder="e.g., -200">
                                </div>
                                
                                <div class="input-group">
                                    <label for="bonusAmount">Bonus Amount ($)</label>
                                    <input type="number" id="bonusAmount" placeholder="e.g., 500">
                                </div>
                                
                                <div class="input-group">
                                    <label for="estimatedBonusValue">Estimated Bonus Value (%)</label>
                                    <input type="number" id="estimatedBonusValue" placeholder="e.g., 60">
                                </div>
                                
                                <button onclick="calculateRiskFree()">Calculate Initial Hedge</button>
                                
                                <div class="results" id="riskFreeResults"></div>
                            </div>
                        </div>

                        <div style="width: 600px;">
                            <h2 class="calc-title">Bonus Bet Hedge</h2>
                            <div class="calculator">
                                  
                                <div class="input-group">
                                    <label for="bonusOddsPlus">Odds 1 (+)</label>
                                    <input type="number" id="bonusOddsPlus" placeholder="e.g., 200">
                                </div>
                                
                                <div class="input-group">
                                    <label for="bonusOddsMinus">Odds 2 (-)</label>
                                    <input type="number" id="bonusOddsMinus" placeholder="e.g., -200">
                                </div>
                                  
                                <div class="input-group">
                                    <label for="bonusBetSize">Bonus Bet Size ($)</label>
                                    <input type="number" id="bonusBetSize" placeholder="e.g., 500">
                                </div>
                                
                                
                                
                                <button onclick="calculateBonus()">Calculate Bonus Bet Hedge</button>
                                
                                <div class="results" id="bonusResults"></div>
                            </div>
                        </div>
                    </div>
                </div>
                                  
                <div id="arbitrage" class="tab-content active">
                    {{ arb_cards_html | safe }}
                </div>
                
                <div id="plus-ev" class="tab-content">
                    {{ plus_ev_cards_html | safe }}
                </div>
            </div>

            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    const refreshButton = document.getElementById('refreshButton');
                    const loadingOverlay = document.getElementById('loadingOverlay');
                    
                    // Function to refresh data
                    async function refreshData() {
                        refreshButton.classList.add('loading');
                        loadingOverlay.style.display = 'flex';
                        
                        try {
                            const response = await fetch(window.location.href);
                            const html = await response.text();
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(html, 'text/html');
                            
                            const arbContent = doc.querySelector('#arbitrage');
                            if (arbContent) {
                                document.querySelector('#arbitrage').innerHTML = arbContent.innerHTML;
                            }
                            
                            const evContent = doc.querySelector('#plus-ev');
                            if (evContent) {
                                document.querySelector('#plus-ev').innerHTML = evContent.innerHTML;
                            }
                            
                            const filterEvent = new Event('change');
                            document.querySelector('.book-filter').dispatchEvent(filterEvent);
                            
                        } catch (error) {
                            console.error('Error refreshing data:', error);
                        } finally {
                            refreshButton.classList.remove('loading');
                            loadingOverlay.style.display = 'none';
                        }
                    }
                    
                    // Refresh button click handler
                    refreshButton.addEventListener('click', refreshData);
                    
                    // Auto refresh every hour instead of every minute
                    setInterval(refreshData, 3600000);            

                    // Tab switching
                    document.querySelectorAll('.tab-button').forEach(button => {
                        button.addEventListener('click', function() {
                            document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
                            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                            
                            this.classList.add('active');
                            document.getElementById(this.dataset.tab).classList.add('active');
                        });
                    });

                    // Bookmaker filtering
                    document.querySelectorAll('.book-filter').forEach(checkbox => {
                        checkbox.addEventListener('change', function() {
                            const selectedBooks = Array.from(document.querySelectorAll('.book-filter:checked'))
                                .map(cb => cb.value.toLowerCase());
                            
                            document.querySelectorAll('.opportunity-row').forEach(row => {
                                const bookLinks = row.querySelectorAll('.book-logo');
                                const bookNames = Array.from(bookLinks).map(link => 
                                    link.alt.toLowerCase().trim()
                                );
                                
                                const shouldShow = bookNames.every(book => 
                                    selectedBooks.includes(book)
                                );
                                row.style.display = shouldShow ? '' : 'none';
                            });
                        });
                    });

                    
                });
                                  
                function calculateRiskFree() {
                    const odds1 = parseFloat(document.getElementById('odds1').value);
                    const odds2 = parseFloat(document.getElementById('odds2').value);
                    const bonusAmount = parseFloat(document.getElementById('bonusAmount').value);
                    const estimatedBonusValue = parseFloat(document.getElementById('estimatedBonusValue').value);

                    const bonusValueDollars = (bonusAmount * estimatedBonusValue) / 100;
                    const bet1Amount = bonusAmount;
                    const bet1Payout = bet1Amount * (1 + odds1/100);
                    const bet2Amount = (bet1Payout - bonusValueDollars) / (1 - 100/odds2);
                    const bet2TotalPayout = bet2Amount * (1 - 100/odds2);
                    const profitIfBet1Wins = bet1Payout - bet1Amount - bet2Amount;
                    const profitIfBet2Wins = bet2TotalPayout - bet2Amount - bet1Amount + bonusValueDollars;

                    document.getElementById('riskFreeResults').innerHTML = `
                        <div class="result-row">
                            <span class="result-label">Estimated Bonus Value:</span>
                            <span>$${bonusValueDollars.toFixed(2)}</span>
                        </div>
                        <div class="result-row">
                            <span class="result-label">Bet Amount 1:</span>
                            <span>$${bet1Amount.toFixed(2)}</span>
                        </div>
                        <div class="result-row">
                            <span class="result-label">Bet Amount 2:</span>
                            <span>$${bet2Amount.toFixed(2)}</span>
                        </div>
                        <div class="profit-section">
                            <h3>Profit Scenarios</h3>
                            <div class="result-row">
                                <span class="result-label">If Bet 1 (+${odds1}) wins:</span>
                                <span>$${profitIfBet1Wins.toFixed(2)}</span>
                            </div>
                            <div class="result-row">
                                <span class="result-label">If Bet 2 (${odds2}) wins:</span>
                                <span>$${profitIfBet2Wins.toFixed(2)} (includes bonus value)</span>
                            </div>
                        </div>
                    `;
                }

                function calculateBonus() {
                    const bonusSize = parseFloat(document.getElementById('bonusBetSize').value);
                    const plusOdds = parseFloat(document.getElementById('bonusOddsPlus').value);
                    const minusOdds = parseFloat(document.getElementById('bonusOddsMinus').value);

                    if (!bonusSize || !plusOdds || !minusOdds || plusOdds <= 0 || minusOdds >= 0) {
                        alert("Please fill in all fields correctly. Plus odds must be positive, minus odds must be negative!");
                        return;
                    }

                    const plusOddsDecimal = 1 + plusOdds / 100;
                    const minusOddsDecimal = 1 - 100 / minusOdds;
                    const bonusBetProfit = bonusSize * plusOddsDecimal - bonusSize;
                    const hedgeBet = bonusBetProfit / minusOddsDecimal;
                    const guaranteedProfit = bonusSize * plusOddsDecimal - bonusSize - hedgeBet;

                    document.getElementById('bonusResults').innerHTML = `
                        <div class="result-row">
                            <span class="result-label">Place bonus bet of:</span>
                            <span>$${bonusSize.toFixed(2)} on +${plusOdds}</span>
                        </div>
                        <div class="result-row">
                            <span class="result-label">Place hedge bet of:</span>
                            <span>$${hedgeBet.toFixed(2)} on ${minusOdds}</span>
                        </div>
                        <div class="profit-section">
                            <div class="result-row">
                                <span class="result-label">Guaranteed Profit:</span>
                                <span>$${guaranteedProfit.toFixed(2)}</span>
                            </div>
                        </div>
                    `;
                }             
                
            </script>
        </body>
        </html>
    """, arb_cards_html=arb_cards_html, plus_ev_cards_html=plus_ev_cards_html, bookmaker_filter_html=bookmaker_filter_html)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)