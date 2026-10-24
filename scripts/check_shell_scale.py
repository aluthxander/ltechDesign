"""Qt scale-factor layout smoke; does not change Windows display settings."""

import json
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ltechdesign.ui.window import StudioWindow

app = QApplication([])
window = StudioWindow()
window.show()
app.processEvents()
if len(sys.argv) > 2:
    import time

    window.open_path(sys.argv[2], read_only=True)
    deadline = time.monotonic() + 15
    while window.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert not window.busy and window.current is not None
output = Path(sys.argv[1])
output.parent.mkdir(parents=True, exist_ok=True)
assert window.grab().save(str(output))
assert window.tabs.width() > 100
assert window.object_name.width() > 50
assert window.pages.width() > 50
print(
    json.dumps(
        {
            "dpr": window.devicePixelRatioF(),
            "size": [window.width(), window.height()],
            "canvas_width": window.tabs.width(),
            "screenshot": str(output),
        }
    )
)
while window.documents:
    window.close_tab(0)
    while window.busy:
        app.processEvents()
window.close()
