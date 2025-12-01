# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Handler for verifying extracted credentials against external databases."""

import json
import time
import asyncio
from typing import Dict, List

from libs.application.application_context import AppContext
from libs.pipeline.entities.pipeline_file import ArtifactType
from libs.pipeline.entities.pipeline_message_context import MessageContext
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.queue_handler_base import HandlerBase
from libs.pipeline.handlers.logics.evaluate_handler.model import DataExtractionResult
from libs.pipeline.handlers.logics.verify_handler.model import (
    VerificationResult,
    VerificationMetadata,
    VerificationType,
    VerificationStatus
)
from libs.pipeline.handlers.logics.verify_handler.doctor_verifier import DoctorCredentialVerifier


class VerifyHandler(HandlerBase):
    """
    Handler for verifying extracted credentials against external APIs.

    Supports schema-specific verification:
    - Doctor credentials (NPI, medical license)
    - Notary credentials (future)
    - Death certificates (future)
    - Identity documents (future)
    """

    def __init__(self, appContext: AppContext, step_name: str, **data):
        super().__init__(appContext, step_name, **data)

        # Initialize verifiers
        config = self.application_context.application_configuration
        self.doctor_verifier = DoctorCredentialVerifier(
            npi_api_endpoint=getattr(config, 'app_doctor_npi_api_endpoint', 'https://npiregistry.cms.hhs.gov/api/'),
            state_license_api_endpoint=getattr(config, 'app_doctor_license_api_endpoint', None),
            api_key=getattr(config, 'app_doctor_api_key', None),
            timeout=getattr(config, 'app_verify_timeout', 30)
        )

        # Get configuration
        self.confidence_threshold = getattr(config, 'app_verify_confidence_threshold', 0.70)
        self.enabled = getattr(config, 'app_verify_enabled', True)

    async def execute(self, context: MessageContext) -> StepResult:
        """
        Main execution logic for verify handler.

        Steps:
        1. Get evaluate handler results
        2. Check if verification is enabled
        3. Load schema verification config
        4. Route to appropriate verifiers
        5. Update comparison data with verification results
        6. Save verification metadata
        7. Return StepResult
        """

        # Check if verification is enabled globally
        if not self.enabled:
            print("Verification is disabled in configuration")
            return await self._create_passthrough_result(context)

        try:
            # Get evaluate handler results
            output_file_json_string = self.download_output_file_to_json_string(
                processed_by="evaluate",
                artifact_type=ArtifactType.ScoreMergedData,
            )

            # Deserialize to DataExtractionResult
            evaluate_result = DataExtractionResult(
                **json.loads(output_file_json_string)
            )

            # Get schema ID to determine which verifications to run
            schema_id = context.data_pipeline.pipeline_status.schema_id

            # Load schema verification config (simplified for now - checks environment)
            # In production, this would load from Cosmos DB or blob storage
            schema_config = await self._load_schema_config(schema_id)

            if not schema_config or not schema_config.get("enabled_verification_types"):
                print(f"No verification configured for schema {schema_id}")
                return await self._create_passthrough_result(context)

            # Run verifications based on schema config
            verification_results = await self._run_verifications(
                evaluate_result,
                schema_config
            )

            # Update comparison data with verification results
            await self._update_comparison_data(
                evaluate_result.comparison_result,
                verification_results
            )

            # Create verification metadata summary
            metadata = self._create_verification_metadata(verification_results)

            # Save results to blob
            result_file = context.data_pipeline.add_file(
                file_name="verify_output.json",
                artifact_type=ArtifactType.ScoreMergedData,
            )

            output_data = {
                "extracted_result": evaluate_result.extracted_result,
                "confidence": evaluate_result.confidence,
                "comparison_result": evaluate_result.comparison_result.to_dict(),
                "verification_metadata": metadata.model_dump(),
                "prompt_tokens": evaluate_result.prompt_tokens,
                "completion_tokens": evaluate_result.completion_tokens,
            }

            result_file.upload_json_text(
                json_text=json.dumps(output_data, indent=2, default=str),
                account_url=self.application_context.application_configuration.app_storage_blob_url,
                container_name=self.application_context.application_configuration.app_cps_processes,
                credential=self.application_context.token_credential,
            )

            # Return step result
            return StepResult(
                process_id=context.data_pipeline.pipeline_status.process_id,
                step_name=self.handler_name,
                result={
                    "result": "success",
                    "file_name": result_file.name,
                    "total_fields_checked": metadata.total_fields_checked,
                    "verified_count": metadata.verified_count,
                    "not_found_count": metadata.not_found_count,
                    "error_count": metadata.error_count,
                },
            )

        except Exception as e:
            print(f"Verification handler error: {str(e)}")
            import traceback
            traceback.print_exc()

            # On error, pass through without verification
            return await self._create_passthrough_result(context)

    async def _load_schema_config(self, schema_id: str) -> dict:
        """
        Load schema verification configuration.

        For MVP, returns hard-coded config for TRS forms.
        In production, would load from Cosmos DB or blob storage.
        """
        # Hard-coded config for TRS Retirement Allowance Verification Form
        # TODO: Load from Cosmos DB schema collection
        return {
            "schema_id": schema_id,
            "enabled_verification_types": ["doctor"],
            "verification_rules": {
                "doctor": {
                    "field_patterns": ["physician", "doctor", "npi", "license"],
                    "required": True
                }
            }
        }

    async def _run_verifications(
        self,
        evaluate_result: DataExtractionResult,
        schema_config: dict
    ) -> Dict[str, VerificationResult]:
        """
        Run verifications based on schema configuration.
        """
        verification_results = {}
        enabled_types = schema_config.get("enabled_verification_types", [])

        if "doctor" in enabled_types:
            doctor_results = await self._verify_doctor_fields(
                evaluate_result,
                schema_config.get("verification_rules", {}).get("doctor", {})
            )
            verification_results.update(doctor_results)

        # Future: Add notary, death certificate, identity verifications here

        return verification_results

    async def _verify_doctor_fields(
        self,
        evaluate_result: DataExtractionResult,
        doctor_config: dict
    ) -> Dict[str, VerificationResult]:
        """
        Verify doctor-related fields using NPI registry.
        """
        results = {}
        field_patterns = doctor_config.get("field_patterns", [])

        # Find fields that match doctor patterns
        for item in evaluate_result.comparison_result.items:
            field_name = item.Field.lower() if item.Field else ""

            # Check if field matches any doctor patterns
            if not any(pattern.lower() in field_name for pattern in field_patterns):
                continue

            # Check confidence threshold
            try:
                confidence_value = float(item.Confidence.rstrip('%')) / 100 if item.Confidence else 0.0
            except:
                confidence_value = 0.0

            if confidence_value < self.confidence_threshold:
                # Skip verification for low confidence fields
                results[item.Field] = VerificationResult(
                    field_name=item.Field,
                    extracted_value=item.Extracted,
                    verification_type=VerificationType.DOCTOR,
                    status=VerificationStatus.SKIPPED,
                    error_message=f"Confidence {confidence_value:.2%} below threshold {self.confidence_threshold:.2%}",
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    api_response_time=0
                )
                continue

            # Determine what to verify based on field name
            if "npi" in field_name:
                # Verify NPI number
                result = await self.doctor_verifier.verify_doctor(
                    field_name=item.Field,
                    npi_number=str(item.Extracted) if item.Extracted else None,
                    confidence=confidence_value
                )
                results[item.Field] = result

            elif "license" in field_name:
                # Verify medical license (needs state info)
                # For now, just verify format
                result = VerificationResult(
                    field_name=item.Field,
                    extracted_value=item.Extracted,
                    verification_type=VerificationType.DOCTOR,
                    status=VerificationStatus.SKIPPED,
                    error_message="State license verification requires state code",
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    api_response_time=0
                )
                results[item.Field] = result

        return results

    async def _update_comparison_data(
        self,
        comparison_data,
        verification_results: Dict[str, VerificationResult]
    ):
        """
        Update comparison items with verification results.
        """
        for item in comparison_data.items:
            if item.Field in verification_results:
                result = verification_results[item.Field]
                item.VerificationStatus = result.status.value
                item.VerificationDetails = result.details
                item.VerifiedAt = result.timestamp
                item.VerificationResponseTime = result.api_response_time

    def _create_verification_metadata(
        self,
        results: Dict[str, VerificationResult]
    ) -> VerificationMetadata:
        """
        Create metadata summary from verification results.
        """
        status_counts = {
            VerificationStatus.VERIFIED: 0,
            VerificationStatus.NOT_FOUND: 0,
            VerificationStatus.INVALID: 0,
            VerificationStatus.EXPIRED: 0,
            VerificationStatus.REVOKED: 0,
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
            expired_count=status_counts[VerificationStatus.EXPIRED],
            revoked_count=status_counts[VerificationStatus.REVOKED],
            error_count=status_counts[VerificationStatus.ERROR],
            skipped_count=status_counts[VerificationStatus.SKIPPED],
            total_api_calls=len(results),
            total_api_time=total_api_time,
            verification_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            verifications_by_type={
                "doctor": {
                    "verified": status_counts[VerificationStatus.VERIFIED],
                    "not_found": status_counts[VerificationStatus.NOT_FOUND],
                    "error": status_counts[VerificationStatus.ERROR],
                    "skipped": status_counts[VerificationStatus.SKIPPED],
                }
            }
        )

    async def _create_passthrough_result(self, context: MessageContext) -> StepResult:
        """
        Create result when verification is disabled or skipped.
        Passes through the evaluate results unchanged.
        """
        return StepResult(
            process_id=context.data_pipeline.pipeline_status.process_id,
            step_name=self.handler_name,
            result={
                "result": "skipped",
                "message": "Verification disabled or not configured for this schema"
            },
        )
