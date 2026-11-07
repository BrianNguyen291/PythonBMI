import unittest

from bmi_logic import BmiInputError, bmi_guidance, calculate_bmi, format_delta, military_status, trend


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

    def test_calculate_bmi_rounds_to_one_decimal(self):
        self.assertEqual(calculate_bmi(170, 65), 22.5)
        self.assertEqual(calculate_bmi(170, 90), 31.1)

    def test_calculate_bmi_blames_the_right_field(self):
        for height, weight, field in [(1e-300, 65, "height"), (1e308, 65, "height"), (1, 1e308, "weight")]:
            with self.subTest(height=height, weight=weight):
                with self.assertRaises(BmiInputError) as ctx:
                    calculate_bmi(height, weight)
                self.assertEqual(ctx.exception.field, field)

    def test_trend_orders_oldest_first_with_deltas(self):
        points = trend([("22.5", "t3"), ("24.2", "t2"), ("26.0", "t1")])
        self.assertEqual([p["created_at"] for p in points], ["t1", "t2", "t3"])
        self.assertEqual([p["delta"] for p in points], [None, -1.8, -1.7])
        self.assertEqual(points[-1]["label"], "健康體位")

    def test_format_delta(self):
        self.assertEqual(format_delta(1.8), "▲ +1.8")
        self.assertEqual(format_delta(-1.7), "▼ −1.7")
        self.assertEqual(format_delta(0), "— 0.0")


if __name__ == "__main__":
    unittest.main()
