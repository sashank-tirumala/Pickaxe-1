import requests
import pandas as pd
from datetime import datetime, timezone
import time
import json
import logging


class OddsArbitrageFinder:  
    def __init__(self, api_key, state='md'):
        self.api_key = api_key
        self.state = state.lower()
        self.base_url = "https://api.the-odds-api.com/v4/sports"
        self.sports = [
            'americanfootball_ncaaf',
            'basketball_ncaab',
            'basketball_nba',
            'icehockey_nhl',
            'americanfootball_nfl',
            'basketball_wnba'
        ]
        
        self.featured_markets = ['h2h', 'spreads', 'totals']
        self.additional_markets = ['alternate_spreads', 'alternate_totals']
        
        # Add player prop markets by sport
        self.player_props = {
            'NFL': [
                'player_pass_yds', 'player_pass_tds', 'player_pass_completions',
                'player_rush_attempts', 'player_receptions', 'player_reception_yds'
            ],
            'NBA': [
                'player_points', 'player_rebounds', 'player_assists',
                'player_threes', 'player_points_rebounds_assists'
            ],
            'NHL': [
                'player_points', 'player_shots_on_goal', 'player_goals',
                'player_assists'
            ]
        }
        
        self.low_hold_threshold = 1.03
        
        self.regions = {
            'us': ['betmgm', 'betrivers', 'caesars', 'draftkings', 'fanduel'],
            'eu': ['pinnacle']
        }
    
    def get_player_props(self, sport, event_id):
        """Fetch player props for a specific event"""
        url = f"{self.base_url}/{sport}/events/{event_id}/odds"
        
        # Get the appropriate player props list based on sport
        sport_name = sport.upper().split('_')[1] if '_' in sport else sport.upper()
        prop_markets = self.player_props.get(sport_name, [])
        
        if not prop_markets:
            return []
        
        try:
            params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'markets': ','.join(prop_markets),
                'oddsFormat': 'decimal',
                'includeLinks': 'true'
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('bookmakers', [])
            
        except requests.exceptions.RequestException as e:
            if response.status_code != 404:
                print(f"Error fetching player props for event {event_id}: {e}")
        
        return []

    def process_player_props(self, bookmakers, sport):
        markets = {}
        
        # Filter for US books only
        us_books = [book.lower() for book in self.regions['us']]
        bookmakers = [bm for bm in bookmakers if bm['title'].lower() in us_books]
        
        sport_name = sport.upper().split('_')[1] if '_' in sport else sport.upper()
        prop_markets = self.player_props.get(sport_name, [])
        
        for bookmaker in bookmakers:
            for market in bookmaker['markets']:
                if market['key'] in prop_markets:
                    for outcome in market['outcomes']:
                        player_name = outcome.get('description', 'Unknown')
                        prop_type = market['key'].replace('player_', '')  # Remove 'player_' prefix
                        market_key = f"{market['key']}_{player_name}"
                        
                        if market_key not in markets:
                            markets[market_key] = []
                        
                        markets[market_key].append({
                            'bookmaker': bookmaker['title'],
                            'player': player_name,
                            'prop_type': prop_type,  # Store full prop type
                            'team': outcome['name'],
                            'price': outcome.get('price', 0),
                            'point': outcome.get('point'),
                            'link': bookmaker.get('link', '')
                        })
        
        return markets

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


    # Rest of the class implementation remains the same as it's sport-agnostic
    def decimal_to_american(self, decimal_odds):
        """
        Convert decimal odds to American odds format with proper error handling
        """
        try:
            # Handle invalid or edge case odds
            if decimal_odds <= 1:
                return -10000  # Return a very unfavorable line for invalid odds
                
            if decimal_odds >= 2:
                return round((decimal_odds - 1) * 100)
            else:
                return round(-100 / (decimal_odds - 1))
        except (ZeroDivisionError, ValueError):
            return -10000 

    def get_events(self, sport):
        """Fetch upcoming events for a sport"""
        url = f"{self.base_url}/{sport}/events"
        params = {
            'apiKey': self.api_key,
            'regions': 'us'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            current_time = datetime.now(timezone.utc)
            
            # Filter for upcoming games only
            return [
                event for event in data 
                if datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00')) > current_time
            ]
        except requests.exceptions.RequestException as e:
            print(f"Error fetching events for {sport}: {e}")
            return []

    def get_featured_odds(self, sport):
        """Fetch odds for featured markets with multiple regions"""
        current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        all_odds = []
        
        # Track seen events to avoid duplicates
        seen_events = set()
        
        # Fetch odds for each region
        for region, bookmakers in self.regions.items():
            url = f"{self.base_url}/{sport}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': region,
                'markets': ','.join(self.featured_markets),
                'oddsFormat': 'decimal',
                'commenceTimeFrom': current_time,
                'includeLinks': 'true'
            }
            
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                odds_data = response.json()
                
                for event in odds_data:
                    event_id = event['id']
                    
                    if event_id not in seen_events:
                        # For first occurrence of event, add all matching bookmakers
                        if bookmakers:
                            # Filter specific bookmakers if specified
                            event['bookmakers'] = [
                                b for b in event['bookmakers'] 
                                if b['title'].lower() in [bm.lower() for bm in bookmakers]
                            ]
                        all_odds.append(event)
                        seen_events.add(event_id)
                    else:
                        # For duplicate events, only add new bookmakers
                        existing_event = next(e for e in all_odds if e['id'] == event_id)
                        existing_books = {b['title'] for b in existing_event['bookmakers']}
                        
                        for bookmaker in event['bookmakers']:
                            if bookmakers and bookmaker['title'].lower() not in [bm.lower() for bm in bookmakers]:
                                continue
                            if bookmaker['title'] not in existing_books:
                                existing_event['bookmakers'].append(bookmaker)
                    
            except requests.exceptions.RequestException as e:
                print(f"Error fetching odds for {sport} in region {region}: {e}")
        
        return all_odds

    def get_event_odds(self, sport, event_id):
        """Fetch odds for additional markets for a specific event"""
        url = f"{self.base_url}/{sport}/events/{event_id}/odds"
        all_odds = []
        
        try:
            params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'markets': ','.join(self.additional_markets),
                'oddsFormat': 'decimal',
                'includeLinks': 'true'
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                bookmakers = data.get('bookmakers', [])
                all_odds.extend(bookmakers)
            
        except requests.exceptions.RequestException as e:
            if response.status_code != 404:
                print(f"Error fetching additional odds for event {event_id}: {e}")
        
        return all_odds

    def calculate_implied_probability(self, decimal_odds):
        """Convert decimal odds to implied probability"""
        return 1 / decimal_odds

    def calculate_kelly_percentage(self, prob_a, prob_b, odds_a, odds_b):
        """
        Calculate optimal bet sizing for arbitrage/low hold situations.
        Returns stake percentages that create equal profit regardless of outcome.
        """
        try:
            # For arbitrage/low hold, we want stakes that equalize potential profit
            # Let's say we bet $X on A at decimal odds_a and $Y on B at decimal odds_b
            # For equal profit: X * odds_a = Y * odds_b
            # And X + Y = 100 (total percentage)
            
            stake_a = (odds_b * 100) / (odds_a + odds_b)
            stake_b = (odds_a * 100) / (odds_a + odds_b)
            
            # Ensure stakes are valid
            if stake_a <= 0 or stake_b <= 0:
                return (50.0, 50.0)
                
            return (stake_a, stake_b)
            
        except (ZeroDivisionError, ValueError):
            return (50.0, 50.0)

    def process_markets(self, bookmakers, market_type):
        """Process markets from bookmakers data with proper handling of alternate lines"""
        markets = {}
        
        for bookmaker in bookmakers:
            for market in bookmaker['markets']:
                if market['key'] == market_type:
                    # For alternate markets, create unique keys including the point value
                    if market_type in ['alternate_spreads', 'alternate_totals']:
                        for outcome in market['outcomes']:
                            point = outcome.get('point')
                            if point is not None:
                                # For spreads, use the absolute value as key to group matching spreads
                                key_point = abs(float(point)) if 'spreads' in market_type else point
                                market_key = f"{market['key']}_{key_point}"
                                
                                if market_key not in markets:
                                    markets[market_key] = []
                                
                                markets[market_key].append({
                                    'bookmaker': bookmaker['title'],
                                    'team': outcome['name'],
                                    'price': outcome.get('price', 0),
                                    'point': point,
                                    'link': bookmaker.get('link', '')
                                })
                    else:
                        # Handle standard markets as before
                        market_key = f"{market['key']}_{market.get('point', '')}"
                        
                        if market_key not in markets:
                            markets[market_key] = []
                        
                        for outcome in market['outcomes']:
                            markets[market_key].append({
                                'bookmaker': bookmaker['title'],
                                'team': outcome['name'],
                                'price': outcome.get('price', 0),
                                'point': outcome.get('point', None),
                                'link': bookmaker.get('link', '')
                            })
        
        return markets
    
    def find_opportunities(self, game, additional_odds=None):
        opportunities = []
        # logging.basicConfig(level=logging.DEBUG)
        # logger = logging.getLogger('arbitrage_finder')
        
        us_books = self.regions['us']
        all_bookmakers = game['bookmakers']
        if additional_odds:
            all_bookmakers.extend(additional_odds)
        
        all_bookmakers = [bm for bm in all_bookmakers if bm['title'].lower() in [b.lower() for b in us_books]]

        for market_type in self.featured_markets + self.additional_markets:
            markets = self.process_markets(all_bookmakers, market_type)
            
            for market_key, market_odds in markets.items():
                odds_by_team = {}
                for odds in market_odds:
                    key = f"{odds['team']}_{odds.get('point', '')}"
                    if key not in odds_by_team or odds['price'] > odds_by_team[key]['price']:
                        odds_by_team[key] = odds
                
                processed_pairs = set()
                for key1, odds1 in odds_by_team.items():
                    for key2, odds2 in odds_by_team.items():
                        if key1 != key2:
                            if odds1['team'] == odds2['team']:
                                continue
                                
                            if (odds1['bookmaker'].lower() not in [b.lower() for b in us_books] or 
                                odds2['bookmaker'].lower() not in [b.lower() for b in us_books]):
                                continue
                                
                            if ('spreads' in market_type or 'alternate_spreads' in market_type):
                                point1 = float(odds1.get('point', 0) or 0)
                                point2 = float(odds2.get('point', 0) or 0)
                                
                                if point1 == 0 or point2 == 0:
                                    continue
                                    
                                if abs(point1 + point2) > 0.1:
                                    continue
                            
                            if ('totals' in market_type or 'alternate_totals' in market_type):
                                if odds1.get('point') != odds2.get('point'):
                                    continue
                            
                            pair_key = tuple(sorted([key1, key2]))
                            if pair_key not in processed_pairs:
                                processed_pairs.add(pair_key)
                                
                                prob1 = self.calculate_implied_probability(odds1['price'])
                                prob2 = self.calculate_implied_probability(odds2['price'])
                                total_prob = prob1 + prob2
                                
                                if total_prob <= self.low_hold_threshold:
                                    stake1, stake2 = self.calculate_kelly_percentage(
                                        prob1, prob2, odds1['price'], odds2['price']
                                    )
                                    
                                    hold_percentage = (total_prob - 1) * 100
                                    opportunity_type = 'Arbitrage' if total_prob < 1 else 'Low Hold'
                                    profit_percentage = round(((1 / total_prob) - 1) * 100, 2) if total_prob < 1 else 0
                                    
                                    opportunities.append({
                                        'sport': game['sport_title'],
                                        'opportunity_type': opportunity_type,
                                        'market_type': market_type,
                                        'market_point': odds1.get('point'),
                                        'game': f"{game['home_team']} vs {game['away_team']}",
                                        'commence_time': game['commence_time'],
                                        'team1_name': odds1['team'],
                                        'team1_book': odds1['bookmaker'],
                                        'team1_odds': self.decimal_to_american(odds1['price']),
                                        'team1_point': odds1.get('point'),
                                        'team1_stake': round(stake1, 2),
                                        'team1_link': odds1.get('link', ''),
                                        'team2_name': odds2['team'],
                                        'team2_book': odds2['bookmaker'],
                                        'team2_odds': self.decimal_to_american(odds2['price']),
                                        'team2_point': odds2.get('point'),
                                        'team2_stake': round(stake2, 2),
                                        'team2_link': odds2.get('link', ''),
                                        'hold_percentage': round(hold_percentage, 2),
                                        'profit_percentage': profit_percentage
                                    })
        
        # logger.info(f"Checking player props for {game['sport_key']} game: {game['home_team']} vs {game['away_team']}")
        player_props = self.get_player_props(game['sport_key'], game['id'])
        
        if player_props:
            prop_markets = self.process_player_props(player_props, game['sport_key'])
            
            for market_key, market_odds in prop_markets.items():
                prop_type = market_odds[0]['prop_type']
                player_name = market_odds[0]['player']
                prop_readable = self.get_prop_description(prop_type, game['sport_key'])
                
                # logger.info(f"Analyzing {prop_readable} prop for {player_name}")
                
                odds_by_outcome = {}
                for odds in market_odds:
                    key = f"{odds['team']}_{odds['bookmaker']}_{odds.get('point', '')}"
                    if key not in odds_by_outcome or odds['price'] > odds_by_outcome[key]['price']:
                        odds_by_outcome[key] = odds
                
                processed_pairs = set()
                for key1, odds1 in odds_by_outcome.items():
                    for key2, odds2 in odds_by_outcome.items():
                        if odds1['bookmaker'] == odds2['bookmaker']:
                            continue
                            
                        if key1 != key2 and odds1['point'] == odds2['point']:
                            if 'OVER' in odds1['team'].upper() and 'UNDER' in odds2['team'].upper():
                                pair_key = tuple(sorted([key1, key2]))
                                if pair_key not in processed_pairs:
                                    processed_pairs.add(pair_key)
                                    
                                    prob1 = self.calculate_implied_probability(odds1['price'])
                                    prob2 = self.calculate_implied_probability(odds2['price'])
                                    total_prob = prob1 + prob2
                                    
                                    # logger.debug(f"""
                                    #     Potential opportunity found:
                                    #     Player: {player_name}
                                    #     Prop: {prop_readable}
                                    #     Book1: {odds1['bookmaker']} {odds1['team']} {odds1['point']} @ {odds1['price']} (prob: {prob1:.4f})
                                    #     Book2: {odds2['bookmaker']} {odds2['team']} {odds2['point']} @ {odds2['price']} (prob: {prob2:.4f})
                                    #     Total probability: {total_prob:.4f}
                                    # """)
                                    
                                    if total_prob <= self.low_hold_threshold:
                                        stake1, stake2 = self.calculate_kelly_percentage(
                                            prob1, prob2, odds1['price'], odds2['price']
                                        )
                                        
                                        hold_percentage = (total_prob - 1) * 100
                                        opportunity_type = 'Arbitrage' if total_prob < 1 else 'Low Hold'
                                        profit_percentage = round(((1 / total_prob) - 1) * 100, 2) if total_prob < 1 else 0
                                        
                                        # if profit_percentage > 10:
                                        #     logger.warning(f"""
                                        #         Suspiciously high profit percentage ({profit_percentage}%)!
                                        #         Please verify this opportunity manually:
                                        #         {player_name} {prop_readable}
                                        #         {odds1['bookmaker']}: {odds1['team']} {odds1['point']} @ {odds1['price']}
                                        #         {odds2['bookmaker']}: {odds2['team']} {odds2['point']} @ {odds2['price']}
                                        #     """)
                                        
                                        prop_description = f"{player_name} - {prop_readable}"
                                        
                                        opportunities.append({
                                            'sport': game['sport_title'],
                                            'opportunity_type': opportunity_type,
                                            'market_type': 'player_prop',
                                            'prop_description': prop_description,
                                            'market_point': odds1['point'],
                                            'game': f"{game['home_team']} vs {game['away_team']}",
                                            'commence_time': game['commence_time'],
                                            'team1_name': f"{odds1['team']} ({odds1['point']})",
                                            'team1_book': odds1['bookmaker'],
                                            'team1_odds': self.decimal_to_american(odds1['price']),
                                            'team1_point': odds1['point'],
                                            'team1_stake': round(stake1, 2),
                                            'team1_link': odds1['link'],
                                            'team2_name': f"{odds2['team']} ({odds2['point']})",
                                            'team2_book': odds2['bookmaker'],
                                            'team2_odds': self.decimal_to_american(odds2['price']),
                                            'team2_point': odds2['point'],
                                            'team2_stake': round(stake2, 2),
                                            'team2_link': odds2['link'],
                                            'hold_percentage': round(hold_percentage, 2),
                                            'profit_percentage': profit_percentage
                                        })
        
        return opportunities

    # In the find_arbitrage method, replace the spread validation with this improved version:

    def find_arbitrage(self, game, additional_odds=None):
        """Find arbitrage opportunities in a single game with improved alternate market handling"""
        arbitrage_opportunities = []
        
        # Combine standard and additional bookmakers
        all_bookmakers = game['bookmakers']
        if additional_odds:
            all_bookmakers.extend(additional_odds)
    
        # Process each market type
        all_markets = self.featured_markets + self.additional_markets
        for market_type in all_markets:
            markets = self.process_markets(all_bookmakers, market_type)
            
            # Process each specific market (including each alternate line)
            for market_key, market_odds in markets.items():
                # Group odds by team and point combination
                odds_by_team = {}
                for odds in market_odds:
                    key = f"{odds['team']}_{odds.get('point', '')}"
                    if key not in odds_by_team or odds['price'] > odds_by_team[key]['price']:
                        odds_by_team[key] = odds
                
                # Find matching pairs for arbitrage
                processed_pairs = set()
                for key1, odds1 in odds_by_team.items():
                    for key2, odds2 in odds_by_team.items():
                        if key1 != key2:
                            # Skip if same team
                            if odds1['team'] == odds2['team']:
                                continue
                                
                            # Validate spread matching
                            if ('spreads' in market_type or 'alternate_spreads' in market_type):
                                point1 = float(odds1.get('point', 0) or 0)
                                point2 = float(odds2.get('point', 0) or 0)
                                
                                # Skip if points are not set
                                if point1 == 0 or point2 == 0:
                                    continue
                                    
                                # For spread bets, ensure the points are opposite and equal
                                if abs(point1 + point2) > 0.1:  # Use 0.1 to account for floating point precision
                                    # print(f"Checking spreads: {odds1['team']} {point1} vs {odds2['team']} {point2}")
                                    continue
                            
                            # Validate totals matching
                            if ('totals' in market_type or 'alternate_totals' in market_type):
                                if odds1.get('point') != odds2.get('point'):
                                    continue
                            
                            pair_key = tuple(sorted([key1, key2]))
                            if pair_key not in processed_pairs:
                                processed_pairs.add(pair_key)
                                
                                prob1 = self.calculate_implied_probability(odds1['price'])
                                prob2 = self.calculate_implied_probability(odds2['price'])
                                
                                if prob1 + prob2 < 1:
                                    stake1, stake2 = self.calculate_kelly_percentage(
                                        prob1, prob2, odds1['price'], odds2['price']
                                    )
                                    
                                    arbitrage_opportunities.append({
                                        'sport': game['sport_title'],
                                        'market_type': 'alternate_spreads' if 'alternate_spreads' in market_key 
                                                       else 'alternate_totals' if 'alternate_totals' in market_key
                                                       else market_key.split('_')[0],
                                        'market_point': odds1.get('point'),
                                        'game': f"{game['home_team']} vs {game['away_team']}",
                                        'commence_time': game['commence_time'],
                                        'team1_name': odds1['team'],
                                        'team1_book': odds1['bookmaker'],
                                        'team1_odds': self.decimal_to_american(odds1['price']),
                                        'team1_point': odds1.get('point'),
                                        'team1_stake': round(stake1, 2),
                                        'team1_link': odds1.get('link', ''),  # Add link for first bet
                                        'team2_name': odds2['team'],
                                        'team2_book': odds2['bookmaker'],
                                        'team2_odds': self.decimal_to_american(odds2['price']),
                                        'team2_point': odds2.get('point'),
                                        'team2_stake': round(stake2, 2),
                                        'team2_link': odds2.get('link', ''),  # Add link for second bet
                                        'profit_percentage': round(((1 / (prob1 + prob2)) - 1) * 100, 2)
                                    })
    
        return arbitrage_opportunities

    def generate_arbitrage_table(self):
        print("Analyzing...")
        all_opportunities = []
        all_odds_data = []
        
        for sport in self.sports:
            featured_odds = self.get_featured_odds(sport)
            
            for game in featured_odds:
                odds_data = self.collect_all_odds(game)
                all_odds_data.extend(odds_data)
                
                additional_odds = self.get_event_odds(sport, game['id'])
                opportunities = self.find_opportunities(game, additional_odds)
                all_opportunities.extend(opportunities)
        
        self.all_odds_data = all_odds_data
        
        if all_opportunities:
            df = pd.DataFrame(all_opportunities)
            df['timestamp'] = datetime.now(timezone.utc)
            
            # Update columns list to include prop_description
            columns = [
                'opportunity_type', 'hold_percentage', 
                'sport', 'market_type', 'prop_description',  # Added prop_description
                'market_point', 'game', 'commence_time',
                'team1_name', 'team1_book', 'team1_odds', 'team1_point', 'team1_stake', 'team1_link',
                'team2_name', 'team2_book', 'team2_odds', 'team2_point', 'team2_stake', 'team2_link',
                'profit_percentage', 'timestamp'
            ]
            return df[columns]
        else:
            # Make sure empty DataFrame has same columns
            return pd.DataFrame(columns=[
                'opportunity_type', 'hold_percentage', 
                'sport', 'market_type', 'prop_description',  # Added prop_description
                'market_point', 'game', 'commence_time',
                'team1_name', 'team1_book', 'team1_odds', 'team1_point', 'team1_stake', 'team1_link',
                'team2_name', 'team2_book', 'team2_odds', 'team2_point', 'team2_stake', 'team2_link',
                'profit_percentage', 'timestamp'
            ])

    def collect_all_odds(self, game):
        """Collect and organize all odds for the odds screen"""
        odds_data = []
        
        # Combine standard and additional bookmakers
        all_bookmakers = game['bookmakers']
        
        # Process each market type
        for market_type in self.featured_markets:
            markets = self.process_markets(all_bookmakers, market_type)
            
            for market_key, market_odds in markets.items():
                # Create a standardized format for each market
                market_data = {
                    'sport': game['sport_title'],
                    'game': f"{game['home_team']} vs {game['away_team']}",
                    'commence_time': game['commence_time'],
                    'market_type': market_type,
                    'market_point': None,
                    'outcomes': []
                }
                
                # Group odds by bookmaker
                odds_by_bookmaker = {}
                for odds in market_odds:
                    book = odds['bookmaker']
                    if book not in odds_by_bookmaker:
                        odds_by_bookmaker[book] = []
                    odds_by_bookmaker[book].append({
                        'team': odds['team'],
                        'price': odds['price'],
                        'point': odds.get('point'),
                        'american_odds': self.decimal_to_american(odds['price']),
                        'link': odds.get('link', '')
                    })
                
                market_data['books'] = odds_by_bookmaker
                odds_data.append(market_data)
        
        return odds_data

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
            <table>
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
                    <td><a href="{row['team1_link']}" target="_blank">{row['team1_book']}</a></td>
                    <td class="{odds1_class}">{row['team1_odds']}</td>
                    <td class="stake">{row['team1_stake']:.1f}%</td>
                    <td>{row['team2_name']} {team2_point}</td>
                    <td><a href="{row['team2_link']}" target="_blank">{row['team2_book']}</a></td>
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
    
    def remove_vig(self, odds1, odds2):
        if odds1 < 0:
            dec1 = 1 - (100 / odds1)
        else:
            dec1 = (odds1 / 100) + 1
            
        if odds2 < 0:
            dec2 = 1 - (100 / odds2)
        else:
            dec2 = (odds2 / 100) + 1
        
        prob1 = 1 / dec1
        prob2 = 1 / dec2
        
        total_prob = prob1 + prob2
        fair_prob1 = prob1 / total_prob
        fair_prob2 = prob2 / total_prob
        
        fair_dec1 = 1 / fair_prob1
        fair_dec2 = 1 / fair_prob2
        
        fair_american1 = self.decimal_to_american(fair_dec1)
        fair_american2 = self.decimal_to_american(fair_dec2)
        
        return fair_american1, fair_american2

    def get_fair_odds(self, game_data):
        if 'h2h' not in game_data['markets']:
            return {}
            
        pinnacle_odds = None
        for market in game_data['markets'].values():
            if 'pinnacle' in market['books']:
                pinnacle_odds = sorted(market['books']['pinnacle'], key=lambda x: x['team'])
                break
                
        if not pinnacle_odds or len(pinnacle_odds) != 2:
            return {}
            
        fair_odds1, fair_odds2 = self.remove_vig(
            pinnacle_odds[0]['american_odds'],
            pinnacle_odds[1]['american_odds']
        )
        
        return {
            pinnacle_odds[0]['team']: fair_odds1,
            pinnacle_odds[1]['team']: fair_odds2
        }

    def generate_odds_screen_html(self, all_odds_data):
        if not all_odds_data:
            return """<div class="no-odds">No odds data available</div>"""
        
        sports = sorted(set(odds['sport'] for odds in all_odds_data))
        
        html = """
        <div class="odds-screen">
            <div class="filters">
                <select id="sportFilter" class="filter-select">
                    <option value="all">All Sports</option>"""
        
        for sport in sports:
            html += f'<option value="{sport}">{sport}</option>'
        
        html += """
                </select>
                <select id="betTypeFilter" class="filter-select">
                    <option value="h2h">Moneyline</option>
                    <option value="spreads">Spread</option>
                    <option value="totals">Total</option>
                </select>
            </div>
            <div class="odds-table-container">
                <table class="odds-table">
                    <thead>
                        <tr>
                            <th class="game-info" style="min-width:160px;">Game Info</th>
                            <th class="fair-odds-column">Fair Odds</th>"""
        
        all_bookmakers = set()
        for odds in all_odds_data:
            for book in odds['books'].keys():
                if book.lower() in [b.lower() for b in self.regions['us']]:
                    all_bookmakers.add(book)
        
        sorted_bookmakers = sorted(all_bookmakers)
        
        for book in sorted_bookmakers:
            html += f'<th class="book-column">{book}</th>'
        
        html += """
                        </tr>
                    </thead>
                    <tbody>"""
        
        games = {}
        for odds in all_odds_data:
            game_key = f"{odds['game']}_{odds['commence_time']}"
            if game_key not in games:
                games[game_key] = {
                    'sport': odds['sport'],
                    'game': odds['game'],
                    'time': odds['commence_time'],
                    'markets': {}
                }
            games[game_key]['markets'][odds['market_type']] = odds
        
        sorted_games = dict(sorted(games.items(), key=lambda x: x[1]['time']))
        
        for game_key, game_data in sorted_games.items():
            game_datetime = datetime.fromisoformat(game_data['time'].replace('Z', '+00:00'))
            game_date = game_datetime.strftime('%m/%d')
            game_time = game_datetime.strftime('%I:%M %p')
            
            fair_odds = self.get_fair_odds(game_data)
            
            markets_json = json.dumps({
                market_type: {
                    'books': game_data['markets'][market_type]['books']
                } for market_type in game_data['markets']
            })
            
            home_team = game_data['game'].split(' vs ')[0].split()[-1]
            away_team = game_data['game'].split(' vs ')[1].split()[-1]
            
            html += f"""
                <tr class="game-row" 
                    data-sport="{game_data['sport']}" 
                    data-game-key="{game_key}"
                    data-markets='{markets_json}'>
                    <td class="game-info">
                        <div class="game-datetime">
                            <span class="game-date">{game_date}</span>
                            <span class="game-time">{game_time}</span>
                        </div>
                        <div class="game-name">{away_team} @ {home_team}</div>
                    </td>
                    <td class="fair-odds-cell">"""
            
            if 'h2h' in game_data['markets']:
                odds = sorted(game_data['markets']['h2h']['books'].get(list(game_data['markets']['h2h']['books'].keys())[0], []), key=lambda x: x['team'])
                for outcome in odds:
                    fair_odd = fair_odds.get(outcome['team'])
                    if fair_odd:
                        odds_class = 'odds-negative' if fair_odd < 0 else 'odds-positive'
                        html += f"""
                            <div class="team-odds">
                                <span class="odds {odds_class} fair-odds-value">
                                    {fair_odd}
                                </span>
                            </div>"""
                    else:
                        html += '<div class="team-odds">-</div>'
            else:
                html += '-'
                
            html += '</td>'
            
            for book in sorted_bookmakers:
                html += f'<td class="odds-cell" data-book="{book}">'
                
                if 'h2h' in game_data['markets'] and book in game_data['markets']['h2h']['books']:
                    odds = sorted(game_data['markets']['h2h']['books'][book], key=lambda x: x['team'])
                    for outcome in odds:
                        odds_class = 'odds-negative' if outcome['american_odds'] < 0 else 'odds-positive'
                        
                        fair_odd = fair_odds.get(outcome['team'])
                        if fair_odd:
                            if (fair_odd < 0 and outcome['american_odds'] > fair_odd) or \
                            (fair_odd > 0 and outcome['american_odds'] > fair_odd):
                                odds_class += ' value-odds'
                        
                        html += f"""
                            <div class="team-odds">
                                <a href="{outcome['link']}" class="odds {odds_class}" target="_blank">
                                    {outcome['american_odds']}
                                </a>
                            </div>"""
                else:
                    html += '-'
                
                html += '</td>'
            
            html += '</tr>'
        
        html += """
                    </tbody>
                </table>
            </div>
        </div>
        <style>
            .odds-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }
            .odds-table th, .odds-table td {
                padding: 6px;
                text-align: center;
                border: 1px solid #ddd;
                white-space: nowrap;
            }
            .game-info {
                text-align: left;
                background: #f8f9fa;
                position: sticky;
                left: 0;
                z-index: 2;
                padding: 8px;
            }
            .book-column {
                min-width: 70px;
                font-size: 12px;
                position: sticky;
                top: 0;
                background: #f5f5f5;
                z-index: 1;
            }
            .game-datetime {
                display: flex;
                gap: 8px;
                align-items: center;
                margin-bottom: 2px;
            }
            .game-date {
                font-weight: bold;
                color: #2c5282;
            }
            .game-time {
                font-size: 11px;
                color: #666;
            }
            .game-name {
                font-weight: 600;
                font-size: 13px;
            }
            .sport-name {
                font-size: 11px;
                color: #2c5282;
            }
            .odds-cell {
                padding: 4px 6px;
            }
            .team-odds {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 4px;
                padding: 2px;
            }
            .odds {
                font-weight: bold;
                text-decoration: none;
                font-size: 14px;
                padding: 2px 6px;
                border-radius: 3px;
            }
            .odds-negative { color: #dc3545; }
            .odds-positive { color: #28a745; }
            .point {
                font-size: 12px;
                color: #666;
                margin-right: 4px;
            }
            .filters {
                display: flex;
                gap: 8px;
                margin-bottom: 12px;
            }
            .filter-select {
                padding: 4px 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 12px;
            }
            .fair-odds-column {
                min-width: 70px;
                font-size: 12px;
                position: sticky;
                top: 0;
                background: #f5f5f5;
                z-index: 1;
                border-right: 2px solid #ddd;
            }
            .fair-odds-cell {
                background-color: #f8f9fa;
                border-right: 2px solid #ddd;
            }
            .fair-odds-value {
                font-style: italic;
                opacity: 0.9;
            }
            .value-odds {
                background-color: #c3e6cb;
                box-shadow: 0 0 0 1px #28a745;
            }
        </style>
        <script>
            document.getElementById('betTypeFilter').onchange = function() {
                const marketTypeMap = {
                    'h2h': 'h2h',
                    'spreads': 'spreads',
                    'totals': 'totals'
                };
                
                const marketType = marketTypeMap[this.value];
                const rows = document.querySelectorAll('.game-row');
                
                rows.forEach(row => {
                    try {
                        const markets = JSON.parse(row.getAttribute('data-markets'));
                        const oddsCells = row.querySelectorAll('td:not(.game-info):not(.fair-odds-cell)');
                        const fairOddsCell = row.querySelector('.fair-odds-cell');
                        if (fairOddsCell) {
                            fairOddsCell.style.display = marketType === 'h2h' ? '' : 'none';
                        }
                        
                        oddsCells.forEach(cell => {
                            const book = cell.getAttribute('data-book');
                            
                            if (markets[marketType] && markets[marketType].books && markets[marketType].books[book]) {
                                const outcomes = markets[marketType].books[book];
                                let html = '';
                                
                                outcomes.sort((a, b) => a.team.localeCompare(b.team));
                                
                                outcomes.forEach(outcome => {
                                    const oddsClass = outcome.american_odds < 0 ? 'odds-negative' : 'odds-positive';
                                    
                                    if (marketType === 'spreads') {
                                        const point = outcome.point;
                                        html += `
                                            <div class="team-odds">
                                                <span class="point">${point >= 0 ? '+' : ''}${point}</span>
                                                <a href="${outcome.link}" class="odds ${oddsClass}" target="_blank">
                                                    ${outcome.american_odds}
                                                </a>
                                            </div>`;
                                    } else if (marketType === 'totals') {
                                        const overUnder = outcome.team.toLowerCase().includes('over') ? 'O' : 'U';
                                        const point = outcome.point;
                                        html += `
                                            <div class="team-odds">
                                                <span class="point">${overUnder} ${point}</span>
                                                <a href="${outcome.link}" class="odds ${oddsClass}" target="_blank">
                                                    ${outcome.american_odds}
                                                </a>
                                            </div>`;
                                    } else {
                                        html += `
                                            <div class="team-odds">
                                                <a href="${outcome.link}" class="odds ${oddsClass}" target="_blank">
                                                    ${outcome.american_odds}
                                                </a>
                                            </div>`;
                                    }
                                });
                                
                                cell.innerHTML = html || '-';
                            } else {
                                cell.innerHTML = '-';
                            }
                        });
                    } catch (e) {
                        console.error('Error updating odds:', e);
                    }
                });
            };
            
            document.getElementById('sportFilter').onchange = function() {
                const sport = this.value;
                document.querySelectorAll('.game-row').forEach(row => {
                    row.style.display = (sport === 'all' || row.dataset.sport === sport) ? '' : 'none';
                });
            };
        </script>
        """
        
        return html
    
    def generate_html(self, df):
        """Generate HTML with both opportunities and odds screen tabs"""
        # Start with the basic HTML structure
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sports Betting Dashboard</title>
            <style>
                body { 
                    font-family: 'Consolas', 'Monaco', monospace;
                    padding: 30px;
                    background-color: #f8f9fa;
                    line-height: 1.4;
                }
                .container {
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    padding: 20px;
                    overflow-x: auto;
                    margin-bottom: 20px;
                }
                table { 
                    border-collapse: collapse; 
                    width: 100%;
                    margin: 0 auto;
                    font-size: 14px;
                }
                th, td { 
                    padding: 12px 8px;
                    text-align: left;
                    border: 1px solid #e0e0e0;
                }
                th { 
                    background-color: #f5f5f5; 
                    font-weight: bold;
                    position: sticky;
                    top: 0;
                    z-index: 1;
                    border-bottom: 2px solid #ddd;
                }
                tr:nth-child(even) { background-color: #f9f9f9; }
                tr:hover { background-color: #f5f5f5; }
                a { 
                    color: #2c5282;
                    text-decoration: none;
                    padding: 2px 4px;
                    border-radius: 3px;
                }
                a:hover { 
                    background-color: #edf2f7;
                    text-decoration: underline;
                }
                .arbitrage { background-color: #d4edda; }
                .arbitrage:hover { background-color: #c3e6cb; }
                .low-hold { background-color: #fff3cd; }
                .low-hold:hover { background-color: #ffeeba; }
                .type-badge {
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                    letter-spacing: 0.5px;
                }
                .arbitrage-badge { 
                    background-color: #28a745; 
                    color: white;
                }
                .low-hold-badge { 
                    background-color: #ffc107; 
                    color: black;
                }
                .profit-positive { 
                    color: #28a745;
                    font-weight: bold;
                }
                .profit-zero { color: #666; }
                .stake { color: #2c5282; }
                .odds-negative { color: #dc3545; }
                .odds-positive { color: #28a745; }
                .timestamp {
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                    text-align: right;
                }
                .tabs {
                    margin-bottom: 20px;
                }
                .tab-button {
                    padding: 10px 20px;
                    background: #f8f9fa;
                    border: none;
                    border-radius: 4px 4px 0 0;
                    cursor: pointer;
                    font-family: inherit;
                    font-size: 14px;
                    margin-right: 5px;
                }
                .tab-button.active {
                    background: white;
                    border-bottom: 2px solid #2c5282;
                }
                .tab-content {
                    display: none;
                }
                .tab-content.active {
                    display: block;
                }
                
                /* Odds screen specific styles */
                .odds-screen {
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .filters {
                    margin-bottom: 20px;
                }
                .filters select {
                    padding: 8px;
                    margin-right: 10px;
                    border-radius: 4px;
                    border: 1px solid #ddd;
                }
                .game-card {
                    border: 1px solid #eee;
                    margin-bottom: 20px;
                    border-radius: 4px;
                }
                .game-header {
                    padding: 10px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #eee;
                }
                .sport-badge {
                    display: inline-block;
                    padding: 2px 6px;
                    background: #2c5282;
                    color: white;
                    border-radius: 3px;
                    font-size: 12px;
                    margin-right: 10px;
                }
                .markets-container {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    padding: 20px;
                }
                .market-section {
                    border: 1px solid #eee;
                    border-radius: 4px;
                }
                .market-header {
                    padding: 8px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #eee;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <div class="tabs">
                <button class="tab-button active" onclick="showTab('opportunities')">Opportunities</button>
                <button class="tab-button" onclick="showTab('odds-screen')">Odds Screen</button>
            </div>
            
            <div id="opportunities" class="tab-content active">
                [OPPORTUNITIES_CONTENT]
            </div>
            
            <div id="odds-screen" class="tab-content">
                [ODDS_SCREEN_CONTENT]
            </div>
            
            <script>
                function showTab(tabId) {
                    // Hide all tabs
                    document.querySelectorAll('.tab-content').forEach(tab => {
                        tab.classList.remove('active');
                    });
                    document.querySelectorAll('.tab-button').forEach(button => {
                        button.classList.remove('active');
                    });
                    
                    // Show selected tab
                    document.getElementById(tabId).classList.add('active');
                    event.target.classList.add('active');
                }
            </script>
        </body>
        </html>
        """
        
        # Generate opportunities content
        opportunities_html = self.generate_opportunities_html(df)
        
        # Generate odds screen content
        odds_screen_html = self.generate_odds_screen_html(self.all_odds_data)
        
        # Replace placeholders
        html = html.replace('[OPPORTUNITIES_CONTENT]', opportunities_html)
        html = html.replace('[ODDS_SCREEN_CONTENT]', odds_screen_html)
        
        return html


def main():
    # Replace with your API key
    api_key = '1e926844efc2bdb47a3552415b65b3cd'
    
    arbitrage_finder = OddsArbitrageFinder(api_key)
    arbitrage_table = arbitrage_finder.generate_arbitrage_table()
    
    # Generate HTML
    html_content = arbitrage_finder.generate_html(arbitrage_table)
    
    # Save HTML file
    html_filename = "arbitrage_opportunities.html"
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"\nHTML results saved to {html_filename}")
    
    # Still save CSV for data analysis
    if not arbitrage_table.empty:
        csv_filename = "arbitrage_opportunities.csv"
        arbitrage_table.to_csv(csv_filename, index=False)
        print(f"CSV results saved to {csv_filename}")
    else:
        print("\nNo arbitrage opportunities found.")

if __name__ == "__main__":
    main()