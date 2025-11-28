# External Field Verification Project Plan

**Document Version:** 2.1
**Created:** 2024-11-28
**Updated:** 2024-11-28
**Status:** Planning Phase

**Verification Types:** Notary, Doctor/Medical Provider, Identity (Driver's License/Passport), Death Certificate

## Table of Contents
1. [Overview](#overview)
2. [Current Architecture](#current-architecture)
3. [Proposed Solution](#proposed-solution)
4. [Implementation Plan](#implementation-plan)
5. [Data Models](#data-models)
6. [Configuration](#configuration)
7. [Code Examples](#code-examples)
8. [Testing Strategy](#testing-strategy)
9. [Deployment](#deployment)
10. [Key Files Reference](#key-files-reference)

---

## Overview

### Goal
Add external verification capability to validate extracted fields against external databases/APIs during the document processing pipeline. Supports multiple verification types based on document schema.

### Use Cases

**1. Notary Verification**
- **Documents:** Notarized contracts, affidavits, legal documents
- **Fields:** Notary name, license number, commission expiry
- **Verification:** Against state/national notary registries
- **Purpose:** Confirm notary is legitimate and commission is active

**2. Doctor/Medical Provider Verification**
- **Documents:** Medical records, prescriptions, doctor's notes, medical certificates
- **Fields:** Doctor name, medical license number, DEA number, NPI number
- **Verification:** Against state medical boards, NPI registry, DEA database
- **Purpose:** Confirm provider is licensed and credentials are valid

**3. Identity Verification (Driver's License / Passport)**
- **Documents:** Identity verification forms, KYC documents, applications
- **Fields:** License/passport number, expiration date, issuing authority
- **Verification:** Against DMV databases, passport verification services
- **Purpose:** Confirm identity document is valid and not expired/revoked

**4. Death Certificate Verification**
- **Documents:** Death certificates, probate documents, estate settlement forms
- **Fields:** Death certificate number, deceased name, date of death, certifying physician, funeral home
- **Verification:** Against vital records databases, state health departments, Social Security Death Index (SSDI)
- **Purpose:** Confirm death certificate is legitimate and record exists in official registries

### Benefits
- **Data Quality:** Ensures extracted information is legitimate and current
- **Fraud Prevention:** Flags invalid, expired, or revoked credentials
- **Compliance:** Meets regulatory requirements for credential verification
- **Confidence Boosting:** Increases confidence scores for verified fields
- **Audit Trail:** Records all verification attempts with timestamps
- **Schema-Specific:** Different verification types apply to different document types
- **Configurable:** Enable/disable per schema or globally

---

## Current Architecture

### Pipeline Flow
```
API Upload → Extract Handler → Map Handler → Evaluate Handler → Save Handler → Cosmos DB
             (Document AI)      (GPT-4)        (Confidence)       (Storage)
```

### How It Works Today

**1. Extract Handler**
- Uses Azure Document Intelligence to extract text/layout from PDF/images
- Output: Markdown representation of document content
- Artifact: `content_understanding_output.json`

**2. Map Handler**
- Uses Azure OpenAI GPT-4 to parse markdown into structured schema
- Schema defines expected fields (e.g., notary_name, notary_license)
- Output: JSON with extracted fields + confidence scores (from logprobs)
- Artifact: `gpt_output.json`

**3. Evaluate Handler**
- Merges confidence scores from Document AI and GPT
- Compares each field against threshold (0.8 = 80%)
- Creates comparison data showing which fields passed/failed
- Output: Final confidence scores + comparison results
- Artifact: `evaluate_output.json`

**4. Save Handler**
- Aggregates all results from previous steps
- Stores in Cosmos DB `ContentProcess` collection
- Makes results available via API
- Artifact: `step_outputs.json`

### Key Architectural Patterns

**Queue-Based Processing:**
- Each handler reads from its own Azure Storage Queue
- Processes message asynchronously
- Saves results to Azure Blob Storage
- Enqueues to next step's queue
- Updates Cosmos DB with status

**Handler Base Class:**
All handlers extend `HandlerBase` which provides:
- Queue connection and message polling
- Deserialization of `DataPipeline` objects
- Error handling and retry logic
- Dead-letter queue for failures
- Cosmos DB status updates

**Dynamic Handler Loading:**
Handlers are loaded dynamically based on `APP_PROCESS_STEPS` config:
```python
# Config: APP_PROCESS_STEPS=extract,map,evaluate,save
# Loads: ExtractHandler, MapHandler, EvaluateHandler, SaveHandler
```

---

## Proposed Solution

### New Pipeline Flow
```
API Upload → Extract → Map → Evaluate → VERIFY → Save → Cosmos DB
             (Doc AI)   (GPT)  (Score)     (NEW)    (Store)
                                            ↓
                                    Verification Router
                                            ↓
                        ┌───────────┬───────┼───────┬────────────┐
                        ↓           ↓       ↓       ↓            ↓
                   Notary API  Doctor API  │  Identity API  Death Cert API
                                           │
                                      (SSDI/Vital Records)
```

### Verify Handler Responsibilities

1. **Receive evaluated results** from previous step
2. **Identify schema type** to determine which verification types apply
3. **Route fields to appropriate verifier** (notary, doctor, identity)
4. **Check confidence threshold** - only verify high-confidence extractions
5. **Call external APIs** in parallel for each field requiring verification
6. **Aggregate verification results** from multiple verification types
7. **Update comparison data** with verification status
8. **Save verification results** to blob storage
9. **Pass to Save Handler** for final storage

### Verification Type Routing

**Schema-Based Configuration:**
- Each schema defines which verification types it requires
- Example: "Notarized Medical Record" schema → notary + doctor verification
- Example: "Identity Verification Form" schema → identity verification only
- Example: "Medical Prescription" schema → doctor verification only

**Field Pattern Matching:**
- Within each verification type, field patterns determine which fields to verify
- Example: Notary type → verify fields matching "notary_*"
- Example: Doctor type → verify fields matching "doctor_*", "physician_*", "provider_*"
- Example: Identity type → verify fields matching "license_*", "passport_*", "id_*"

### Integration Points

**Input:**
- Evaluated comparison data from Evaluate Handler
- External API endpoint and credentials from config
- Field patterns to verify from config

**Output:**
- Augmented comparison data with verification status
- Verification metadata (counts, timestamps, API responses)
- Updated confidence scores (optional boost for verified fields)

**Error Handling:**
- API timeouts → mark as ERROR, continue pipeline
- Invalid responses → log error, mark as ERROR
- Low confidence fields → skip verification (SKIPPED status)
- Network failures → retry once, then ERROR

---

## Implementation Plan

### Phase 1: Create Verify Handler (Core Implementation)

#### 1.1 Create File Structure
```
src/ContentProcessor/src/libs/pipeline/handlers/
├── verify_handler.py                        # Main handler class
└── logics/verify_handler/
    ├── __init__.py
    ├── notary_verifier.py                   # External API client
    └── model.py                              # Verification data models
```

#### 1.2 Implement VerifyHandler Class

**Location:** `src/ContentProcessor/src/libs/pipeline/handlers/verify_handler.py`

**Key Methods:**
```python
class VerifyHandler(HandlerBase):
    handler_name: str = "verify"

    async def execute(self, context: MessageContext) -> StepResult:
        """
        Main execution logic for verify handler

        Steps:
        1. Get evaluate handler results
        2. Extract comparison data
        3. Filter fields to verify (by pattern + confidence)
        4. Call external API for each field
        5. Update comparison items with verification status
        6. Save results to blob
        7. Return StepResult
        """
        pass

    async def _verify_fields(
        self,
        comparison_items: List[ExtractionComparisonItem]
    ) -> Dict[str, VerificationResult]:
        """Verify multiple fields in parallel"""
        pass

    def _should_verify_field(
        self,
        field_name: str,
        confidence: float
    ) -> bool:
        """Check if field matches patterns and meets threshold"""
        pass
```

**Implementation Notes:**
- Extends `HandlerBase` (provides queue handling, error management)
- Uses `async/await` for non-blocking external API calls
- Parallel verification using `asyncio.gather()` for multiple fields
- Configurable timeout per API call (default: 30 seconds)
- Graceful degradation - verification failures don't stop pipeline

#### 1.3 Create Verification Models

**Location:** `src/ContentProcessor/src/libs/pipeline/handlers/logics/verify_handler/model.py`

```python
from enum import Enum
from typing import Optional, Any, List
from pydantic import BaseModel

class VerificationType(str, Enum):
    """Types of verification available"""
    NOTARY = "notary"
    DOCTOR = "doctor"
    IDENTITY = "identity"
    DEATH_CERTIFICATE = "death_certificate"

class VerificationStatus(str, Enum):
    """Possible verification outcomes"""
    VERIFIED = "verified"           # Found in database, valid
    NOT_FOUND = "not_found"         # Not in database
    INVALID = "invalid"             # Found but invalid/expired
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
        "notary": {"verified": 2, "not_found": 0, "error": 0},
        "doctor": {"verified": 1, "not_found": 0, "expired": 1},
        "identity": {"verified": 1, "invalid": 0, "error": 0}
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
        "notary": ["notary_name", "notary_license", "notary_commission"],
        "doctor": ["doctor_name", "medical_license", "npi_number"],
        "identity": ["license_number", "passport_number"],
        "death_certificate": ["certificate_number", "deceased_name", "date_of_death"]
    }
    """
```

#### 1.4 Implement External API Clients

Create separate verifier classes for each verification type.

##### 1.4.1 Notary Verifier

**Location:** `src/ContentProcessor/src/libs/pipeline/handlers/logics/verify_handler/notary_verifier.py`

```python
import httpx
import asyncio
from typing import Dict, Any
from .model import VerificationResult, VerificationStatus

class NotaryVerifier:
    """Client for external notary verification API"""

    def __init__(
        self,
        api_endpoint: str,
        api_key: str,
        timeout: int = 30
    ):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.timeout = timeout

    async def verify_notary(
        self,
        field_name: str,
        notary_name: str,
        confidence: float
    ) -> VerificationResult:
        """
        Verify a notary name against external database

        Args:
            field_name: Name of the field being verified
            notary_name: The notary name to verify
            confidence: Extraction confidence (0.0 - 1.0)

        Returns:
            VerificationResult with status and details
        """
        import time
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_endpoint}/verify",
                    json={
                        "notary_name": notary_name,
                        "confidence": confidence
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )

                api_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    data = response.json()
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=notary_name,
                        status=VerificationStatus.VERIFIED,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )
                elif response.status_code == 404:
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=notary_name,
                        status=VerificationStatus.NOT_FOUND,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )
                else:
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=notary_name,
                        status=VerificationStatus.ERROR,
                        error_message=f"HTTP {response.status_code}",
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

        except asyncio.TimeoutError:
            return VerificationResult(
                field_name=field_name,
                extracted_value=notary_name,
                status=VerificationStatus.ERROR,
                error_message="API timeout",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return VerificationResult(
                field_name=field_name,
                extracted_value=notary_name,
                status=VerificationStatus.ERROR,
                error_message=str(e),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )
```

##### 1.4.2 Doctor/Medical Provider Verifier

**Location:** `src/ContentProcessor/src/libs/pipeline/handlers/logics/verify_handler/doctor_verifier.py`

```python
import httpx
import asyncio
from typing import Dict, Any
from .model import VerificationResult, VerificationStatus, VerificationType

class DoctorVerifier:
    """Client for medical provider verification APIs"""

    def __init__(
        self,
        npi_api_endpoint: str,
        state_license_api_endpoint: str,
        api_key: str,
        timeout: int = 30
    ):
        self.npi_api_endpoint = npi_api_endpoint
        self.state_license_api_endpoint = state_license_api_endpoint
        self.api_key = api_key
        self.timeout = timeout

    async def verify_doctor(
        self,
        field_name: str,
        doctor_name: str = None,
        npi_number: str = None,
        license_number: str = None,
        state: str = None,
        confidence: float = None
    ) -> VerificationResult:
        """
        Verify doctor/medical provider credentials

        Can verify by:
        - NPI number (National Provider Identifier)
        - State medical license number
        - Doctor name (fuzzy match against registries)

        Args:
            field_name: Name of the field being verified
            doctor_name: Doctor's name
            npi_number: National Provider Identifier
            license_number: State medical license number
            state: State code (e.g., "CA", "NY") for license lookup
            confidence: Extraction confidence (0.0 - 1.0)

        Returns:
            VerificationResult with status and details
        """
        import time
        start_time = time.time()

        try:
            # Try NPI verification first if NPI provided
            if npi_number:
                result = await self._verify_by_npi(field_name, npi_number, start_time)
                if result.status == VerificationStatus.VERIFIED:
                    return result

            # Try state license verification if license and state provided
            if license_number and state:
                result = await self._verify_by_state_license(
                    field_name, license_number, state, start_time
                )
                if result.status == VerificationStatus.VERIFIED:
                    return result

            # If no specific identifiers, mark as not found
            return VerificationResult(
                field_name=field_name,
                extracted_value=doctor_name or npi_number or license_number,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

        except asyncio.TimeoutError:
            return VerificationResult(
                field_name=field_name,
                extracted_value=doctor_name or npi_number or license_number,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.ERROR,
                error_message="API timeout",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return VerificationResult(
                field_name=field_name,
                extracted_value=doctor_name or npi_number or license_number,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.ERROR,
                error_message=str(e),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

    async def _verify_by_npi(
        self,
        field_name: str,
        npi_number: str,
        start_time: float
    ) -> VerificationResult:
        """Verify using NPI Registry"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.npi_api_endpoint}/api/",
                params={
                    "number": npi_number,
                    "version": "2.1"
                },
                headers={"Accept": "application/json"}
            )

            api_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                if data.get("result_count", 0) > 0:
                    result = data["results"][0]
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=npi_number,
                        verification_type=VerificationType.DOCTOR,
                        status=VerificationStatus.VERIFIED,
                        details={
                            "npi": result.get("number"),
                            "name": result.get("basic", {}).get("name"),
                            "credential": result.get("basic", {}).get("credential"),
                            "taxonomy": result.get("taxonomies", [{}])[0].get("desc")
                        },
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

            return VerificationResult(
                field_name=field_name,
                extracted_value=npi_number,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=api_time
            )

    async def _verify_by_state_license(
        self,
        field_name: str,
        license_number: str,
        state: str,
        start_time: float
    ) -> VerificationResult:
        """Verify using state medical board API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.state_license_api_endpoint}/verify",
                json={
                    "license_number": license_number,
                    "state": state
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )

            api_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "").lower()

                if status == "active":
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=license_number,
                        verification_type=VerificationType.DOCTOR,
                        status=VerificationStatus.VERIFIED,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )
                elif status == "expired":
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=license_number,
                        verification_type=VerificationType.DOCTOR,
                        status=VerificationStatus.EXPIRED,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )
                elif status in ["revoked", "suspended"]:
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=license_number,
                        verification_type=VerificationType.DOCTOR,
                        status=VerificationStatus.REVOKED,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

            return VerificationResult(
                field_name=field_name,
                extracted_value=license_number,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=api_time
            )
```

##### 1.4.3 Identity Verifier (Driver's License / Passport)

**Location:** `src/ContentProcessor/src/libs/pipeline/handlers/logics/verify_handler/identity_verifier.py`

```python
import httpx
import asyncio
from typing import Dict, Any
from datetime import datetime
from .model import VerificationResult, VerificationStatus, VerificationType

class IdentityVerifier:
    """Client for identity document verification APIs (DL, Passport)"""

    def __init__(
        self,
        dmv_api_endpoint: str,
        passport_api_endpoint: str,
        api_key: str,
        timeout: int = 30
    ):
        self.dmv_api_endpoint = dmv_api_endpoint
        self.passport_api_endpoint = passport_api_endpoint
        self.api_key = api_key
        self.timeout = timeout

    async def verify_identity(
        self,
        field_name: str,
        document_type: str,  # "drivers_license" or "passport"
        document_number: str,
        state_or_country: str = None,
        expiration_date: str = None,
        confidence: float = None
    ) -> VerificationResult:
        """
        Verify identity document (driver's license or passport)

        Args:
            field_name: Name of the field being verified
            document_type: "drivers_license" or "passport"
            document_number: License/passport number
            state_or_country: State code (US) or country code
            expiration_date: Document expiration date (YYYY-MM-DD)
            confidence: Extraction confidence (0.0 - 1.0)

        Returns:
            VerificationResult with status and details
        """
        import time
        start_time = time.time()

        try:
            if document_type.lower() == "drivers_license":
                return await self._verify_drivers_license(
                    field_name,
                    document_number,
                    state_or_country,
                    expiration_date,
                    start_time
                )
            elif document_type.lower() == "passport":
                return await self._verify_passport(
                    field_name,
                    document_number,
                    state_or_country,
                    expiration_date,
                    start_time
                )
            else:
                return VerificationResult(
                    field_name=field_name,
                    extracted_value=document_number,
                    verification_type=VerificationType.IDENTITY,
                    status=VerificationStatus.ERROR,
                    error_message=f"Unknown document type: {document_type}",
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    api_response_time=(time.time() - start_time) * 1000
                )

        except asyncio.TimeoutError:
            return VerificationResult(
                field_name=field_name,
                extracted_value=document_number,
                verification_type=VerificationType.IDENTITY,
                status=VerificationStatus.ERROR,
                error_message="API timeout",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return VerificationResult(
                field_name=field_name,
                extracted_value=document_number,
                verification_type=VerificationType.IDENTITY,
                status=VerificationStatus.ERROR,
                error_message=str(e),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

    async def _verify_drivers_license(
        self,
        field_name: str,
        license_number: str,
        state: str,
        expiration_date: str,
        start_time: float
    ) -> VerificationResult:
        """Verify driver's license against DMV database"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.dmv_api_endpoint}/verify",
                json={
                    "license_number": license_number,
                    "state": state,
                    "expiration_date": expiration_date
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )

            api_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "").lower()

                # Check if expired
                if expiration_date:
                    exp_date = datetime.strptime(expiration_date, "%Y-%m-%d")
                    if exp_date < datetime.now():
                        return VerificationResult(
                            field_name=field_name,
                            extracted_value=license_number,
                            verification_type=VerificationType.IDENTITY,
                            status=VerificationStatus.EXPIRED,
                            details=data,
                            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            api_response_time=api_time
                        )

                if status == "valid":
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=license_number,
                        verification_type=VerificationType.IDENTITY,
                        status=VerificationStatus.VERIFIED,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )
                elif status in ["revoked", "suspended"]:
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=license_number,
                        verification_type=VerificationType.IDENTITY,
                        status=VerificationStatus.REVOKED,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )
                elif status == "invalid":
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=license_number,
                        verification_type=VerificationType.IDENTITY,
                        status=VerificationStatus.INVALID,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

            return VerificationResult(
                field_name=field_name,
                extracted_value=license_number,
                verification_type=VerificationType.IDENTITY,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=api_time
            )

    async def _verify_passport(
        self,
        field_name: str,
        passport_number: str,
        country: str,
        expiration_date: str,
        start_time: float
    ) -> VerificationResult:
        """Verify passport against passport verification service"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.passport_api_endpoint}/verify",
                json={
                    "passport_number": passport_number,
                    "country": country,
                    "expiration_date": expiration_date
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )

            api_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "").lower()

                # Check if expired
                if expiration_date:
                    exp_date = datetime.strptime(expiration_date, "%Y-%m-%d")
                    if exp_date < datetime.now():
                        return VerificationResult(
                            field_name=field_name,
                            extracted_value=passport_number,
                            verification_type=VerificationType.IDENTITY,
                            status=VerificationStatus.EXPIRED,
                            details=data,
                            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            api_response_time=api_time
                        )

                if status == "valid":
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=passport_number,
                        verification_type=VerificationType.IDENTITY,
                        status=VerificationStatus.VERIFIED,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )
                elif status in ["revoked", "cancelled"]:
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=passport_number,
                        verification_type=VerificationType.IDENTITY,
                        status=VerificationStatus.REVOKED,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

            return VerificationResult(
                field_name=field_name,
                extracted_value=passport_number,
                verification_type=VerificationType.IDENTITY,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=api_time
            )
```

##### 1.4.4 Death Certificate Verifier

**Location:** `src/ContentProcessor/src/libs/pipeline/handlers/logics/verify_handler/death_certificate_verifier.py`

```python
import httpx
import asyncio
from typing import Dict, Any
from datetime import datetime
from .model import VerificationResult, VerificationStatus, VerificationType

class DeathCertificateVerifier:
    """Client for death certificate verification APIs"""

    def __init__(
        self,
        vital_records_api_endpoint: str,
        ssdi_api_endpoint: str,
        api_key: str,
        timeout: int = 30
    ):
        self.vital_records_api_endpoint = vital_records_api_endpoint
        self.ssdi_api_endpoint = ssdi_api_endpoint
        self.api_key = api_key
        self.timeout = timeout

    async def verify_death_certificate(
        self,
        field_name: str,
        certificate_number: str = None,
        deceased_name: str = None,
        date_of_death: str = None,
        state: str = None,
        certifying_physician: str = None,
        confidence: float = None
    ) -> VerificationResult:
        """
        Verify death certificate against vital records databases

        Can verify by:
        - Death certificate number (most reliable)
        - Deceased person's name + date of death
        - Social Security Death Index (SSDI) lookup

        Args:
            field_name: Name of the field being verified
            certificate_number: Official death certificate number
            deceased_name: Full name of deceased person
            date_of_death: Date of death (YYYY-MM-DD)
            state: State where death certificate was issued
            certifying_physician: Name of certifying physician
            confidence: Extraction confidence (0.0 - 1.0)

        Returns:
            VerificationResult with status and details
        """
        import time
        start_time = time.time()

        try:
            # Try certificate number verification first (most reliable)
            if certificate_number and state:
                result = await self._verify_by_certificate_number(
                    field_name,
                    certificate_number,
                    state,
                    start_time
                )
                if result.status == VerificationStatus.VERIFIED:
                    return result

            # Try SSDI verification if name and date available
            if deceased_name and date_of_death:
                result = await self._verify_by_ssdi(
                    field_name,
                    deceased_name,
                    date_of_death,
                    start_time
                )
                if result.status == VerificationStatus.VERIFIED:
                    return result

            # If no verifiable information, mark as not found
            return VerificationResult(
                field_name=field_name,
                extracted_value=certificate_number or deceased_name,
                verification_type=VerificationType.DEATH_CERTIFICATE,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

        except asyncio.TimeoutError:
            return VerificationResult(
                field_name=field_name,
                extracted_value=certificate_number or deceased_name,
                verification_type=VerificationType.DEATH_CERTIFICATE,
                status=VerificationStatus.ERROR,
                error_message="API timeout",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return VerificationResult(
                field_name=field_name,
                extracted_value=certificate_number or deceased_name,
                verification_type=VerificationType.DEATH_CERTIFICATE,
                status=VerificationStatus.ERROR,
                error_message=str(e),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

    async def _verify_by_certificate_number(
        self,
        field_name: str,
        certificate_number: str,
        state: str,
        start_time: float
    ) -> VerificationResult:
        """Verify using state vital records database"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.vital_records_api_endpoint}/verify",
                json={
                    "certificate_number": certificate_number,
                    "state": state,
                    "record_type": "death"
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )

            api_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "").lower()

                if status == "verified":
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=certificate_number,
                        verification_type=VerificationType.DEATH_CERTIFICATE,
                        status=VerificationStatus.VERIFIED,
                        details={
                            "certificate_number": data.get("certificate_number"),
                            "deceased_name": data.get("deceased_name"),
                            "date_of_death": data.get("date_of_death"),
                            "place_of_death": data.get("place_of_death"),
                            "certifying_physician": data.get("certifying_physician"),
                            "issuing_state": data.get("state")
                        },
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )
                elif status == "invalid":
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=certificate_number,
                        verification_type=VerificationType.DEATH_CERTIFICATE,
                        status=VerificationStatus.INVALID,
                        details=data,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

            return VerificationResult(
                field_name=field_name,
                extracted_value=certificate_number,
                verification_type=VerificationType.DEATH_CERTIFICATE,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=api_time
            )

    async def _verify_by_ssdi(
        self,
        field_name: str,
        deceased_name: str,
        date_of_death: str,
        start_time: float
    ) -> VerificationResult:
        """Verify using Social Security Death Index"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Parse name into components
            name_parts = deceased_name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""

            response = await client.post(
                f"{self.ssdi_api_endpoint}/search",
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "death_date": date_of_death
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )

            api_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                # Check for exact or close match
                for result in results:
                    result_date = result.get("death_date")
                    result_name = f"{result.get('first_name')} {result.get('last_name')}"

                    # Fuzzy match on name and exact match on date
                    if (result_date == date_of_death and
                        result_name.lower() == deceased_name.lower()):
                        return VerificationResult(
                            field_name=field_name,
                            extracted_value=deceased_name,
                            verification_type=VerificationType.DEATH_CERTIFICATE,
                            status=VerificationStatus.VERIFIED,
                            details={
                                "deceased_name": result_name,
                                "date_of_death": result_date,
                                "ssn_last4": result.get("ssn_last4"),
                                "birth_date": result.get("birth_date"),
                                "death_state": result.get("death_state"),
                                "verification_source": "SSDI"
                            },
                            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            api_response_time=api_time
                        )

            return VerificationResult(
                field_name=field_name,
                extracted_value=deceased_name,
                verification_type=VerificationType.DEATH_CERTIFICATE,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=api_time
            )
```

---

### Phase 2: Extend Data Models

#### 2.1 Extend Comparison Model

**Location:** `src/ContentProcessor/src/libs/pipeline/handlers/logics/evaluate_handler/comparison.py`

**Current Model:**
```python
class ExtractionComparisonItem(BaseModel):
    Field: str
    Extracted: Any
    Confidence: str
    IsAboveThreshold: bool
```

**Extended Model:**
```python
class ExtractionComparisonItem(BaseModel):
    Field: str
    Extracted: Any
    Confidence: str
    IsAboveThreshold: bool

    # NEW FIELDS FOR VERIFICATION
    VerificationStatus: Optional[str] = None
    VerificationDetails: Optional[dict] = None
    VerifiedAt: Optional[str] = None
    VerificationResponseTime: Optional[float] = None
```

#### 2.2 Extend ContentProcess Model

**Location:** `src/ContentProcessorAPI/app/routers/models/contentprocessor/content_process.py`

**Add New Field:**
```python
class ContentProcess(BaseModel):
    process_id: str
    processed_file_name: str
    # ... existing fields ...

    # NEW FIELD FOR VERIFICATION
    verification_metadata: Optional[dict] = None
    """
    Example structure:
    {
        "total_fields_checked": 3,
        "verified_count": 2,
        "not_found_count": 1,
        "error_count": 0,
        "skipped_count": 0,
        "total_api_calls": 3,
        "total_api_time": 450.5,
        "verification_timestamp": "2024-11-28T10:30:00Z"
    }
    """
```

---

### Phase 3: Configuration

#### 3.1 Environment Variables

Add to `.env` or Azure Container App Environment Variables:

```bash
# ===== PIPELINE CONFIGURATION =====
APP_PROCESS_STEPS=extract,map,evaluate,verify,save

# ===== NOTARY VERIFICATION =====
APP_NOTARY_API_ENDPOINT=https://api.notaryregistry.gov/v1
APP_NOTARY_API_KEY=your_notary_api_key_here

# ===== DOCTOR/MEDICAL PROVIDER VERIFICATION =====
APP_DOCTOR_NPI_API_ENDPOINT=https://npiregistry.cms.hhs.gov
APP_DOCTOR_LICENSE_API_ENDPOINT=https://api.statemedicalboards.com/v1
APP_DOCTOR_API_KEY=your_medical_api_key_here

# ===== IDENTITY VERIFICATION (DL/Passport) =====
APP_IDENTITY_DMV_API_ENDPOINT=https://api.dmv-verification.com/v1
APP_IDENTITY_PASSPORT_API_ENDPOINT=https://api.passport-verification.com/v1
APP_IDENTITY_API_KEY=your_identity_api_key_here

# ===== DEATH CERTIFICATE VERIFICATION =====
APP_DEATH_CERT_VITAL_RECORDS_API_ENDPOINT=https://api.vitalrecords.gov/v1
APP_DEATH_CERT_SSDI_API_ENDPOINT=https://api.ssa.gov/ssdi/v1
APP_DEATH_CERT_API_KEY=your_death_cert_api_key_here

# ===== VERIFICATION BEHAVIOR =====
APP_VERIFY_CONFIDENCE_THRESHOLD=0.70
APP_VERIFY_TIMEOUT=30
APP_VERIFY_ENABLED=true
APP_VERIFY_CONFIDENCE_BOOST=0.05

# ===== SCHEMA-SPECIFIC VERIFICATION CONFIG =====
# Stored in Cosmos DB or blob storage (see section 3.3)
```

#### 3.2 Update AppConfiguration Class

**Location:** `src/ContentProcessor/src/libs/application/application_configuration.py`

**Add New Fields:**
```python
class AppConfiguration(ModelBaseSettings):
    # ... existing configuration ...

    # Notary Verification
    app_notary_api_endpoint: str = ""
    app_notary_api_key: str = ""

    # Doctor/Medical Provider Verification
    app_doctor_npi_api_endpoint: str = "https://npiregistry.cms.hhs.gov"  # Public NPI registry
    app_doctor_license_api_endpoint: str = ""
    app_doctor_api_key: str = ""

    # Identity Verification (Driver's License / Passport)
    app_identity_dmv_api_endpoint: str = ""
    app_identity_passport_api_endpoint: str = ""
    app_identity_api_key: str = ""

    # Death Certificate Verification
    app_death_cert_vital_records_api_endpoint: str = ""
    app_death_cert_ssdi_api_endpoint: str = ""
    app_death_cert_api_key: str = ""

    # General Verification Settings
    app_verify_confidence_threshold: float = 0.70
    app_verify_timeout: int = 30
    app_verify_enabled: bool = True
    app_verify_confidence_boost: float = 0.0
```

#### 3.3 Schema-Specific Verification Configuration

**Storage Location:** Cosmos DB `schema` collection or blob storage at `cps-configuration/verification-config/{schema_id}.json`

**Configuration Format:**

```json
{
  "schema_id": "abcd1234-5678-90ab-cdef-1234567890ab",
  "schema_name": "Notarized Medical Record",
  "enabled_verification_types": ["notary", "doctor"],
  "verification_rules": {
    "notary": {
      "enabled": true,
      "field_mappings": {
        "notary_name": {
          "field_name": "notary_name",
          "verification_method": "name_lookup",
          "required": true
        },
        "notary_license": {
          "field_name": "notary_license_number",
          "verification_method": "license_lookup",
          "required": true
        },
        "notary_commission_expiry": {
          "field_name": "notary_commission_expiry_date",
          "verification_method": "expiry_check",
          "required": false
        }
      },
      "confidence_threshold": 0.70
    },
    "doctor": {
      "enabled": true,
      "field_mappings": {
        "doctor_name": {
          "field_name": "physician_name",
          "verification_method": "name_lookup",
          "required": true
        },
        "npi_number": {
          "field_name": "npi",
          "verification_method": "npi_lookup",
          "required": true
        },
        "medical_license": {
          "field_name": "medical_license_number",
          "verification_method": "state_license_lookup",
          "required": false,
          "additional_fields": ["state"]
        }
      },
      "confidence_threshold": 0.75
    }
  }
}
```

**Example Configurations for Different Schema Types:**

##### Notary Document Only
```json
{
  "schema_id": "schema-001",
  "schema_name": "Notarized Contract",
  "enabled_verification_types": ["notary"],
  "verification_rules": {
    "notary": {
      "enabled": true,
      "field_mappings": {
        "notary_name": {"field_name": "notary_name", "required": true},
        "notary_license": {"field_name": "notary_license_number", "required": true}
      }
    }
  }
}
```

##### Medical Record Only
```json
{
  "schema_id": "schema-002",
  "schema_name": "Medical Prescription",
  "enabled_verification_types": ["doctor"],
  "verification_rules": {
    "doctor": {
      "enabled": true,
      "field_mappings": {
        "doctor_name": {"field_name": "prescribing_physician", "required": true},
        "npi_number": {"field_name": "npi", "required": true},
        "dea_number": {"field_name": "dea", "required": false}
      }
    }
  }
}
```

##### Identity Verification Form
```json
{
  "schema_id": "schema-003",
  "schema_name": "KYC Identity Verification",
  "enabled_verification_types": ["identity"],
  "verification_rules": {
    "identity": {
      "enabled": true,
      "field_mappings": {
        "drivers_license_number": {
          "field_name": "dl_number",
          "document_type": "drivers_license",
          "required": true,
          "additional_fields": ["state", "expiration_date"]
        },
        "passport_number": {
          "field_name": "passport_number",
          "document_type": "passport",
          "required": false,
          "additional_fields": ["country", "expiration_date"]
        }
      }
    }
  }
}
```

##### Multi-Verification Schema (Notarized Medical Record)
```json
{
  "schema_id": "schema-004",
  "schema_name": "Notarized Medical Certificate",
  "enabled_verification_types": ["notary", "doctor"],
  "verification_rules": {
    "notary": {
      "enabled": true,
      "field_mappings": {
        "notary_name": {"field_name": "notary_name", "required": true},
        "notary_license": {"field_name": "notary_license", "required": true}
      }
    },
    "doctor": {
      "enabled": true,
      "field_mappings": {
        "doctor_name": {"field_name": "certifying_physician", "required": true},
        "medical_license": {"field_name": "physician_license", "required": true}
      }
    }
  }
}
```

##### Death Certificate Schema
```json
{
  "schema_id": "schema-005",
  "schema_name": "Death Certificate",
  "enabled_verification_types": ["death_certificate", "doctor"],
  "verification_rules": {
    "death_certificate": {
      "enabled": true,
      "field_mappings": {
        "certificate_number": {
          "field_name": "death_certificate_number",
          "required": true,
          "additional_fields": ["state"]
        },
        "deceased_name": {
          "field_name": "deceased_full_name",
          "required": true
        },
        "date_of_death": {
          "field_name": "date_of_death",
          "required": true
        }
      }
    },
    "doctor": {
      "enabled": true,
      "field_mappings": {
        "certifying_physician": {
          "field_name": "certifying_physician_name",
          "required": false
        },
        "physician_license": {
          "field_name": "physician_medical_license",
          "required": false
        }
      }
    }
  }
}
```

---

### Phase 4: Queue Setup

#### 4.1 Create Verify Queue

**Queue Name:** `verify`

**Queue Configuration:**
- Visibility timeout: 30 seconds (from `app_message_queue_visibility_timeout`)
- Message TTL: 7 days (default)
- Max delivery count: 5 (then move to dead-letter)

**Dead Letter Queue:** `verify-deadletter` (created automatically)

**Note:** Queue is created automatically by handler on startup using existing pattern in `HandlerBase`

#### 4.2 Update Handler Loading

**File:** `src/ContentProcessor/src/libs/process_host/handler_type_loader.py`

No code changes needed - dynamic loader will automatically find `verify_handler.py` and load `VerifyHandler` class based on `APP_PROCESS_STEPS` configuration.

---

### Phase 5: UI Display (Optional Enhancement)

#### 5.1 Show Verification Status in JSON Editor

**Location:** `src/ContentProcessorWeb/src/Components/JSONEditor/JSONEditor.tsx`

**Enhancement Ideas:**
- Display verification badge next to verified fields
- Color-code fields by verification status:
  - ✓ Green: Verified
  - ⚠ Yellow: Not Found
  - ✗ Red: Error
  - ⊘ Gray: Skipped
- Tooltip on hover showing verification details

#### 5.2 Add Verification Summary Panel

**New Component:** `VerificationSummary.tsx`

**Display:**
- Total fields verified
- Success rate (verified / total)
- Average API response time
- Last verification timestamp
- Link to view verification details

---

## Data Models

### Complete Data Flow with Verification

```json
{
  "process_id": "123e4567-e89b-12d3-a456-426614174000",
  "processed_file_name": "notarized_document.pdf",
  "status": "Completed",

  "result": {
    "notary_name": "John Smith",
    "notary_license": "CA-12345",
    "notary_commission_expiry": "2025-12-31",
    "document_date": "2024-11-28"
  },

  "confidence": {
    "notary_name": 0.95,
    "notary_license": 0.88,
    "notary_commission_expiry": 0.92,
    "document_date": 0.99
  },

  "extracted_comparison_data": {
    "items": [
      {
        "Field": "notary_name",
        "Extracted": "John Smith",
        "Confidence": "95.00%",
        "IsAboveThreshold": true,
        "VerificationStatus": "verified",
        "VerificationDetails": {
          "license_number": "CA-12345",
          "status": "active",
          "commission_expiry": "2025-12-31"
        },
        "VerifiedAt": "2024-11-28T10:30:15Z",
        "VerificationResponseTime": 245.3
      },
      {
        "Field": "notary_license",
        "Extracted": "CA-12345",
        "Confidence": "88.00%",
        "IsAboveThreshold": true,
        "VerificationStatus": "verified",
        "VerifiedAt": "2024-11-28T10:30:15Z",
        "VerificationResponseTime": 238.7
      },
      {
        "Field": "document_date",
        "Extracted": "2024-11-28",
        "Confidence": "99.00%",
        "IsAboveThreshold": true,
        "VerificationStatus": null,
        "VerifiedAt": null
      }
    ]
  },

  "verification_metadata": {
    "total_fields_checked": 2,
    "verified_count": 2,
    "not_found_count": 0,
    "invalid_count": 0,
    "error_count": 0,
    "skipped_count": 1,
    "total_api_calls": 2,
    "total_api_time": 484.0,
    "verification_timestamp": "2024-11-28T10:30:15Z"
  }
}
```

---

## Configuration

### Example Configuration File

**File:** `.env`

```bash
# ===== EXISTING CONFIGURATION =====
APP_PROCESS_STEPS=extract,map,evaluate,verify,save
APP_MESSAGE_QUEUE_INTERVAL=5
APP_MESSAGE_QUEUE_VISIBILITY_TIMEOUT=30
APP_STORAGE_QUEUE_URL=https://stg6fsvw.queue.core.windows.net/
APP_STORAGE_BLOB_URL=https://stg6fsvw.blob.core.windows.net/
APP_CPS_PROCESSES=cps-processes
APP_COSMOS_CONNSTR=AccountEndpoint=https://...
APP_COSMOS_DATABASE=content-processing
APP_COSMOS_CONTAINER_PROCESS=process
APP_COSMOS_CONTAINER_SCHEMA=schema
APP_CONTENT_UNDERSTANDING_ENDPOINT=https://...
APP_AZURE_OPENAI_ENDPOINT=https://...
APP_AZURE_OPENAI_MODEL=gpt-4

# ===== NEW VERIFICATION CONFIGURATION =====

# External API Configuration
APP_NOTARY_API_ENDPOINT=https://api.notaryregistry.gov/v1
APP_NOTARY_API_KEY=sk_live_abc123xyz456

# Field Matching Patterns (comma-separated)
# Will verify any field containing these patterns (case-insensitive)
APP_VERIFY_FIELD_PATTERNS=notary_name,notary_license,notary_commission

# Confidence Threshold (0.0 - 1.0)
# Only verify fields with confidence >= this threshold
APP_VERIFY_CONFIDENCE_THRESHOLD=0.70

# API Timeout (seconds)
APP_VERIFY_TIMEOUT=30

# Enable/Disable Verification
APP_VERIFY_ENABLED=true

# Optional: Confidence Boost (0.0 - 0.2)
# Add this to confidence score for verified fields
# Example: 0.85 confidence + 0.05 boost = 0.90
APP_VERIFY_CONFIDENCE_BOOST=0.05
```

### Azure Container App Configuration

To set environment variables in Azure Container App:

```bash
# Get container app name
az containerapp list --resource-group <resource-group> --query "[].name"

# Set environment variables
az containerapp update \
  --name <container-app-name> \
  --resource-group <resource-group> \
  --set-env-vars \
    APP_PROCESS_STEPS="extract,map,evaluate,verify,save" \
    APP_NOTARY_API_ENDPOINT="https://api.notaryregistry.gov/v1" \
    APP_NOTARY_API_KEY="secretref:notary-api-key" \
    APP_VERIFY_FIELD_PATTERNS="notary_name,notary_license" \
    APP_VERIFY_CONFIDENCE_THRESHOLD="0.70" \
    APP_VERIFY_TIMEOUT="30" \
    APP_VERIFY_ENABLED="true"

# For sensitive values, use secrets
az containerapp secret set \
  --name <container-app-name> \
  --resource-group <resource-group> \
  --secrets notary-api-key="your-actual-api-key"
```

---

## Code Examples

### Complete VerifyHandler Implementation

**File:** `src/ContentProcessor/src/libs/pipeline/handlers/verify_handler.py`

```python
import asyncio
from typing import List, Dict
from libs.pipeline.queue_handler_base import HandlerBase, MessageContext
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.handlers.logics.evaluate_handler.comparison import (
    ExtractionComparisonItem,
    ExtractionComparisonData
)
from libs.pipeline.handlers.logics.verify_handler.notary_verifier import NotaryVerifier
from libs.pipeline.handlers.logics.verify_handler.model import (
    VerificationResult,
    VerificationMetadata,
    VerificationStatus
)
from libs.pipeline.entities.file_details import ArtifactType
import json
import time

class VerifyHandler(HandlerBase):
    """
    Handler for verifying extracted fields against external databases

    Responsibilities:
    - Identify fields requiring verification based on patterns
    - Check confidence threshold before verification
    - Call external API for verification
    - Update comparison data with verification results
    - Track verification metadata (counts, timing)
    """

    handler_name: str = "verify"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize notary verifier client
        config = self.application_context.application_configuration
        self.verifier = NotaryVerifier(
            api_endpoint=config.app_notary_api_endpoint,
            api_key=config.app_notary_api_key,
            timeout=config.app_verify_timeout
        )

        # Get configuration
        self.field_patterns = config.app_verify_field_patterns
        self.confidence_threshold = config.app_verify_confidence_threshold
        self.enabled = config.app_verify_enabled
        self.confidence_boost = getattr(config, 'app_verify_confidence_boost', 0.0)

    async def execute(self, context: MessageContext) -> StepResult:
        """
        Main execution logic for verify handler
        """
        try:
            # If verification disabled, pass through
            if not self.enabled:
                return self._create_passthrough_result(context)

            # Get evaluate handler results
            evaluate_result = context.data_pipeline.get_step_result("evaluate")
            if not evaluate_result:
                raise Exception("Evaluate step result not found")

            # Load comparison data from evaluate step
            comparison_data = self._load_comparison_data(evaluate_result)

            # Filter fields to verify
            fields_to_verify = [
                item for item in comparison_data.items
                if self._should_verify_field(item)
            ]

            # Verify fields in parallel
            verification_results = await self._verify_fields(fields_to_verify)

            # Update comparison items with verification results
            for item in comparison_data.items:
                if item.Field in verification_results:
                    result = verification_results[item.Field]
                    item.VerificationStatus = result.status.value
                    item.VerificationDetails = result.details
                    item.VerifiedAt = result.timestamp
                    item.VerificationResponseTime = result.api_response_time

                    # Optional: Boost confidence for verified fields
                    if result.status == VerificationStatus.VERIFIED and self.confidence_boost > 0:
                        self._boost_confidence(item, self.confidence_boost)

            # Create verification metadata
            metadata = self._create_verification_metadata(verification_results)

            # Save results to blob
            result_file = context.data_pipeline.add_file(
                file_name="verify_output.json",
                artifact_type=ArtifactType.ScoreMergedData
            )

            output_data = {
                "comparison_data": comparison_data.dict(),
                "verification_metadata": metadata.dict(),
                "verification_results": {
                    field: result.dict()
                    for field, result in verification_results.items()
                }
            }

            result_file.upload_json_text(
                json_text=json.dumps(output_data, indent=2),
                account_url=self.application_context.application_configuration.app_storage_blob_url,
                container_name=self.application_context.application_configuration.app_cps_processes,
                credential=self.application_context.token_credential
            )

            # Return step result
            return StepResult(
                process_id=context.data_pipeline.pipeline_status.process_id,
                step_name=self.handler_name,
                result={
                    "result": "success",
                    "file_name": result_file.name,
                    "fields_verified": len(fields_to_verify),
                    "verified_count": metadata.verified_count,
                    "not_found_count": metadata.not_found_count,
                    "error_count": metadata.error_count
                }
            )

        except Exception as e:
            raise Exception(f"Verify handler failed: {str(e)}")

    def _should_verify_field(self, item: ExtractionComparisonItem) -> bool:
        """Check if field should be verified"""
        # Check confidence threshold
        confidence_value = float(item.Confidence.rstrip('%')) / 100
        if confidence_value < self.confidence_threshold:
            return False

        # Check field pattern match
        field_lower = item.Field.lower()
        return any(pattern.lower() in field_lower for pattern in self.field_patterns)

    async def _verify_fields(
        self,
        fields: List[ExtractionComparisonItem]
    ) -> Dict[str, VerificationResult]:
        """Verify multiple fields in parallel"""
        tasks = []
        for item in fields:
            confidence_value = float(item.Confidence.rstrip('%')) / 100
            task = self.verifier.verify_notary(
                field_name=item.Field,
                notary_name=str(item.Extracted),
                confidence=confidence_value
            )
            tasks.append((item.Field, task))

        # Execute in parallel
        results = {}
        gathered = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        for (field_name, _), result in zip(tasks, gathered):
            if isinstance(result, Exception):
                # Handle exception
                results[field_name] = VerificationResult(
                    field_name=field_name,
                    extracted_value="",
                    status=VerificationStatus.ERROR,
                    error_message=str(result),
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    api_response_time=0
                )
            else:
                results[field_name] = result

        return results

    def _create_verification_metadata(
        self,
        results: Dict[str, VerificationResult]
    ) -> VerificationMetadata:
        """Create metadata summary from verification results"""
        status_counts = {
            VerificationStatus.VERIFIED: 0,
            VerificationStatus.NOT_FOUND: 0,
            VerificationStatus.INVALID: 0,
            VerificationStatus.ERROR: 0,
            VerificationStatus.SKIPPED: 0
        }

        total_api_time = 0
        for result in results.values():
            status_counts[result.status] += 1
            total_api_time += result.api_response_time

        return VerificationMetadata(
            total_fields_checked=len(results),
            verified_count=status_counts[VerificationStatus.VERIFIED],
            not_found_count=status_counts[VerificationStatus.NOT_FOUND],
            invalid_count=status_counts[VerificationStatus.INVALID],
            error_count=status_counts[VerificationStatus.ERROR],
            skipped_count=status_counts[VerificationStatus.SKIPPED],
            total_api_calls=len(results),
            total_api_time=total_api_time,
            verification_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    def _load_comparison_data(self, evaluate_result) -> ExtractionComparisonData:
        """Load comparison data from evaluate step result"""
        # Implementation depends on how evaluate stores data
        # This is a placeholder
        pass

    def _boost_confidence(self, item: ExtractionComparisonItem, boost: float):
        """Increase confidence score for verified fields"""
        current = float(item.Confidence.rstrip('%')) / 100
        new_confidence = min(1.0, current + boost)
        item.Confidence = f"{new_confidence * 100:.2f}%"

    def _create_passthrough_result(self, context: MessageContext) -> StepResult:
        """Create result when verification is disabled"""
        return StepResult(
            process_id=context.data_pipeline.pipeline_status.process_id,
            step_name=self.handler_name,
            result={
                "result": "skipped",
                "message": "Verification disabled"
            }
        )
```

---

## Testing Strategy

### Unit Tests

**Location:** `src/ContentProcessor/src/tests/pipeline/handlers/test_verify_handler.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock
from libs.pipeline.handlers.verify_handler import VerifyHandler
from libs.pipeline.handlers.logics.verify_handler.model import VerificationStatus

@pytest.mark.asyncio
async def test_verify_handler_success():
    """Test successful verification"""
    # Setup
    handler = VerifyHandler(...)
    context = create_mock_context(
        notary_name="John Smith",
        confidence=0.95
    )

    # Mock external API
    handler.verifier.verify_notary = AsyncMock(
        return_value=VerificationResult(
            status=VerificationStatus.VERIFIED,
            details={"license": "CA-12345"}
        )
    )

    # Execute
    result = await handler.execute(context)

    # Assert
    assert result.result["result"] == "success"
    assert result.result["verified_count"] == 1

@pytest.mark.asyncio
async def test_verify_handler_not_found():
    """Test notary not found in database"""
    # Test implementation
    pass

@pytest.mark.asyncio
async def test_verify_handler_timeout():
    """Test API timeout handling"""
    # Test implementation
    pass

@pytest.mark.asyncio
async def test_verify_handler_low_confidence_skipped():
    """Test low confidence fields are skipped"""
    # Test implementation
    pass
```

### Integration Tests

**Test with real API:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_verification():
    """Test complete pipeline with verification"""
    # 1. Upload test document with known notary
    # 2. Wait for processing
    # 3. Retrieve results
    # 4. Assert verification data present
    # 5. Assert verification status correct
    pass
```

### Performance Tests

**Load Testing:**
```python
@pytest.mark.performance
async def test_parallel_verification_performance():
    """Test verification with multiple fields"""
    # Test 10 fields verified in parallel
    # Assert total time < 2 * single_api_time
    pass
```

---

## Deployment

### Deployment Checklist

- [ ] **Code Complete**
  - [ ] VerifyHandler implemented
  - [ ] NotaryVerifier client implemented
  - [ ] Data models created
  - [ ] Configuration added
  - [ ] Unit tests written and passing

- [ ] **Configuration**
  - [ ] Environment variables added to Azure Container App
  - [ ] API key stored in Azure Key Vault
  - [ ] Field patterns configured
  - [ ] Confidence threshold tuned

- [ ] **Infrastructure**
  - [ ] Verify queue created (automatic)
  - [ ] Dead-letter queue configured
  - [ ] External API connectivity tested
  - [ ] Firewall rules updated if needed

- [ ] **Testing**
  - [ ] Unit tests passing
  - [ ] Integration tests passing
  - [ ] End-to-end test with sample document
  - [ ] Performance testing complete

- [ ] **Monitoring**
  - [ ] Application Insights logging configured
  - [ ] Alert rules created for API failures
  - [ ] Dashboard created for verification metrics

- [ ] **Documentation**
  - [ ] API documentation updated
  - [ ] User guide updated
  - [ ] Troubleshooting guide created

### Deployment Steps

#### 1. Deploy Code Changes

```bash
# Commit changes
git add .
git commit -m "Add notary verification handler"

# Build and push Docker images
cd infra/scripts
./build_images.sh

# Deploy via azd
azd up
```

#### 2. Configure Environment Variables

```bash
# Set environment variables
az containerapp update \
  --name <app-name> \
  --resource-group <rg> \
  --set-env-vars \
    APP_PROCESS_STEPS="extract,map,evaluate,verify,save" \
    APP_NOTARY_API_ENDPOINT="https://api.notaryregistry.gov/v1" \
    APP_VERIFY_FIELD_PATTERNS="notary_name,notary_license" \
    APP_VERIFY_CONFIDENCE_THRESHOLD="0.70"

# Set API key secret
az containerapp secret set \
  --name <app-name> \
  --resource-group <rg> \
  --secrets notary-api-key="<actual-key>"

az containerapp update \
  --name <app-name> \
  --resource-group <rg> \
  --set-env-vars APP_NOTARY_API_KEY="secretref:notary-api-key"
```

#### 3. Verify Deployment

```bash
# Check logs
az containerapp logs show \
  --name <app-name> \
  --resource-group <rg> \
  --follow

# Test with sample document
curl -X POST https://<api-url>/contentprocessor/submit \
  -F "file=@sample_notary_doc.pdf" \
  -F 'data={"Schema_Id":"<schema-id>"}'

# Check status
curl https://<api-url>/contentprocessor/status/<process-id>

# Get results
curl https://<api-url>/contentprocessor/processed/<process-id>
```

---

## Key Files Reference

### Core Pipeline Files

| File Path | Purpose |
|-----------|---------|
| `src/ContentProcessor/src/libs/pipeline/queue_handler_base.py` | Base class for all handlers |
| `src/ContentProcessor/src/libs/pipeline/entities/pipeline_data.py` | DataPipeline object definition |
| `src/ContentProcessor/src/libs/pipeline/entities/pipeline_status.py` | Pipeline status tracking |
| `src/ContentProcessor/src/libs/pipeline/entities/pipeline_step_result.py` | Step result model |
| `src/ContentProcessor/src/libs/pipeline/entities/file_details.py` | File and artifact management |

### Existing Handlers

| File Path | Handler | Purpose |
|-----------|---------|---------|
| `src/ContentProcessor/src/libs/pipeline/handlers/extract_handler.py` | ExtractHandler | Document Intelligence extraction |
| `src/ContentProcessor/src/libs/pipeline/handlers/map_handler.py` | MapHandler | GPT-4 schema mapping |
| `src/ContentProcessor/src/libs/pipeline/handlers/evaluate_handler.py` | EvaluateHandler | Confidence scoring |
| `src/ContentProcessor/src/libs/pipeline/handlers/save_handler.py` | SaveHandler | Cosmos DB storage |

### Evaluate Handler Models

| File Path | Purpose |
|-----------|---------|
| `src/ContentProcessor/src/libs/pipeline/handlers/logics/evaluate_handler/model.py` | DataExtractionResult model |
| `src/ContentProcessor/src/libs/pipeline/handlers/logics/evaluate_handler/comparison.py` | Comparison data models |

### API Files

| File Path | Purpose |
|-----------|---------|
| `src/ContentProcessorAPI/app/routers/contentprocessor.py` | Main API endpoints |
| `src/ContentProcessorAPI/app/routers/models/contentprocessor/content_process.py` | ContentProcess model |

### Configuration Files

| File Path | Purpose |
|-----------|---------|
| `src/ContentProcessor/src/libs/application/application_configuration.py` | App configuration model |
| `.env` | Local environment variables |

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `src/ContentProcessor/src/libs/pipeline/handlers/verify_handler.py` | Main verify handler |
| `src/ContentProcessor/src/libs/pipeline/handlers/logics/verify_handler/__init__.py` | Package init |
| `src/ContentProcessor/src/libs/pipeline/handlers/logics/verify_handler/model.py` | Verification models |
| `src/ContentProcessor/src/libs/pipeline/handlers/logics/verify_handler/notary_verifier.py` | API client |
| `src/ContentProcessor/src/tests/pipeline/handlers/test_verify_handler.py` | Unit tests |

---

## Implementation Timeline

### Week 1: Foundation
- **Day 1-2:** Create data models and API client
- **Day 3-4:** Implement VerifyHandler class
- **Day 5:** Write unit tests

### Week 2: Integration
- **Day 1-2:** Extend existing models (comparison, ContentProcess)
- **Day 3:** Add configuration support
- **Day 4-5:** Integration testing

### Week 3: Deployment
- **Day 1-2:** Deploy to test environment
- **Day 3:** Performance testing and tuning
- **Day 4:** Documentation
- **Day 5:** Production deployment

### Week 4: Enhancement (Optional)
- **Day 1-3:** UI enhancements
- **Day 4-5:** Monitoring and alerting setup

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| External API downtime | High | Cache results, graceful degradation, timeout handling |
| API rate limiting | Medium | Implement exponential backoff, request queuing |
| Increased processing time | Medium | Parallel verification, confidence threshold tuning |
| API cost | Medium | Only verify high-confidence fields, set daily limits |
| False negatives (valid notary not found) | High | Manual review process, user feedback mechanism |
| Security (API key exposure) | High | Use Azure Key Vault, rotate keys regularly |

---

## Success Metrics

### Technical Metrics
- **Verification Success Rate:** > 95%
- **API Response Time:** < 500ms average
- **Error Rate:** < 2%
- **Pipeline Processing Time Impact:** < 10% increase

### Business Metrics
- **False Positive Reduction:** 80% decrease
- **Manual Review Time:** 50% reduction
- **User Confidence:** Increased trust in extracted data
- **Fraud Detection:** Track invalid notaries caught

---

## Future Enhancements

### Phase 2 Features
1. **Multiple Verification Sources**
   - Support multiple API providers
   - Fallback to secondary source if primary fails
   - Consensus verification (2+ sources agree)

2. **Caching**
   - Cache verified notaries for 24 hours
   - Reduce duplicate API calls
   - Faster processing for known notaries

3. **Machine Learning**
   - Learn from verification patterns
   - Predict which fields need verification
   - Auto-adjust confidence thresholds

4. **Batch Verification**
   - Group multiple documents
   - Single API call for batch verification
   - Cost optimization

5. **Real-time Notifications**
   - Alert users when verification fails
   - Webhook integration for downstream systems
   - Slack/Teams notifications

6. **Analytics Dashboard**
   - Verification success trends
   - API performance metrics
   - Cost tracking
   - Most common verification failures

---

## Support and Troubleshooting

### Common Issues

**Issue:** Verification handler not running
- **Check:** `APP_PROCESS_STEPS` includes "verify"
- **Check:** Handler logs for initialization errors
- **Check:** Queue connection string valid

**Issue:** All verifications showing ERROR
- **Check:** External API endpoint reachable
- **Check:** API key valid and not expired
- **Check:** Firewall rules allow outbound HTTPS
- **Check:** Timeout not too short

**Issue:** No fields being verified
- **Check:** `APP_VERIFY_FIELD_PATTERNS` matches field names
- **Check:** Confidence threshold not too high
- **Check:** `APP_VERIFY_ENABLED=true`

**Issue:** Slow processing
- **Check:** API response times in logs
- **Check:** Timeout setting appropriate
- **Check:** Number of fields being verified per document
- **Consider:** Increase confidence threshold to verify fewer fields

### Debugging Commands

```bash
# View handler logs
az containerapp logs show \
  --name <app-name> \
  --resource-group <rg> \
  --type console \
  --follow

# Check queue messages
az storage queue peek \
  --name verify \
  --connection-string "<conn-string>"

# View dead-letter queue
az storage queue peek \
  --name verify-deadletter \
  --connection-string "<conn-string>"

# Check Cosmos DB for verification data
az cosmosdb sql container query \
  --account-name <cosmos-account> \
  --database-name content-processing \
  --container-name process \
  --query "SELECT c.process_id, c.verification_metadata FROM c WHERE IS_DEFINED(c.verification_metadata)"
```

---

## Contact and Resources

**Project Owner:** [Your Name]
**Technical Lead:** [Your Name]
**External API Provider:** [Provider Name]
**Documentation:** This file
**Source Code:** `src/ContentProcessor/src/libs/pipeline/handlers/verify_handler.py`

---

**Document Status:** Planning Phase
**Last Updated:** 2024-11-28
**Next Review:** Before implementation begins
