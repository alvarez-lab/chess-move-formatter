import argparse
import sys

from .formatter import MoveFormatError, normalize_game, normalize_move


def build_parser():
    parser = argparse.ArgumentParser(
        prog="chessfmt",
        description="Normalize chess move notation into strict SAN.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="file of move text to read; defaults to stdin",
    )
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="accept common non-standard notation instead of rejecting it",
    )
    parser.add_argument(
        "--move",
        metavar="TOKEN",
        help="normalize a single move token instead of a whole game",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.move is not None:
        try:
            print(normalize_move(args.move, lenient=args.lenient))
        except MoveFormatError as exc:
            print(f"chessfmt: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    try:
        print(normalize_game(text, lenient=args.lenient))
    except MoveFormatError as exc:
        print(f"chessfmt: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
