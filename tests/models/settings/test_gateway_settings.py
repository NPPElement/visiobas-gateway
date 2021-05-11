import unittest
from pathlib import Path

from models.settings.gateway_settings import GatewaySettings


class MyTestCase(unittest.TestCase):
    def test_env_file_exists(self):
        self.assertTrue(self.gateway_env_path.exists())

    def setUp(self) -> None:
        self.gateway_env_path = Path(
            __file__).resolve().parent.parent.parent.parent / 'gateway/config/gateway.env'
        self.gw_settings = GatewaySettings(_env_file=self.gateway_env_path)


if __name__ == '__main__':
    unittest.main()
