"""Media mutation contract remains fully usable without Qt or source files."""

from dataclasses import replace
from typing import Literal

import pytest

from ltechdesign.commands import Create, Dispatcher, RegisterAsset, Request, Result, SetMedia
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.models import Asset, AssetId, Crop, DocumentSession, MediaData, Style

pytestmark = pytest.mark.core


class Retention:
    def prepare(self, *_: object) -> "Retention":
        return self

    def commit(self) -> None:
        pass

    def abort(self) -> None:
        pass

    def discard(self, *_: object) -> None:
        pass


def test_set_media_preserves_container_and_undoes_cross_type_replace() -> None:
    p = create_project()
    image = Asset(
        id=AssetId("raster"),
        path="assets/data/" + "a" * 64,
        sha256="a" * 64,
        media_type="image/png",
        byte_length=1,
    )
    vector = replace(
        image,
        id=AssetId("vector"),
        media_type="image/svg+xml",
        path="assets/data/" + "b" * 64,
        sha256="b" * 64,
    )
    d = Dispatcher(DocumentSession(project=p), assets=Retention())

    def dispatch(
        ops: tuple[Operation, ...] = (), action: Literal["execute", "undo", "redo"] = "execute"
    ) -> Result:
        from uuid import uuid4

        return d.dispatch(
            Request(
                session_id=d.snapshot.session_id,
                expected_revision=d.snapshot.revision,
                request_id=str(uuid4()),
                action_name="Media",
                source="GUI",
                operations=ops,
                action=action,
            ),
            client_id="test",
        )

    node = replace(
        create_node(
            "image", p.document.pages[0].id, width=120, height=75, data=MediaData(asset_id=image.id)
        ),
        x=18,
        y=29,
        rotation=37,
        opacity=0.4,
        style=Style(radius=(10, 5, 8, 12)),
    )
    assert dispatch((RegisterAsset(asset=image, staging_id="a"), Create(node=node))).ok
    before = d.snapshot.project
    data = MediaData(asset_id=vector.id, fit="fill", crop=Crop(x=0.2, width=0.6))
    assert dispatch(
        (RegisterAsset(asset=vector, staging_id="b"), SetMedia(node_id=node.id, data=data))
    ).ok
    changed = d.snapshot.project.document.nodes[node.id]
    assert replace(changed, type=node.type, data=node.data) == node
    assert changed.type == "svg" and changed.data == data
    assert dispatch(action="undo").ok
    assert d.snapshot.project == before
    assert dispatch(action="redo").ok
    assert d.snapshot.project.document.nodes[node.id] == changed
    unchanged = d.snapshot
    error = dispatch((SetMedia(node_id=node.id, data=MediaData(asset_id=AssetId("absent"))),))
    assert not error.ok and d.snapshot == unchanged
    d.close()


def test_crop_validation_prevents_partial_mutations() -> None:
    from ltechdesign.domain.errors import ModelError

    for values in (dict(x=0.8, width=0.5), dict(height=0), dict(y=float("nan")), dict(width=-1)):
        with pytest.raises(ModelError):
            Crop(**values)
