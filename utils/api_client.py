import aiohttp
from typing import Optional, Dict

async def get_anime_info(title: str) -> Optional[Dict]:
    """
    MyAnimeList API dan anime ma'lumotlarini olish
    """
    async with aiohttp.ClientSession() as session:
        try:
            # MyAnimeList API URL va API key
            url = f"https://api.myanimelist.net/v2/anime"
            headers = {
                "X-MAL-CLIENT-ID": "your_mal_client_id"
            }
            params = {
                "q": title,
                "limit": 1
            }
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["data"]:
                        return data["data"][0]["node"]
                return None
        except Exception as e:
            print(f"Error fetching anime info: {e}")
            return None 