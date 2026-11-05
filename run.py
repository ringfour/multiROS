"""Source entrypoint: works from a pinned submodule without installing a package."""
from multiros.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
