#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tiny LAN listener that collects the boot-page diagnostics from the iPhone.

Run:  python scripts/diag_server.py
Then open the app on the phone; results are printed here and appended to diag.log
"""
import datetime
import http.server
import json
import os
import socket
import socketserver
import sys

PORT = 8787
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "diag.log")


class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n).decode("utf-8", "replace")
            data = json.loads(raw) if raw else {}
        except Exception as exc:  # noqa: BLE001
            data = {"parse_error": str(exc), "raw": raw[:500]}

        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{stamp}] 收到手机诊断 协议判定={data.get('verdict')}")
        for k in ("origin", "isSecureContext", "hasNavigatorGpu", "screen",
                  "dpr", "hw", "ua", "detail"):
            if k in data:
                print(f"  {k}: {data[k]}")

        try:
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001
            pass

        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *_args):
        pass


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:  # noqa: BLE001
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    print(f"诊断监听已启动：http://{lan_ip()}:{PORT}/report")
    print("让手机连同一个 Wi-Fi，然后打开 App，结果会显示在这里。Ctrl+C 结束。")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")
            sys.exit(0)
