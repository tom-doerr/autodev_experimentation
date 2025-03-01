"""
Code style and linting metrics collection.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from autodev.metrics.base import MetricsCollector, MetricResult, normalize_value, create_error_metric


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
    
    def _collect_pylint_metrics(self) -> List[MetricResult]:
        """
        Collect pylint metrics.
        
        Returns:
            List of MetricResult objects
        """
        python_files = list(self.project_path.glob("**/*.py"))
        if not python_files:
            return [create_error_metric(
                "pylint_score", 
                "No Python files found to analyze"
            )]
        
        # Run pylint command
        # Using --recursive=y to scan the entire directory
        return_code, stdout, stderr = self.run_command(
            ["pylint", "--output-format=json", "--recursive=y", "."]
        )
        
        # Pylint exit codes: 0=no error, 1=fatal, 2=error, 4=warning, 8=refactor, 16=convention
        # Multiple codes can be OR'ed together, so we don't check the return code
        
        if not stdout:
            return [create_error_metric(
                "pylint_score", 
                f"Failed to run pylint: {stderr}"
            )]
        
        try:
            # Parse pylint JSON output
            lint_data = json.loads(stdout)
            
            # Count issues by type
            issue_counts = {
                "fatal": 0,
                "error": 0,
                "warning": 0,
                "refactor": 0,
                "convention": 0,
                "info": 0
            }
            
            issues_by_file = {}
            
            for issue in lint_data:
                issue_type = issue.get("type", "")
                if issue_type in issue_counts:
                    issue_counts[issue_type] += 1
                
                # Track issues by file
                file_path = issue.get("path", "unknown")
                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []
                issues_by_file[file_path].append(issue)
            
            # Calculate total issues and weighted score
            total_issues = sum(issue_counts.values())
            
            # Calculate weighted penalty
            # Weights: fatal=100, error=10, warning=1, refactor=0.5, convention=0.1
            weighted_penalty = (
                issue_counts["fatal"] * 100 +
                issue_counts["error"] * 10 +
                issue_counts["warning"] * 1 +
                issue_counts["refactor"] * 0.5 +
                issue_counts["convention"] * 0.1
            )
            
            # Calculate pylint score (10 - weighted penalty)
            # Clamp between 0 and 10
            raw_score = max(0, min(10, 10 - (weighted_penalty / len(python_files))))
            
            # Normalize: 10 = 1.0, 0 = 0.0
            score_norm = normalize_value(raw_score, 0, 10)
            
            # Create metric results
            results = [
                MetricResult(
                    name="pylint_score",
                    raw_value=raw_score,
                    normalized_value=score_norm,
                    details={
                        "issue_counts": issue_counts,
                        "total_issues": total_issues,
                        "files_analyzed": len(python_files),
                        "files_with_issues": len(issues_by_file)
                    }
                )
            ]
            
            # Add metrics for specific issue types
            
            # Error density (lower is better)
            error_density = (issue_counts["fatal"] + issue_counts["error"]) / len(python_files)
            # Normalize: 0 errors = 1.0, 5+ errors per file = 0.0
            error_norm = normalize_value(error_density, 0, 5, invert=True)
            results.append(MetricResult(
                name="pylint_error_density",
                raw_value=error_density,
                normalized_value=error_norm,
                details={
                    "fatal_count": issue_counts["fatal"],
                    "error_count": issue_counts["error"],
                    "files_analyzed": len(python_files)
                }
            ))
            
            # Clean file percentage
            clean_files = len(python_files) - len(issues_by_file)
            clean_percentage = clean_files / len(python_files) if len(python_files) > 0 else 0
            results.append(MetricResult(
                name="pylint_clean_file_percentage",
                raw_value=clean_percentage * 100,  # as percentage
                normalized_value=clean_percentage,
                details={
                    "clean_files": clean_files,
                    "total_files": len(python_files)
                }
            ))
            
            return results
            
        except Exception as e:
            return [create_error_metric(
                "pylint_score", 
                f"Error processing pylint data: {str(e)}"
            )]
    
    def _collect_flake8_metrics(self) -> List[MetricResult]:
        """
        Collect flake8 metrics.
        
        Returns:
            List of MetricResult objects
        """
        python_files = list(self.project_path.glob("**/*.py"))
        if not python_files:
            return [create_error_metric(
                "flake8_violations", 
                "No Python files found to analyze"
            )]
        
        # Run flake8 command
        return_code, stdout, stderr = self.run_command(
            ["flake8", "--statistics", "--count", "."]
        )
        
        # flake8 returns 1 if there are violations
        if return_code not in (0, 1) or (return_code == 1 and not stdout):
            return [create_error_metric(
                "flake8_violations", 
                f"Failed to run flake8: {stderr}"
            )]
        
        try:
            # Parse flake8 output to count violations
            if not stdout or stdout.strip() == "":
                # No violations
                violation_count = 0
            else:
                # Last line contains the count
                violation_count = int(stdout.strip().split('\n')[-1])
            
            # Calculate violations per file
            violations_per_file = violation_count / len(python_files) if len(python_files) > 0 else 0
            
            # Normalize: 0 violations = 1.0, 10+ violations per file = 0.0
            violations_norm = normalize_value(violations_per_file, 0, 10, invert=True)
            
            return [MetricResult(
                name="flake8_violations",
                raw_value=violation_count,
                normalized_value=violations_norm,
                details={
                    "violations_per_file": violations_per_file,
                    "files_analyzed": len(python_files)
                }
            )]
            
        except Exception as e:
            return [create_error_metric(
                "flake8_violations", 
                f"Error processing flake8 data: {str(e)}"
            )]
    
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
