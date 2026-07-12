from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_qr.py <ruta_png> [target_url_esperado]")
        return 2
    path = Path(sys.argv[1])
    expected = sys.argv[2] if len(sys.argv) > 2 else None
    if not path.is_file():
        print(f"file: {path}")
        print("exists: no")
        return 1

    image = Image.open(path)
    decoded = _decode_with_opencv(path)

    print(f"file: {path}")
    print(f"exists: yes")
    print(f"format: {image.format}")
    print(f"size: {image.size[0]}x{image.size[1]}")
    print(f"mode: {image.mode}")
    print(f"decoded: {decoded or '(not decoded)'}")
    if expected is not None:
        print(f"expected: {expected}")
        print(f"matches_expected: {decoded == expected}")
    return 0 if expected is None or decoded == expected else 1


def _decode_with_opencv(path: Path) -> str:
    try:
        import cv2
    except ImportError:
        return ""
    image = cv2.imread(str(path))
    if image is None:
        return ""
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    return decoded or ""


if __name__ == "__main__":
    raise SystemExit(main())
