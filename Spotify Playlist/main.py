from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-secret-key')

# Constants
BILLBOARD_URL = "https://www.billboard.com/charts/hot-100"
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIPY_REDIRECT_URI')

print("Environment Variables:")
print(f"Client ID: {SPOTIFY_CLIENT_ID}")
print(f"Redirect URI: {SPOTIFY_REDIRECT_URI}")

def get_spotify_client():
    """Create and return a Spotify client"""
    try:
        auth_manager = SpotifyOAuth(
            scope="playlist-modify-private",
            redirect_uri=SPOTIFY_REDIRECT_URI,
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            show_dialog=True,
            cache_handler=spotipy.cache_handler.MemoryCacheHandler()
        )
        return spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        print(f"Error creating Spotify client: {e}")
        raise

def get_billboard_songs(date):
    """Fetch songs from Billboard for a given date"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
        }
        response = requests.get(f"{BILLBOARD_URL}/{date}", headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        song_names_spans = soup.select("li ul li h3")
        return [song.getText().strip() for song in song_names_spans]
    except Exception as e:
        print(f"Error fetching Billboard songs: {e}")
        raise

def create_spotify_playlist(date):
    """Create a Spotify playlist with Billboard songs from a specific date"""
    try:
        # Get Billboard songs
        song_names = get_billboard_songs(date)
        if not song_names:
            return "No songs found for this date"

        # Initialize Spotify client
        sp = get_spotify_client()
        
        # Verify authentication
        try:
            user_id = sp.current_user()["id"]
        except Exception as e:
            print(f"Spotify authentication error: {e}")
            return f"Spotify authentication failed: {str(e)}"

        # Search for songs on Spotify
        song_uris = []
        year = date.split("-")[0]
        
        for song in song_names:
            try:
                result = sp.search(q=f"track:{song} year:{year}", type="track")
                if result["tracks"]["items"]:
                    uri = result["tracks"]["items"][0]["uri"]
                    song_uris.append(uri)
            except Exception as e:
                print(f"Error searching for song {song}: {e}")
                continue

        if not song_uris:
            return "No songs could be found on Spotify"

        # Create and populate playlist
        playlist_name = f"Billboard 100 - {date}"
        playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=False,
            description=f"Billboard Hot 100 songs from {date}"
        )
        
        sp.playlist_add_items(playlist_id=playlist["id"], items=song_uris)
        return playlist["external_urls"]["spotify"]
    
    except Exception as e:
        print(f"Error in create_spotify_playlist: {e}")
        return f"Error creating playlist: {str(e)}"

@app.route("/")
def index():
    """Handle home page GET requests"""
    return render_template("index.html")

@app.route("/create-playlist", methods=["POST"])
def create_playlist():
    """Handle playlist creation POST requests"""
    date = request.form.get("date")
    
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        flash("Please enter a valid date in YYYY-MM-DD format.", "error")
        return redirect(url_for('index'))
    
    playlist_url = create_spotify_playlist(date)
    
    if "spotify.com" in str(playlist_url):
        flash("Playlist created successfully!", "success")
    else:
        flash(f"Error: {playlist_url}", "error")
    
    return render_template("index.html", playlist_url=playlist_url)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)