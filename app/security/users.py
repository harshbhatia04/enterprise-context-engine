"""Fake enterprise users for the Milestone 1 scaffold."""

from copy import deepcopy
from typing import Any

USERS: dict[str, dict[str, Any]] = {
    "admin_user": {
        "user_id": "admin_user",
        "role": "admin",
        "department": "all",
        "allowed_departments": ["hr", "finance", "engineering", "legal", "general"],
        "access_levels": ["all"],
        "description": "Administrator with access to all enterprise documents.",
    },
    "hr_user": {
        "user_id": "hr_user",
        "role": "manager",
        "department": "hr",
        "allowed_departments": ["hr"],
        "access_levels": ["hr"],
        "description": "HR manager with access to HR documents only.",
    },
    "finance_user": {
        "user_id": "finance_user",
        "role": "analyst",
        "department": "finance",
        "allowed_departments": ["finance"],
        "access_levels": ["finance"],
        "description": "Finance analyst with access to finance documents only.",
    },
    "engineer_user": {
        "user_id": "engineer_user",
        "role": "engineer",
        "department": "engineering",
        "allowed_departments": ["engineering"],
        "access_levels": ["engineering"],
        "description": "Engineer with access to engineering documents only.",
    },
    "legal_user": {
        "user_id": "legal_user",
        "role": "counsel",
        "department": "legal",
        "allowed_departments": ["legal"],
        "access_levels": ["legal"],
        "description": "Legal counsel with access to legal documents only.",
    },
    "intern_user": {
        "user_id": "intern_user",
        "role": "intern",
        "department": "general",
        "allowed_departments": ["general", "public"],
        "access_levels": ["general", "public"],
        "description": "Intern with access only to public or general documents.",
    },
}


def list_users() -> list[dict[str, Any]]:
    """Return all fake users as defensive copies."""
    return [deepcopy(user) for user in USERS.values()]


def get_user(user_id: str) -> dict[str, Any]:
    """Return one fake user as a defensive copy."""
    if user_id not in USERS:
        raise KeyError(f"Unknown user_id: {user_id}")
    return deepcopy(USERS[user_id])
