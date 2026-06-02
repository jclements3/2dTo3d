#!/usr/bin/env python3
"""
serve_viewer.py — host the WebGL viewer locally so it has a real URL to capture.

This simulates a "live" 3D website (like the Sketchfab embed) on your machine.
It serves the directory containing 3d-viewer.html over HTTP and prints the URL
that capture_views.py should target.

    python serve_viewer.py                 # serves ./ on http://localhost:8000
    python serve_viewer.py --port 8080
    python serve_viewer.py --dir ./site --file 3d-viewer.html

Leave it running in one terminal; run capture_views.py in another.
"""

import argparse
import http.server
import os
import socketserver
import threading
import webbrowser


def main():
    ap = argparse.ArgumentParser(description="Serve the WebGL viewer locally.")
    ap.add_argument("--dir", default=".", help="directory to serve (default: current)")
    ap.add_argument("--file", default="3d-viewer.html", help="entry HTML file")
    ap.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    ap.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    ap.add_argument("--open", action="store_true", help="open the page in a browser")
    args = ap.parse_args()

    root = os.path.abspath(args.dir)
    if not os.path.isfile(os.path.join(root, args.file)):
        raise SystemExit(f"'{args.file}' not found in {root}")

    # Bind the handler to the chosen directory (Python 3.7+).
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=root, **k)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        url = f"http://{args.host}:{args.port}/{args.file}"
        print(f"Serving {root}")
        print(f"Viewer URL:  {url}")
        print("Press Ctrl+C to stop.")
        if args.open:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
