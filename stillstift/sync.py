"""Send the register's set names and blind predictions to a curator, local or hosted."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from stillstift.register import INDEX, PREDS, index_names, predictions_of

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from pathlib import Path

    from stillstift.store import Prediction, SetName


class RegisterSink(Protocol):
    """A curator that keeps set names and predictions: the local store or the hosted client."""

    def put_set_names(self, names: Mapping[str, SetName]) -> int: ...

    def put_predictions(self, predictions: Iterable[Prediction]) -> int: ...


def send_register(
    sink: RegisterSink,
    entries: Collection[str] | None = None,
    index: Path = INDEX,
    preds: Path = PREDS,
) -> tuple[int, int]:
    """Send the names and predictions of the sets named, or of every set; return both counts.

    The count of predictions is the cells the curator held, so a set not yet rendered counts 0.
    """
    names = {e: n for e, n in index_names(index).items() if entries is None or e in entries}
    predictions = [p for p in predictions_of(preds) if entries is None or p.entry in entries]
    return sink.put_set_names(names), sink.put_predictions(predictions)
