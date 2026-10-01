# -*- coding: utf-8 -*-
"""Headless Chrome 啟動與極簡 CDP 用戶端（websocket-client）。"""
import base64
import itertools
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def chrome_path():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("找不到 Chrome/Edge")


class Chrome:
    def __init__(self, extra_args=(), port=9333, width=1280, height=720, headless=True):
        self.port = port
        self.profile = tempfile.mkdtemp(prefix="webar_chrome_")
        args = [chrome_path(),
                f"--remote-debugging-port={port}",
                f"--user-data-dir={self.profile}",
                "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
                "--autoplay-policy=no-user-gesture-required",
                f"--window-size={width},{height}",
                *extra_args, "about:blank"]
        if headless:
            args.insert(1, "--headless=new")
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.ws = None
        self._ids = itertools.count(1)
        self.events = []
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                page = [t for t in tabs if t.get("type") == "page"][0]
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Chrome CDP 連線失敗")
        import websocket
        self.ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)

    def send(self, method, params=None, timeout=60):
        mid = next(self._ids)
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self.events.append(msg)
        raise TimeoutError(method)

    def poll_events(self, seconds=0.0):
        """在 seconds 內收集事件。"""
        self.ws.settimeout(0.05)
        end = time.time() + seconds
        try:
            while True:
                try:
                    msg = json.loads(self.ws.recv())
                    self.events.append(msg)
                except Exception:
                    if time.time() >= end:
                        break
        finally:
            self.ws.settimeout(60)

    def eval(self, expr, await_promise=True):
        r = self.send("Runtime.evaluate", {"expression": expr, "awaitPromise": await_promise, "returnByValue": True})
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"], ensure_ascii=False)[:800])
        return r.get("result", {}).get("value")

    def screenshot(self, path):
        r = self.send("Page.captureScreenshot", {"format": "png"})
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))

    def set_viewport(self, w, h, mobile=False, dpr=1):
        self.send("Emulation.setDeviceMetricsOverride",
                  {"width": w, "height": h, "deviceScaleFactor": dpr, "mobile": mobile})
        if mobile:
            self.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})

    def close(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(10)
        except Exception:
            self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)
