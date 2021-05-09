import unittest

from models import HTTPNodeConfig


class MyTestCase(unittest.TestCase):
    def test_parse_raw(self):
        HTTPNodeConfig.parse_raw(self.json_str_with_mirror)
        HTTPNodeConfig.parse_raw(self.json_str_without_mirror)

    def setUp(self) -> None:
        self.json_str_with_mirror = '''
        {
            "primary": {
              "url": "http://get-main.com:8080",
              "login": "login",
              "password": "password"
            },
            "mirror": {
              "url": "http://get-mirror.com:8080",
              "login": "login",
              "password": "password"
            }
        }
        '''
        self.json_str_without_mirror = '''
        {
            "primary": {
              "url": "http://get-main.com:8080",
              "login": "login",
              "password": "password"
            }
        }
        '''


if __name__ == '__main__':
    unittest.main()
