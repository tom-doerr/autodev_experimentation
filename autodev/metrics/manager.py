"""
Metrics manager for aggregating and prioritizing code quality metrics.
"""
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Type
import json

from autodev.metrics.base import MetricsCollector, MetricResult
from autodev.metrics.complexity import ComplexityMetricsCollector
from autodev.metrics.style import StyleMetricsCollector
from autodev.metrics.documentation import DocumentationMetricsCollector
from autodev.metrics.coverage import CoverageMetricsCollector
from autodev.metrics.security import SecurityMetricsCollector
from autodev.metrics.normalizer import aggregate_metrics, apply_threshold


logger = logging.getLogger(__name__)


class MetricsManager:
    """Manager for collecting, aggregating, and prioritizing code quality metrics."""
    
    def __init__(self, project_path: str, threshold: float = 0.95):
        """
        Initialize the metrics manager.
        
        Args:
            project_path: Path to the project root
            threshold: Target threshold for all metrics (0-1)
        """
        self.project_path = Path(project_path).resolve()
        self.threshold = threshold
        self.collectors = self._initialize_collectors()
        self.metrics_cache = {}
        self.aggregated_metrics = None
    
    def _initialize_collectors(self) -> Dict[str, MetricsCollector]:
        """
        Initialize metrics collectors.
        
        Returns:
            Dictionary of collector name to collector instance
        """
        collectors = {
            "complexity": ComplexityMetricsCollector(self.project_path),
            "style": StyleMetricsCollector(self.project_path),
            "documentation": DocumentationMetricsCollector(self.project_path),
            "coverage": CoverageMetricsCollector(self.project_path),
            "security": SecurityMetricsCollector(self.project_path)
        }
        
        return collectors
    
    def collect_all_metrics(self) -> Dict[str, List[MetricResult]]:
        """
        Collect all metrics from all collectors.
        
        Returns:
            Dictionary of collector name to list of metric results
        """
        all_metrics = {}
        
        for name, collector in self.collectors.items():
            logger.info(f"Collecting metrics from {name}...")
            try:
                metrics = collector.collect()
                all_metrics[name] = metrics
                logger.info(f"Collected {len(metrics)} metrics from {name}")
            except Exception as e:
                logger.error(f"Error collecting metrics from {name}: {str(e)}")
                all_metrics[name] = []
        
        self.metrics_cache = all_metrics
        return all_metrics
    
    def collect_specific_metrics(self, collectors: List[str]) -> Dict[str, List[MetricResult]]:
        """
        Collect metrics from specific collectors.
        
        Args:
            collectors: List of collector names to use
        
        Returns:
            Dictionary of collector name to list of metric results
        """
        specific_metrics = {}
        
        for name in collectors:
            if name not in self.collectors:
                logger.warning(f"Collector {name} not found")
                continue
            
            logger.info(f"Collecting metrics from {name}...")
            try:
                metrics = self.collectors[name].collect()
                specific_metrics[name] = metrics
                logger.info(f"Collected {len(metrics)} metrics from {name}")
            except Exception as e:
                logger.error(f"Error collecting metrics from {name}: {str(e)}")
                specific_metrics[name] = []
        
        # Update cache with new metrics
        for name, metrics in specific_metrics.items():
            self.metrics_cache[name] = metrics
        
        return specific_metrics
    
    def aggregate_metrics(self, 
                        include_collectors: Optional[List[str]] = None,
                        custom_weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Aggregate all collected metrics.
        
        Args:
            include_collectors: Optional list of collector names to include
            custom_weights: Optional custom weights for specific metrics
        
        Returns:
            Dictionary with aggregated metrics and improvement areas
        """
        all_metrics = []
        
        # Use specified collectors or all collectors
        collectors_to_use = include_collectors or list(self.collectors.keys())
        
        # Flatten metrics from all collectors
        for name in collectors_to_use:
            if name not in self.metrics_cache:
                continue
            
            for metric in self.metrics_cache[name]:
                all_metrics.append({
                    "name": metric.name,
                    "normalized_value": metric.normalized_value,
                    "raw_value": metric.raw_value,
                    "collector": name,
                    "details": metric.details
                })
        
        # Aggregate metrics
        aggregated = aggregate_metrics(all_metrics, self.threshold, custom_weights)
        self.aggregated_metrics = aggregated
        
        # Add additional context
        aggregated["threshold"] = self.threshold
        aggregated["collectors_used"] = collectors_to_use
        
        # Group metrics by collector
        metrics_by_collector = {}
        for name in collectors_to_use:
            if name not in self.metrics_cache:
                continue
            
            collector_metrics = []
            for metric in self.metrics_cache[name]:
                meets_threshold, distance = apply_threshold(metric.normalized_value, self.threshold)
                collector_metrics.append({
                    "name": metric.name,
                    "normalized_value": metric.normalized_value,
                    "raw_value": metric.raw_value,
                    "meets_threshold": meets_threshold,
                    "distance_to_threshold": distance
                })
            
            metrics_by_collector[name] = collector_metrics
        
        aggregated["metrics_by_collector"] = metrics_by_collector
        
        return aggregated
    
    def get_improvement_recommendations(self, max_recommendations: int = 5) -> List[Dict[str, Any]]:
        """
        Get prioritized improvement recommendations based on aggregated metrics.
        
        Args:
            max_recommendations: Maximum number of recommendations to return
        
        Returns:
            List of improvement recommendations
        """
        if not self.aggregated_metrics:
            logger.warning("No aggregated metrics available. Run aggregate_metrics() first.")
            return []
        
        # Get improvement areas from aggregated metrics
        improvement_areas = self.aggregated_metrics.get("improvement_areas", [])
        
        # Limit to max_recommendations
        recommendations = improvement_areas[:max_recommendations]
        
        # Add actionable advice for each recommendation
        for recommendation in recommendations:
            recommendation["advice"] = self._generate_advice(recommendation)
        
        return recommendations
    
    def _generate_advice(self, recommendation: Dict[str, Any]) -> str:
        """
        Generate actionable advice for an improvement recommendation.
        
        Args:
            recommendation: Improvement recommendation dictionary
        
        Returns:
            String containing actionable advice
        """
        metric_name = recommendation.get("name", "")
        details = recommendation.get("details", {})
        
        # Use a mapping of metric types to advice generators to reduce complexity
        advice_generators = {
            "cyclomatic_complexity": self._get_complexity_advice,
            "maintainability_index": self._get_maintainability_advice,
            "comment_density": self._get_comment_advice,
            "pylint_score": self._get_linting_advice,
            "flake8_violations": self._get_linting_advice,
            "black_compliance": self._get_formatting_advice,
            "docstring": self._get_documentation_advice,
            "coverage": self._get_coverage_advice,
            "test_count": self._get_testing_advice,
            "test_density": self._get_testing_advice,
            "security_score": self._get_security_advice,
            "critical_security_issues": self._get_security_advice,
            "dependency_vulnerabilities": self._get_dependency_advice
        }
        
        # Find the right advice generator based on partial matches
        for pattern, generator in advice_generators.items():
            if pattern in metric_name:
                return generator(metric_name, details)
        
        # Default advice for unknown metrics
        return "Identify specific areas for improvement and address them systematically."
    
    def _get_complexity_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for complexity metrics."""
        complex_functions = details.get("complex_functions", [])
        if complex_functions:
            function_list = ", ".join([f"{func['function']} in {func['file']} (complexity: {func['complexity']})" 
                                  for func in complex_functions[:3]])
            return f"Refactor complex functions to reduce cyclomatic complexity. Top candidates: {function_list}"
        return "Refactor functions to reduce cyclomatic complexity. Split large functions into smaller ones."
    
    def _get_maintainability_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for maintainability metrics."""
        poor_files = details.get("files_by_category", {}).get("poor", 0)
        return f"Improve maintainability by simplifying code structure, adding comments, and reducing complexity."
    
    def _get_comment_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for comment metrics."""
        return "Add more comments to your code, focusing on explaining the 'why' rather than the 'what'."
    
    def _get_linting_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for linting metrics."""
        return "Fix style issues reported by linters. Run 'pylint' or 'flake8' for specific recommendations."
    
    def _get_formatting_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for code formatting metrics."""
        return "Format your code with Black to ensure consistent styling."
    
    def _get_documentation_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for documentation metrics."""
        return "Add or improve docstrings, focusing on classes, methods, and functions. Follow a consistent style."
    
    def _get_coverage_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for coverage metrics."""
        low_coverage_files = details.get("low_coverage_files", [])
        if low_coverage_files:
            file_list = ", ".join([f"{f['file']} ({f['coverage']:.1f}%)" for f in low_coverage_files[:3]])
            return f"Increase test coverage by writing tests for uncovered code. Focus on these files: {file_list}"
        return "Increase test coverage by writing more tests, especially for untested functionality."
    
    def _get_testing_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for test metrics."""
        return "Add more tests, aiming for at least one test per non-test file."
    
    def _get_security_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for security metrics."""
        critical_issues = details.get("critical_issues", [])
        if critical_issues:
            issue_list = ", ".join([f"{issue['test_name']} in {issue['file']}:{issue['line']}" 
                               for issue in critical_issues[:3]])
            return f"Fix security issues identified by Bandit. Critical issues: {issue_list}"
        return "Address security vulnerabilities identified by static analysis tools."
    
    def _get_dependency_advice(self, metric_name: str, details: Dict[str, Any]) -> str:
        """Generate advice for dependency metrics."""
        vulnerabilities = details.get("vulnerabilities", [])
        if vulnerabilities:
            vuln_list = ", ".join([f"{v['dependency']} {v['installed_version']}" for v in vulnerabilities[:3]])
            return f"Update dependencies with security vulnerabilities: {vuln_list}"
        return "Update dependencies with known security vulnerabilities."
    
    def export_metrics(self, output_path: Optional[str] = None) -> str:
        """
        Export metrics to a JSON file.
        
        Args:
            output_path: Optional path to write JSON file to
        
        Returns:
            Path to the output file
        """
        if not self.metrics_cache:
            logger.warning("No metrics to export. Run collect_all_metrics() first.")
            return ""
        
        # Convert metrics to serializable format
        serializable_metrics = {}
        for collector, metrics in self.metrics_cache.items():
            serializable_metrics[collector] = [metric.to_dict() for metric in metrics]
        
        # Add aggregated metrics if available
        export_data = {
            "metrics": serializable_metrics
        }
        
        if self.aggregated_metrics:
            export_data["aggregated"] = self.aggregated_metrics
        
        # Determine output path
        if not output_path:
            output_path = str(self.project_path / "metrics_report.json")
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported metrics to {output_path}")
        return output_path
    
    def print_summary(self) -> None:
        """Print a summary of the metrics to the console."""
        if not self.aggregated_metrics:
            logger.warning("No aggregated metrics available. Run aggregate_metrics() first.")
            return
        
        print("\n===== CODE QUALITY METRICS SUMMARY =====")
        print(f"Overall Score: {self.aggregated_metrics['overall_score']:.2f} (Threshold: {self.threshold:.2f})")
        print(f"Metrics above threshold: {self.aggregated_metrics['metrics_above_threshold']} / {self.aggregated_metrics['metrics_count']}")
        
        print("\n--- Top Improvement Areas ---")
        for i, area in enumerate(self.aggregated_metrics['improvement_areas'][:5]):
            print(f"{i+1}. {area['name']}: {area['current_value']:.2f} (Distance to threshold: {area['distance_to_threshold']:.2f})")
        
        print("\n--- Metrics by Category ---")
        for collector, metrics in self.aggregated_metrics['metrics_by_collector'].items():
            above_threshold = sum(1 for m in metrics if m['meets_threshold'])
            print(f"{collector.capitalize()}: {above_threshold}/{len(metrics)} metrics above threshold")
        
        print("\n--- Recommendations ---")
        recommendations = self.get_improvement_recommendations()
        for i, rec in enumerate(recommendations):
            print(f"{i+1}. {rec['advice']}")
        
        print("\n========================================")
