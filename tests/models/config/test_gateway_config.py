import unittest
from pathlib import Path

from models import VisioGatewayConfig

TEMPLATE_PATH = Path(__file__).resolve().parent / 'gateway-template.json'


class MyTestCase(unittest.TestCase):
    def test_parse_raw(self):
        VisioGatewayConfig.parse_raw(self.gateway_json_str)

    def setUp(self) -> None:
        self.gateway_json_str = TEMPLATE_PATH.read_text()


if __name__ == '__main__':
    unittest.main()
