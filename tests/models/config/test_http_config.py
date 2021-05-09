import unittest
from pathlib import Path

from models import VisioHTTPClientConfig

TEMPLATE_PATH = Path(__file__).resolve().parent / 'http-template.json'


class MyTestCase(unittest.TestCase):
    def test_parse_raw(self):
        VisioHTTPClientConfig.parse_raw(self.http_json_str)

    def setUp(self) -> None:
        self.http_json_str = TEMPLATE_PATH.read_text()


if __name__ == '__main__':
    unittest.main()
