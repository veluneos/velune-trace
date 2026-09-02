#!/usr/bin/env python3

"""
Velune formatting utilities.

Shared formatting functions used by CLI reporters.
"""


def ns_to_sec(ns: int | None) -> str:
    if ns is None:
        return "N/A"
    return f"{ns / 1_000_000_000:.9f}"
