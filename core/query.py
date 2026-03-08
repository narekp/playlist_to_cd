import re

from .artists import split_artists
from .naming import format_artists_for_filename


def build_query_variants(artist, track):
    """
    Build an ordered list of search query strings for a track.
    Preserves original title first, adds full artist context,
    applies light normalisation, and only simplifies as a last resort.
    """
    artists_list = split_artists(artist)
    first_artist = artists_list[0] if artists_list else artist.strip()
    full_artist = format_artists_for_filename(artist)   # e.g. "Artist1, Artist2, Artist3"

    # Original title (keep as is)
    orig_title = track.strip()

    # Lightly normalised title: collapse multiple spaces only
    light_title = re.sub(r'\s+', ' ', orig_title)

    # Simplified title (last resort): remove parenthesised and quoted content
    simple_title = light_title
    simple_title = re.sub(r'\(.*?\)', '', simple_title)
    simple_title = re.sub(r'\".*?\"', '', simple_title)
    simple_title = re.sub(r'\s+', ' ', simple_title).strip()

    variants = []

    # Variant 1: first artist + original title
    if first_artist and orig_title:
        variants.append(f"{first_artist} {orig_title}")

    # Variant 2: full artist + original title
    if full_artist and orig_title and full_artist != first_artist:
        variants.append(f"{full_artist} {orig_title}")

    # Variant 3: first artist + light title (if different from original)
    if first_artist and light_title and light_title != orig_title:
        variants.append(f"{first_artist} {light_title}")

    # Variant 4: full artist + light title (if different from original)
    if full_artist and light_title and light_title != orig_title and full_artist != first_artist:
        variants.append(f"{full_artist} {light_title}")

    # Variant 5: first artist + simple title (if different from light)
    if first_artist and simple_title and simple_title != light_title:
        variants.append(f"{first_artist} {simple_title}")

    # Ensure at least one variant exists
    if not variants:
        variants.append(f"{first_artist} {orig_title}")

    return variants

