"""Unit tests for GitHub URL validation — no DB or network required."""
import pytest

from app.utils import InvalidRepoURL, validate_github_url


@pytest.mark.parametrize(
    "url,expected_name",
    [
        ("https://github.com/pallets/flask", "pallets/flask"),
        ("https://github.com/pallets/flask.git", "pallets/flask"),
        ("https://github.com/pallets/flask/", "pallets/flask"),
        ("http://github.com/Owner-1/repo_2.name", "Owner-1/repo_2.name"),
        ("  https://github.com/a/b  ", "a/b"),
    ],
)
def test_valid_urls(url, expected_name):
    clone_url, repo_name = validate_github_url(url)
    assert repo_name == expected_name
    assert clone_url.startswith("https://github.com/")
    assert clone_url.endswith(".git")


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "https://gitlab.com/a/b",
        "https://github.com/onlyowner",
        "https://github.com/a/b/tree/main/src",
        "ftp://github.com/a/b",
    ],
)
def test_invalid_urls(url):
    with pytest.raises(InvalidRepoURL):
        validate_github_url(url)
