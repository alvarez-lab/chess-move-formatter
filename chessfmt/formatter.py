"""Normalize chess move notation into strict Standard Algebraic Notation (SAN)."""

import re

PIECE_LETTERS = "KQRBN"

CASTLE_KINGSIDE = "O-O"
CASTLE_QUEENSIDE = "O-O-O"

# Piece letters that can be safely upper-cased when fixing lowercase input.
# 'b' is deliberately excluded: lowercase 'b' is also a valid file letter
# (b-file), so "bxc4" is genuinely ambiguous between a pawn capture and a
# bishop move and must not be guessed at, even in lenient mode.
_SAFE_LOWERCASE_PIECES = "kqrn"

_SAN_RE = re.compile(
    r"^(?P<piece>[KQRBN])?"
    r"(?P<from_file>[a-h])?(?P<from_rank>[1-8])?"
    r"(?P<capture>x)?"
    r"(?P<dest>[a-h][1-8])"
    r"(?P<promotion>=[QRBN])?"
    r"(?P<check>[+#])?$"
)

_CASTLE_RE = re.compile(r"^(?P<side>[Oo0]-[Oo0](?:-[Oo0])?)(?P<check>[+#])?$")

_MOVE_NUMBER_RE = re.compile(r"^\d+\.+$")

_RESULT_TOKENS = frozenset({"1-0", "0-1", "1/2-1/2", "*"})


class MoveFormatError(ValueError):
    """Raised when a move token cannot be parsed as valid (or fixable) SAN."""


def normalize_move(token, *, lenient=False):
    """Normalize a single move token, e.g. 'nxe4' -> 'Nxe4' in lenient mode.

    In strict mode (the default) only cosmetic whitespace is trimmed; any
    move that isn't already unambiguous, canonical SAN raises
    MoveFormatError. In lenient mode a fixed set of common shorthand and
    transcription quirks are corrected first.
    """
    raw = token.strip()
    if not raw:
        raise MoveFormatError("empty move")

    castled = _normalize_castling(raw, lenient=lenient)
    if castled is not None:
        return castled

    candidate = _apply_lenient_fixes(raw) if lenient else raw

    match = _SAN_RE.match(candidate)
    if not match:
        raise MoveFormatError(f"unrecognized move: {token!r}")

    piece = match.group("piece") or ""
    from_file = match.group("from_file") or ""
    from_rank = match.group("from_rank") or ""
    capture = "x" if match.group("capture") else ""
    dest = match.group("dest")
    promotion = match.group("promotion") or ""
    check = match.group("check") or ""

    return f"{piece}{from_file}{from_rank}{capture}{dest}{promotion}{check}"


def normalize_game(text, *, lenient=False):
    """Normalize a whitespace-separated stream of move numbers and moves.

    Move numbers are renumbered from the surviving moves rather than kept
    verbatim, so gaps or typos in the source numbering don't propagate.
    Game result markers (1-0, 0-1, 1/2-1/2, *) pass through unchanged.
    """
    output = []
    move_number = 1
    white_to_move = True

    for raw_token in text.split():
        if _MOVE_NUMBER_RE.match(raw_token):
            continue
        if raw_token in _RESULT_TOKENS:
            output.append(raw_token)
            continue

        try:
            normalized = normalize_move(raw_token, lenient=lenient)
        except MoveFormatError as exc:
            side = "white" if white_to_move else "black"
            raise MoveFormatError(f"move {move_number} ({side}): {exc}") from exc

        if white_to_move:
            output.append(f"{move_number}.{normalized}")
        else:
            output.append(normalized)
            move_number += 1
        white_to_move = not white_to_move

    return " ".join(output)


def _normalize_castling(raw, *, lenient):
    match = _CASTLE_RE.match(raw)
    if not match:
        return None

    side = match.group("side")
    check = match.group("check") or ""
    is_queenside = side.count("-") == 2
    canonical = CASTLE_QUEENSIDE if is_queenside else CASTLE_KINGSIDE

    if not lenient and side != canonical:
        raise MoveFormatError(
            f"castling must be written {canonical!r}, got {raw!r} "
            "(pass --lenient to accept 0-0 style notation)"
        )

    return canonical + check


def _apply_lenient_fixes(raw):
    fixed = raw

    # Drop trailing annotation glyphs (!, ?, !!, ?!, !?, ??).
    fixed = re.sub(r"[!?]+$", "", fixed)

    # Accept ':' as a capture marker, an older convention than 'x'.
    fixed = fixed.replace(":", "x")

    # Drop a trailing en passant annotation; it's informational, not part
    # of the move's identity once the destination square is known.
    fixed = re.sub(r"\s*e\.?p\.?$", "", fixed, flags=re.IGNORECASE)

    if fixed[:1] in _SAFE_LOWERCASE_PIECES:
        fixed = fixed[0].upper() + fixed[1:]

    # Accept promotion without the '=' separator, e.g. 'e8Q' or 'e8(Q)'.
    fixed = re.sub(r"(?<=[1-8])\(?([QRBN])\)?$", r"=\1", fixed)

    return fixed
