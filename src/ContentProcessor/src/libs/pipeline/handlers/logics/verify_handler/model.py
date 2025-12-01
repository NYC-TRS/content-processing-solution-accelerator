# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Data models for verification results and configuration."""

from enum import Enum
from typing import Optional, Any, List
from pydantic import BaseModel


class VerificationType(str, Enum):
    """Types of verification available"""
    DOCTOR = "doctor"
    NOTARY = "notary"
    DEATH_CERTIFICATE = "death_certificate"
    IDENTITY = "identity"


class VerificationStatus(str, Enum):
    """Possible verification outcomes"""
    VERIFIED = "verified"           # Found in database, valid
    NOT_FOUND = "not_found"         # Not in database
    INVALID = "invalid"             # Found but invalid/format error
    EXPIRED = "expired"             # Found but expired
    REVOKED = "revoked"             # Found but revoked/suspended
    ERROR = "error"                 # API call failed
    SKIPPED = "skipped"             # Low confidence, didn't verify


class VerificationResult(BaseModel):
    """Result from a single field verification"""
    field_name: str
    extracted_value: Any
    verification_type: VerificationType
    status: VerificationStatus
    details: Optional[dict] = None          # API response data
    timestamp: str
    api_response_time: float                # Milliseconds
    error_message: Optional[str] = None     # If status == ERROR


class VerificationMetadata(BaseModel):
    """Summary of all verifications for a document"""
    total_fields_checked: int
    verified_count: int
    not_found_count: int
    invalid_count: int
    expired_count: int
    revoked_count: int
    error_count: int
    skipped_count: int
    total_api_calls: int
    total_api_time: float                   # Total milliseconds
    verification_timestamp: str

    # Breakdown by verification type
    verifications_by_type: dict = {}
    """
    Example:
    {
        "doctor": {"verified": 2, "not_found": 0, "error": 0}
    }
    """


class SchemaVerificationConfig(BaseModel):
    """Configuration for which verification types apply to a schema"""
    schema_id: str
    enabled_verification_types: List[VerificationType]
    field_mappings: dict
    """
    Example:
    {
        "doctor": {
            "physician_name": {"field_name": "physician_name", "required": true},
            "physician_license_number": {"field_name": "physician_license_number", "required": true}
        }
    }
    """
