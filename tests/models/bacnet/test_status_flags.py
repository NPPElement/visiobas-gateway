# import unittest
#
# from models.bacnet import StatusFlag, StatusFlags
#
#
# class MyTestCase(unittest.TestCase):
#     def test_enable(self):
#         self.all_disabled.enable(flag=StatusFlag.OVERRIDEN)
#         self.assertEqual(self.all_disabled.flags, StatusFlag.OVERRIDEN.value)
#
#     def test_disable(self):
#         self.all_enabled.disable(flag=StatusFlag.FAULT)
#         self.assertEqual(self.all_enabled.flags, 0b1101)
#
#     def test_check(self):
#         self.assertEqual(self.all_enabled.check(flag=StatusFlag.FAULT), True)
#         self.all_enabled.disable(flag=StatusFlag.FAULT)
#         self.assertEqual(self.all_enabled.check(flag=StatusFlag.FAULT), False)
#
#     def setUp(self) -> None:
#         self.all_enabled = StatusFlags(flags=[1, 1, 1, 1])
#         self.all_disabled = StatusFlags(flags=0)
#
#
# if __name__ == "__main__":
#     unittest.main()
