import os
from pathlib import Path

from . import config


class LocalStorage:
    def __init__(self, root):
        self.root = Path(root)

    def save(self, key, data: bytes):
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, p)

    def delete(self, key):
        (self.root / key).unlink(missing_ok=True)

    def url(self, key):
        return f"/media/{key}"


storage = LocalStorage(config.MEDIA_DIR)
