import re

import skypulse


def test_version_is_set():
    assert skypulse.__version__
    assert isinstance(skypulse.__version__, str)


def test_version_is_semver():
    assert re.match(r"^\d+\.\d+\.\d+", skypulse.__version__)


def test_version_matches_expected():
    assert skypulse.__version__ == "2.1.2"
