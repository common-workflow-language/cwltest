import argparse
import sys
from time import sleep

from cwltest import UNSUPPORTED_FEATURE

UNSUPPORTED_FEATURE_TOOL = "return-unsupported.cwl"
ERROR_TOOL = "return-1.cwl"
TIMEOUT_TOOL = "timeout.cwl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("processfile")
    parser.add_argument("jobfile")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0")
    parser.add_argument("--outdir")
    parser.add_argument("--quiet", action="store_true")

    args = parser.parse_args()

    if args.processfile.endswith(UNSUPPORTED_FEATURE_TOOL):
        exit(UNSUPPORTED_FEATURE)
    elif args.processfile.endswith(ERROR_TOOL):
        exit(1)
    elif args.processfile.endswith(TIMEOUT_TOOL):
        print("timeout stderr", file=sys.stderr)
        sys.stderr.flush()
        sleep(100000)
        exit(1)

    exit(0)


if __name__ == "__main__":
    main()
