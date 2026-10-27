"""Small dependency-free ComfyUI client (HTTP + a minimal WebSocket reader)."""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Callable


class ComfyError(Exception):
    pass


class ComfyClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self.base_url = base_url.rstrip("/")
        self.client_id = uuid.uuid4().hex

    # ------------------------------------------------------------------ HTTP

    def _request(self, path: str, data: dict | None = None, timeout: float = 15, raw: bool = False,
                 headers: dict | None = None, method: str | None = None):
        url = self.base_url + path
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", **(headers or {})}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = resp.read()
                if raw:
                    return payload, resp.headers
                return json.loads(payload.decode("utf-8")) if payload else {}
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail)
            except ValueError:
                pass
            raise ComfyError(_format_http_error(err.code, detail)) from err
        except (urllib.error.URLError, socket.timeout, ConnectionError) as err:
            raise ComfyError(f"ComfyUI is unreachable ({self.base_url}): {err}") from err

    def is_alive(self) -> bool:
        try:
            self._request("/system_stats", timeout=3)
            return True
        except ComfyError:
            return False

    def system_stats(self) -> dict:
        return self._request("/system_stats", timeout=5)

    # -------------------------------------------------------- Plenio Song API

    def has_plenio_api(self) -> bool:
        try:
            res = self._request("/plenio/api/v1/templates", timeout=3)
            return isinstance(res, (list, dict))
        except ComfyError:
            return False

    def plenio_info(self) -> dict:
        return self._request("/plenio/api/v1", timeout=5)

    def plenio_templates(self) -> list[dict] | dict:
        return self._request("/plenio/api/v1/templates", timeout=10)

    def plenio_create_job(self, job_data: dict) -> dict:
        return self._request("/plenio/api/v1/jobs", data=job_data, timeout=30)

    def plenio_get_job(self, job_id: str) -> dict:
        return self._request("/plenio/api/v1/jobs/" + urllib.parse.quote(str(job_id)), timeout=15)

    def plenio_cancel_job(self, job_id: str) -> None:
        try:
            self._request("/plenio/api/v1/jobs/" + urllib.parse.quote(str(job_id)), method="DELETE", timeout=10)
        except Exception:
            pass

    def plenio_from_record(self, record: dict) -> dict:
        return self._request("/plenio/api/v1/from-record", data=record, timeout=15)

    def object_info(self, node_class: str) -> dict:
        return self._request("/object_info/" + urllib.parse.quote(node_class), timeout=20)

    def folder_paths(self) -> dict:
        return self._request("/internal/folder_paths", timeout=10)

    def queue_prompt(self, prompt: dict) -> str:
        res = self._request("/prompt", {"prompt": prompt, "client_id": self.client_id}, timeout=30)
        if "prompt_id" not in res:
            raise ComfyError(f"Unexpected response from ComfyUI: {res}")
        return res["prompt_id"]

    def history(self, prompt_id: str) -> dict:
        return self._request("/history/" + prompt_id, timeout=15).get(prompt_id, {})

    def interrupt(self) -> None:
        self._request("/interrupt", {}, timeout=10)

    def clear_queue(self) -> None:
        self._request("/queue", {"clear": True}, timeout=10)

    def view(self, filename: str, subfolder: str, ftype: str, range_header: str | None = None):
        qs = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": ftype})
        headers = {"Range": range_header} if range_header else None
        return self._request("/view?" + qs, raw=True, timeout=60, headers=headers)

    # ------------------------------------------------------------- execution

    def run_prompt(self, prompt: dict, on_event: Callable[[dict], None], should_cancel: Callable[[], bool]) -> dict:
        """Queue ``prompt`` and block until it finished. Returns the history entry."""
        listener = _WsListener(self.base_url, self.client_id, on_event)
        listener.start()
        try:
            prompt_id = self.queue_prompt(prompt)
            listener.prompt_id = prompt_id
            on_event({"type": "queued", "prompt_id": prompt_id})
            while True:
                if should_cancel():
                    try:
                        self.interrupt()
                    except ComfyError:
                        pass
                    raise ComfyError("Cancelled.")
                entry = self.history(prompt_id)
                if entry:
                    status = (entry.get("status") or {})
                    if status.get("status_str") == "error":
                        raise ComfyError(_history_error(status))
                    if status.get("completed") or entry.get("outputs") is not None:
                        return entry
                time.sleep(0.8)
        finally:
            listener.stop()


