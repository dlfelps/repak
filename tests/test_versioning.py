import pytest

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
    assert versioning.next_version(["1.0", "0.0.1", "garbage"]) == "0.1"
    assert versioning.next_version(["1.0", "0.5"]) == "0.6"


def test_ceiling_raises():
    with pytest.raises(versioning.VersionExhausted):
        versioning.next_version(["0.99"])
