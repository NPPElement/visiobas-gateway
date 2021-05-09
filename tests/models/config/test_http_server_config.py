import unittest

from models import HTTPServerConfig


class MyTestCase(unittest.TestCase):
    def test_parse_raw(self):
        HTTPServerConfig.parse_raw(self.config_json_str)

    def setUp(self) -> None:
        self.config_json_str = '''
        {
          "url": "http://get-main.com:8080",
          "login": "login",
          "password": "password"
        }
        '''


if __name__ == '__main__':
    unittest.main()
