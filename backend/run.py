"""Start the API from any cwd:  python backend/run.py"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)  # so .env is found
sys.path.insert(0, HERE)

sys.stdout.reconfigure(line_buffering=True)  # print() shows up in logs immediately

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8010")))
