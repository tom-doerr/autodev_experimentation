import pytest
from pathlib import Path
import sys
import os

# Ensure the package is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from autodev.metrics.base import MetricsCollector, MetricResult, create_error_metric
from autodev.metrics.manager import MetricsManager
from autodev.metrics.style import StyleMetricsCollector
from autodev.metrics.security import SecurityMetricsCollector
from autodev.metrics.documentation import DocumentationMetricsCollector
from autodev.metrics.coverage import CoverageMetricsCollector


def test_create_error_metric():
    """Test that error metrics are created correctly."""
    metric = create_error_metric("test_metric", "Test error")
    
    assert metric.name == "test_metric"
    assert metric.raw_value == 0
    assert metric.normalized_value == 0
    assert metric.success is False
    assert metric.error == "Test error"


def test_metrics_manager_initialization():
    """Test that the metrics manager initializes correctly."""
    manager = MetricsManager(Path.cwd())
    
    # Check that collectors are initialized
    assert len(manager.collectors) > 0
    assert "style" in manager.collectors
    assert "security" in manager.collectors
    assert "documentation" in manager.collectors
    assert "coverage" in manager.collectors
    
    # Check that the collectors are instances of the correct classes
    assert isinstance(manager.collectors["style"], StyleMetricsCollector)
    assert isinstance(manager.collectors["security"], SecurityMetricsCollector)
    assert isinstance(manager.collectors["documentation"], DocumentationMetricsCollector)
    assert isinstance(manager.collectors["coverage"], CoverageMetricsCollector)


def test_metrics_collector_collect_empty():
    """Test that metrics collector returns empty list when no data is available."""
    class TestCollector(MetricsCollector):
        def collect(self):
            return []
    
    collector = TestCollector(Path.cwd())
    metrics = collector.collect()
    
    assert isinstance(metrics, list)
    assert len(metrics) == 0


def test_metric_result_initialization():
    """Test that metric result initializes correctly."""
    metric = MetricResult(
        name="test_metric",
        raw_value=42,
        normalized_value=0.75,
        success=True,
        details={"key": "value"}
    )
    
    assert metric.name == "test_metric"
    assert metric.raw_value == 42
    assert metric.normalized_value == 0.75
    assert metric.success is True
    assert metric.details == {"key": "value"}
    assert metric.error is None


def test_metric_result_to_dict():
    """Test that metric result converts to dict correctly."""
    metric = MetricResult(
        name="test_metric",
        raw_value=42,
        normalized_value=0.75,
        success=True,
        details={"key": "value"}
    )
    
    metric_dict = metric.to_dict()
    
    assert metric_dict["name"] == "test_metric"
    assert metric_dict["raw_value"] == 42
    assert metric_dict["normalized_value"] == 0.75
    assert metric_dict["success"] is True
    assert metric_dict["details"] == {"key": "value"}
    assert metric_dict["error"] is None


def test_style_metrics_collector():
    """Test that style metrics collector returns metrics when tools are available."""
    collector = StyleMetricsCollector(Path.cwd())
    metrics = collector.collect()
    
    # We're not checking specific values since tools may or may not be installed
    # Just check that it doesn't crash and returns a list
    assert isinstance(metrics, list)
    
    # If flake8 and pylint are installed, we should get metrics
    # Otherwise, we should get an empty list for those metrics
    # But the collector should still work
    
    # Check that all metrics have the expected structure
    for metric in metrics:
        assert isinstance(metric, MetricResult)
        assert isinstance(metric.name, str)
        assert hasattr(metric, 'normalized_value')
        assert hasattr(metric, 'raw_value')
        assert hasattr(metric, 'success')


def test_security_metrics_collector():
    """Test that security metrics collector returns metrics when tools are available."""
    collector = SecurityMetricsCollector(Path.cwd())
    metrics = collector.collect()
    
    # We're not checking specific values since tools may or may not be installed
    # Just check that it doesn't crash and returns a list
    assert isinstance(metrics, list)
    
    # Check that all metrics have the expected structure
    for metric in metrics:
        assert isinstance(metric, MetricResult)
        assert isinstance(metric.name, str)
        assert hasattr(metric, 'normalized_value')
        assert hasattr(metric, 'raw_value')
        assert hasattr(metric, 'success')


def test_documentation_metrics_collector():
    """Test that documentation metrics collector returns metrics when tools are available."""
    collector = DocumentationMetricsCollector(Path.cwd())
    metrics = collector.collect()
    
    # We're not checking specific values since tools may or may not be installed
    # Just check that it doesn't crash and returns a list
    assert isinstance(metrics, list)
    
    # Check that all metrics have the expected structure
    for metric in metrics:
        assert isinstance(metric, MetricResult)
        assert isinstance(metric.name, str)
        assert hasattr(metric, 'normalized_value')
        assert hasattr(metric, 'raw_value')
        assert hasattr(metric, 'success')


def test_metrics_manager_collect_all():
    """Test that metrics manager collects all metrics without crashing."""
    manager = MetricsManager(Path.cwd())
    metrics = manager.collect_all_metrics()
    
    # Check that metrics were collected for each collector
    assert isinstance(metrics, dict)
    assert len(metrics) > 0
    
    # Check that all collectors produced metrics or empty lists without crashing
    for collector_name, collector_metrics in metrics.items():
        assert isinstance(collector_metrics, list)
