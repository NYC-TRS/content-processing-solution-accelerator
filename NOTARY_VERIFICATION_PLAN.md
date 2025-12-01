# NY State Notary Verification Implementation Plan

## Overview

Implement verification for New York State notary credentials using the **NY Department of State Commissioned Notaries Public** database via Socrata Open Data API.

**Dataset**: `rwbv-mz6z` - Active Commissioned Notaries Public
**API Endpoint**: `https://data.ny.gov/resource/rwbv-mz6z.json`
**Update Frequency**: Daily
**Authority**: NY State Department of State, Division of Licensing

---

## Available Notary Data

### Verifiable Fields
- **Commission Number**: Unique identifier (primary verification field)
- **Commission Holder Name**: Full name of notary
- **Commissioned County**: County where commissioned
- **Commission Type**: Traditional or Electronic
- **Term Issue Date**: When commission was issued
- **Term Expiration Date**: When commission expires (critical!)
- **Business Information**: Name, address, city, state, zip

### Verification Scenarios
1. **Valid & Active**: Commission number found, not expired
2. **Expired**: Commission number found, but past expiration date
3. **Not Found**: Commission number not in database
4. **Name Mismatch**: Commission number found, but name doesn't match

---

## Implementation Architecture

### 1. Data Model Extensions

#### Add to `VerificationType` enum (model.py):
```python
class VerificationType(str, Enum):
    DOCTOR = "doctor"
    NOTARY = "notary"  # ADD THIS
    DEATH_CERTIFICATE = "death_certificate"
    IDENTITY = "identity"
```

#### Update `VerificationMetadata` (model.py):
```python
verifications_by_type: dict = {}
"""
Example:
{
    "doctor": {"verified": 2, "not_found": 0, "error": 0},
    "notary": {"verified": 1, "expired": 1, "not_found": 0}  # ADD THIS
}
"""
```

### 2. Create Notary Verifier Service

**File**: `src/ContentProcessor/src/libs/pipeline/handlers/logics/verify_handler/notary_verifier.py`

