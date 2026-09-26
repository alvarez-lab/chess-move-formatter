"""Track piece positions across a game so moves can be checked against what
is actually on the board, not just against SAN's shape.

This does not (yet) know about check: it will happily let you move a pinned
piece or walk your king into an attack. It only verifies the mechanical
parts of legality - a piece of the right kind exists, it can reach the
destination given the pieces in its way, and the capture/non-capture marker
matches what's actually on the destination square.
"""

_FILES = "abcdefgh"
_BACK_RANK = "RNBQKBNR"

_KNIGHT_OFFSETS = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
_KING_OFFSETS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
_BISHOP_DIRS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
_ROOK_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
_QUEEN_DIRS = _BISHOP_DIRS + _ROOK_DIRS


class IllegalMoveError(ValueError):
    """Raised when a move is well-formed SAN but not legal on this board."""


def _offset(square, dx, dy):
    file_i = _FILES.index(square[0]) + dx
    rank_i = int(square[1]) + dy
    if 0 <= file_i < 8 and 1 <= rank_i <= 8:
        return _FILES[file_i] + str(rank_i)
    return None


class Board:
    """A sparse map of occupied squares to (color, piece letter)."""

    def __init__(self):
        self.squares = {}
        for i, letter in enumerate(_BACK_RANK):
            file_letter = _FILES[i]
            self.squares[file_letter + "1"] = ("w", letter)
            self.squares[file_letter + "2"] = ("w", "P")
            self.squares[file_letter + "7"] = ("b", "P")
            self.squares[file_letter + "8"] = ("b", letter)
        # Square a pawn skipped over on its last double-step, if any -
        # the only square an en passant capture may currently target.
        self.en_passant_target = None

    def apply_castle(self, color, *, queenside):
        rank = "1" if color == "w" else "8"
        king_from = "e" + rank
        if self.squares.get(king_from) != (color, "K"):
            raise IllegalMoveError(f"no {color} king on {king_from} to castle")

        rook_file = "a" if queenside else "h"
        rook_from = rook_file + rank
        if self.squares.get(rook_from) != (color, "R"):
            raise IllegalMoveError(f"no {color} rook on {rook_from} to castle")

        between = ("b", "c", "d") if queenside else ("f", "g")
        for file_letter in between:
            if (file_letter + rank) in self.squares:
                raise IllegalMoveError(f"castling blocked on {file_letter}{rank}")

        king_to = ("c" if queenside else "g") + rank
        rook_to = ("d" if queenside else "f") + rank
        del self.squares[king_from]
        del self.squares[rook_from]
        self.squares[king_to] = (color, "K")
        self.squares[rook_to] = (color, "R")
        self.en_passant_target = None

    def apply_move(self, color, *, piece, from_file, from_rank, capture, dest, promotion):
        piece = piece or "P"

        if piece == "P":
            candidates = self._pawn_candidates(dest, color, capture)
        elif piece == "N":
            candidates = self._step_candidates(dest, _KNIGHT_OFFSETS, color, "N")
        elif piece == "K":
            candidates = self._step_candidates(dest, _KING_OFFSETS, color, "K")
        elif piece == "B":
            candidates = self._ray_candidates(dest, _BISHOP_DIRS, color, "B")
        elif piece == "R":
            candidates = self._ray_candidates(dest, _ROOK_DIRS, color, "R")
        elif piece == "Q":
            candidates = self._ray_candidates(dest, _QUEEN_DIRS, color, "Q")
        else:
            raise IllegalMoveError(f"unknown piece {piece!r}")

        if from_file:
            candidates = [sq for sq in candidates if sq[0] == from_file]
        if from_rank:
            candidates = [sq for sq in candidates if sq[1] == from_rank]

        if not candidates:
            raise IllegalMoveError(f"no {color} {piece} can reach {dest}")
        if len(candidates) > 1:
            raise IllegalMoveError(
                f"ambiguous move: more than one {color} {piece} can reach {dest}"
            )
        src = candidates[0]

        dest_occupant = self.squares.get(dest)
        is_en_passant = (
            piece == "P"
            and capture
            and dest_occupant is None
            and dest == self.en_passant_target
        )

        if capture:
            if dest_occupant is None and not is_en_passant:
                raise IllegalMoveError(f"{dest} is empty, but move was written as a capture")
            if dest_occupant is not None and dest_occupant[0] == color:
                raise IllegalMoveError(f"cannot capture own piece on {dest}")
        elif dest_occupant is not None:
            raise IllegalMoveError(f"{dest} is occupied, but move was not written as a capture")

        promotes = dest[1] in ("1", "8")
        if promotion and not (piece == "P" and promotes):
            raise IllegalMoveError("promotion specified on a move that isn't a pawn reaching the last rank")
        if piece == "P" and promotes and not promotion:
            raise IllegalMoveError(f"pawn reaching {dest} must specify a promotion piece")

        captured_square = None
        if is_en_passant:
            captured_square = dest[0] + src[1]
            opponent = "b" if color == "w" else "w"
            if self.squares.get(captured_square) != (opponent, "P"):
                raise IllegalMoveError(f"no pawn to capture en passant on {captured_square}")

        del self.squares[src]
        if captured_square is not None:
            del self.squares[captured_square]
        self.squares[dest] = (color, promotion[-1] if promotion else piece)

        if piece == "P" and abs(int(dest[1]) - int(src[1])) == 2:
            mid_rank = (int(dest[1]) + int(src[1])) // 2
            self.en_passant_target = dest[0] + str(mid_rank)
        else:
            self.en_passant_target = None

    def _ray_candidates(self, dest, dirs, color, piece):
        results = []
        for dx, dy in dirs:
            sq = dest
            while True:
                sq = _offset(sq, dx, dy)
                if sq is None:
                    break
                occupant = self.squares.get(sq)
                if occupant is None:
                    continue
                if occupant == (color, piece):
                    results.append(sq)
                break
        return results

    def _step_candidates(self, dest, offsets, color, piece):
        results = []
        for dx, dy in offsets:
            sq = _offset(dest, dx, dy)
            if sq is not None and self.squares.get(sq) == (color, piece):
                results.append(sq)
        return results

    def _pawn_candidates(self, dest, color, capture):
        direction = 1 if color == "w" else -1
        dest_file_i = _FILES.index(dest[0])
        dest_rank = int(dest[1])
        results = []

        if capture:
            for df in (-1, 1):
                file_i = dest_file_i + df
                if 0 <= file_i < 8:
                    src_rank = dest_rank - direction
                    if 1 <= src_rank <= 8:
                        src = _FILES[file_i] + str(src_rank)
                        if self.squares.get(src) == (color, "P"):
                            results.append(src)
            return results

        one_back = dest_rank - direction
        if 1 <= one_back <= 8:
            src = dest[0] + str(one_back)
            if self.squares.get(src) == (color, "P"):
                results.append(src)

        start_rank = 2 if color == "w" else 7
        two_back = dest_rank - 2 * direction
        if two_back == start_rank:
            src = dest[0] + str(two_back)
            mid = dest[0] + str(one_back)
            if self.squares.get(src) == (color, "P") and mid not in self.squares:
                results.append(src)

        return results
