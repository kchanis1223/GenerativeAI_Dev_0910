"""Vue 개발 화면에서 호출할 로컬 전용 JSON API."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from badaro.agent import DispatchAgent


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=8000)
    thread_id: UUID | None = None


ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}


def create_server(service=None, port=8000):
    service = service or DispatchAgent()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # 요청 URL·본문은 로그로 출력하지 않는다.

        def send_json(self, status, value):
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            origin = self.headers.get("Origin")
            if origin in ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self.send_json(
                    200,
                    {
                        "status": "ok",
                        "mode": service.settings.mode,
                        **(
                            {"scenarios": True}
                            if type(service).__name__ == "ScenarioService"
                            else {}
                        ),
                    },
                )
            else:
                self.send_json(404, {"message": "경로를 찾을 수 없습니다"})

        def do_OPTIONS(self):
            if self.path != "/api/chat" or self.headers.get("Origin") not in ORIGINS:
                return self.send_json(403, {"message": "허용되지 않은 요청입니다"})
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_POST(self):
            if self.path != "/api/chat":
                return self.send_json(404, {"message": "경로를 찾을 수 없습니다"})
            if self.headers.get("Origin") and self.headers["Origin"] not in ORIGINS:
                return self.send_json(403, {"message": "허용되지 않은 요청입니다"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 64000:
                    raise ValueError
                payload = ChatInput.model_validate_json(self.rfile.read(length))
            except (ValueError, ValidationError):
                return self.send_json(400, {"message": "message와 thread_id 형식을 확인해 주세요"})
            reply = service.chat(
                payload.message, str(payload.thread_id) if payload.thread_id else None
            )
            self.send_json(200, reply.model_dump(mode="json"))

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="바다로 로컬 Agent API")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--scenarios", action="store_true", help="M01~M08 고정 시연")
    args = parser.parse_args()
    service = None
    if args.scenarios:
        from badaro.scenarios import ScenarioService

        service = ScenarioService()
    with create_server(service=service, port=args.port) as server:
        print(f"바다로 로컬 API: http://127.0.0.1:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
