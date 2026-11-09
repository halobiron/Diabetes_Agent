"""Backend dev server with auto-reload that also works on Windows.

`uvicorn --reload` can hang here: it detects a change but the old worker never exits, so the
new code is not served. watchfiles restarts the process itself and force-kills it if needed.

Run from the project root, with the environment from `.env` loaded:

    python -m watchfiles --filter python --sigint-timeout 2 --sigkill-timeout 2 \
        scripts.dev_server.run api agents rl tools memory models
"""

import os


def run():
    import uvicorn

    uvicorn.run(
        "api.app:app",
        host=os.environ.get("DEV_HOST", "127.0.0.1"),
        port=int(os.environ.get("DEV_PORT", "8010")),
    )
