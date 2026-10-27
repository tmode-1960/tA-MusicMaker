"""Minimal fake ComfyUI used to smoke-test the app without GPU/models.  python tests/mock_comfy.py [port]"""
import json
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROMPTS = {}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, status=200, raw=None, ctype="application/json"):
        body = raw if raw is not None else json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/system_stats"):
            return self._send({"devices": [{"name": "cuda:0 Mock RTX", "vram_total": 24 * 2**30, "vram_free": 20 * 2**30}]})
        if self.path.startswith("/object_info/PlenioSongBrief"):
            return self._send({"PlenioSongBrief": {"input": {"required": {
                "mode": [["new song every run", "one song, stop to review"]],
                "length": ["COMBO", {"options": ["short (about 1:30)", "long (about 4:30)"]}]}}}})
        if self.path.startswith("/history/"):
            pid = self.path.rsplit("/", 1)[1]
            p = PROMPTS.get(pid)
            if not p or time.time() - p["t"] < 2:
                return self._send({})
            outs = {}
            for nid, n in p["prompt"].items():
                if n["class_type"] == "PreviewAny":
                    outs[nid] = {"text": [f"mock {nid}"]}
                if n["class_type"] == "PreviewAudio":
                    outs[nid] = {"audio": [{"filename": "mock.wav", "subfolder": "", "type": "temp"}]}
            return self._send({pid: {"outputs": outs, "status": {"status_str": "success", "completed": True}}})
        if self.path.startswith("/view"):
            return self._send(None, raw=b"RIFF....", ctype="audio/wav")
        self._send({}, 404)

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path == "/prompt":
            prompt = data["prompt"]
            for nid, n in prompt.items():
                for k, v in n["inputs"].items():
                    if isinstance(v, list) and v[0] not in prompt:
                        return self._send({"error": {"message": f"dangling link {nid}.{k}"}}, 400)
            pid = uuid.uuid4().hex
            PROMPTS[pid] = {"prompt": prompt, "t": time.time()}
            json.dump(prompt, open(f"mock_last_prompt.json", "w"), indent=1)
            return self._send({"prompt_id": pid})
        self._send({})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8199), H).serve_forever()
