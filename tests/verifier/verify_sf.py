import unittest

from gateway.verifier import BACnetVerifier


class TestToStr(unittest.TestCase):

    def test_verify_list_sf(self):
        cases = ([0, 0, 0, 0],
                 [1, 0, 1, 0],
                 [1, 1, 1, 1],
                 [0, 0, 0, 1],
                 [0, 0, 1, 0],
                 4,
                 6,
                 0
                 )
        expected = (0,
                    10,
                    15,
                    1,
                    2,
                    4,
                    6,
                    0)
        for case, _expected in zip(cases, expected):
            with self.subTest(case=case):
                _result = BACnetVerifier.verify_sf(sf=case)
                self.assertEqual(_expected, _result)


if __name__ == '__main__':
    unittest.main()
