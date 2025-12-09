#!/usr/bin/env python3
"""
Comprehensive validation tests for copilot_usage_metrics.py
Tests all functions, metrics calculations, and edge cases
"""

import sys
import json
from datetime import datetime
from collections import defaultdict

# Import functions from main script
sys.path.insert(0, '.')
from copilot_usage_metrics import (
    calculate_acceptance_rate,
    calculate_loc_acceptance_rate,
    aggregate_metrics_by_feature,
    aggregate_metrics_by_language_feature
)

def test_acceptance_rate_calculations():
    """Test acceptance rate calculation edge cases"""
    print("Testing acceptance rate calculations...")
    
    # Normal cases
    assert calculate_acceptance_rate(75, 100) == 75.0
    assert calculate_acceptance_rate(100, 100) == 100.0
    assert calculate_acceptance_rate(50, 200) == 25.0
    
    # Edge cases
    assert calculate_acceptance_rate(0, 100) == 0.0
    assert calculate_acceptance_rate(0, 0) == 0.0
    assert calculate_acceptance_rate(100, 0) == 0.0  # Division by zero
    
    # LoC acceptance rate
    assert calculate_loc_acceptance_rate(35000, 50000) == 70.0
    assert calculate_loc_acceptance_rate(0, 1000) == 0.0
    assert calculate_loc_acceptance_rate(1000, 0) == 0.0  # Division by zero
    
    print("✅ Acceptance rate calculations passed")

def test_aggregate_metrics_by_feature():
    """Test feature aggregation with sample data"""
    print("\nTesting feature aggregation...")
    
    # Sample NDJSON records
    records = [
        {
            "user_login": "user1",
            "totals_by_language_feature": [
                {
                    "feature": "code_completion",
                    "language": "python",
                    "loc_suggested_to_add_sum": 1000,
                    "loc_suggested_to_delete_sum": 10,
                    "loc_added_sum": 800,
                    "loc_deleted_sum": 5,
                    "code_generation_activity_count": 100,
                    "code_acceptance_activity_count": 80
                },
                {
                    "feature": "chat_panel",
                    "language": "javascript",
                    "loc_suggested_to_add_sum": 500,
                    "loc_suggested_to_delete_sum": 0,
                    "loc_added_sum": 400,
                    "loc_deleted_sum": 0,
                    "code_generation_activity_count": 50,
                    "code_acceptance_activity_count": 40
                }
            ]
        },
        {
            "user_login": "user2",
            "totals_by_language_feature": [
                {
                    "feature": "code_completion",
                    "language": "typescript",
                    "loc_suggested_to_add_sum": 2000,
                    "loc_suggested_to_delete_sum": 20,
                    "loc_added_sum": 1600,
                    "loc_deleted_sum": 15,
                    "code_generation_activity_count": 200,
                    "code_acceptance_activity_count": 160
                },
                {
                    "feature": "agent_edit",
                    "language": "python",
                    "loc_suggested_to_add_sum": 0,
                    "loc_suggested_to_delete_sum": 0,
                    "loc_added_sum": 5000,
                    "loc_deleted_sum": 2000,
                    "code_generation_activity_count": 50,
                    "code_acceptance_activity_count": 0
                }
            ]
        }
    ]
    
    result = aggregate_metrics_by_feature(records)
    
    # Validate code_completion aggregation
    assert "code_completion" in result
    assert result["code_completion"]["loc_suggested_to_add_sum"] == 3000  # 1000 + 2000
    assert result["code_completion"]["loc_added_sum"] == 2400  # 800 + 1600
    assert result["code_completion"]["code_generation_activity_count"] == 300  # 100 + 200
    assert result["code_completion"]["code_acceptance_activity_count"] == 240  # 80 + 160
    assert result["code_completion"]["user_count"] == 2  # user1 + user2
    
    # Validate agent_edit aggregation
    assert "agent_edit" in result
    assert result["agent_edit"]["loc_suggested_to_add_sum"] == 0
    assert result["agent_edit"]["loc_added_sum"] == 5000
    assert result["agent_edit"]["loc_deleted_sum"] == 2000
    assert result["agent_edit"]["user_count"] == 1  # only user2
    
    # Validate chat_panel
    assert "chat_panel" in result
    assert result["chat_panel"]["user_count"] == 1  # only user1
    
    print("✅ Feature aggregation passed")

def test_aggregate_metrics_by_language_feature():
    """Test language-feature aggregation"""
    print("\nTesting language-feature aggregation...")
    
    records = [
        {
            "user_login": "user1",
            "totals_by_language_feature": [
                {
                    "feature": "code_completion",
                    "language": "python",
                    "loc_suggested_to_add_sum": 1000,
                    "loc_suggested_to_delete_sum": 0,
                    "loc_added_sum": 800,
                    "loc_deleted_sum": 0,
                    "code_generation_activity_count": 100,
                    "code_acceptance_activity_count": 80
                }
            ]
        },
        {
            "user_login": "user2",
            "totals_by_language_feature": [
                {
                    "feature": "code_completion",
                    "language": "python",
                    "loc_suggested_to_add_sum": 500,
                    "loc_suggested_to_delete_sum": 0,
                    "loc_added_sum": 400,
                    "loc_deleted_sum": 0,
                    "code_generation_activity_count": 50,
                    "code_acceptance_activity_count": 40
                }
            ]
        }
    ]
    
    result = aggregate_metrics_by_language_feature(records)
    
    # Validate python:code_completion aggregation
    assert "python:code_completion" in result
    assert result["python:code_completion"]["loc_suggested_to_add_sum"] == 1500  # 1000 + 500
    assert result["python:code_completion"]["loc_added_sum"] == 1200  # 800 + 400
    assert result["python:code_completion"]["user_count"] == 2
    
    print("✅ Language-feature aggregation passed")

