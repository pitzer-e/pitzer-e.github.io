"""Compatibility entry point: rebuild all artifacts from the local source snapshot."""
from run_pipeline import main

if __name__ == '__main__':
    main(default_local=True)
