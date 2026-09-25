"""Synthetic identifiers with valid checksums.

Everything here is invented. PESELs use the 1800s birth-month encoding
(month + 80): checksum-valid, but no living person can hold one. Phones
come from the 600 000 xxx block, e-mails use the reserved .test TLD.
NIP/REGON/IBAN have valid check digits and are otherwise random.
"""

from __future__ import annotations

import random

PESEL_WEIGHTS = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)
REGON9_WEIGHTS = (8, 9, 2, 3, 4, 5, 6, 7)


def pesel_1800s(year: int, month: int, day: int, serial: int, female: bool) -> str:
    sex = serial % 5 * 2 + (0 if female else 1)
    digits = f"{year % 100:02d}{month + 80:02d}{day:02d}{serial:03d}{sex}"
    total = sum(int(d) * w for d, w in zip(digits, PESEL_WEIGHTS))
    return digits + str((10 - total % 10) % 10)


def pesel_is_valid(value: str) -> bool:
    if len(value) != 11 or not value.isdigit():
        return False
    total = sum(int(d) * w for d, w in zip(value[:10], PESEL_WEIGHTS))
    return (10 - total % 10) % 10 == int(value[10])


def random_pesel(rng: random.Random, female: bool) -> str:
    return pesel_1800s(
        rng.randrange(1850, 1899),
        rng.randrange(1, 13),
        rng.randrange(1, 29),
        rng.randrange(100, 1000),
        female,
    )


def nip(rng: random.Random) -> str:
    while True:
        digits = f"{rng.randrange(101, 999)}{rng.randrange(0, 10**6):06d}"
        check = sum(int(d) * w for d, w in zip(digits, NIP_WEIGHTS)) % 11
        if check != 10:
            return digits + str(check)


def nip_is_valid(value: str) -> bool:
    digits = value.replace("-", "")
    if len(digits) != 10 or not digits.isdigit():
        return False
    check = sum(int(d) * w for d, w in zip(digits[:9], NIP_WEIGHTS)) % 11
    return check != 10 and check == int(digits[9])


def format_nip(value: str) -> str:
    return f"{value[:3]}-{value[3:6]}-{value[6:8]}-{value[8:]}"


def regon9(rng: random.Random) -> str:
    digits = f"{rng.randrange(10**7, 10**8)}"
    check = sum(int(d) * w for d, w in zip(digits, REGON9_WEIGHTS)) % 11
    return digits + str(0 if check == 10 else check)


def regon_is_valid(value: str) -> bool:
    if len(value) != 9 or not value.isdigit():
        return False
    check = sum(int(d) * w for d, w in zip(value[:8], REGON9_WEIGHTS)) % 11
    return (0 if check == 10 else check) == int(value[8])


def _iban_check_digits(bban: str) -> str:
    # "PL" -> 25 21, check digits "00" moved to the end.
    return f"{98 - int(bban + '252100') % 97:02d}"


def iban_pl(rng: random.Random) -> str:
    bban = "".join(str(rng.randrange(10)) for _ in range(24))
    return "PL" + _iban_check_digits(bban) + bban


def iban_is_valid(value: str) -> bool:
    compact = value.replace(" ", "")
    if len(compact) != 28 or not compact.startswith("PL") or not compact[2:].isdigit():
        return False
    return compact[2:4] == _iban_check_digits(compact[4:])


def format_iban(value: str) -> str:
    return value[:4] + " " + " ".join(value[4 + i : 8 + i] for i in range(0, 24, 4))


def phone(rng: random.Random) -> str:
    return f"600 000 {rng.randrange(100, 1000)}"


def id_card(rng: random.Random) -> str:
    """Polish ID card number shape (3 letters, check digit, 5 digits)."""
    letters = "".join(rng.choice("ABCDEFGHJKLMNPRSTUWXYZ") for _ in range(3))
    rest = [rng.randrange(10) for _ in range(5)]
    total = sum((ord(c) - 55) * w for c, w in zip(letters, (7, 3, 1)))
    total += sum(n * w for n, w in zip(rest, (7, 3, 1, 7, 3)))
    return f"{letters}{total % 10}{''.join(map(str, rest))}"