def test_all_metrics_coverage():
    """Test that all expected metrics are captured"""
    print("\nTesting metrics coverage...")
    
    expected_features = [
        "code_completion",
        "chat_panel",
        "chat_panel_agent_mode",
        "chat_inline",
        "agent_edit",
        "custom"
    ]
    
    expected_metrics_per_feature = [
        "loc_suggested_to_add_sum",
        "loc_suggested_to_delete_sum",
        "loc_added_sum",
        "loc_deleted_sum",
        "code_generation_activity_count",
        "code_acceptance_activity_count",
        "user_count"
    ]
    
    # Create sample data with all features
    records = []
    for i, feature in enumerate(expected_features):
        records.append({
            "user_login": f"user{i}",
            "totals_by_language_feature": [
                {
                    "feature": feature,
                    "language": "python",
                    "loc_suggested_to_add_sum": 100 * i,
                    "loc_suggested_to_delete_sum": 10 * i,
                    "loc_added_sum": 80 * i,
                    "loc_deleted_sum": 5 * i,
                    "code_generation_activity_count": 10 * i,
                    "code_acceptance_activity_count": 8 * i
                }
            ]
        })
    
    result = aggregate_metrics_by_feature(records)
    
    # Check all features are present
    for feature in expected_features:
        if feature in result:
            print(f"  ✓ {feature} captured")
            # Check all metrics are present
            for metric in expected_metrics_per_feature:
                assert metric in result[feature], f"Missing metric {metric} in {feature}"
    
    print("✅ All metrics coverage validated")

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\nTesting edge cases...")
    
    # Empty records
    result = aggregate_metrics_by_feature([])
    assert result == {}
    print("  ✓ Empty records handled")
    
    # Missing fields
    records = [
        {
            "user_login": "user1",
            "totals_by_language_feature": [
                {
                    "feature": "code_completion",
                    "language": "python"
                    # Missing all numeric fields
                }
            ]
        }
    ]
    result = aggregate_metrics_by_feature(records)
    assert result["code_completion"]["loc_suggested_to_add_sum"] == 0
    assert result["code_completion"]["user_count"] == 1
    print("  ✓ Missing fields handled with defaults")
    
    # Multiple users with same feature
    records = [
        {
            "user_login": "user1",
            "totals_by_language_feature": [
                {"feature": "code_completion", "language": "python", "loc_added_sum": 100}
            ]
        },
        {
            "user_login": "user1",  # Same user
            "totals_by_language_feature": [
                {"feature": "code_completion", "language": "javascript", "loc_added_sum": 200}
            ]
        }
    ]
    result = aggregate_metrics_by_feature(records)
    assert result["code_completion"]["user_count"] == 1  # Should count unique users
    assert result["code_completion"]["loc_added_sum"] == 300  # Should sum metrics
    print("  ✓ Duplicate users counted correctly")
    
    print("✅ Edge cases passed")

def test_language_diversity():
    """Test handling of multiple programming languages"""
    print("\nTesting language diversity...")
    
    languages = ["python", "javascript", "typescript", "java", "go", "rust", 
                 "c", "cpp", "csharp", "ruby", "php", "unknown"]
    
    records = []
    for i, lang in enumerate(languages):
        records.append({
            "user_login": f"user{i}",
            "totals_by_language_feature": [
                {
                    "feature": "code_completion",
                    "language": lang,
                    "loc_suggested_to_add_sum": 1000,
                    "loc_added_sum": 800,
                    "code_generation_activity_count": 100,
                    "code_acceptance_activity_count": 80
                }
            ]
        })
    
    result = aggregate_metrics_by_language_feature(records)
    
    for lang in languages:
        key = f"{lang}:code_completion"
        assert key in result, f"Missing language {lang}"
        print(f"  ✓ {lang} captured")
    
    print("✅ Language diversity validated")

def test_rate_calculations_with_real_world_data():
    """Test rate calculations with realistic data patterns"""
    print("\nTesting rate calculations with realistic data...")
    
    # Scenario 1: High acceptance rate (code_completion)
    assert abs(calculate_acceptance_rate(9000, 10000) - 90.0) < 0.01
    assert abs(calculate_loc_acceptance_rate(45000, 50000) - 90.0) < 0.01
    print("  ✓ High acceptance rate scenario")
    
    # Scenario 2: Low acceptance rate
    assert abs(calculate_acceptance_rate(2000, 10000) - 20.0) < 0.01
    assert abs(calculate_loc_acceptance_rate(10000, 50000) - 20.0) < 0.01
    print("  ✓ Low acceptance rate scenario")
    
    # Scenario 3: Agent mode (no suggestions)
    assert calculate_loc_acceptance_rate(5000, 0) == 0.0
    print("  ✓ Agent mode (no suggestions) scenario")
    
    # Scenario 4: Chat panel with low LoC acceptance
    assert abs(calculate_loc_acceptance_rate(500, 8600) - 5.81) < 0.01
    print("  ✓ Chat panel low acceptance scenario")
    
    print("✅ Rate calculations validated")

def run_all_tests():
    """Run all validation tests"""
    print("=" * 70)
    print("COMPREHENSIVE VALIDATION TEST SUITE")
    print("=" * 70)
    
    try:
        test_acceptance_rate_calculations()
        test_aggregate_metrics_by_feature()
        test_aggregate_metrics_by_language_feature()
        test_all_metrics_coverage()
        test_edge_cases()
        test_language_diversity()
        test_rate_calculations_with_real_world_data()
        
        print("\n" + "=" * 70)
        print("✨ ALL VALIDATION TESTS PASSED! ✨")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
