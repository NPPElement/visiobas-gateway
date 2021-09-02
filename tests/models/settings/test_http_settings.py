# import unittest
# from pathlib import Path
#
# from models import HTTPSettings
#
#
# class MyTestCase(unittest.TestCase):
#     def test_env_file_exists(self):
#         self.assertTrue(self.http_env_path.exists())
#
#     def setUp(self) -> None:
#         self.http_env_path = (
#             Path(__file__).resolve().parent.parent.parent.parent
#             / "gateway/config/http.env"
#         )
#
#         self.http_settings = HTTPSettings(_env_file=self.http_env_path)
#
#
# if __name__ == "__main__":
#     unittest.main()
