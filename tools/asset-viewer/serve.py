#!/usr/bin/env python3
"""WRF Asset Viewer — a tiny FModel-style reference navigator for the *exported*
JSON tree.

FModel browses the .pak files; this doesn't need to. The export step already
wrote every asset to JSON under EXPORT_DIR, with cross-asset references kept as
{"ObjectName":.., "ObjectPath": "/Game/.../Foo.3"}. This serves that tree as a
static web root plus a single-page viewer that turns every ObjectPath into a
clickable link, resolving it exactly the way the parser does
(WRFrontiersDB-Parser/src/utils.py: strip a Class'..' wrapper, split('.')[0],
replace /Game/ -> <game>/Content/, add .json, and the trailing .N is the array
index to jump to).

Usage:
    python tools/asset-viewer/serve.py            # defaults to /srv/dev/wrf/data/exports
    python tools/asset-viewer/serve.py --export-dir /path/to/exports --port 8765
    python tools/asset-viewer/serve.py --game-name WRFrontiers

Then open the printed URL. Paste a warning line, an ObjectPath, or a file path
and follow the chain. Nothing is written; it only reads the export tree.
"""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
from functools import partial
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIEWER = HERE / "viewer.html"


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serve the export dir as the web root, but hand back the viewer page at /."""

    game_name = "WRFrontiers"

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):  # noqa: N802 (stdlib naming)
        route = self.path.split("?", 1)[0]
        if route in ("/", "/index.html", "/viewer", "/__viewer__"):
            self._send_viewer()
            return
        # Everything else is a data file under the export dir.
        super().do_GET()

    def _send_viewer(self):
        try:
            html = VIEWER.read_text(encoding="utf-8")
        except OSError as exc:
            self.send_error(500, f"viewer.html unreadable: {exc}")
            return
        html = html.replace(
            "window.__GAME_NAME__ || \"WRFrontiers\"",
            f'"{self.game_name}"',
        )
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quieter: only log misses
        if args and str(args[0]).startswith(('"GET', "'GET")) and "404" in " ".join(map(str, args)):
            super().log_message(fmt, *args)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export-dir", default=os.environ.get("EXPORT_DIR", "/srv/dev/wrf/data/exports"),
                    help="Root of the exported JSON tree (default: /srv/dev/wrf/data/exports).")
    ap.add_argument("--game-name", default=os.environ.get("GAME_NAME", "WRFrontiers"),
                    help="Game name used in the /Game/ -> <game>/Content/ mapping (default: WRFrontiers).")
    ap.add_argument("--port", type=int, default=8765, help="Port to serve on (default: 8765).")
    ap.add_argument("--host", default="127.0.0.1", help="Host/interface (default: 127.0.0.1).")
    args = ap.parse_args()

    export_dir = Path(args.export_dir).resolve()
    if not export_dir.is_dir():
        ap.error(f"export dir not found: {export_dir}")
    if not VIEWER.is_file():
        ap.error(f"viewer.html missing next to serve.py: {VIEWER}")

    Handler.game_name = args.game_name
    handler = partial(Handler, directory=str(export_dir))

    with Server((args.host, args.port), handler) as httpd:
        url = f"http://{args.host}:{args.port}/"
        print(f"WRF Asset Viewer  ->  {url}")
        print(f"  export dir : {export_dir}")
        print(f"  game name  : {args.game_name}")
        print("  Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
