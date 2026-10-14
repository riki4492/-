import random
import unittest

from warikan_core import calculate


class SplitTests(unittest.TestCase):
    def test_exact_example(self):
        r = calculate(25000, [("部長", 5000)], [("上司", 1, "1.5"), ("普通", 3, "1.0")], unit=100)
        self.assertEqual(r["difference"], 0)
        self.assertEqual(r["collected"], 25000)
        self.assertEqual(r["people"], 5)

    def test_exact_with_nondivisible_unit(self):
        r = calculate(10001, [], [("同額", 3, "1")], unit=100)
        self.assertEqual(sum(r["rows"][0]["payments"]), 10001)
        self.assertEqual(max(r["rows"][0]["payments"]) - min(r["rows"][0]["payments"]), 100)

    def test_remaining_zero(self):
        r = calculate(1000, [("幹事", 1000)], [("無料", 3, "1")], unit=100)
        self.assertEqual(r["difference"], 0)
        self.assertEqual(r["rows"][1]["payments"], [0, 0, 0])

    def test_overfixed(self):
        with self.assertRaisesRegex(ValueError, "超えて"):
            calculate(1000, [("固定", 1001)], [("普通", 1, 1)])

    def test_missing_people(self):
        with self.assertRaisesRegex(ValueError, "分ける人"):
            calculate(1000, [("固定", 100)], [])

    def test_roundup_has_surplus(self):
        r = calculate(10001, [], [("同額", 3, "1")], unit=100, mode="roundup")
        self.assertGreater(r["difference"], 0)
        self.assertTrue(all(p % 100 == 0 for p in r["rows"][0]["payments"]))

    def test_random_exact(self):
        rng = random.Random(1776)
        for _ in range(2500):
            total = rng.randrange(1, 2500000)
            fixed_sum = rng.randint(0, total)
            ranks = [("A", rng.randint(1, 5), "1.5"), ("B", rng.randint(1, 7), "0.8"), ("C", rng.randint(0, 3), "0.3")]
            unit = rng.choice((1, 10, 100))
            r = calculate(total, [("X", fixed_sum)], ranks, unit=unit)
            self.assertEqual(r["difference"], 0)
            self.assertEqual(r["collected"], total)
            self.assertTrue(all(p >= 0 for row in r["rows"] for p in row["payments"]))


if __name__ == "__main__":
    unittest.main()
