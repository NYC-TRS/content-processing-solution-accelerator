# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Unit tests for confidence calculation logic.
These tests verify that confidence values are calculated correctly and consistently.
"""

import pytest
from libs.pipeline.handlers.logics.evaluate_handler.confidence import (
    get_confidence_values,
    find_keys_with_min_confidence,
    merge_confidence_values,
)


class TestGetConfidenceValues:
    """Tests for extracting confidence values from nested data structures."""

    def test_get_confidence_values_simple_dict(self):
        """Test extracting confidence from a simple dictionary."""
        data = {
            "field1": {"confidence": 0.95, "value": "test"},
            "field2": {"confidence": 0.85, "value": "test2"},
        }
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 2
        assert 0.95 in confidence_values
        assert 0.85 in confidence_values

    def test_get_confidence_values_nested_dict(self):
        """Test extracting confidence from nested dictionaries."""
        data = {
            "field1": {"confidence": 0.95, "value": "test"},
            "nested": {
                "field2": {"confidence": 0.85, "value": "test2"},
                "deep": {"field3": {"confidence": 0.75, "value": "test3"}},
            },
        }
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 3
        assert 0.95 in confidence_values
        assert 0.85 in confidence_values
        assert 0.75 in confidence_values

    def test_get_confidence_values_with_list(self):
        """Test extracting confidence from structures containing lists."""
        data = {
            "items": [
                {"confidence": 0.95, "value": "item1"},
                {"confidence": 0.85, "value": "item2"},
            ]
        }
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 2
        assert 0.95 in confidence_values
        assert 0.85 in confidence_values

    def test_get_confidence_values_ignores_zero(self):
        """Test that zero confidence values are ignored."""
        data = {
            "field1": {"confidence": 0.95, "value": "test"},
            "field2": {"confidence": 0, "value": "test2"},
        }
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 1
        assert 0.95 in confidence_values
        assert 0 not in confidence_values

    def test_get_confidence_values_ignores_none(self):
        """Test that None confidence values are ignored."""
        data = {
            "field1": {"confidence": 0.95, "value": "test"},
            "field2": {"confidence": None, "value": "test2"},
        }
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 1
        assert 0.95 in confidence_values

    def test_get_confidence_values_empty_data(self):
        """Test handling of empty data structures."""
        assert get_confidence_values({}) == []
        assert get_confidence_values([]) == []

    def test_get_confidence_values_no_confidence_keys(self):
        """Test data without any confidence keys."""
        data = {"field1": {"value": "test"}, "field2": {"value": "test2"}}
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 0


class TestFindKeysWithMinConfidence:
    """Tests for finding keys with minimum confidence values."""

    def test_find_keys_with_min_confidence_simple(self):
        """Test finding keys with minimum confidence in simple structure."""
        data = {
            "field1": {"confidence": 0.95, "value": "test"},
            "field2": {"confidence": 0.85, "value": "test2"},
        }
        keys = find_keys_with_min_confidence(data, 0.85)
        assert "field2" in keys

    def test_find_keys_with_min_confidence_nested(self):
        """Test finding keys with minimum confidence in nested structure."""
        data = {
            "field1": {"confidence": 0.95, "value": "test"},
            "nested": {"field2": {"confidence": 0.85, "value": "test2"}},
        }
        keys = find_keys_with_min_confidence(data, 0.85)
        assert "nested.field2" in keys

    def test_find_keys_with_zero_confidence(self):
        """Test finding keys with zero confidence."""
        data = {
            "field1": {"confidence": 0.95, "value": "test"},
            "field2": {"confidence": 0, "value": "test2"},
            "field3": {"confidence": 0, "value": "test3"},
        }
        keys = find_keys_with_min_confidence(data, 0)
        assert len(keys) == 2
        assert "field2" in keys
        assert "field3" in keys

    def test_find_keys_with_min_confidence_in_list(self):
        """Test finding keys with minimum confidence in list structures."""
        data = {
            "items": [
                {"confidence": 0.95, "value": "item1"},
                {"confidence": 0.85, "value": "item2"},
            ]
        }
        keys = find_keys_with_min_confidence(data, 0.85)
        assert "items[1]" in keys


class TestMergeConfidenceValues:
    """Tests for merging confidence evaluations."""

    def test_merge_confidence_values_simple(self):
        """Test merging two simple confidence evaluations."""
        confidence_a = {
            "field1": {"confidence": 0.95, "value": "test"},
            "field2": {"confidence": 0.85, "value": "test2"},
        }
        confidence_b = {
            "field1": {"confidence": 0.90, "value": "test"},
            "field2": {"confidence": 0.80, "value": "test2"},
        }
        merged = merge_confidence_values(confidence_a, confidence_b)

        # Should use min() by default
        assert merged["field1"]["confidence"] == 0.90
        assert merged["field2"]["confidence"] == 0.80
        assert "overall_confidence" in merged
        assert "total_evaluated_fields_count" in merged
        assert merged["total_evaluated_fields_count"] == 2

    def test_merge_confidence_values_calculates_overall_confidence(self):
        """Test that overall confidence is calculated correctly."""
        confidence_a = {
            "field1": {"confidence": 0.90, "value": "test"},
            "field2": {"confidence": 0.80, "value": "test2"},
        }
        confidence_b = {
            "field1": {"confidence": 0.95, "value": "test"},
            "field2": {"confidence": 0.85, "value": "test2"},
        }
        merged = merge_confidence_values(confidence_a, confidence_b)

        # Overall confidence should be average of min values: (0.90 + 0.80) / 2 = 0.85
        assert merged["overall_confidence"] == 0.85
        assert merged["min_extracted_field_confidence"] == 0.80

    def test_merge_confidence_values_handles_zero_confidence(self):
        """Test that zero confidence fields are tracked correctly."""
        confidence_a = {
            "field1": {"confidence": 0.95, "value": "test"},
            "field2": {"confidence": 0, "value": "test2"},
        }
        confidence_b = {
            "field1": {"confidence": 0.90, "value": "test"},
            "field2": {"confidence": 0, "value": "test2"},
        }
        merged = merge_confidence_values(confidence_a, confidence_b)

        assert merged["zero_confidence_fields_count"] == 1
        assert "field2" in merged["zero_confidence_fields"]
        # Only field1 should count towards overall confidence
        assert merged["total_evaluated_fields_count"] == 1

    def test_merge_confidence_values_nested_structure(self):
        """Test merging confidence values in nested structures."""
        confidence_a = {
            "address": {
                "street": {"confidence": 0.95, "value": "123 Main St"},
                "city": {"confidence": 0.90, "value": "Springfield"},
            }
        }
        confidence_b = {
            "address": {
                "street": {"confidence": 0.92, "value": "123 Main St"},
                "city": {"confidence": 0.85, "value": "Springfield"},
            }
        }
        merged = merge_confidence_values(confidence_a, confidence_b)

        assert merged["address"]["street"]["confidence"] == 0.92
        assert merged["address"]["city"]["confidence"] == 0.85

    def test_merge_confidence_values_with_list(self):
        """Test merging confidence values in list structures."""
        confidence_a = {
            "items": [
                {"confidence": 0.95, "value": "item1"},
                {"confidence": 0.85, "value": "item2"},
            ]
        }
        confidence_b = {
            "items": [
                {"confidence": 0.90, "value": "item1"},
                {"confidence": 0.80, "value": "item2"},
            ]
        }
        merged = merge_confidence_values(confidence_a, confidence_b)

        assert merged["items"][0]["confidence"] == 0.90
        assert merged["items"][1]["confidence"] == 0.80

    def test_merge_confidence_values_empty_confidence(self):
        """Test merging when no valid confidence values exist."""
        confidence_a = {"field1": {"confidence": 0, "value": "test"}}
        confidence_b = {"field1": {"confidence": 0, "value": "test"}}
        merged = merge_confidence_values(confidence_a, confidence_b)

        assert merged["overall_confidence"] == 0.0
        assert merged["total_evaluated_fields_count"] == 0
        assert merged["zero_confidence_fields_count"] == 1

    def test_merge_confidence_values_preserves_field_values(self):
        """Test that field values are preserved during merge."""
        confidence_a = {
            "field1": {"confidence": 0.95, "value": "test_value"},
        }
        confidence_b = {
            "field1": {"confidence": 0.90, "value": "test_value"},
        }
        merged = merge_confidence_values(confidence_a, confidence_b)

        assert merged["field1"]["value"] == "test_value"

    def test_merge_confidence_ignores_one_null_confidence(self):
        """Test that merge ignores null confidence from one source."""
        confidence_a = {
            "field1": {"confidence": 0.95, "value": "test"},
        }
        confidence_b = {
            "field1": {"confidence": None, "value": "test"},
        }
        merged = merge_confidence_values(confidence_a, confidence_b)

        # Should use the non-null value
        assert merged["field1"]["confidence"] == 0.95

    def test_merge_confidence_rounds_correctly(self):
        """Test that confidence values are rounded to 3 decimal places."""
        confidence_a = {
            "field1": {"confidence": 0.123456, "value": "test"},
        }
        confidence_b = {
            "field1": {"confidence": 0.123789, "value": "test"},
        }
        merged = merge_confidence_values(confidence_a, confidence_b)

        # Should round to 3 decimal places
        assert merged["field1"]["confidence"] == 0.123


class TestConfidenceEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_confidence_with_mixed_types(self):
        """Test handling of mixed data types."""
        data = {
            "field1": {"confidence": 0.95, "value": "string"},
            "field2": {"confidence": 0.85, "value": 123},
            "field3": {"confidence": 0.75, "value": True},
            "field4": {"confidence": 0.65, "value": None},
        }
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 4

    def test_confidence_with_internal_fields(self):
        """Test that internal fields (starting with _) are handled correctly."""
        data = {
            "field1": {"confidence": 0.95, "value": "test"},
            "_internal": {"confidence": 0.85, "value": "internal"},
        }
        # The confidence module doesn't explicitly filter _ fields,
        # but we should verify it doesn't break
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 2

    def test_deeply_nested_structure(self):
        """Test handling of deeply nested structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {"level5": {"confidence": 0.95, "value": "deep"}}
                    }
                }
            }
        }
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 1
        assert 0.95 in confidence_values

    def test_large_dataset_performance(self):
        """Test confidence calculation with large datasets."""
        # Create a large dataset
        data = {
            f"field{i}": {"confidence": 0.95, "value": f"value{i}"}
            for i in range(1000)
        }
        confidence_values = get_confidence_values(data)
        assert len(confidence_values) == 1000
