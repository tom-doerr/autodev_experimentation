"""
Code style and linting metrics collection.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import subprocess
import logging

from autodev.metrics.base import MetricsCollector, MetricResult, normalize_value, create_error_metric

logger = logging.getLogger(__name__)

def _is_tool_available(tool_name: str) -> bool:
    """Check if a tool is available."""
    try:
        subprocess.run([tool_name, "--version"], check=True, stdout=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

class StyleMetricsCollector(MetricsCollector):
    """Collector for code style and linting metrics."""
    
    def collect(self) -> List[MetricResult]:
        """
        Collect code style metrics using pylint, flake8, and black.
        
        Returns:
            List of MetricResult objects
        """
        metrics = []
        
        # Collect pylint metrics
        metrics.extend(self._collect_pylint_metrics())
        
        # Collect flake8 metrics
        metrics.extend(self._collect_flake8_metrics())
        
        # Collect black metrics
        metrics.extend(self._collect_black_metrics())
        
        return metrics
    
    def _project_has_files(self, extension: str) -> bool:
        """
        Check if the project has files with the given extension.
        
        Args:
            extension: File extension to check for (e.g., ".py")
            
        Returns:
            True if files with the extension exist, False otherwise
        """
        # Convert generator to list first
        files = list(self.project_path.glob(f"**/*{extension}"))
        return len(files) > 0
    
    def _collect_pylint_metrics(self) -> List[MetricResult]:
        """Collect pylint quality metrics."""
        # Check if tool is available
        if not _is_tool_available("pylint"):
            logger.warning("pylint not installed, skipping metrics")
            return []
            
        # Skip if no Python files
        if not self._project_has_files(".py"):
            logger.warning("No Python files found, skipping pylint metrics")
            return []
        
        pylint_output = subprocess.run(
            ["pylint", "--exit-zero", "--output-format=json", str(self.project_path)],
            capture_output=True, text=True, check=False
        )
        
        if pylint_output.returncode > 1:  # Exit code 1 means violations found, which is expected
            logger.error(f"Error running pylint: {pylint_output.stderr}")
            return [create_error_metric("pylint_score", f"Error running pylint: {pylint_output.stderr}")]
        
        try:
            # Pylint score is a float between 0-10, where 10 is perfect
            score_match = re.search(r'Your code has been rated at ([0-9.]+)/10', pylint_output.stderr)
            if score_match:
                score = float(score_match.group(1))
            else:
                # Try to parse from regular output when no score is shown (e.g., for empty repos)
                score = 10.0  # Default to perfect score for empty repos
            
            # Handle issues when available
            issues = []
            try:
                issues = json.loads(pylint_output.stdout)
            except json.JSONDecodeError:
                logger.warning("No valid JSON issues from pylint")
            
            # Count issues by type
            issue_types = {}
            for issue in issues:
                issue_type = issue.get("type", "unknown")
                if issue_type not in issue_types:
                    issue_types[issue_type] = 0
                issue_types[issue_type] += 1
            
            # Calculate normalized score (0-1)
            normalized_score = normalize_value(score, 0, 10)
            
            return [
                MetricResult(
                    name="pylint_score",
                    raw_value=score,
                    normalized_value=normalized_score,
                    success=True,
                    details={
                        "total_issues": len(issues),
                        "issue_types": issue_types
                    }
                )
            ]
        except Exception as e:
            logger.error(f"Error parsing pylint output: {str(e)}")
            return [create_error_metric("pylint_score", f"Error parsing pylint output: {str(e)}")]
    
    def _collect_flake8_metrics(self) -> List[MetricResult]:
        """Collect flake8 quality metrics."""
        # Check if tool is available
        if not _is_tool_available("flake8"):
            logger.warning("flake8 not installed, skipping metrics")
            return []

        flake8_output = subprocess.run(
            ["flake8", "--exit-zero", "--statistics", "--format=json", str(self.project_path)],
            capture_output=True, text=True, check=False
        )
        
        if flake8_output.returncode > 1:  # Exit code 1 means violations found, which is expected
            logger.error(f"Error running flake8: {flake8_output.stderr}")
            return [create_error_metric("flake8_violations", f"Error running flake8: {flake8_output.stderr}")]
        
        try:
            violations = json.loads(flake8_output.stdout)
            total_files = len(list(self.project_path.glob("**/*.py")))
            total_violations = len(violations)
            
            avg_violations_per_file = total_violations / total_files if total_files > 0 else 0
            
            # Group violations by type
            violation_types = {}
            for v in violations:
                code = v.get("code", "unknown")
                if code not in violation_types:
                    violation_types[code] = 0
                violation_types[code] += 1
            
            # Calculate score - lower violations is better
            # Max expected violations is 10 per file
            max_expected = max(10 * total_files, 1)
            raw_score = max(0, max_expected - total_violations)
            normalized_score = normalize_value(raw_score, 0, max_expected)
            
            return [
                MetricResult(
                    name="flake8_violations",
                    raw_value=total_violations,
                    normalized_value=normalized_score,
                    success=True,
                    details={
                        "total_files": total_files,
                        "total_violations": total_violations,
                        "avg_violations_per_file": avg_violations_per_file,
                        "violation_types": violation_types
                    }
                )
            ]
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from flake8: {flake8_output.stdout}")
            return [create_error_metric("flake8_violations", "Invalid JSON from flake8")]
        except Exception as e:
            logger.error(f"Error parsing flake8 output: {str(e)}")
            return [create_error_metric("flake8_violations", f"Error parsing flake8 output: {str(e)}")]

    def _collect_black_metrics(self) -> List[MetricResult]:
        """
        Collect black formatting metrics.
        
        Returns:
            List of MetricResult objects
        """
        python_files = list(self.project_path.glob("**/*.py"))
        if not python_files:
            return [create_error_metric(
                "black_compliance", 
                "No Python files found to analyze"
            )]
        
        # Run black in check mode
        return_code, stdout, stderr = self.run_command(
            ["black", "--check", "--quiet", "."]
        )
        
        try:
            # black returns 0 if all files are properly formatted
            # and 1 if some files would be reformatted
            if return_code == 0:
                # All files are compliant
                compliant_files = len(python_files)
                non_compliant_files = 0
            else:
                # Count non-compliant files
                non_compliant_files = 0
                for line in stderr.split('\n'):
                    if "would be reformatted" in line:
                        non_compliant_files += 1
                
                compliant_files = len(python_files) - non_compliant_files
            
            # Calculate compliance percentage
            compliance_percentage = compliant_files / len(python_files) if len(python_files) > 0 else 1.0
            
            return [MetricResult(
                name="black_compliance",
                raw_value=compliance_percentage * 100,  # as percentage
                normalized_value=compliance_percentage,
                details={
                    "compliant_files": compliant_files,
                    "non_compliant_files": non_compliant_files,
                    "total_files": len(python_files)
                }
            )]
            
        except Exception as e:
            return [create_error_metric(
                "black_compliance", 
                f"Error processing black data: {str(e)}"
            )]
