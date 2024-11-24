class BetslipURLGenerator:
    """
    Utility class to generate betslip URLs for different sportsbooks
    """
    
    @staticmethod
    def generate_betrivers_url(market_id, selection_id, state='md'):
        """Generate BetRivers betslip URL"""
        # Format: https://md.betrivers.com/?page=sportsbook#event/1020832252?coupon=single|3575593386|
        return f"https://{state}.betrivers.com/?page=sportsbook#event/{market_id}?coupon=single|{selection_id}|"
    
    @staticmethod
    def generate_fanduel_url(market_id, selection_id, state='md'):
        """Generate FanDuel betslip URL"""
        # Format: https://account.md.sportsbook.fanduel.com/sportsbook/addToBetslip?marketId[0]=42.465617287&selectionId[0]=61449341
        return f"https://account.{state}.sportsbook.fanduel.com/sportsbook/addToBetslip?marketId[0]={market_id}&selectionId[0]={selection_id}"
    
    @staticmethod
    def generate_betmgm_url(event_id, selection_id, state='md'):
        """Generate BetMGM betslip URL"""
        # Format: https://sports.md.betmgm.com/en/sports/events/16627204/?options=-844684506&wm=7096743
        return f"https://sports.{state}.betmgm.com/en/sports/events/{event_id}/?options={selection_id}"
    
    @staticmethod
    def generate_caesars_url(selection_id, state='md'):
        """Generate Caesars betslip URL"""
        # Format: https://sportsbook.caesars.com/us/md/bet/betslip?selectionIds=8ad7a9db-fc30-3873-ba1a-0f9e5ab9d84e
        return f"https://sportsbook.caesars.com/us/{state}/bet/betslip?selectionIds={selection_id}"
    
    @staticmethod
    def generate_draftkings_url(event_id, outcome_id, state='md'):
        """Generate DraftKings betslip URL"""
        # Format: https://sportsbook.draftkings.com/event/30568752?outcomes=0QA222961856%2394388097_13L88808Q1-424241391Q20
        return f"https://sportsbook.draftkings.com/event/{event_id}?outcomes={outcome_id}"

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
                event_parts = parts[1].split('?coupon=single|')
                if len(event_parts) > 1:
                    params['market_id'] = event_parts[0]
                    params['selection_id'] = event_parts[1].rstrip('|')
            return 'betrivers', params
            
        elif 'fanduel.com' in url:
            if 'marketid[0]=' in url and 'selectionid[0]=' in url:
                market_id = url.split('marketid[0]=')[1].split('&')[0]
                selection_id = url.split('selectionid[0]=')[1].split('&')[0]
                params['market_id'] = market_id
                params['selection_id'] = selection_id
            return 'fanduel', params
            
        elif 'betmgm.com' in url:
            if '/events/' in url and 'options=' in url:
                event_id = url.split('/events/')[1].split('/?')[0]
                selection_id = url.split('options=')[1].split('&')[0]
                params['event_id'] = event_id
                params['selection_id'] = selection_id
            return 'betmgm', params
            
        elif 'caesars.com' in url:
            if 'selectionids=' in url:
                selection_id = url.split('selectionids=')[1].split('&')[0]
                params['selection_id'] = selection_id
            return 'caesars', params
            
        elif 'draftkings.com' in url:
            if '/event/' in url and 'outcomes=' in url:
                event_id = url.split('/event/')[1].split('?')[0]
                outcome_id = url.split('outcomes=')[1].split('&')[0]
                params['event_id'] = event_id
                params['outcome_id'] = outcome_id
            return 'draftkings', params
            
        return None, {}