"""
Tests for the metrics manager.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from autodev.metrics.manager import MetricsManager
from autodev.metrics.base import MetricResult


@pytest.fixture
def mock_project_path():
    """Provide a mock project path."""
    return str(Path(__file__).parent.parent.parent)


@pytest.fixture
def metrics_manager(mock_project_path):
    """Provide a metrics manager instance."""
    return MetricsManager(mock_project_path)


@pytest.fixture
def mock_metric_results():
    """Provide mock metric results."""
    return [
        MetricResult(
            name="test_metric_1",
            raw_value=75,
            normalized_value=0.75,
            details={"some_detail": "value1"}
        ),
        MetricResult(
            name="test_metric_2",
            raw_value=85,
            normalized_value=0.85,
            details={"some_detail": "value2"}
        ),
        MetricResult(
            name="test_metric_3",
            raw_value=98,
            normalized_value=0.98,
            details={"some_detail": "value3"}
        )
    ]


def test_metrics_manager_init(metrics_manager):
    """Test metrics manager initialization."""
    assert metrics_manager.threshold == 0.95
    assert len(metrics_manager.collectors) == 5
    assert "complexity" in metrics_manager.collectors
    assert "style" in metrics_manager.collectors
    assert "documentation" in metrics_manager.collectors
    assert "coverage" in metrics_manager.collectors
    assert "security" in metrics_manager.collectors


@patch("autodev.metrics.complexity.ComplexityMetricsCollector.collect")
@patch("autodev.metrics.style.StyleMetricsCollector.collect")
def test_collect_specific_metrics(mock_style, mock_complexity, metrics_manager, mock_metric_results):
    """Test collecting metrics from specific collectors."""
    mock_complexity.return_value = mock_metric_results[:2]
    mock_style.return_value = mock_metric_results[2:]
    
    # Collect only complexity metrics
    metrics = metrics_manager.collect_specific_metrics(["complexity"])
    
    assert "complexity" in metrics
    assert len(metrics["complexity"]) == 2
    assert metrics["complexity"][0].name == "test_metric_1"
    assert metrics["complexity"][1].name == "test_metric_2"
    
    # Complexity should have been cached
    assert "complexity" in metrics_manager.metrics_cache
    assert len(metrics_manager.metrics_cache["complexity"]) == 2
    
    # Style should not have been called or cached
    mock_style.assert_not_called()
    assert "style" not in metrics_manager.metrics_cache
    
    # Now collect style metrics
    metrics = metrics_manager.collect_specific_metrics(["style"])
    
    assert "style" in metrics
    assert len(metrics["style"]) == 1
    assert metrics["style"][0].name == "test_metric_3"
    
    # Style should now be cached
    assert "style" in metrics_manager.metrics_cache
    assert len(metrics_manager.metrics_cache["style"]) == 1
    
    # Both should be cached now
    assert len(metrics_manager.metrics_cache) == 2


@patch("autodev.metrics.complexity.ComplexityMetricsCollector.collect")
@patch("autodev.metrics.style.StyleMetricsCollector.collect")
def test_aggregate_metrics(mock_style, mock_complexity, metrics_manager, mock_metric_results):
    """Test aggregating metrics."""
    mock_complexity.return_value = [
        MetricResult(name="metric1", raw_value=80, normalized_value=0.8),
        MetricResult(name="metric2", raw_value=90, normalized_value=0.9)
    ]
    mock_style.return_value = [
        MetricResult(name="metric3", raw_value=100, normalized_value=1.0)
    ]
    
    # Collect metrics
    metrics_manager.collect_specific_metrics(["complexity", "style"])
    
    # Aggregate all
    aggregated = metrics_manager.aggregate_metrics()
    
    assert aggregated["overall_score"] == pytest.approx(0.9)  # Average of 0.8, 0.9, 1.0
    assert aggregated["metrics_count"] == 3
    assert aggregated["metrics_above_threshold"] == 1  # Only metric3 is above 0.95
    assert aggregated["metrics_below_threshold"] == 2
    assert len(aggregated["improvement_areas"]) == 2
    assert aggregated["improvement_areas"][0]["name"] == "metric1"  # metric1 is furthest from threshold
    
    # Check metrics by collector
    assert "complexity" in aggregated["metrics_by_collector"]
    assert "style" in aggregated["metrics_by_collector"]
    assert len(aggregated["metrics_by_collector"]["complexity"]) == 2
    assert len(aggregated["metrics_by_collector"]["style"]) == 1


def test_get_improvement_recommendations(metrics_manager):
    """Test getting improvement recommendations."""
    # Set up mock aggregated metrics
    metrics_manager.aggregated_metrics = {
        "improvement_areas": [
            {
                "name": "cyclomatic_complexity",
                "current_value": 0.7,
                "distance_to_threshold": 0.25,
                "improvement_weight": 0.0625,
                "details": {
                    "complex_functions": [
                        {"function": "func1", "file": "file1.py", "complexity": 15}
                    ]
                }
            },
            {
                "name": "docstring_coverage",
                "current_value": 0.8,
                "distance_to_threshold": 0.15,
                "improvement_weight": 0.0225,
                "details": {}
            }
        ]
    }
    
    recommendations = metrics_manager.get_improvement_recommendations()
    
    assert len(recommendations) == 2
    assert "advice" in recommendations[0]
    assert "func1" in recommendations[0]["advice"]
    assert "advice" in recommendations[1]
    assert "docstring" in recommendations[1]["advice"].lower()


def test_export_metrics(metrics_manager, tmp_path):
    """Test exporting metrics to a file."""
    # Set up mock data
    metrics_manager.metrics_cache = {
        "complexity": [
            MetricResult(name="metric1", raw_value=80, normalized_value=0.8)
        ]
    }
    metrics_manager.aggregated_metrics = {
        "overall_score": 0.8,
        "metrics_count": 1
    }
    
    # Export to temporary file
    output_path = str(tmp_path / "test_metrics.json")
    result_path = metrics_manager.export_metrics(output_path)
    
    assert result_path == output_path
    assert os.path.exists(output_path)
    
    # Clean up
    os.remove(output_path)
