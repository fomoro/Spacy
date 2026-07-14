import unittest

from scripts.validate_resources import validate


class ResourceContractTests(unittest.TestCase):
    def test_resources_are_cross_referenced_and_unambiguous(self):
        self.assertEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
