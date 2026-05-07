"""Allow running the package as ``python -m visual_crypto``."""

from .cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