```python
"""Notary credential verification using NY State DOS database."""

import httpx
import time
from datetime import datetime
from typing import Optional
from .model import VerificationResult, VerificationStatus, VerificationType


class NotaryCredentialVerifier:
    """Client for NY State notary verification API"""

    def __init__(
        self,
        notary_api_endpoint: str = "https://data.ny.gov/resource/rwbv-mz6z.json",
        api_token: Optional[str] = None,  # Socrata app token (optional, increases rate limit)
        timeout: int = 30
    ):
        self.notary_api_endpoint = notary_api_endpoint
        self.api_token = api_token
        self.timeout = timeout
        self.cache = {}  # In-memory cache for commission lookups

    async def verify_notary(
        self,
        field_name: str,
        notary_name: str = None,
        commission_number: str = None,
        county: str = None,
        confidence: float = None
    ) -> VerificationResult:
        """
        Verify NY State notary credentials

        Args:
            field_name: Name of the field being verified
            notary_name: Notary's full name
            commission_number: NY State commission number
            county: County where commissioned
            confidence: Extraction confidence (0.0 - 1.0)

        Returns:
            VerificationResult with status and details
        """
        start_time = time.time()

        try:
            # Try commission number verification first
            if commission_number:
                result = await self._verify_by_commission_number(
                    field_name, commission_number, notary_name, start_time
                )
                return result

            # If no commission number, try name + county lookup
            if notary_name and county:
                result = await self._verify_by_name_and_county(
                    field_name, notary_name, county, start_time
                )
                return result

            # If no identifiers, mark as not found
            return VerificationResult(
                field_name=field_name,
                extracted_value=notary_name or commission_number,
                verification_type=VerificationType.NOTARY,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return VerificationResult(
                field_name=field_name,
                extracted_value=notary_name or commission_number,
                verification_type=VerificationType.NOTARY,
                status=VerificationStatus.ERROR,
                error_message=str(e),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

    async def _verify_by_commission_number(
        self,
        field_name: str,
        commission_number: str,
        notary_name: Optional[str],
        start_time: float
    ) -> VerificationResult:
        """Verify using commission number (most reliable)"""

        # Check cache first
        if commission_number in self.cache:
            cached_result = self.cache[commission_number]
            return self._build_result_from_cached(
                field_name, commission_number, cached_result, start_time
            )

        # Build query: $where=commission_number='<number>'
        params = {
            "$where": f"commission_number='{commission_number}'",
            "$limit": 1
        }

        # Add app token if available (increases rate limit)
        if self.api_token:
            params["$$app_token"] = self.api_token

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.notary_api_endpoint,
                params=params
            )

            api_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()

                if len(data) > 0:
                    notary = data[0]

                    # Check expiration
                    expiration_date = notary.get("term_expiration_date")
                    if expiration_date:
                        exp_date = datetime.fromisoformat(expiration_date.replace("T", " ").split(".")[0])
                        if exp_date < datetime.now():
                            return VerificationResult(
                                field_name=field_name,
                                extracted_value=commission_number,
                                verification_type=VerificationType.NOTARY,
                                status=VerificationStatus.EXPIRED,
                                details={
                                    "commission_number": notary.get("commission_number"),
                                    "name": notary.get("commission_holder_name"),
                                    "county": notary.get("commissioned_county"),
                                    "expiration_date": expiration_date,
                                    "commission_type": notary.get("commission_type")
                                },
                                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                api_response_time=api_time
                            )

                    # Check name mismatch (if name provided)
                    if notary_name:
                        db_name = notary.get("commission_holder_name", "").lower()
                        if notary_name.lower() not in db_name and db_name not in notary_name.lower():
                            return VerificationResult(
                                field_name=field_name,
                                extracted_value=commission_number,
                                verification_type=VerificationType.NOTARY,
                                status=VerificationStatus.INVALID,
                                details={
                                    "reason": "Name mismatch",
                                    "extracted_name": notary_name,
                                    "database_name": notary.get("commission_holder_name"),
                                    "commission_number": commission_number
                                },
                                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                api_response_time=api_time
                            )

                    # Valid and active
                    details = {
                        "commission_number": notary.get("commission_number"),
                        "name": notary.get("commission_holder_name"),
                        "county": notary.get("commissioned_county"),
                        "commission_type": notary.get("commission_type"),
                        "issue_date": notary.get("term_issue_date"),
                        "expiration_date": notary.get("term_expiration_date"),
                        "status": "Active",
                        "cached": False
                    }

                    # Cache the result
                    self.cache[commission_number] = details

                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=commission_number,
                        verification_type=VerificationType.NOTARY,
                        status=VerificationStatus.VERIFIED,
                        details=details,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

            return VerificationResult(
                field_name=field_name,
                extracted_value=commission_number,
                verification_type=VerificationType.NOTARY,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=api_time
            )

    async def _verify_by_name_and_county(
        self,
        field_name: str,
        notary_name: str,
        county: str,
        start_time: float
    ) -> VerificationResult:
        """Verify using name and county (less reliable, may return multiple matches)"""

        params = {
            "$where": f"commission_holder_name LIKE '%{notary_name}%' AND commissioned_county='{county.upper()}'",
            "$limit": 5
        }

        if self.api_token:
            params["$$app_token"] = self.api_token

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.notary_api_endpoint,
                params=params
            )

            api_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()

                if len(data) == 1:
                    # Single match - high confidence
                    notary = data[0]
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=notary_name,
                        verification_type=VerificationType.NOTARY,
                        status=VerificationStatus.VERIFIED,
                        details={
                            "commission_number": notary.get("commission_number"),
                            "name": notary.get("commission_holder_name"),
                            "county": notary.get("commissioned_county"),
                            "match_method": "name_and_county"
                        },
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )
                elif len(data) > 1:
                    # Multiple matches - ambiguous
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=notary_name,
                        verification_type=VerificationType.NOTARY,
                        status=VerificationStatus.INVALID,
                        details={
                            "reason": "Multiple matches found",
                            "match_count": len(data),
                            "suggestion": "Use commission number for exact verification"
                        },
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

            return VerificationResult(
                field_name=field_name,
                extracted_value=notary_name,
                verification_type=VerificationType.NOTARY,
                status=VerificationStatus.NOT_FOUND,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=api_time
            )

    def _build_result_from_cached(
        self,
        field_name: str,
        commission_number: str,
        cached_data: dict,
        start_time: float
    ) -> VerificationResult:
        """Build result from cached data"""
        return VerificationResult(
            field_name=field_name,
            extracted_value=commission_number,
            verification_type=VerificationType.NOTARY,
            status=VerificationStatus.VERIFIED,
            details={**cached_data, "cached": True},
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            api_response_time=(time.time() - start_time) * 1000
        )
```

