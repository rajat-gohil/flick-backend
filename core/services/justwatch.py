# backend/core/services/justwatch.py
import requests
import json

class JustWatchService:
    def __init__(self):
        self.base_url = "https://apis.justwatch.com/content"
        self.locale = "en_IN"  # Change based on user location
    
    def get_streaming_providers(self, movie_title, release_year=None):
        """
        Get streaming providers for a movie
        """
        try:
            # Search for the movie
            search_url = f"{self.base_url}/titles/search/popular"
            params = {
                'query': movie_title,
                'content_types': ['movie'],
                'page': 1,
                'page_size': 5
            }
            
            response = requests.get(search_url, params=params)
            data = response.json()
            
            if data.get('items'):
                # Get first result
                movie = data['items'][0]
                movie_id = movie['id']
                
                # Get streaming providers for this movie
                providers_url = f"{self.base_url}/titles/movie/{movie_id}/locale/{self.locale}"
                provider_response = requests.get(providers_url)
                provider_data = provider_response.json()
                
                return self._extract_providers(provider_data)
            
            return []
            
        except Exception as e:
            print(f"JustWatch API error: {str(e)}")
            return []
    
    def _extract_providers(self, provider_data):
        """
        Extract streaming providers from JustWatch response
        """
        providers = []
        
        if 'offers' in provider_data:
            for offer in provider_data['offers']:
                provider = {
                    'name': offer.get('provider_name', ''),
                    'url': offer.get('urls', {}).get('standard_web', ''),
                    'icon': offer.get('provider_icon_url', ''),
                    'type': offer.get('monetization_type', ''),  # buy, rent, flatrate (subscription)
                    'price': offer.get('retail_price', None),
                    'currency': offer.get('currency', '')
                }
                providers.append(provider)
        
        return providers

# Usage in your match view
def get_streaming_redirect_url(movie_title, release_year=None):
    """
    Get redirect URL for streaming providers
    """
    justwatch = JustWatchService()
    providers = justwatch.get_streaming_providers(movie_title, release_year)
    
    # Prioritize popular streaming services
    priority_providers = ['Netflix', 'Amazon Prime Video', 'Disney Plus', 'Hotstar', 'SonyLIV']
    
    for provider in providers:
        if provider['name'] in priority_providers and provider['url']:
            return provider['url']
    
    # Fallback to first available provider
    if providers and providers[0]['url']:
        return providers[0]['url']
    
    return None
