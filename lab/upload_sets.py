"""Upload lab sets from the local store to the hosted curator: `python -m lab.upload_sets X5 X6`.

Every rendered cell of each set goes to /api/upload with its PNG (the infotext rides in it), the
cells the curator already holds are skipped, then send_register sends the sets' names and
predictions, and each set is read back to show how many cells the curator lists. The curator
comes from STILLSTIFT_CURATOR_URL, _USER and _PASSWORD.
"""

from __future__ import annotations

import sys
from contextlib import closing

from stillstift.curator import CuratorClient, CuratorError
from stillstift.store import Store
from stillstift.sync import send_register


def upload(client: CuratorClient, store: Store, entry: str) -> int:
    """Upload the set's rendered cells the curator lacks; return how many were sent."""
    held = client.rendered_cells(entry)
    sent = 0
    for cell in store.cells(entry):
        if cell.cell_id in held or cell.image_path is None or not cell.image_path.is_file():
            continue
        client.upload(cell, cell.image_path.read_bytes())
        sent += 1
    return sent


def main(argv: list[str]) -> int:
    if not argv:
        sys.stderr.write("usage: python -m lab.upload_sets <set> [<set> ...]\n")
        return 1
    client = CuratorClient.from_env()
    if client is None:
        sys.stderr.write("upload: set STILLSTIFT_CURATOR_URL, _USER and _PASSWORD\n")
        return 1
    try:
        with closing(client), closing(Store.open()) as store:
            for entry in argv:
                sent = upload(client, store, entry)
                sys.stdout.write(f"{entry}: {sent} uploaded\n")
            names, predictions = send_register(client, set(argv))
            sys.stdout.write(f"register: {names} names, {predictions} predictions kept\n")
            for entry in argv:
                exported = client.export(entry)
                count = 0 if exported is None else len(exported.cells)
                sys.stdout.write(f"{entry}: the curator lists {count} cells\n")
    except CuratorError as error:
        sys.stderr.write(f"upload: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
