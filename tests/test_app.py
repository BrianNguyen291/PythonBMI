import os
import tempfile
import unittest

from app import app, bmi_guidance, military_status


class BmiAppTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        app.config["DATABASE"] = self.db_path
        self.client = app.test_client()

    def tearDown(self):
        os.remove(self.db_path)

    def test_initial_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("了解自己的<br><em>健康狀況。</em>", page)
        self.assertIn("計算你的 BMI", page)

    def test_calculation_and_advice(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn("22.5", page)
        self.assertIn("健康體位", page)
        self.assertIn("維持均衡飲食", page)

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

    def test_name_is_shown_in_result(self):
        named = self.client.post("/", data={"name": "Brian", "height": "170", "weight": "65"}).get_data(as_text=True)
        anonymous = self.client.post("/", data={"height": "170", "weight": "65"}).get_data(as_text=True)
        self.assertIn("Brian，你的體位屬於", named)
        self.assertIn("你的體位屬於", anonymous)
        self.assertNotIn("，你的體位屬於", anonymous)

    def test_obese_result_uses_red_tone(self):
        obese = self.client.post("/", data={"height": "170", "weight": "90"}).get_data(as_text=True)
        overweight = self.client.post("/", data={"height": "170", "weight": "75"}).get_data(as_text=True)
        self.assertIn("result-panel obese", obese)
        self.assertNotIn("result-panel obese", overweight)

    def test_invalid_fields_do_not_produce_result(self):
        for height, weight in [("", "65"), ("0", "65"), ("abc", "65"), ("170", "-2"), ("inf", "65"), ("170", "nan"), ("1e-300", "65"), ("1e308", "65"), ("1", "1e308")]:
            with self.subTest(height=height, weight=weight):
                response = self.client.post("/", data={"height": height, "weight": weight})
                page = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('aria-invalid="true"', page)
                self.assertNotIn("YOUR RESULT", page)

    def test_input_is_escaped(self):
        response = self.client.post("/", data={"height": '<script>alert(1)</script>', "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertNotIn("<script>", page)
        self.assertIn("請輸入大於 0", page)

    def test_named_results_are_listed_with_history(self):
        self.client.post("/", data={"name": "Brian", "height": "170", "weight": "65"})
        self.client.post("/", data={"name": "Brian", "height": "170", "weight": "90"})
        self.client.post("/", data={"name": "Amy", "height": "160", "weight": "50"})

        users = self.client.get("/users").get_data(as_text=True)
        self.assertIn('href="/users/Brian"', users)
        self.assertIn('href="/users/Amy"', users)

        history = self.client.get("/users/Brian").get_data(as_text=True)
        self.assertIn("22.5", history)
        self.assertIn("31.1", history)
        listing = history[history.index("歷次計算"):]
        self.assertLess(listing.index("31.1"), listing.index("22.5"))  # newest first
        self.assertRegex(history, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")

    def test_anonymous_results_are_not_recorded(self):
        self.client.post("/", data={"height": "170", "weight": "65"})
        users = self.client.get("/users").get_data(as_text=True)
        self.assertNotIn('href="/users/', users)

    def test_invalid_input_is_not_recorded(self):
        self.client.post("/", data={"name": "Brian", "height": "abc", "weight": "65"})
        self.assertEqual(self.client.get("/users/Brian").status_code, 404)

    def test_unknown_user_returns_404(self):
        self.assertEqual(self.client.get("/users/nobody").status_code, 404)

    def test_name_with_slash_and_html_is_escaped(self):
        name = "<b>a/b</b>"
        self.client.post("/", data={"name": name, "height": "170", "weight": "65"})
        users = self.client.get("/users").get_data(as_text=True)
        self.assertNotIn("<b>a/b</b>", users)
        history = self.client.get("/users/%3Cb%3Ea/b%3C/b%3E")
        self.assertEqual(history.status_code, 200)
        self.assertNotIn("<b>a/b</b>", history.get_data(as_text=True))
        self.assertIn("22.5", history.get_data(as_text=True))

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

    def test_military_status_shown_with_disclaimer(self):
        page = self.client.post("/", data={"height": "170", "weight": "65"}).get_data(as_text=True)
        self.assertIn("兵役體位（試算） <strong>常備役</strong>", page)
        self.assertIn("以兵役複檢結果為準", page)
        self.assertIn("2023-06-01", page)
        invalid = self.client.post("/", data={"height": "0", "weight": "65"}).get_data(as_text=True)
        self.assertNotIn("兵役體位", invalid)

    def test_trend_chart_and_deltas(self):
        self.client.post("/", data={"name": "Brian", "height": "170", "weight": "75"})  # 26.0 過重
        self.client.post("/", data={"name": "Brian", "height": "170", "weight": "70"})  # 24.2 過重
        self.client.post("/", data={"name": "Brian", "height": "170", "weight": "65"})  # 22.5 健康
        page = self.client.get("/users/Brian").get_data(as_text=True)
        self.assertIn("trend-chart", page)
        self.assertEqual(page.count("<circle"), 3)
        self.assertIn("▼ −1.8", page)
        self.assertIn("▼ −1.7", page)
        self.assertIn("第一次 26.0 → 最近一次 22.5（▼ −3.5）", page)
        self.assertIn("體重過重 → 健康體位", page)

    def test_single_record_has_no_chart(self):
        self.client.post("/", data={"name": "Amy", "height": "160", "weight": "50"})
        page = self.client.get("/users/Amy").get_data(as_text=True)
        self.assertNotIn("trend-chart", page)
        self.assertNotIn("▲", page)
        self.assertIn("再量一次就能看到趨勢", page)

    def test_export_csv(self):
        self.client.post("/", data={"name": "小明", "height": "170", "weight": "65"})
        self.client.post("/", data={"name": "小明", "height": "170", "weight": "90"})
        response = self.client.get("/export/小明")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertRegex(response.headers["Content-Disposition"], r"bmi-%E5%B0%8F%E6%98%8E-\d{8}\.csv")
        body = response.data
        self.assertTrue(body.startswith(b"\xef\xbb\xbf"))
        lines = body.decode("utf-8-sig").splitlines()
        self.assertEqual(lines[0], "量測時間,BMI,體位")
        self.assertRegex(lines[1], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},22\.5,健康體位$")
        self.assertTrue(lines[2].endswith(",31.1,肥胖"))
        self.assertEqual(self.client.get("/export/nobody").status_code, 404)


if __name__ == "__main__":
    unittest.main()
