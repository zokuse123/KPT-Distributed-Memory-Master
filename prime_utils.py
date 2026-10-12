"""Prime-number routines shared by sequential and distributed measurements."""

from __future__ import annotations

import math


def is_prime(number: int) -> bool:
    """Return whether *number* is prime using trial division."""
    if number < 2:
        return False
    if number == 2:
        return True
    if number % 2 == 0:
        return False

    limit = math.isqrt(number)
    for divisor in range(3, limit + 1, 2):
        if number % divisor == 0:
            return False
    return True


def count_primes(start: int, end: int) -> int:
    """Count primes in the inclusive interval [start, end]."""
    if start > end:
        return 0
    return sum(1 for number in range(start, end + 1) if is_prime(number))

