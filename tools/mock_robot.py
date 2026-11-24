"""Fake ResQBot gateway for testing the dashboard on a PC: python tools/mock_robot.py [port]
Serves dashboard/index.html and the API, drops 1 in 5 requests and delays others, like a weak Wi-Fi link."""
import base64, hashlib, json, random, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
state = {"mode": "manual", "rx": 0, "drive": [0, 0], "drill": False, "headlight": False, "flash": 0, "log": []}
T0 = time.time()


def status():
    return {"mode": state["mode"], "state": "manual control", "uptime": int(time.time() - T0), "object": 27.0,
            "ambient": 27.5, "airTemp": 29.0, "humidity": 60, "distance": 120, "gas": 200, "battery": 7.8,
            "batteryPct": 70, "score": 0, "scanProgress": 100, "pan": 90, "motion": False, "pirReady": True,
            "gasAlarm": False, "batteryLow": False, "thermalOk": True, "dhtOk": True, "headlight": state["headlight"], "drill": state["drill"],
            "moving": state["drive"] != [0, 0], "rx": state["rx"], "rxBad": 0, "blocked": False, "alert": False,
            "survivors": 0, "scans": 0,
            "finding": {"found": False, "fire": False, "background": None, "peak": None, "delta": 0, "bearing": 0, "cells": 0},
            "grid": {"panMin": 20, "panStep": 10, "rows": [[None] * 15, [None] * 15]},
            "camera": "", "flash": state["flash"], "clients": 1, "link": True, "events": []}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/":
            return self.send((ROOT / "dashboard" / "index.html").read_text(encoding="utf-8"), "text/html")
        if u.path == "/ws" and self.headers.get("Upgrade", "").lower() == "websocket":
            return self.websocket()
        if u.path == "/mock/log":
            return self.send(json.dumps(state["log"]))
        if random.random() < 0.2:                       # lost request: no answer at all
            time.sleep(3)
            return
        time.sleep(random.choice([0, 0, 0.05, 0.3, 0.9]))
        if u.path == "/api/status":
            return self.send(json.dumps(status()))
        if u.path == "/api/drive":
            state["drive"] = [int(q.get("l", 0)), int(q.get("r", 0))]
            state["rx"] += 1
        elif u.path == "/api/drill":
            state["drill"] = q.get("on") == "1"
        elif u.path == "/api/mode":
            state["mode"] = q.get("m", "manual")
        elif u.path == "/api/headlight":
            state["headlight"] = q.get("on") == "1"
        elif u.path == "/led":
            state["flash"] = int(q.get("level", 0))
        state["log"].append([round(time.time() - T0, 2), u.path, q])
        self.send('{"ok":true}')


    def websocket(self):                                # just enough RFC 6455 for short text frames
        key = self.headers["Sec-WebSocket-Key"] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", base64.b64encode(hashlib.sha1(key.encode()).digest()).decode())
        self.end_headers()
        self.wfile.flush()
        r = self.rfile
        while True:
            h = r.read(2)
            if len(h) < 2 or h[0] & 0x0F == 8:
                return
            n = h[1] & 0x7F
            if n == 126:
                n = int.from_bytes(r.read(2), "big")
            mask = r.read(4)
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(r.read(n))).decode()
            if data.startswith("D,"):
                state["drive"] = [int(x) for x in data[2:].split(",")]
                state["rx"] += 1
            elif data.startswith("R,"):
                state["drill"] = data[2] == "1"
            state["log"].append([round(time.time() - T0, 2), "ws", data])


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"mock robot on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
