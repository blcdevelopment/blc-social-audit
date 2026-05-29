from enum import StrEnum


class AuditStatus(StrEnum):
    QUEUED = "queued"
    CRAWLING = "crawling"
    COLLECTING_PERFORMANCE = "collecting_performance"
    EXTRACTING = "extracting"
    SCORING = "scoring"
    COMMENTING = "commenting"
    VALIDATING = "validating"
    RENDERING = "rendering"
    COMPLETE = "complete"
    FAILED = "failed"


JOB_STATUS_VALUES = tuple(status.value for status in AuditStatus)
TERMINAL_STATUSES = {AuditStatus.COMPLETE.value, AuditStatus.FAILED.value}
