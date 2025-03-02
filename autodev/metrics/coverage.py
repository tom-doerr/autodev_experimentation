"""
Test coverage metrics collection.
"""
import json
import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

from autodev.metrics.base import MetricsCollector, MetricResult, normalize_value, create_error_metric

logger = logging.getLogger(__name__)

class CoverageMetricsCollector(MetricsCollector):
    """Collector for test coverage metrics."""
    
    def collect(self) -> List[MetricResult]:
        """
        Collect test coverage metrics.
        
        Returns:
            List of MetricResult objects
        """
        metrics = []
        
        # First, run coverage to gather data
        self._run_coverage()
        
        # Collect line coverage metrics
        metrics.extend(self._collect_line_coverage())
        
        # Collect branch coverage metrics
        metrics.extend(self._collect_branch_coverage())
        
        # Collect test metrics
        metrics.extend(self._collect_test_metrics())
        
        return metrics
    
    def _run_coverage(self) -> bool:
        """
        Run pytest with coverage to gather coverage data.
        
        Returns:
            True if successful, False otherwise
        """
        # Run pytest with coverage
        return_code, stdout, stderr = self.run_command(
            ["python", "-m", "pytest", "--cov=.", "--cov-report=json", "-v"]
        )
        
        # pytest could fail but still generate coverage data, so we don't check return code
        
        # Check if coverage JSON file was created
        coverage_file = self.project_path / ".coverage"
        json_coverage_file = self.project_path / "coverage.json"
        
        return coverage_file.exists() or json_coverage_file.exists()
    
    def _collect_line_coverage(self) -> List[MetricResult]:
        """
        Collect line coverage metrics.
        
        Returns:
            List of MetricResult objects
        """
        json_coverage_file = self.project_path / "coverage.json"
        
        if not json_coverage_file.exists():
            return [create_error_metric(
                "line_coverage", 
                "Coverage data not found. Make sure tests can run successfully."
            )]
        
        try:
            # Load coverage data
            with open(json_coverage_file, 'r') as f:
                coverage_data = json.load(f)
            
            # Process coverage data
            total_coverage = self._extract_total_coverage(coverage_data)
            files_coverage = self._extract_file_coverage(coverage_data)
            
            # Calculate distributions and thresholds
            coverage_distribution = self._calculate_coverage_distribution(files_coverage)
            low_coverage_files = self._identify_low_coverage_files(files_coverage)
            
            # Calculate and return metrics
            return self._create_coverage_metrics(total_coverage, files_coverage, 
                                                coverage_distribution, low_coverage_files)
            
        except Exception as e:
            return [create_error_metric(
                "line_coverage", 
                f"Error processing coverage data: {str(e)}"
            )]
    
    def _extract_total_coverage(self, coverage_data: Dict[str, Any]) -> float:
        """Extract total coverage percentage from coverage data."""
        return coverage_data.get("totals", {}).get("percent_covered", 0)
    
    def _extract_file_coverage(self, coverage_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract per-file coverage data, skipping test files."""
        files_coverage = []
        for file_path, file_data in coverage_data.get("files", {}).items():
            # Skip any test files
            if "test" in file_path.lower():
                continue
            
            percent_covered = file_data.get("summary", {}).get("percent_covered", 0)
            files_coverage.append({
                "file": file_path,
                "coverage": percent_covered,
                "missing_lines": file_data.get("missing_lines", [])
            })
        
        # Sort files by coverage (ascending)
        files_coverage.sort(key=lambda x: x["coverage"])
        return files_coverage
    
    def _calculate_coverage_distribution(self, files_coverage: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate the distribution of files across coverage ranges."""
        return {
            "0-20%": len([f for f in files_coverage if f["coverage"] < 20]),
            "20-40%": len([f for f in files_coverage if 20 <= f["coverage"] < 40]),
            "40-60%": len([f for f in files_coverage if 40 <= f["coverage"] < 60]),
            "60-80%": len([f for f in files_coverage if 60 <= f["coverage"] < 80]),
            "80-100%": len([f for f in files_coverage if 80 <= f["coverage"] <= 100])
        }
    
    def _identify_low_coverage_files(self, files_coverage: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify files with low test coverage."""
        low_coverage_threshold = 40  # Consider files with less than 40% coverage as low
        return [f for f in files_coverage if f["coverage"] < low_coverage_threshold]
    
    def _create_coverage_metrics(self, total_coverage: float, files_coverage: List[Dict[str, Any]],
                                coverage_distribution: Dict[str, int], 
                                low_coverage_files: List[Dict[str, Any]]) -> List[MetricResult]:
        """Create metric results for coverage data."""
        # Normalize: 0% = 0.0, 100% = 1.0
        coverage_norm = total_coverage / 100
        
        # 1. Overall line coverage
        results = [MetricResult(
            name="line_coverage",
            raw_value=total_coverage,
            normalized_value=coverage_norm,
            details={
                "files_analyzed": len(files_coverage),
                "coverage_distribution": coverage_distribution,
                "low_coverage_files": low_coverage_files[:5]  # Show top 5 lowest covered files
            }
        )]
        
        # 2. Coverage quality (percentage of files with good coverage)
        results.append(self._create_coverage_quality_metric(files_coverage))
        
        return results
    
    def _create_coverage_quality_metric(self, files_coverage: List[Dict[str, Any]]) -> MetricResult:
        """Create a metric for coverage quality."""
        good_coverage_threshold = 80  # Consider files with 80%+ coverage as good
        good_coverage_files = len([f for f in files_coverage if f["coverage"] >= good_coverage_threshold])
        good_coverage_percentage = good_coverage_files / len(files_coverage) if files_coverage else 0
        
        return MetricResult(
            name="coverage_quality",
            raw_value=good_coverage_percentage * 100,  # as percentage
            normalized_value=good_coverage_percentage,
            details={
                "good_coverage_files": good_coverage_files,
                "total_files": len(files_coverage),
                "good_coverage_threshold": good_coverage_threshold
            }
        )
    
    def _collect_branch_coverage(self) -> List[MetricResult]:
        """Collect branch coverage metrics."""
        # Check if coverage data available
        if not self._coverage_data_exists():
            logger.warning("No coverage data found, skipping branch coverage metrics")
            return []
        
        try:
            # Parse coverage data
            coverage_data = self._get_coverage_data()
            
            if not coverage_data:
                logger.warning("No coverage data available")
                return []
            
            # Calculate branch coverage
            branch_data = coverage_data.get("branch_coverage", {})
            
            if not branch_data:
                logger.warning("No branch coverage data available")
                return []
            
            total_branches = branch_data.get("total_branches", 0)
            covered_branches = branch_data.get("covered_branches", 0)
            
            coverage_percent = (covered_branches / total_branches) * 100 if total_branches > 0 else 0
            
            # Normalize coverage percentage to 0-1 scale
            normalized_value = normalize_value(coverage_percent, 0, 100)
            
            # Collect branch coverage by file
            branches_by_file = branch_data.get("branches_by_file", {})
            
            file_details = []
            for file_path, file_data in branches_by_file.items():
                file_total = file_data.get("total", 0)
                file_covered = file_data.get("covered", 0)
                file_coverage = (file_covered / file_total) * 100 if file_total > 0 else 0
                
                file_details.append({
                    "file": file_path,
                    "total_branches": file_total,
                    "covered_branches": file_covered,
                    "coverage_percent": file_coverage
                })
            
            # Sort file details by coverage percentage (ascending)
            file_details.sort(key=lambda x: x["coverage_percent"])
            
            return [
                MetricResult(
                    name="branch_coverage",
                    raw_value=coverage_percent,
                    normalized_value=normalized_value,
                    success=True,
                    details={
                        "total_branches": total_branches,
                        "covered_branches": covered_branches,
                        "coverage_percent": coverage_percent,
                        "files": file_details[:10]  # Top 10 files with lowest coverage
                    }
                )
            ]
        except Exception as e:
            logger.error(f"Error processing branch coverage: {str(e)}")
            return [create_error_metric("branch_coverage", f"Error processing branch coverage: {str(e)}")]
    
    def _coverage_data_exists(self) -> bool:
        """Check if coverage data exists."""
        json_coverage_file = self.project_path / "coverage.json"
        return json_coverage_file.exists()
    
    def _get_coverage_data(self) -> Dict[str, Any]:
        """Get coverage data from JSON file."""
        json_coverage_file = self.project_path / "coverage.json"
        with open(json_coverage_file, 'r') as f:
            return json.load(f)
    
    def _collect_test_metrics(self) -> List[MetricResult]:
        """
        Collect test execution metrics.
        
        Returns:
            List of MetricResult objects
        """
        # Run pytest to collect test metrics
        return_code, stdout, stderr = self.run_command(
            ["python", "-m", "pytest", "--collect-only", "-v"]
        )
        
        if return_code != 0:
            return [create_error_metric(
                "test_count", 
                f"Failed to collect tests: {stderr}"
            )]
        
        try:
            # Parse test metrics from pytest output
            test_functions, test_files_found = self._parse_pytest_output(stdout)
            
            # Calculate metrics and return results
            return self._create_test_metrics(test_functions, test_files_found)
            
        except Exception as e:
            return [create_error_metric(
                "test_count", 
                f"Error processing test metrics: {str(e)}"
            )]
    
    def _parse_pytest_output(self, stdout: str) -> Tuple[int, Set[str]]:
        """
        Parse pytest output to extract test counts.
        
        Args:
            stdout: Command output from pytest
            
        Returns:
            Tuple of (test_function_count, set_of_test_files)
        """
        test_functions = 0
        
        # First try to get collected items count
        for line in stdout.split('\n'):
            if re.search(r'collecting\s+\.\.\.\s+collected\s+(\d+)\s+items', line):
                match = re.search(r'collected\s+(\d+)\s+items', line)
                if match:
                    test_functions = int(match.group(1))
                    break
        
        if test_functions == 0:
            # Try counting individual test functions by line
            for line in stdout.split('\n'):
                if re.search(r'<\w+\s+[\w\.]+\.[^>]+>', line):
                    test_functions += 1
        
        # Count test files
        test_files_found = set()
        for line in stdout.split('\n'):
            file_match = re.search(r'([^/]+/[^/]+/test_[^/\s]+\.py)', line)
            if file_match:
                test_files_found.add(file_match.group(1))
        
        return test_functions, test_files_found
    
    def _create_test_metrics(self, test_functions: int, test_files_found: Set[str]) -> List[MetricResult]:
        """
        Create metrics based on test counts.
        
        Args:
            test_functions: Number of test functions found
            test_files_found: Set of test file paths
            
        Returns:
            List of MetricResult objects
        """
        # Get file counts
        test_files = len(test_files_found)
        python_files = list(self.project_path.glob("**/*.py"))
        non_test_files = len([f for f in python_files if not f.name.startswith("test_")])
        
        # Calculate test density
        test_density = test_functions / non_test_files if non_test_files > 0 else 0
        
        # Normalize: 0 tests per file = 0.0, 5+ tests per file = 1.0
        test_density_norm = normalize_value(test_density, 0, 5)
        
        return [
            MetricResult(
                name="test_count",
                raw_value=test_functions,
                normalized_value=min(1.0, test_functions / 100),  # normalize against 100 tests
                details={
                    "test_files": test_files,
                    "non_test_files": non_test_files,
                    "test_density": test_density,
                    "tests_per_file": test_functions / test_files if test_files > 0 else 0
                }
            ),
            MetricResult(
                name="test_density",
                raw_value=test_density,
                normalized_value=test_density_norm,
                details={
                    "test_functions": test_functions,
                    "non_test_files": non_test_files,
                    "minimum_good_density": 1.0  # at least 1 test per file
                }
            )
        ]
