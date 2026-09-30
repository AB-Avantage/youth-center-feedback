from dataclasses import dataclass
import json
from pathlib import Path

from django.db import DatabaseError, connections


class EZYXSUnavailable(Exception):
    """The external EZYXS database could not be read."""


@dataclass(frozen=True)
class Facility:
    id: int
    name: str
    name_en: str = ""

    def label(self, language):
        return (self.name_en or self.name) if language == "en" else self.name


@dataclass(frozen=True)
class Customer:
    id: int
    name: str
    phone: str
    email: str


def normalize_phone(value):
    translation = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    return (value or "").translate(translation).strip().replace(" ", "").replace("-", "")


def phone_variants(value):
    phone = normalize_phone(value)
    variants = {phone}
    if phone.startswith("+20") and len(phone) == 13:
        variants.add("0" + phone[3:])
        variants.add(phone[1:])
    if phone.startswith("20") and len(phone) == 12:
        variants.add("0" + phone[2:])
    if phone.startswith("0") and len(phone) == 11:
        variants.add("20" + phone[1:])
        variants.add("+20" + phone[1:])
    return sorted(variants)


def active_facilities():
    try:
        with connections["ezyxs"].cursor() as cursor:
            cursor.execute("SELECT id, name, name_en FROM facility_facility WHERE is_active = %s ORDER BY name", [True])
            facilities = [Facility(*row) for row in cursor.fetchall()]
    except DatabaseError as exc:
        raise EZYXSUnavailable("Could not read EZYXS facilities") from exc
    if facilities:
        return facilities
    snapshot = Path(__file__).resolve().parent / "data" / "moys_test_facilities.json"
    return [Facility(**item) for item in json.loads(snapshot.read_text(encoding="utf-8"))]


def find_customer_by_phone(value):
    variants = phone_variants(value)
    placeholders = ", ".join(["%s"] * len(variants))
    sql = (
        "SELECT u.id, p.full_name, p.phone_number, u.email "
        "FROM accounts_customerprofile p "
        "JOIN accounts_customuser u ON u.id = p.user_id "
        f"WHERE p.phone_number IN ({placeholders}) "
        "AND u.is_active = %s AND u.user_type = %s LIMIT 2"
    )
    try:
        with connections["ezyxs"].cursor() as cursor:
            cursor.execute(sql, [*variants, True, "customer"])
            rows = cursor.fetchall()
    except DatabaseError as exc:
        raise EZYXSUnavailable("Could not read EZYXS customer") from exc
    return Customer(*rows[0]) if len(rows) == 1 else None
