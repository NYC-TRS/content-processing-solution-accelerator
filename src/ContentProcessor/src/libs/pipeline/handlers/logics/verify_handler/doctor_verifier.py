# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Doctor credential verification using NPI Registry and state medical boards."""

import httpx
import asyncio
import time
from typing import Optional
from .model import VerificationResult, VerificationStatus, VerificationType


class DoctorCredentialVerifier:
    """Client for medical provider verification APIs"""

    def __init__(
        self,
        npi_api_endpoint: str = "https://npiregistry.cms.hhs.gov/api/",
        state_license_api_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        self.npi_api_endpoint = npi_api_endpoint
        self.state_license_api_endpoint = state_license_api_endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.cache = {}  # Simple in-memory cache for NPI lookups

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
        start_time = time.time()

        try:
            # Try NPI verification first if NPI provided
            if npi_number:
                result = await self._verify_by_npi(field_name, npi_number, start_time)
                if result.status == VerificationStatus.VERIFIED:
                    return result

            # Try state license verification if license and state provided
            if license_number and state and self.state_license_api_endpoint:
                result = await self._verify_by_state_license(
                    field_name, license_number, state, start_time
                )
                if result.status == VerificationStatus.VERIFIED:
                    return result

            # Try name + state verification if name and state provided (fallback when no NPI)
            if doctor_name and state:
                result = await self._verify_by_name_and_state(
                    field_name, doctor_name, state, start_time
                )
                return result

            # If no identifiers at all, mark as not found
            return VerificationResult(
                field_name=field_name,
                extracted_value=doctor_name or npi_number or license_number,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.NOT_FOUND,
                error_message="No verifiable identifiers provided (need NPI, or name+state, or license+state)",
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

    async def _verify_by_name_and_state(
        self,
        field_name: str,
        doctor_name: str,
        state: str,
        start_time: float
    ) -> VerificationResult:
        """Verify using physician name and state (when NPI not available)"""

        # Parse name into first and last
        name_parts = doctor_name.replace("Dr.", "").replace("Dr", "").strip().split()
        if len(name_parts) < 2:
            return VerificationResult(
                field_name=field_name,
                extracted_value=doctor_name,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.ERROR,
                error_message="Unable to parse first and last name",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

        first_name = name_parts[0]
        last_name = name_parts[-1]  # Handle middle names/initials

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.npi_api_endpoint,
                params={
                    "first_name": first_name,
                    "last_name": last_name,
                    "state": state,
                    "version": "2.1",
                    "limit": 10  # Get multiple results for matching
                },
                headers={"Accept": "application/json"}
            )

            api_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                result_count = data.get("result_count", 0)

                if result_count == 0:
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=doctor_name,
                        verification_type=VerificationType.DOCTOR,
                        status=VerificationStatus.NOT_FOUND,
                        error_message=f"No providers found with name '{doctor_name}' in state {state}",
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

                # Find exact match (prefer active providers)
                active_matches = []
                all_matches = []

                for result in data.get("results", []):
                    basic = result.get("basic", {})
                    result_first = basic.get("first_name", "").lower()
                    result_last = basic.get("last_name", "").lower()

                    # Check if names match
                    if result_first == first_name.lower() and result_last == last_name.lower():
                        if basic.get("status") == "A":
                            active_matches.append(result)
                        all_matches.append(result)

                # Prefer active matches
                matches = active_matches if active_matches else all_matches

                if len(matches) == 1:
                    # Single exact match - high confidence
                    result = matches[0]
                    basic = result.get("basic", {})

                    details = {
                        "npi": result.get("number"),
                        "name": f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip(),
                        "credential": basic.get("credential"),
                        "status": "Active" if basic.get("status") == "A" else "Inactive",
                        "state": state,
                        "verification_method": "name_and_state"
                    }

                    # Add taxonomy (specialty) if available
                    if result.get("taxonomies"):
                        details["specialty"] = result["taxonomies"][0].get("desc")

                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=doctor_name,
                        verification_type=VerificationType.DOCTOR,
                        status=VerificationStatus.VERIFIED,
                        details=details,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

                elif len(matches) > 1:
                    # Multiple exact matches - ambiguous
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=doctor_name,
                        verification_type=VerificationType.DOCTOR,
                        status=VerificationStatus.INVALID,
                        error_message=f"Multiple providers found with name '{doctor_name}' in {state}. Cannot verify without NPI or license number.",
                        details={"match_count": len(matches)},
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

                else:
                    # No exact matches, but found similar names
                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=doctor_name,
                        verification_type=VerificationType.DOCTOR,
                        status=VerificationStatus.NOT_FOUND,
                        error_message=f"Found {result_count} providers with similar names in {state}, but no exact match for '{doctor_name}'",
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        api_response_time=api_time
                    )

            return VerificationResult(
                field_name=field_name,
                extracted_value=doctor_name,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.ERROR,
                error_message=f"API error: {response.status_code}",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=api_time
            )

    async def _verify_by_npi(
        self,
        field_name: str,
        npi_number: str,
        start_time: float
    ) -> VerificationResult:
        """Verify using NPI Registry (free public API)"""

        # Check cache first
        if npi_number in self.cache:
            cached_result = self.cache[npi_number]
            return VerificationResult(
                field_name=field_name,
                extracted_value=npi_number,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.VERIFIED,
                details={**cached_result, "cached": True},
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.npi_api_endpoint,
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

                    # Check if provider is active
                    status = result.get("basic", {}).get("status", "")
                    if status != "A":
                        return VerificationResult(
                            field_name=field_name,
                            extracted_value=npi_number,
                            verification_type=VerificationType.DOCTOR,
                            status=VerificationStatus.INVALID,
                            details={"reason": "NPI status is not Active", "npi_status": status},
                            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            api_response_time=api_time
                        )

                    # Extract provider details
                    details = {
                        "npi": result.get("number"),
                        "name": f"{result.get('basic', {}).get('first_name', '')} {result.get('basic', {}).get('last_name', '')}".strip(),
                        "credential": result.get("basic", {}).get("credential"),
                        "status": "Active",
                        "cached": False
                    }

                    # Add taxonomy (specialty) if available
                    if result.get("taxonomies"):
                        details["specialty"] = result["taxonomies"][0].get("desc")

                    # Cache the result (7-day TTL recommended)
                    self.cache[npi_number] = details

                    return VerificationResult(
                        field_name=field_name,
                        extracted_value=npi_number,
                        verification_type=VerificationType.DOCTOR,
                        status=VerificationStatus.VERIFIED,
                        details=details,
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
        """Verify using state medical board API (if configured)"""

        if not self.state_license_api_endpoint or not self.api_key:
            return VerificationResult(
                field_name=field_name,
                extracted_value=license_number,
                verification_type=VerificationType.DOCTOR,
                status=VerificationStatus.SKIPPED,
                error_message="State license API not configured",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                api_response_time=(time.time() - start_time) * 1000
            )

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
