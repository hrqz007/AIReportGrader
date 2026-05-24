from __future__ import annotations

import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
URL = "http://127.0.0.1:8000"


def open_browser_later() -> None:
    time.sleep(2.5)
    try:
        webbrowser.open(URL, new=2)
    except Exception:
        # The console already shows the URL. Browser startup failure should not
        # stop the local grading system.
        pass


def main() -> None:
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))

    print("")
    print("系统网址：", URL)
    print("如果浏览器没有自动打开，请复制上面的系统网址到浏览器访问。")
    print("请不要关闭当前命令行窗口；关闭后系统会停止运行。")
    print("")

    threading.Thread(target=open_browser_later, daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