def _format_http_error(code: int, detail) -> str:
    if isinstance(detail, dict):
        err = detail.get("error")
        msg = err.get("message") if isinstance(err, dict) else str(err) if err else ""
        extra = err.get("details") if isinstance(err, dict) else ""
        parts = [f"ComfyUI rejected prompt (HTTP {code}): {msg} {extra}".strip()]
        for node_id, info in (detail.get("node_errors") or {}).items():
            for e in info.get("errors", []):
                parts.append(f"  Node {node_id} ({info.get('class_type')}): {e.get('message')} {e.get('details', '')}")
        return "\n".join(parts)
    return f"ComfyUI error (HTTP {code}): {detail}"


def _history_error(status: dict) -> str:
    for kind, data in status.get("messages", []):
        if kind == "execution_error":
            return (f"Error in node {data.get('node_id')} ({data.get('node_type')}): "
                    f"{data.get('exception_message', '').strip()}")
    return "Execution failed in ComfyUI."


class _WsListener(threading.Thread):
    """Best-effort progress feed; the job still completes via history polling if this fails."""

    def __init__(self, base_url: str, client_id: str, on_event: Callable[[dict], None]):
        super().__init__(daemon=True)
        self.base_url = base_url
        self.client_id = client_id
        self.on_event = on_event
        self.prompt_id: str | None = None
        self._halt = threading.Event()
        self._sock: socket.socket | None = None

    def stop(self):
        self._halt.set()
        try:
            if self._sock:
                self._sock.close()
        except OSError:
            pass

    def run(self):
        try:
            self._loop()
        except Exception:
            pass

    def _loop(self):
        parsed = urllib.parse.urlparse(self.base_url)
        host, port = parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        if parsed.scheme == "https":
            return
        sock = socket.create_connection((host, port), timeout=10)
        self._sock = sock
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall((
            f"GET /ws?clientId={self.client_id} HTTP/1.1\r\nHost: {host}:{port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return
            buf += chunk
        _, _, buf = buf.partition(b"\r\n\r\n")
        sock.settimeout(None)
        message = b""
        while not self._halt.is_set():
            try:
                frame, buf = self._read_frame(sock, buf)
            except socket.timeout:
                continue
            if frame is None:
                return
            fin, opcode, payload = frame
            if opcode == 8:
                return
            if opcode == 9:
                self._send(sock, 10, payload)
                continue
            if opcode in (1, 0):
                message += payload
                if fin:
                    text, message = message, b""
                    self._handle(text)

    def _read_exact(self, sock, buf, n):
        while len(buf) < n:
            chunk = sock.recv(65536)
            if not chunk:
                raise ConnectionError("closed")
            buf += chunk
        return buf[:n], buf[n:]

    def _read_frame(self, sock, buf):
        try:
            head, buf = self._read_exact(sock, buf, 2)
        except ConnectionError:
            return None, buf
        fin, opcode = bool(head[0] & 0x80), head[0] & 0x0F
        masked, length = bool(head[1] & 0x80), head[1] & 0x7F
        if length == 126:
            ext, buf = self._read_exact(sock, buf, 2)
            length = struct.unpack(">H", ext)[0]
        elif length == 127:
            ext, buf = self._read_exact(sock, buf, 8)
            length = struct.unpack(">Q", ext)[0]
        mask = b""
        if masked:
            mask, buf = self._read_exact(sock, buf, 4)
        payload, buf = self._read_exact(sock, buf, length)
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return (fin, opcode, payload), buf

    def _send(self, sock, opcode, payload: bytes):
        mask = os.urandom(4)
        header = bytes([0x80 | opcode, 0x80 | len(payload)]) + mask
        sock.sendall(header + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _handle(self, raw: bytes):
        try:
            msg = json.loads(raw.decode("utf-8"))
        except ValueError:
            return
        data = msg.get("data", {}) or {}
        if self.prompt_id and data.get("prompt_id") not in (None, self.prompt_id):
            return
        self.on_event({"type": msg.get("type"), **data})

