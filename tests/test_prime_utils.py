import unittest

from benchmark import split_range
from prime_utils import count_primes, is_prime


class PrimeUtilsTests(unittest.TestCase):
    def test_is_prime_edges_and_values(self):
        for value in (-10, -1, 0, 1, 4, 9, 25):
            self.assertFalse(is_prime(value))
        for value in (2, 3, 5, 97):
            self.assertTrue(is_prime(value))

    def test_known_prime_counts(self):
        self.assertEqual(count_primes(2, 10), 4)
        self.assertEqual(count_primes(2, 100), 25)
        self.assertEqual(count_primes(2, 100_000), 9_592)
        self.assertEqual(count_primes(100, 99), 0)

    def test_split_has_no_gap_or_overlap(self):
        for n in (3, 4, 100_000, 1_000_000):
            left, right = split_range(n)
            self.assertEqual(left[0], 2)
            self.assertEqual(left[1] + 1, right[0])
            self.assertEqual(right[1], n)


if __name__ == "__main__":
    unittest.main()

