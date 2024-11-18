"""File system interface for accessing Arvados collections."""

# Copyright (C) The Arvados Authors. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0

import os
import errno
import urllib.parse
import re
import logging
import threading
from collections import OrderedDict
from typing import IO, Tuple, Optional

import cwltest.stdfsaccess

import arvados.util
import arvados.collection
import arvados.arvfile
import arvados.errors

logger = logging.getLogger("arvados.cwl-runner")

pdh_size = re.compile(r"([0-9a-f]{32})\+(\d+)(\+\S+)*")


class CollectionCache:
    """Keeps track of recently used collections to avoid having to reload them over and over."""

    def __init__(
        self,
        api_client: arvados.api.ThreadSafeAPIClient,
        keep_client: arvados.keep.KeepClient,
        num_retries: int,
        cap: int = 256 * 1024 * 1024,
        min_entries: int = 2,
    ) -> None:
        """Create a new collection cache."""
        self.api_client = api_client
        self.keep_client = keep_client
        self.num_retries = num_retries
        self.collections: OrderedDict[
            str, Tuple[arvados.collection.CollectionReader, int]
        ] = OrderedDict()
        self.lock = threading.Lock()
        self.total = 0
        self.cap = cap
        self.min_entries = min_entries

    def set_cap(self, cap: int) -> None:
        """Set the cache cap."""
        self.cap = cap

    def cap_cache(self, required: int) -> None:
        """Remove collections until the cache usage is under the cap."""
        # ordered dict iterates from oldest to newest
        for pdh, v in list(self.collections.items()):
            available = self.cap - self.total
            if available >= required or len(self.collections) < self.min_entries:
                return
            # cut it loose
            logger.debug(
                "Evicting collection reader %s from cache (cap %s total %s required %s)",
                pdh,
                self.cap,
                self.total,
                required,
            )
            del self.collections[pdh]
            self.total -= v[1]

    def get(self, locator: str) -> arvados.collection.CollectionReader:
        """Get a collection.  Returns cached version if possible, creates a new reader if not."""
        with self.lock:
            if locator not in self.collections:
                m = pdh_size.match(locator)
                if m:
                    self.cap_cache(int(m.group(2)) * 128)
                logger.debug("Creating collection reader for %s", locator)
                try:
                    cr = arvados.collection.CollectionReader(
                        locator,
                        api_client=self.api_client,
                        keep_client=self.keep_client,
                        num_retries=self.num_retries,
                    )
                except arvados.errors.ApiError as ap:
                    raise IOError(
                        errno.ENOENT,
                        "Could not access collection '%s': %s"
                        % (locator, str(ap._get_reason())),
                    ) from ap
                sz = len(cr.manifest_text()) * 128
                self.collections[locator] = (cr, sz)
                self.total += sz
            else:
                cr, sz = self.collections[locator]
                # bump it to the back
                del self.collections[locator]
                self.collections[locator] = (cr, sz)
            return cr


class CollectionFsAccess(cwltest.stdfsaccess.StdFsAccess):
    """Implement the cwltool FsAccess interface for Arvados Collections."""

    def __init__(self, basedir: str, collection_cache: CollectionCache) -> None:
        """Create Arvados collection access object."""
        super(CollectionFsAccess, self).__init__(basedir)
        self.collection_cache = collection_cache

    def get_collection(
        self, path: str
    ) -> Tuple[Optional[arvados.collection.CollectionReader], Optional[str]]:
        """If it is a keep: URI, get the collection."""
        sp = path.split("/", 1)
        p = sp[0]
        if p.startswith("keep:") and (
            arvados.util.keep_locator_pattern.match(p[5:])
            or arvados.util.collection_uuid_pattern.match(p[5:])
        ):
            locator = p[5:]
            rest = (
                os.path.normpath(urllib.parse.unquote(sp[1])) if len(sp) == 2 else None
            )
            return (self.collection_cache.get(locator), rest)
        else:
            return (None, path)

    def open(self, fn: str, mode: str, encoding: Optional[str] = None) -> IO[bytes]:
        """Open a file from a keep: or file: URI."""
        collection, rest = self.get_collection(fn)
        if collection is not None and rest is not None:
            return collection.open(rest, mode, encoding=encoding)
        else:
            return super(CollectionFsAccess, self).open(self._abs(fn), mode)

    def size(self, fn: str) -> int:
        """Get the size of the file resource pointed to by a URI."""
        collection, rest = self.get_collection(fn)
        if collection is not None:
            if rest:
                arvfile = collection.find(rest)
                if isinstance(arvfile, arvados.arvfile.ArvadosFile):
                    return arvfile.size()
            raise IOError(errno.EINVAL, "Not a path to a file %s" % (fn))
        else:
            return super(CollectionFsAccess, self).size(fn)

    def isfile(self, fn: str) -> bool:
        """Determine if a resource pointed to by a URI represents a file."""
        collection, rest = self.get_collection(fn)
        if collection is not None:
            if rest:
                return isinstance(collection.find(rest), arvados.arvfile.ArvadosFile)
            else:
                return False
        else:
            return super(CollectionFsAccess, self).isfile(fn)

    def isdir(self, fn: str) -> bool:
        """Determine if a resource pointed to by a URI represents a directory."""
        collection, rest = self.get_collection(fn)
        if collection is not None:
            if rest:
                return isinstance(
                    collection.find(rest), arvados.collection.RichCollectionBase
                )
            else:
                return True
        else:
            return super(CollectionFsAccess, self).isdir(fn)