### 3. Update Configuration

**File**: `src/ContentProcessor/src/libs/application/application_configuration.py`

Add notary configuration fields:
```python
# Notary verification configuration (optional, with defaults)
app_notary_api_endpoint: str = "https://data.ny.gov/resource/rwbv-mz6z.json"
app_notary_api_token: str = ""  # Socrata app token (optional)
```

### 4. Update VerifyHandler

**File**: `src/ContentProcessor/src/libs/pipeline/handlers/verify_handler.py`

In `__init__`:
```python
# Initialize notary verifier
self.notary_verifier = NotaryCredentialVerifier(
    notary_api_endpoint=getattr(config, 'app_notary_api_endpoint', 'https://data.ny.gov/resource/rwbv-mz6z.json'),
    api_token=getattr(config, 'app_notary_api_token', None),
    timeout=getattr(config, 'app_verify_timeout', 30)
)
```

In `_run_verifications`:
```python
if "notary" in enabled_types:
    notary_results = await self._verify_notary_fields(
        evaluate_result,
        schema_config.get("verification_rules", {}).get("notary", {})
    )
    verification_results.update(notary_results)
```

Add new method:
```python
async def _verify_notary_fields(
    self,
    evaluate_result: DataExtractionResult,
    notary_config: dict
) -> Dict[str, VerificationResult]:
    """
    Verify notary-related fields using NY State DOS database.
    """
    results = {}
    field_patterns = notary_config.get("field_patterns", [])

    for item in evaluate_result.comparison_result.items:
        field_name = item.Field.lower() if item.Field else ""

        # Check if field matches any notary patterns
        if not any(pattern.lower() in field_name for pattern in field_patterns):
            continue

        # Check confidence threshold
        try:
            confidence_value = float(item.Confidence.rstrip('%')) / 100 if item.Confidence else 0.0
        except:
            confidence_value = 0.0

        if confidence_value < self.confidence_threshold:
            results[item.Field] = VerificationResult(
                field_name=item.Field,
                extracted_value=item.Extracted,
                verification_type=VerificationType.NOTARY,
                status=VerificationStatus.SKIPPED,
                error_message=f"Confidence {confidence_value:.2%} below threshold {self.confidence_threshold:.2%}",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=0
            )
            continue

        # Determine what to verify based on field name
        if "commission" in field_name and "number" in field_name:
            # Verify commission number
            result = await self.notary_verifier.verify_notary(
                field_name=item.Field,
                commission_number=str(item.Extracted) if item.Extracted else None,
                confidence=confidence_value
            )
            results[item.Field] = result

        elif "notary" in field_name and "name" in field_name:
            # Verify notary name (needs county for better accuracy)
            # Try to find county field in the same document
            county = None
            for other_item in evaluate_result.comparison_result.items:
                if "county" in other_item.Field.lower():
                    county = other_item.Extracted
                    break

            result = await self.notary_verifier.verify_notary(
                field_name=item.Field,
                notary_name=str(item.Extracted) if item.Extracted else None,
                county=county,
                confidence=confidence_value
            )
            results[item.Field] = result

    return results
```

