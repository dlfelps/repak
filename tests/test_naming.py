import pytest

from repak import naming


@pytest.mark.parametrize(
    "folder,expected",
    [
        ("MyProject", "myproject"),
        ("my_project", "my-project"),
        ("My.Cool  Project!!", "my-cool-project"),
        ("--weird--", "weird"),
        ("a___b...c", "a-b-c"),
    ],
)
def test_normalize(folder, expected):
    assert naming.normalize(folder) == expected


def test_pypi_module_script_names():
    assert naming.pypi_name("My_Proj") == "repak-my-proj"
    assert naming.module_name("My_Proj") == "repak_my_proj"
    assert naming.console_script("My_Proj") == "unpak-my-proj"


@pytest.mark.parametrize("bad", ["", "   ", "!!!", "---"])
def test_invalid_names_rejected(bad):
    with pytest.raises(naming.NameError_):
        naming.normalize(bad)
