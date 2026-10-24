"""Asset two-phase retention port; disk/blob implementation belongs to segment 04.

prepare must pin all roots and validate/own staging without publishing registrations.
Failure leaves prior roots intact. abort discards owned staging and temporary pins.
commit is a NON-THROWING in-memory root/registration swap: all fallible I/O belongs
in prepare. No callback, GC or filesystem I/O may run between commit and publication.
Store GC additionally marks independent snapshot/recovery/queued/running-job leases;
never collect while prepare/commit is active. Client timeout must not release leases.
"""

from collections.abc import Mapping
from typing import Protocol

from ltechdesign.domain.errors import fail
from ltechdesign.domain.models import Asset, AssetId


class PreparedAssets(Protocol):
    def commit(self) -> None: ...
    def abort(self) -> None: ...


class AssetRetention(Protocol):
    def prepare(
        self, roots: Mapping[AssetId, Asset], staged: Mapping[str, Asset]
    ) -> PreparedAssets: ...

    def discard(self, staged: Mapping[str, Asset]) -> None:
        """Idempotent, non-throwing cleanup on failure before prepare succeeds."""
        ...


class MetadataOnlyRetention:
    """No byte ownership claim. Existing assets remain the admission service's lease.

    Native blob registration cannot succeed accidentally without a real store adapter.
    """

    def prepare(
        self, roots: Mapping[AssetId, Asset], staged: Mapping[str, Asset]
    ) -> PreparedAssets:
        if staged:
            fail("asset_store_unavailable", code="unsupported_capability")
        return self

    def discard(self, staged: Mapping[str, Asset]) -> None:
        pass

    def commit(self) -> None:
        pass

    def abort(self) -> None:
        pass