### 5. Schema Configuration Example

For schemas that need notary verification:
```python
{
    "schema_id": "power-of-attorney",
    "enabled_verification_types": ["notary"],
    "verification_rules": {
        "notary": {
            "field_patterns": ["notary", "commission", "commissioned"],
            "required": True
        }
    }
}
```

---

## Implementation Steps

### Phase 1: Core Implementation
1. ✅ Add `NOTARY` to `VerificationType` enum
2. ✅ Create `notary_verifier.py` with `NotaryCredentialVerifier` class
3. ✅ Add notary configuration to `application_configuration.py`
4. ✅ Update `verify_handler.py` to initialize and call notary verifier
5. ✅ Add `_verify_notary_fields` method to VerifyHandler
6. ✅ Update verification metadata to include notary stats

### Phase 2: Schema Updates
1. Create schemas for notary-required documents (power of attorney, affidavits, etc.)
2. Configure verification rules for each schema
3. Test field extraction for notary fields

### Phase 3: Testing
1. Test with valid, active commission numbers
2. Test with expired commissions
3. Test with invalid/not found commissions
4. Test with name + county verification
5. Test name mismatch scenarios
6. Test API timeout/error handling

### Phase 4: Deployment
1. Deploy updated code
2. Add environment variables for notary API
3. Enable notary verification for specific schemas
4. Monitor API usage and rate limits

---

## Socrata API Considerations

### Authentication
- **No auth required** for basic usage
- **App Token recommended** for higher rate limits
  - Get token: https://data.ny.gov/profile/edit/developer_settings
  - Pass as `$$app_token` parameter
  - Increases limit from 1000/day to 100,000/day

### Query Syntax (SoQL)
- Use `$where` for filtering: `commission_number='12345678'`
- Use `LIKE` for partial matching: `commission_holder_name LIKE '%Smith%'`
- Use `$limit` to control results
- Combine conditions with `AND`, `OR`

### Rate Limits
- **Without token**: 1000 requests/day
- **With app token**: 100,000 requests/day
- Consider caching for frequently verified notaries

### Response Format
```json
[
  {
    "commission_holder_name": "JOHN DOE",
    "commission_number": "01DO1234567",
    "commissioned_county": "NEW YORK",
    "commission_type": "TRADITIONAL",
    "term_issue_date": "2022-01-15T00:00:00.000",
    "term_expiration_date": "2026-01-14T00:00:00.000",
    "business_name": "Law Office of John Doe",
    "business_address_1": "123 Main St",
    "business_city": "New York",
    "business_state": "NY",
    "business_zip": "10001"
  }
]
```

---

## Document Types Requiring Notary Verification

1. **Power of Attorney**
2. **Affidavits**
3. **Deeds**
4. **Wills**
5. **Loan Documents**
6. **Sworn Statements**
7. **Acknowledgments**

For TRS, notary verification would apply to documents like:
- Retirement applications requiring notarization
- Beneficiary designation forms
- Loan applications from pension funds

---

## Benefits for NYC TRS

1. **Fraud Prevention**: Verify notary commissions are valid and active
2. **Compliance**: Ensure documents have legitimate notarization
3. **Automation**: Reduce manual notary credential checks
4. **Audit Trail**: Complete verification history in Cosmos DB
5. **Real-time**: Daily updated data from NY State DOS

---

## Next Steps

1. Review and approve this plan
2. Decide which TRS forms require notary verification
3. Obtain Socrata app token (optional but recommended)
4. Implement Phase 1 (core notary verifier)
5. Test with real notary commission numbers
6. Deploy alongside doctor verification

---

## Estimated Effort

- **Implementation**: 4-6 hours
- **Testing**: 2-3 hours
- **Schema configuration**: 1-2 hours
- **Total**: ~1 day of development

Similar complexity to doctor verification already implemented.
