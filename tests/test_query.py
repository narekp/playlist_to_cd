"""Tests for core.query."""

from core.query import build_query_variants


class TestBuildQueryVariants:
    def test_single_artist_simple_title_exact(self):
        assert build_query_variants("Jack Johnson", "Banana Pancakes") == [
            "Jack Johnson Banana Pancakes"
        ]

    def test_multi_artist_includes_full_artist_context_in_order(self):
        assert build_query_variants("A, B, C", "Track") == [
            "A Track",
            "A, B, C Track",
        ]

    def test_title_with_parenthetical_adds_simplified_variant(self):
        assert build_query_variants("Artist", "Song (Remix)") == [
            "Artist Song (Remix)",
            "Artist Song",
        ]

    def test_title_with_quotes_adds_simplified_variant(self):
        assert build_query_variants("Artist", 'Song "Live"') == [
            'Artist Song "Live"',
            "Artist Song",
        ]

    def test_extra_spaces_preserve_then_normalize_in_order(self):
        assert build_query_variants("A, B", "  Song   Title  ") == [
            "A Song   Title",
            "A, B Song   Title",
            "A Song Title",
            "A, B Song Title",
        ]

    def test_empty_artist_falls_back_to_unknown_artist_variant(self):
        assert build_query_variants("", "Track") == ["Unknown Track"]

    def test_empty_track_falls_back_to_artist_with_trailing_space(self):
        assert build_query_variants("Artist", "") == ["Artist "]
