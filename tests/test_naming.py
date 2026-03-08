"""Tests for core.naming."""
import pytest

from core.naming import format_artists_for_filename, format_artists_for_metadata, safe_name


class TestSafeName:
    def test_normal_string(self):
        assert safe_name("Banana Pancakes") == "Banana Pancakes"

    def test_empty_and_none(self):
        assert safe_name("") == "unknown"
        assert safe_name(None) == "unknown"
        assert safe_name("   ") == "unknown"

    def test_invalid_chars_replaced(self):
        assert safe_name('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"

    def test_multiple_spaces_collapsed(self):
        assert safe_name("  a   b   c  ") == "a b c"

    def test_truncation_at_180(self):
        long_str = "a" * 200
        assert len(safe_name(long_str)) == 180
        assert safe_name(long_str) == "a" * 180


class TestFormatArtistsForFilename:
    def test_empty(self):
        assert format_artists_for_filename("") == "Unknown"
        assert format_artists_for_filename(None) == "Unknown"

    def test_single_artist(self):
        assert format_artists_for_filename("Jack Johnson") == "Jack Johnson"

    def test_multiple_artists_comma(self):
        assert format_artists_for_filename("A, B, C") == "A, B, C"

    def test_multiple_artists_semicolon(self):
        assert format_artists_for_filename("A; B; C") == "A, B, C"


class TestFormatArtistsForMetadata:
    def test_empty(self):
        assert format_artists_for_metadata("") == "Unknown"
        assert format_artists_for_metadata(None) == "Unknown"

    def test_single_artist(self):
        assert format_artists_for_metadata("Jack Johnson") == "Jack Johnson"

    def test_two_artists(self):
        assert format_artists_for_metadata("A, B") == "A, B"

    def test_more_than_two_truncates(self):
        assert format_artists_for_metadata("A, B, C") == "A, B"
        assert format_artists_for_metadata("A; B; C; D") == "A, B"
