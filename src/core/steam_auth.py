"""
Steam Authentication Manager - OAuth2 & Local Server
Speichern als: src/core/steam_auth.py
"""
import webbrowser
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from PyQt6.QtCore import QObject, pyqtSignal
from src.config import config
from src.utils.i18n import t

class SteamAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Fängt den Redirect von Steam auf"""
        parsed_path = urlparse(self.path)
        query = parse_qs(parsed_path.query)

        if 'code' in query:
            # Erfolg! Code extrahieren
            auth_code = query['code'][0]
            self.server.auth_token = auth_code # Speichern im Server-Objekt
            
            # Erfolgsseite anzeigen
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = f"""
            <html>
            <head><title>{t('ui.login.html_success_header')}</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px; background: #222; color: #fff;">
                <h1>{t('ui.login.html_success_header')}</h1>
                <p>{t('ui.login.html_success_body')}</p>
                <script>setTimeout(function() {{ window.close(); }}, 3000);</script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error: No code received.")

class SteamAuthManager(QObject):
    auth_success = pyqtSignal(str) # Sendet den Auth Code / Token
    auth_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.server = None
        self.thread = None
        # redirect_uri muss in Steamworks auf http://localhost:5000/auth gesetzt sein!
        self.redirect_uri = "http://localhost:5000/auth"
        self.port = 5000

    def start_login(self):
        """Startet den OAuth Prozess"""
        if not config.STEAM_CLIENT_ID:
            self.auth_error.emit("Missing STEAM_CLIENT_ID in .env")
            return

        # 1. Lokalen Server starten (in Thread, damit UI nicht blockiert)
        self.thread = threading.Thread(target=self._run_server)
        self.thread.daemon = True
        self.thread.start()

        # 2. Browser öffnen
        # URL Konstruktion (Standard OAuth2 Pattern)
        auth_url = (
            "https://steamcommunity.com/oauth/login?"
            "response_type=code&"
            f"client_id={config.STEAM_CLIENT_ID}&"
            "state=random_state_string&"
            f"redirect_uri={self.redirect_uri}"
        )
        print(t('logs.auth.starting'))
        webbrowser.open(auth_url)

    def _run_server(self):
        try:
            self.server = HTTPServer(('localhost', self.port), SteamAuthHandler)
            self.server.auth_token = None
            print(t('logs.auth.server_started', port=self.port))
            
            # Warten auf EINE Anfrage (handle_request kehrt nach 1 Request zurück)
            self.server.handle_request()
            
            if self.server.auth_token:
                print(t('logs.auth.token_received'))
                self.auth_success.emit(self.server.auth_token)
            else:
                self.auth_error.emit("No token received")
                
            self.server.server_close()
            
        except Exception as e:
            self.auth_error.emit(str(e))
