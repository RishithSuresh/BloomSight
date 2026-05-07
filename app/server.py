"""Standard-library HTTP server for the BloomSight UI.

The server exposes a tiny JSON API that wraps the ``visual_crypto``
package and serves the static front-end. No third-party web framework
is required.

Routes
------
GET  /                  - HTML application shell
GET  /static/<path>     - Static asset (CSS / JS)
POST /api/encrypt       - body: {image, method, n_shares, themed, seed}
POST /api/decrypt       - body: {shares: [b64...], method, downsample}
"""

from __future__ import annotations

import base64
import io
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image

# Make the sibling ``visual_crypto`` package importable when run via
# ``python -m app`` or directly as a script.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from visual_crypto import naor_shamir, theme, xor  # noqa: E402

_STATIC_ROOT = _HERE / "static"
_TEMPLATE = _HERE / "templates" / "index.html"
_DEFAULT_PORT = 8000


def _b64_to_image(data_url: str) -> Image.Image:
    payload = data_url.split(",", 1)[-1]
    raw = base64.b64decode(payload)
    img = Image.open(io.BytesIO(raw))
    img.load()
    return img


def _image_to_b64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _encrypt(payload: Dict[str, Any]) -> Dict[str, Any]:
    img = _b64_to_image(payload["image"])
    method = payload.get("method", "xor")
    seed = payload.get("seed")
    themed = bool(payload.get("themed", False))

    if method == "xor":
        n = int(payload.get("n_shares", 2))
        shares = xor.xor_encrypt(img, n_shares=n, seed=seed)
    elif method == "naor-shamir":
        s1, s2 = naor_shamir.naor_shamir_encrypt(img, seed=seed)
        shares = [s1, s2]
    else:
        raise ValueError(f"Unknown method {method!r}")

    out = []
    for i, share in enumerate(shares):
        rendered = share
        if themed:
            fg, bg = theme.palette_for(i)
            rendered = theme.apply_nature_tint(share, fg=fg, bg=bg)
        out.append({
            "index": i + 1,
            "image": _image_to_b64(rendered),
            "raw": _image_to_b64(share),
            "width": share.size[0],
            "height": share.size[1],
        })
    return {"method": method, "themed": themed, "shares": out}


def _decrypt(payload: Dict[str, Any]) -> Dict[str, Any]:
    method = payload.get("method", "xor")
    images = [_b64_to_image(s) for s in payload["shares"]]

    if method == "xor":
        recovered = xor.xor_decrypt(images)
    elif method == "naor-shamir":
        if len(images) != 2:
            raise ValueError("naor-shamir requires exactly two shares")
        loaded = []
        for im in images:
            loaded.append(theme.from_nature_tint(im) if im.mode in ("RGB", "RGBA") else im)
        recovered = naor_shamir.naor_shamir_decrypt(loaded[0], loaded[1])
        if payload.get("downsample", True):
            recovered = naor_shamir.downsample_revealed(recovered)
    else:
        raise ValueError(f"Unknown method {method!r}")

    return {"image": _image_to_b64(recovered)}


class Handler(BaseHTTPRequestHandler):
    server_version = "BloomSight/1.0"

    def log_message(self, fmt, *args):  # pragma: no cover - quieter logs
        sys.stderr.write("[ui] " + (fmt % args) + "\n")

    # --- helpers -----------------------------------------------------------
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    # --- routing -----------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            data = _TEMPLATE.read_bytes()
            self._send(HTTPStatus.OK, data, "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            target = (_STATIC_ROOT / rel).resolve()
            if _STATIC_ROOT.resolve() not in target.parents and target != _STATIC_ROOT:
                self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return
            if not target.is_file():
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            ctype, _ = mimetypes.guess_type(str(target))
            self._send(HTTPStatus.OK, target.read_bytes(),
                       ctype or "application/octet-stream")
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            if self.path == "/api/encrypt":
                self._send_json(HTTPStatus.OK, _encrypt(payload))
            elif self.path == "/api/decrypt":
                self._send_json(HTTPStatus.OK, _decrypt(payload))
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})


def main(argv: List[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    port = int(args[0]) if args else _DEFAULT_PORT
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[BloomSight] http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
