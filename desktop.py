"""
desktop.py — Standalone Desktop Native Window Launcher for LM-Arena.
"""

import os
import sys
import time
import socket
import threading
import urllib.request
import webview

from utils import lifecycle

# Configure WebView2 arguments for audio playback and microphone capabilities
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
    "--use-fake-ui-for-media-stream "
    "--autoplay-policy=no-user-gesture-required "
    "--enable-features=SpeechRecognition,MediaStream "
    "--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5000,http://localhost:5000"
)


def find_available_port(default_port: int = 5000) -> int:
    """Finds an available TCP port on localhost."""
    for port in range(default_port, default_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return default_port


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """Waits until the server HTTP endpoint returns 200 OK."""
    import ssl
    ctx = ssl._create_unverified_context()
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ArenaDesktop/1.0"})
            with urllib.request.urlopen(req, timeout=1.5, context=ctx) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def start_flask_server(port: int, ssl_context=None):
    """Imports and runs the Flask app across all network interfaces (LAN, Wi-Fi, Tailscale)."""
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    try:
        from app import app
        app.run(host='0.0.0.0', port=port, ssl_context=ssl_context, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print(f"Error starting Flask server: {err}", flush=True)
        try:
            from variables.settings import LOGS_DIR
            with open(os.path.join(LOGS_DIR, "flask_server.log"), "w", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass


def main():
    lifecycle.install()

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("grendel.lm_arena.desktop.1.0")
        except Exception:
            pass

    use_https = os.getenv('USE_HTTPS', 'false').lower() == 'true'
    ssl_cert = os.getenv('SSL_CERT', 'certs/cert.pem')
    ssl_key = os.getenv('SSL_KEY', 'certs/key.pem')
    ssl_context = None
    protocol = 'http'
    if use_https and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_context = (ssl_cert, ssl_key)
        protocol = 'https'

    port = find_available_port(5000)
    server_url = f"{protocol}://127.0.0.1:{port}"

    # Start Flask server thread
    server_thread = threading.Thread(target=start_flask_server, args=(port, ssl_context), daemon=True)
    server_thread.start()

    splash_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LM-Arena</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: #121214;
            color: #dcd7ce;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            width: 100vw;
            overflow: hidden;
            user-select: none;
        }
        .loading-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            animation: pulse-scale 2s infinite ease-in-out;
        }
        .loading-logo {
            font-size: 3.5rem;
            line-height: 1;
            filter: drop-shadow(0 4px 16px rgba(212, 175, 55, 0.35));
            animation: pulse-heart 1.5s infinite ease-in-out;
        }
        @keyframes pulse-heart {
            0%, 100% { transform: scale(1); filter: drop-shadow(0 0 4px rgba(196, 160, 82, 0.3)); }
            50% { transform: scale(1.1); filter: drop-shadow(0 0 16px rgba(196, 160, 82, 0.7)); }
        }
        @keyframes pulse-scale {
            0%, 100% { transform: scale(0.98); }
            50% { transform: scale(1.02); }
        }
    </style>
</head>
<body>
    <div class="loading-content">
        <div class="loading-logo">📜</div>
    </div>
</body>
</html>"""

    # Launch native desktop window immediately with instant splash screen
    window = webview.create_window(
        title="LM-Arena",
        html=splash_html,
        width=1320,
        height=880,
        min_size=(960, 640),
        background_color="#121214",
        text_select=True
    )

    def load_app_when_ready(win, url):
        if wait_for_server(f"{url}/api/health", timeout=30.0):
            win.load_url(url)
        else:
            win.load_html("<html><body style='background:#121214;color:#f87171;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;'><p>Failed to start local server. Please check logs.</p></body></html>")

    def on_shown():
        if sys.platform == "win32" and getattr(window, "native", None) and getattr(window.native, "webview", None):
            def on_key_down(sender, args):
                if args.Control and args.Shift and not args.Alt and int(args.KeyCode) == 82:  # Keys.R
                    args.Handled = True
                    if sender.CoreWebView2:
                        sender.CoreWebView2.CallDevToolsProtocolMethodAsync("Page.reload", '{"ignoreCache": true}')
                    else:
                        sender.Reload()

            window.native.webview.KeyDown += on_key_down

    window.events.shown += on_shown

    app_icon_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'img', 'app_icon.ico'))
    if not os.path.exists(app_icon_path):
        app_icon_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'img', 'app_icon.png'))

    # Blocks until the window closes. Shutdown runs after the window is gone, so the UI never hangs on exit.
    if sys.platform == "win32":
        webview.start(load_app_when_ready, (window, server_url), gui='edgechromium', debug=False, icon=app_icon_path)
    else:
        webview.start(load_app_when_ready, (window, server_url), debug=False, icon=app_icon_path)

    lifecycle.shutdown()
    os._exit(0)


if __name__ == "__main__":
    main()
