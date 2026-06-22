import re

from bs4 import BeautifulSoup, Tag


class UnexpectedResponseException(Exception):
    """Raised when a controller page cannot be parsed as expected."""


def require_class(soup: BeautifulSoup, class_name: str, field_name: str) -> Tag:
    element = soup.find(class_=class_name)
    if element is None:
        raise UnexpectedResponseException(f"Missing {field_name} in device response")
    return element


def require_selector(soup: BeautifulSoup, selector: str, field_name: str) -> Tag:
    element = soup.select_one(selector)
    if element is None:
        raise UnexpectedResponseException(f"Missing {field_name} in device response")
    return element


def require_match(pattern: str, contents: str, field_name: str) -> re.Match:
    match = re.search(pattern, contents)
    if match is None:
        raise UnexpectedResponseException(f"Missing {field_name} in device response")
    return match
