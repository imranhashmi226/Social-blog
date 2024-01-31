# from __main__ import app
import unittest
from app import app
# try:
    
# except Exception as e:
#     print("something is missing")

class FlaskTest(unittest.TestCase):
    def test_art(self):
        tester = app.test_client(self)
        res = tester.get("/login")
        statuscode = res.status_code
        self.assertEqual(statuscode,200)

    def test_app(self):
        tester = app.test_client(self)
        res = tester.get("/signup")
        status = res.status_code
        self.assertEqual(status,200)
        


if __name__ == "__main__":
    unittest.main()