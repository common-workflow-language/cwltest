"""Abstracted IO access."""

import os
import urllib
from typing import IO, Any

from schema_salad.ref_resolver import uri_file_path


def abspath(src: str, basedir: str) -> str:
    """Determine local filesystem absolute path given a basedir, handling both plain paths and URIs."""
    if src.startswith("file://"):
        abpath = uri_file_path(src)
    elif urllib.parse.urlsplit(src).scheme in ["http", "https"]:
        return src
    else:
        if basedir.startswith("file://"):
            abpath = src if os.path.isabs(src) else basedir + "/" + src
        else:
            abpath = src if os.path.isabs(src) else os.path.join(basedir, src)
    return abpath


class StdFsAccess:
    """Local filesystem implementation."""

    def __init__(self, basedir: str) -> None:
        """Perform operations with respect to a base directory."""
        self.basedir = basedir

    def _abs(self, p: str) -> str:
        return abspath(p, self.basedir)

    def open(self, fn: str, mode: str) -> IO[Any]:
        """Open a file from a file: URI."""
        return open(self._abs(fn), mode)

    def size(self, fn: str) -> int:
        """Get the size of the file resource pointed to by a URI."""
        return os.stat(self._abs(fn)).st_size

    def isfile(self, fn: str) -> bool:
        """Determine if a resource pointed to by a URI represents a file."""
        return os.path.isfile(self._abs(fn))

    def isdir(self, fn: str) -> bool:
        """Determine if a resource pointed to by a URI represents a directory."""
        return os.path.isdir(self._abs(fn))
