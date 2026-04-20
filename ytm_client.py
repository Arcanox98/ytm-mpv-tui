from ytmusicapi import YTMusic
import os

class YTMClient:
    def __init__(self):
        auth_file = "browser.json"
        if os.path.exists(auth_file):
            try:
                self.ytm = YTMusic(auth_file)
            except Exception:
                self.ytm = YTMusic()
        else:
            self.ytm = YTMusic()

    def search_songs(self, query):
        try:
            results = self.ytm.search(query, filter="songs")
            songs = []
            for res in results:
                songs.append({
                    "id": res["videoId"],
                    "title": res["title"],
                    "artist": ", ".join([a["name"] for a in res["artists"]]),
                    "thumbnail": res["thumbnails"][-1]["url"] if res.get("thumbnails") else None
                })
            return songs
        except: return []

    def get_recommendations(self):
        try:
            # Reducimos el límite para cargar más rápido
            results = self.ytm.get_home(limit=3)
            songs = []
            for section in results:
                if 'contents' in section:
                    for res in section['contents']:
                        if 'videoId' in res:
                            songs.append({
                                "id": res["videoId"],
                                "title": res["title"],
                                "artist": ", ".join([a["name"] for a in res.get("artists", [])]) if res.get("artists") else "YTM",
                                "thumbnail": res["thumbnails"][-1]["url"] if res.get("thumbnails") else None
                            })
            return songs
        except: return []
