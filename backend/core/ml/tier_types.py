"""Shared ML tier value types that do not depend on the database layer."""

import enum


class DataTier(str, enum.Enum):
    bronze = "bronze"
    silver = "silver"
    gold = "gold"
    unrated = "unrated"
