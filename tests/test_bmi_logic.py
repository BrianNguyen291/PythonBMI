import unittest

from app import bmi_guidance, military_status


class BmiLogicTests(unittest.TestCase):
    def test_taiwan_adult_thresholds(self):
        for bmi, category in [
            (18.4, "體重過輕"),
            (18.5, "健康體位"),
            (23.9, "健康體位"),
            (24.0, "體重過重"),
            (26.9, "體重過重"),
            (27.0, "肥胖"),
        ]:
            with self.subTest(bmi=bmi):
                self.assertEqual(bmi_guidance(bmi)["label"], category)

    def test_military_status_boundaries(self):
        for bmi, status in [
            (14.9, "免役"),
            (15.0, "替代役"),
            (16.4, "替代役"),
            (16.5, "常備役"),
            (32.0, "常備役"),
            (32.1, "替代役"),
            (35.0, "替代役"),
            (35.1, "免役"),
        ]:
            with self.subTest(bmi=bmi):
                self.assertEqual(military_status(bmi), status)


if __name__ == "__main__":
    unittest.main()
