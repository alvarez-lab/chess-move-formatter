# chess-move-formatter

A command-line formatter that takes messy chess move notation and turns it
into strict Standard Algebraic Notation (SAN).

Move text copied out of old books, forum posts, or someone's hand-typed
game log is rarely clean SAN: castling written as `0-0` instead of `O-O`,
captures marked with `:` instead of `x`, piece letters in lowercase,
promotions written as `e8Q` instead of `e8=Q`, stray `!` and `?`
annotations left on the end of moves. Feeding that straight into a PGN
parser tends to blow up somewhere downstream. This tool normalizes it
first, and it is strict by default: if a move isn't already unambiguous
SAN, it fails loudly instead of guessing.

## Why strict by default

Silently "fixing" ambiguous notation is how you end up with a game
transcript that doesn't match what was actually played. `chessfmt` only
rewrites cosmetic differences (whitespace) unless you explicitly ask for
more. Pass `--lenient` when you know the input is messy and you're willing
to accept its best-effort corrections.

## Usage

Normalize a whole game read from stdin:

```
$ echo "1. e4 e5 2. Nf3 Nc6 3. Bb5" | python -m chessfmt.cli
1.e4 e5 2.Nf3 Nc6 3.Bb5
```

Strict mode rejects non-standard castling notation:

```
$ echo "1. e4 e5 2. Nf3 Nc6 3. 0-0" | python -m chessfmt.cli
chessfmt: move 3 (white): castling must be written 'O-O', got '0-0' (pass --lenient to accept 0-0 style notation)
```

`--lenient` accepts it, along with a handful of other common quirks:

```
$ echo "1. e4 e5 2. nf3 Nc6 3. 0-0 a6 4. Bxc6 dxc6" | python -m chessfmt.cli --lenient
1.e4 e5 2.Nf3 Nc6 3.O-O a6 4.Bxc6 dxc6
```

Normalize one move at a time with `--move`, useful for scripting or tests:

```
$ python -m chessfmt.cli --move "Q:a8!" --lenient
Qxa8
$ python -m chessfmt.cli --move "e8Q" --lenient
e8=Q
```

## What lenient mode fixes

- `0-0` / `0-0-0` -> `O-O` / `O-O-O`
- `:` used as a capture marker -> `x`
- lowercase piece letters (`n`, `q`, `r`, `k`) -> uppercase. Lowercase `b`
  is left alone on purpose, since it's ambiguous with the b-file.
- promotions without `=` (`e8Q`, `e8(Q)`) -> `e8=Q`
- trailing annotation glyphs (`!`, `?`, `!!`, `?!`, etc.) are stripped
- a trailing `e.p.` en passant annotation is stripped

Everything else that isn't recognizable as SAN still raises an error, in
both modes.

## Status

Early skeleton: single-move and whole-game text normalization work, but
there's no board-state tracking yet, so moves are checked for shape, not
legality. See the roadmap in the project notes for what's next.

## Installing

No dependencies beyond the standard library. From this directory:

```
pip install -e .
chessfmt --lenient game.txt
```

Or run it without installing:

```
python -m chessfmt.cli --lenient game.txt
```
