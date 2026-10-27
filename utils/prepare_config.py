#!/usr/bin/env python3
"""Resolve a checked-in firmware configuration for the current checkout."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = args.config.resolve()
    output = args.output.resolve()
    if source == output:
        parser.error("output must differ from the source configuration")
    try:
        config = json.loads(source.read_text())
        for region in config["flash"]:
            firmware = Path(region["file"])
            if not firmware.is_absolute():
                firmware = source.parent / firmware
            firmware = firmware.resolve(strict=True)
            if not firmware.is_file():
                raise ValueError(f"not a firmware file: {firmware}")
            region["file"] = str(firmware)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(config, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
