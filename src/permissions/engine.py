from enum import Enum


class Permission(str, Enum):
    PROJECT_VIEW = "project:view"
    PROJECT_EDIT = "project:edit"
    PROJECT_CREATE = "project:create"
    PARTICIPANT_VIEW = "participant:view"
    PARTICIPANT_EDIT = "participant:edit"
    PARTICIPANT_CREATE = "participant:create"
    APPROVAL_VIEW = "approval:view"
    APPROVAL_DECIDE = "approval:decide"
    ADMIN_ALL = "admin:all"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "PLATFORM_ADMIN": set(Permission),
    "BUYER": {
        Permission.PROJECT_VIEW,
        Permission.PARTICIPANT_VIEW,
        Permission.APPROVAL_VIEW,
    },
    "TRADING_COMPANY": {
        Permission.PROJECT_VIEW,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_CREATE,
        Permission.PARTICIPANT_VIEW,
        Permission.PARTICIPANT_EDIT,
        Permission.PARTICIPANT_CREATE,
        Permission.APPROVAL_VIEW,
        Permission.APPROVAL_DECIDE,
    },
    "MANUFACTURER": {
        Permission.PROJECT_VIEW,
        Permission.PARTICIPANT_VIEW,
    },
    "FABRIC_SUPPLIER": {
        Permission.PROJECT_VIEW,
        Permission.PARTICIPANT_VIEW,
    },
    "TRIM_SUPPLIER": {
        Permission.PROJECT_VIEW,
        Permission.PARTICIPANT_VIEW,
    },
    "PACKAGING_SUPPLIER": {
        Permission.PROJECT_VIEW,
        Permission.PARTICIPANT_VIEW,
    },
    "LOGISTICS_PROVIDER": {
        Permission.PROJECT_VIEW,
        Permission.PARTICIPANT_VIEW,
    },
    "FINANCE_SERVICE_PROVIDER": {
        Permission.PROJECT_VIEW,
        Permission.PARTICIPANT_VIEW,
    },
    "QC_INSPECTOR": {
        Permission.PROJECT_VIEW,
        Permission.PARTICIPANT_VIEW,
    },
    "INTERMEDIARY": {
        Permission.PROJECT_VIEW,
        Permission.PROJECT_EDIT,
        Permission.PARTICIPANT_VIEW,
        Permission.PARTICIPANT_EDIT,
    },
}


def has_permission(user_roles: list[str], permission: Permission) -> bool:
    for role in user_roles:
        if permission in ROLE_PERMISSIONS.get(role, set()):
            return True
    return False
