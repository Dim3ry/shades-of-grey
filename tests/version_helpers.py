"""Shared helpers for anything in a test that depends on WHICH version of the app is current.

Why this file exists: tests used to hard-code the version number ("APP_VERSION is v54 or later") and each version bump
meant editing old tests. Now the version checks live in ONE place (tests/test_version_plumbing.py) and every other test
that needs to know the version uses these helpers. A normal chunk's test never checks the app version itself.

    current()            the version in app.js, e.g. "v69"
    parse("v21.7")       (21, 7); compares as numbers, so v21.10 is newer than v21.9
    at_least("v69")      True when the app is v69 or newer
    newer_than("v69")    True when the app is newer than v69
    changelog_versions(page)   every version in the Updates list, newest first (needs an open app page)
    has_entry(page, "v69")     True when the Updates list has an entry for that version
    data_version()       the DATA_VERSION number written in app.js
"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.realpath(os.path.join(HERE, ".."))


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def current():
    m = re.search(r'const APP_VERSION = "(v[^"]+)"', read("app.js"))
    return m.group(1) if m else ""


def parse(version):
    return tuple(int(n) for n in version.lstrip("v").split("."))


def at_least(version):
    return parse(current()) >= parse(version)


def newer_than(version):
    return parse(current()) > parse(version)


def changelog_versions(page):
    return page.evaluate("CHANGELOG.map(c => c.version)")


def has_entry(page, version):
    return version in changelog_versions(page)


def data_version():
    m = re.search(r"const DATA_VERSION = (\d+)", read("app.js"))
    return int(m.group(1)) if m else None
