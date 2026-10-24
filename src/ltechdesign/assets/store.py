"""Process-local immutable blobs with transactional roots and explicit independent leases.

One retention adapter per dispatcher; job/recovery/snapshot leases outlive its close.
Persistent recovery inventories are the responsibility of segment 14.
"""

import threading
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from uuid import uuid4

from ltechdesign.domain.errors import fail
from ltechdesign.domain.models import Asset, AssetId

from .validation import validate_asset


class BlobStore:
    def __init__(self, *, byte_budget: int = 512 * 1024 * 1024) -> None:
        if type(byte_budget) is not int or not 1 <= byte_budget <= 512 * 1024 * 1024:
            raise ValueError("Invalid blob budget")
        self._budget = byte_budget
        self._lock = threading.RLock()
        self._blobs: dict[str, bytes] = {}
        self._staged: dict[str, Asset] = {}
        self._reserved: set[str] = set()
        self._roots: dict[str, frozenset[str]] = {}
        self._pending = 0

    def _put(self, asset: Asset, payload: bytes) -> None:
        validate_asset(asset, payload)
        if asset.path not in self._blobs:
            if sum(map(len, self._blobs.values())) + len(payload) > self._budget:
                fail("blob_store_bytes", code="limit_exceeded")
            self._blobs[asset.path] = payload

    def stage(self, asset: Asset, payload: bytes) -> str:
        with self._lock:
            self._put(asset, payload)
            key = str(uuid4())
            self._staged[key] = asset
            return key

    def admit(self, assets: tuple[Asset, ...], blobs: Mapping[str, bytes]) -> "BlobLease":
        """Validate whole load in a private store, then atomically import and pin it."""
        if set(blobs) != {asset.path for asset in assets}:
            fail("asset_inventory_mismatch")
        staging = BlobStore(byte_budget=self._budget)
        for asset in assets:
            staging._put(asset, blobs[asset.path])
        with self._lock:
            merged = self._blobs | staging._blobs
            if sum(map(len, merged.values())) > self._budget:
                fail("blob_store_bytes", code="limit_exceeded")
            self._blobs = merged
            return self.pin(assets)

    def _paths(self, assets: Mapping[AssetId, Asset]) -> frozenset[str]:
        for asset in assets.values():
            payload = self._blobs.get(asset.path)
            if payload is None or len(payload) != asset.byte_length:
                fail("missing_asset", asset_id=asset.id)
        return frozenset(a.path for a in assets.values())

    def pin(self, assets: tuple[Asset, ...]) -> "BlobLease":
        """Pin a live snapshot, named snapshot, recovery inventory or queued/running job."""
        with self._lock:
            paths = self._paths({a.id: a for a in assets})
            key = str(uuid4())
            self._roots[key] = paths
            return BlobLease(self, key, MappingProxyType({p: self._blobs[p] for p in paths}))

    def retention(self) -> "StoreRetention":
        with self._lock:
            key = str(uuid4())
            self._roots[key] = frozenset()
            return StoreRetention(self, key)

    def collect(self) -> tuple[str, ...]:
        with self._lock:
            if self._pending:
                fail("asset_transaction_active", code="queue_full")
            marked = {a.path for a in self._staged.values()}
            for paths in self._roots.values():
                marked.update(paths)
            removed = tuple(p for p in self._blobs if p not in marked)
            for path in removed:
                del self._blobs[path]
            return removed


@dataclass(slots=True)
class BlobLease:
    _store: BlobStore
    _key: str
    blobs: Mapping[str, bytes]

    def release(self) -> None:
        with self._store._lock:
            self._store._roots.pop(self._key, None)
            self.blobs = MappingProxyType({})

    def __enter__(self) -> "BlobLease":
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


@dataclass(slots=True)
class StoreRetention:
    _store: BlobStore
    _key: str

    def prepare(self, roots: Mapping[AssetId, Asset], staged: Mapping[str, Asset]) -> "Prepared":
        with self._store._lock:
            if self._store._reserved.intersection(staged):
                fail("staging_in_use", code="queue_full")
            if any(self._store._staged.get(key) != asset for key, asset in staged.items()):
                fail("invalid_staging_id")
            paths = self._store._paths(roots)
            self._store._reserved.update(staged)
            self._store._pending += 1
            return Prepared(self, paths, tuple(staged))

    def discard(self, staged: Mapping[str, Asset]) -> None:
        with self._store._lock:
            for key in staged:
                if key not in self._store._reserved:
                    self._store._staged.pop(key, None)


@dataclass(slots=True)
class Prepared:
    _retention: StoreRetention
    _paths: frozenset[str]
    _staged: tuple[str, ...]
    _finished: bool = False

    def _finish(self, commit: bool) -> None:
        store = self._retention._store
        with store._lock:
            if self._finished:
                return
            if commit:
                store._roots[self._retention._key] = self._paths
            for key in self._staged:
                store._staged.pop(key, None)
                store._reserved.discard(key)
            store._pending -= 1
            self._finished = True

    def commit(self) -> None:
        self._finish(True)

    def abort(self) -> None:
        self._finish(False)
