import logging
import os
import sys


def setup_logging() -> None:
    """Configure app logging and reduce noisy third-party warnings on CPU hosts."""
    os.environ.setdefault("ORT_LOGGING_LEVEL", "3")  # onnxruntime: errors only

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )

    for name in ("httpx", "httpcore", "urllib3", "huggingface_hub"):
        logging.getLogger(name).setLevel(logging.WARNING)
