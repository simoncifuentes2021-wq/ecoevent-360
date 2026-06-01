from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    CLIENT = "CLIENT"
    SUPERVISOR = "SUPERVISOR"
    WORKER = "WORKER"


class EventStatus(StrEnum):
    QUOTE = "QUOTE"
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    REPORT_DELIVERED = "REPORT_DELIVERED"
    CANCELLED = "CANCELLED"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OBSERVED = "OBSERVED"
    CANCELLED = "CANCELLED"


class IncidentStatus(StrEnum):
    REPORTED = "REPORTED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PriorityLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WasteDestination(StrEnum):
    RECYCLING = "RECYCLING"
    COMPOSTING = "COMPOSTING"
    LANDFILL = "LANDFILL"
    RECOVERY = "RECOVERY"
    SPECIAL_DISPOSAL = "SPECIAL_DISPOSAL"
    OTHER = "OTHER"


class CarbonScope(StrEnum):
    SCOPE_1 = "SCOPE_1"
    SCOPE_2 = "SCOPE_2"
    SCOPE_3 = "SCOPE_3"


class SurveyStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class ReportStatus(StrEnum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    DELIVERED = "DELIVERED"
    ARCHIVED = "ARCHIVED"
