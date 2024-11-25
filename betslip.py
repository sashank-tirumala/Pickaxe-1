class BetslipURLGenerator:
    """
    Utility class to generate betslip URLs for different sportsbooks
    """
    
    @staticmethod
    def generate_betrivers_url(event_id, market_id, outcome_id, state='md'):
        """Generate BetRivers betslip URL"""
        return f"https://{state}.betrivers.com/?page=sportsbook#event/{event_id}?betsource=direct&market={market_id}&outcome={outcome_id}"
    
    @staticmethod
    def generate_fanduel_url(event_id, market_id, outcome_id, state='md'):
        """Generate FanDuel betslip URL"""
        return f"https://sportsbook.fanduel.com/{state}/selection/{event_id}-{market_id}?btag={outcome_id}"
    
    @staticmethod
    def generate_betmgm_url(event_id, market_id, outcome_id, state='md'):
        """Generate BetMGM betslip URL"""
        return f"https://sports.{state}.betmgm.com/en/sports/event/{event_id}?market={market_id}&selection={outcome_id}"
    
    @staticmethod
    def generate_caesars_url(event_id, market_id, outcome_id, state='md'):
        """Generate Caesars betslip URL"""
        return f"https://sportsbook.caesars.com/us/{state}/bet?id={event_id}&market={market_id}&selection={outcome_id}"
    
    @staticmethod
    def generate_draftkings_url(event_id, market_id, outcome_id, state='md'):
        """Generate DraftKings betslip URL"""
        return f"https://sportsbook.draftkings.com/{state}/event/{event_id}?category={market_id}&subcategory={outcome_id}"

    @classmethod
    def parse_existing_url(cls, url):
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