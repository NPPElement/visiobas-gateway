# Adopted from: <https://github.com/openapi-generators/openapi-python-client/
# blob/main/tests/test_utils.py>

import pytest
from visiobas_gateway.utils.identifier import (
    sanitize,
    split_words,
    snake_case,
    kebab_case,
    pascal_case,
    camel_case,
)


def test__sanitize():
    assert (
        sanitize("something*~with lots_- of weird things}=")
        == "somethingwith lots_- of weird things"
    )


@pytest.mark.parametrize(
    "before, after",
    [
        ("connectionID", ["connection", "ID"]),
        ("connection_id", ["connection", "id"]),
        ("connection-id", ["connection", "id"]),
        ("Response200", ["Response", "200"]),
        ("Response200Okay", ["Response", "200", "Okay"]),
        ("S3Config", ["S3", "Config"]),
        ("s3config", ["s3config"]),
    ],
)
def test_split_words(before, after):
    assert split_words(before) == after


def test_snake_case_uppercase_str():
    assert snake_case("HTTP") == "http"
    assert snake_case("HTTP RESPONSE") == "http_response"


def test_snake_case_from_pascal_with_acronyms():
    assert snake_case("HTTPResponse") == "http_response"
    assert snake_case("APIClientHTTPResponse") == "api_client_http_response"
    assert snake_case("OAuthClientHTTPResponse") == "o_auth_client_http_response"
    assert snake_case("S3Config") == "s3_config"


def test_snake_case_from_pascal_with_numbers():
    assert snake_case("Response200") == "response_200"
    assert snake_case("Response200WithContent") == "response_200_with_content"


def test_snake_case_from_pascal():
    assert snake_case("HttpResponsePascalCase") == "http_response_pascal_case"


def test_snake_case_from_camel():
    assert snake_case("httpResponseLowerCamel") == "http_response_lower_camel"
    assert snake_case("connectionID") == "connection_id"


def test_kebab_case():
    assert kebab_case("keep_alive") == "keep-alive"


@pytest.mark.parametrize(
    "before, after",
    [
        ("PascalCase", "PascalCase"),
        ("snake_case", "SnakeCase"),
        ("TLAClass", "TLAClass"),
        ("Title Case", "TitleCase"),
        ("s3_config", "S3Config"),
        ("__LeadingUnderscore", "LeadingUnderscore"),
        ("UPPER_SNAKE_CASE", "UpperSnakeCase"),
    ],
)
def test_pascal_case(before, after):
    assert pascal_case(before) == after


@pytest.mark.parametrize(
    "before, after",
    [
        ("PascalCase", "pascalCase"),
        ("snake_case", "snakeCase"),
        ("TLAClass", "tlaClass"),
        ("Title Case", "titleCase"),
        ("s3_config", "s3Config"),
        ("__LeadingUnderscore", "leadingUnderscore"),
        ("UPPER_SNAKE_CASE", "upperSnakeCase"),
    ],
)
def test_camel_case(before, after):
    assert camel_case(before) == after
