import unittest
from app.door import invitation

class DoorTests(unittest.TestCase):
    def test_invitation(self):
        self.assertIn('민지님, ', invitation(' 민지 '))
    def test_optional_name(self):
        self.assertFalse(invitation().startswith('님'))
    def test_type(self):
        with self.assertRaises(TypeError): invitation(None)
