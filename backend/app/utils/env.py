import os


def env(name: str) -> str:
    return os.getenv(name, "").strip()
