from repak import versioning


def test_new_package_starts_at_0_1():
    assert versioning.next_version(None) == "0.1"
    assert versioning.next_version([]) == "0.1"


def test_increment_single_digit():
    assert versioning.next_version(["0.1"]) == "0.2"


def test_increment_rolls_into_two_digits():
    assert versioning.next_version(["0.8", "0.9"]) == "0.10"
    assert versioning.next_version(["0.10", "0.11"]) == "0.12"


def test_picks_max_existing():
    assert versioning.next_version(["0.3", "0.1", "0.12", "0.2"]) == "0.13"


def test_non_conforming_versions_ignored():
    # Three-part and non-numeric strings are not MAJOR.MINOR and are skipped.
    assert versioning.next_version(["0.0.1", "garbage"]) == "0.1"
    # A minor of 100 or more is out of range and ignored.
    assert versioning.next_version(["0.100", "0.5"]) == "0.6"


def test_minor_rolls_into_major_at_100():
    assert versioning.next_version(["0.99"]) == "1.0"
    assert versioning.next_version(["1.0"]) == "1.1"
    assert versioning.next_version(["1.99"]) == "2.0"


def test_no_ceiling():
    # The scheme is unbounded; high majors keep incrementing.
    assert versioning.next_version(["7.42"]) == "7.43"
    assert versioning.next_version(["0.3", "2.10", "1.5"]) == "2.11"
