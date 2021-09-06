# Adopted from:
# <https://github.com/openapi-generators/openapi-python-client/
# blob/main/openapi_python_client/test_utils.py>

import re
from typing import Callable

DELIMITERS = " _-"


def sanitize(value: str) -> str:
    """Removes every character that isn't 0-9, A-Z, a-z, or a known delimiter"""
    return re.sub(rf"[^\w{DELIMITERS}]+", "", value)


def split_words(value: str) -> list[str]:
    """Split a string on words and known delimiters"""
    # We can't guess words if there is no capital letter
    if any(c.isupper() for c in value):
        value = " ".join(re.split("([A-Z]?[a-z]+)", value))
    return re.findall(rf"[^{DELIMITERS}]+", value)


def snake_case(value: str) -> str:
    """Converts to snake_case"""
    words = split_words(sanitize(value))
    return "_".join(words).lower()


def pascal_case(value: str) -> str:
    """Converts to PascalCase"""
    words = split_words(sanitize(value))
    capitalized_words = (
        word.capitalize() if not word.isupper() else word for word in words
    )
    return "".join(capitalized_words)


def camel_case(value: str) -> str:
    """Converts to camelCase"""
    words = split_words(sanitize(value))
    lower_word = words[0].lower()
    capitalized_words = (
        word.capitalize() if not word.isupper() else word for word in words[1:]
    )
    return "".join((lower_word, *capitalized_words))


def kebab_case(value: str) -> str:
    """Converts to kebab-case"""
    words = split_words(sanitize(value))
    return "-".join(words).lower()


SUPPORTED_CASES: tuple[Callable, ...] = (
    camel_case,
    pascal_case,
    kebab_case,
    snake_case,
)