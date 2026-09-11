"""고정 샘플 날짜로 키 없이 실행하는 로컬 시연 서버. 실제 API는 호출하지 않는다."""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    os.environ.update(USE_MOCK="1", MODEL_MODE="offline", BADARO_DATA_DIR=str(ROOT / "agent/data"))
    from badaro.agent import DispatchAgent
    from badaro.runtime.contracts import Settings
    from badaro.server import create_server

    reference_time = datetime(2026, 9, 11, 9, tzinfo=ZoneInfo("Asia/Seoul"))
    agent = DispatchAgent(settings=Settings(), now=lambda: reference_time)
    with create_server(service=agent, port=args.port) as server:
        print(f"Mock 시연: http://127.0.0.1:{args.port}; 기준일 2026-09-11 고정", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
