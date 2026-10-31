"""RapidFuzz implementation of the application-owned name distance seam."""

from rapidfuzz.distance import DamerauLevenshtein


class RapidFuzzNameDistance:
    """Calculate edit distance without deciding spelling eligibility."""

    def distance(self, left: str, right: str) -> int:
        """Count insertions, deletions, substitutions and adjacent swaps."""
        return DamerauLevenshtein.distance(left, right)
