# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Tests for API confidence data retrieval.
These tests verify that the API correctly returns confidence data from the database
without overwriting it with recalculated values.
"""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.appsettings import AppConfiguration

client = TestClient(app)


@pytest.fixture
def app_config():
    """Create a test application configuration."""
    config = AppConfiguration()
    config.app_cosmos_connstr = "test_connection_string"
    config.app_cosmos_database = "test_database"
    config.app_cosmos_container_process = "test_container"
    config.app_cps_max_filesize_mb = 20
    config.app_storage_blob_url = "test_blob_url"
    return config


class TestConfidenceDataRetrieval:
    """Tests for confidence data retrieval from API endpoints."""

    @patch("app.routers.contentprocessor.get_app_config")
    @patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
    def test_get_process_returns_stored_confidence(
        self, mock_get_status, mock_get_app_config, app_config
    ):
        """Test that GET /processed/{id} returns stored confidence data."""
        mock_get_app_config.return_value = app_config

        # Mock a process with stored confidence data
        stored_confidence = {
            "overall_confidence": 0.85,
            "total_evaluated_fields_count": 10,
            "min_extracted_field_confidence": 0.75,
            "zero_confidence_fields_count": 2,
            "zero_confidence_fields": ["field1", "field2"],
        }

        mock_get_status.return_value = MagicMock(
            process_id="test_process_id",
            processed_file_name="test.pdf",
            processed_file_mime_type="application/pdf",
            processed_time="2025-03-13T12:00:00Z",
            last_modified_by="user",
            status="Completed",
            result={"field1": "value1", "field2": "value2"},
            confidence=stored_confidence,
            target_schema={
                "Id": "schema_id",
                "ClassName": "class_name",
                "Description": "description",
                "FileName": "file_name",
                "ContentType": "content_type",
            },
            comment="test comment",
        )

        response = client.get("/contentprocessor/processed/test_process_id")

        assert response.status_code == 200
        response_data = response.json()
        assert "confidence" in response_data
        # Verify the returned confidence matches stored data
        assert response_data["confidence"] == stored_confidence

    @patch("app.routers.contentprocessor.get_app_config")
    @patch(
        "app.routers.contentprocessor.CosmosContentProcess.get_all_processes_from_cosmos"
    )
    def test_get_all_processes_with_confidence_data(
        self, mock_get_all_processes, mock_get_app_config, app_config
    ):
        """Test that GET /processed returns confidence data correctly."""
        mock_get_app_config.return_value = app_config

        # Mock response with stored confidence data
        mock_get_all_processes.return_value = {
            "items": [
                {
                    "process_id": "process1",
                    "processed_file_name": "test1.pdf",
                    "status": "Completed",
                    "result": {"field1": "value1", "field2": "value2"},
                    "confidence": {
                        "totalFields": 10,
                        "zeroConfidenceCount": 2,
                        "zeroConfidenceFields": ["field1", "field2"],
                    },
                },
                {
                    "process_id": "process2",
                    "processed_file_name": "test2.pdf",
                    "status": "Completed",
                    "result": {"field1": "value1", "field2": ""},
                    "confidence": {
                        "totalFields": 5,
                        "zeroConfidenceCount": 1,
                        "zeroConfidenceFields": ["field2"],
                    },
                },
            ],
            "total_count": 2,
            "total_pages": 1,
            "current_page": 1,
            "page_size": 10,
        }

        response = client.post(
            "/contentprocessor/processed", json={"page_number": 1, "page_size": 10}
        )

        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["items"]) == 2

        # Verify confidence data is present for each item
        for item in response_data["items"]:
            assert "confidence" in item
            assert "totalFields" in item["confidence"]
            assert "zeroConfidenceCount" in item["confidence"]

    @patch("app.routers.contentprocessor.get_app_config")
    @patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
    def test_get_process_with_null_confidence(
        self, mock_get_status, mock_get_app_config, app_config
    ):
        """Test handling of processes with null confidence data."""
        mock_get_app_config.return_value = app_config

        mock_get_status.return_value = MagicMock(
            process_id="test_process_id",
            processed_file_name="test.pdf",
            processed_file_mime_type="application/pdf",
            processed_time="2025-03-13T12:00:00Z",
            last_modified_by="user",
            status="Completed",
            result={"field1": "value1"},
            confidence=None,  # No confidence data stored
            target_schema={
                "Id": "schema_id",
                "ClassName": "class_name",
            },
            comment="",
        )

        response = client.get("/contentprocessor/processed/test_process_id")

        assert response.status_code == 200
        response_data = response.json()
        # Should handle None gracefully
        assert response_data["confidence"] is None

    @patch("app.routers.contentprocessor.get_app_config")
    @patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
    def test_get_process_with_empty_confidence(
        self, mock_get_status, mock_get_app_config, app_config
    ):
        """Test handling of processes with empty confidence data."""
        mock_get_app_config.return_value = app_config

        mock_get_status.return_value = MagicMock(
            process_id="test_process_id",
            processed_file_name="test.pdf",
            processed_file_mime_type="application/pdf",
            processed_time="2025-03-13T12:00:00Z",
            last_modified_by="user",
            status="Completed",
            result={"field1": "value1"},
            confidence={},  # Empty confidence data
            target_schema={
                "Id": "schema_id",
                "ClassName": "class_name",
            },
            comment="",
        )

        response = client.get("/contentprocessor/processed/test_process_id")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["confidence"] == {}


class TestConfidenceBugRegression:
    """
    Regression tests for the (0/0) bug.
    These tests verify that stored confidence data is not overwritten by API calculations.
    """

    @patch("app.routers.contentprocessor.get_app_config")
    @patch(
        "app.routers.contentprocessor.CosmosContentProcess.get_all_processes_from_cosmos"
    )
    def test_bug_stored_confidence_not_overwritten_in_list(
        self, mock_get_all_processes, mock_get_app_config, app_config
    ):
        """
        Regression test: Verify API does not overwrite stored confidence with (0/0).

        This test reproduces the bug scenario where:
        1. Database has stored confidence: {totalFields: 10, zeroConfidenceCount: 2}
        2. API was incorrectly recalculating from result field
        3. Bug caused display of (0/0) instead of (8/10)
        """
        mock_get_app_config.return_value = app_config

        # Simulate database state with stored confidence data
        mock_get_all_processes.return_value = {
            "items": [
                {
                    "process_id": "process1",
                    "processed_file_name": "test.pdf",
                    "status": "Completed",
                    # Result field as JSON string (how it might be stored)
                    "result": json.dumps(
                        {
                            "field1": "value1",
                            "field2": "value2",
                            "field3": "value3",
                            "_internal": "skip",
                        }
                    ),
                    # Stored confidence with actual evaluation data
                    "confidence": {
                        "totalFields": 10,
                        "zeroConfidenceCount": 2,
                        "zeroConfidenceFields": ["field8", "field9"],
                    },
                }
            ],
            "total_count": 1,
            "total_pages": 1,
            "current_page": 1,
            "page_size": 10,
        }

        response = client.post(
            "/contentprocessor/processed", json={"page_number": 1, "page_size": 10}
        )

        assert response.status_code == 200
        response_data = response.json()
        item = response_data["items"][0]

        # CRITICAL: Verify stored confidence is returned, not recalculated
        assert item["confidence"]["totalFields"] == 10
        assert item["confidence"]["zeroConfidenceCount"] == 2
        # This should NOT be (0/0) - the bug we're preventing
        assert item["confidence"]["totalFields"] != 0

    @patch("app.routers.contentprocessor.get_app_config")
    @patch(
        "app.routers.contentprocessor.CosmosContentProcess.get_all_processes_from_cosmos"
    )
    def test_bug_result_field_not_used_for_confidence_calculation(
        self, mock_get_all_processes, mock_get_app_config, app_config
    ):
        """
        Regression test: Verify API does not calculate confidence from result field.

        The bug occurred because API was calculating confidence by counting fields
        in the 'result' dict, which only has 3-4 extracted fields, not the original
        10+ fields that were evaluated.
        """
        mock_get_app_config.return_value = app_config

        # Simulate the bug scenario
        mock_get_all_processes.return_value = {
            "items": [
                {
                    "process_id": "process1",
                    "processed_file_name": "invoice.pdf",
                    "status": "Completed",
                    # Result has only 3 extracted fields
                    "result": {
                        "invoiceNumber": "INV-001",
                        "amount": "1000.00",
                        "date": "2025-03-13",
                    },
                    # But confidence was calculated for 10 fields total
                    "confidence": {
                        "totalFields": 10,
                        "zeroConfidenceCount": 7,
                        "zeroConfidenceFields": [
                            "vendorName",
                            "vendorAddress",
                            "purchaseOrder",
                            "taxAmount",
                            "subtotal",
                            "dueDate",
                            "paymentTerms",
                        ],
                    },
                }
            ],
            "total_count": 1,
            "total_pages": 1,
            "current_page": 1,
            "page_size": 10,
        }

        response = client.post(
            "/contentprocessor/processed", json={"page_number": 1, "page_size": 10}
        )

        assert response.status_code == 200
        response_data = response.json()
        item = response_data["items"][0]

        # CRITICAL: totalFields should be 10 (from stored confidence),
        # NOT 3 (from counting result fields)
        assert item["confidence"]["totalFields"] == 10
        assert item["confidence"]["zeroConfidenceCount"] == 7

        # This verifies we're not recalculating from result
        # (result has 3 fields, confidence has 10 fields)
        assert item["confidence"]["totalFields"] != len(item.get("result", {}))

    @patch("app.routers.contentprocessor.get_app_config")
    @patch(
        "app.routers.contentprocessor.CosmosContentProcess.get_all_processes_from_cosmos"
    )
    def test_bug_mixed_new_and_existing_items(
        self, mock_get_all_processes, mock_get_app_config, app_config
    ):
        """
        Regression test: Verify both new and existing items show correct confidence.

        Tests the scenario where some items have stored confidence data
        and others might have been recently processed.
        """
        mock_get_app_config.return_value = app_config

        mock_get_all_processes.return_value = {
            "items": [
                # Existing item with stored confidence
                {
                    "process_id": "old_process",
                    "processed_file_name": "old.pdf",
                    "status": "Completed",
                    "result": {"field1": "value1", "field2": "value2"},
                    "confidence": {
                        "totalFields": 15,
                        "zeroConfidenceCount": 3,
                        "zeroConfidenceFields": ["field13", "field14", "field15"],
                    },
                },
                # New item with stored confidence
                {
                    "process_id": "new_process",
                    "processed_file_name": "new.pdf",
                    "status": "Completed",
                    "result": {"field1": "value1"},
                    "confidence": {
                        "totalFields": 8,
                        "zeroConfidenceCount": 1,
                        "zeroConfidenceFields": ["field8"],
                    },
                },
            ],
            "total_count": 2,
            "total_pages": 1,
            "current_page": 1,
            "page_size": 10,
        }

        response = client.post(
            "/contentprocessor/processed", json={"page_number": 1, "page_size": 10}
        )

        assert response.status_code == 200
        response_data = response.json()

        # Verify both items maintain their stored confidence
        old_item = next(
            item for item in response_data["items"] if item["process_id"] == "old_process"
        )
        assert old_item["confidence"]["totalFields"] == 15
        assert old_item["confidence"]["zeroConfidenceCount"] == 3

        new_item = next(
            item for item in response_data["items"] if item["process_id"] == "new_process"
        )
        assert new_item["confidence"]["totalFields"] == 8
        assert new_item["confidence"]["zeroConfidenceCount"] == 1


class TestConfidenceDataStructure:
    """Tests for confidence data structure and format."""

    @patch("app.routers.contentprocessor.get_app_config")
    @patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
    def test_confidence_structure_matches_frontend_expectations(
        self, mock_get_status, mock_get_app_config, app_config
    ):
        """Test that confidence data structure matches what frontend expects."""
        mock_get_app_config.return_value = app_config

        # Frontend expects camelCase keys in confidence object
        expected_confidence_structure = {
            "overall_confidence": 0.85,
            "total_evaluated_fields_count": 10,
            "min_extracted_field_confidence": 0.75,
            "zero_confidence_fields_count": 2,
            "zero_confidence_fields": ["field1", "field2"],
            "min_extracted_field_confidence_field": ["field1"],
        }

        mock_get_status.return_value = MagicMock(
            process_id="test_process_id",
            processed_file_name="test.pdf",
            processed_file_mime_type="application/pdf",
            processed_time="2025-03-13T12:00:00Z",
            last_modified_by="user",
            status="Completed",
            result={"field1": "value1"},
            confidence=expected_confidence_structure,
            target_schema={"Id": "schema_id", "ClassName": "class_name"},
            comment="",
        )

        response = client.get("/contentprocessor/processed/test_process_id")

        assert response.status_code == 200
        response_data = response.json()

        # Verify all expected keys are present
        confidence = response_data["confidence"]
        assert "overall_confidence" in confidence
        assert "total_evaluated_fields_count" in confidence
        assert "min_extracted_field_confidence" in confidence
        assert "zero_confidence_fields_count" in confidence
        assert "zero_confidence_fields" in confidence

    @patch("app.routers.contentprocessor.get_app_config")
    @patch(
        "app.routers.contentprocessor.CosmosContentProcess.get_all_processes_from_cosmos"
    )
    def test_list_endpoint_confidence_format(
        self, mock_get_all_processes, mock_get_app_config, app_config
    ):
        """Test confidence format in list endpoint matches expectations."""
        mock_get_app_config.return_value = app_config

        mock_get_all_processes.return_value = {
            "items": [
                {
                    "process_id": "process1",
                    "processed_file_name": "test.pdf",
                    "status": "Completed",
                    "confidence": {
                        "totalFields": 10,
                        "zeroConfidenceCount": 2,
                        "zeroConfidenceFields": ["field1", "field2"],
                    },
                }
            ],
            "total_count": 1,
            "total_pages": 1,
            "current_page": 1,
            "page_size": 10,
        }

        response = client.post(
            "/contentprocessor/processed", json={"page_number": 1, "page_size": 10}
        )

        assert response.status_code == 200
        response_data = response.json()
        item = response_data["items"][0]

        # Verify camelCase format for list endpoint
        assert "totalFields" in item["confidence"]
        assert "zeroConfidenceCount" in item["confidence"]
        assert "zeroConfidenceFields" in item["confidence"]
        assert isinstance(item["confidence"]["zeroConfidenceFields"], list)
