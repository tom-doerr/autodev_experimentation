"""
Security and vulnerability metrics collection.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from autodev.metrics.base import MetricsCollector, MetricResult, normalize_value, create_error_metric


class SecurityMetricsCollector(MetricsCollector):
    """Collector for security and vulnerability metrics."""
    
    def collect(self) -> List[MetricResult]:
        """
        Collect security metrics using bandit and safety.
        
        Returns:
            List of MetricResult objects
        """
        metrics = []
        
        # Collect bandit metrics (static security analysis)
        metrics.extend(self._collect_bandit_metrics())
        
        # Collect safety metrics (dependency vulnerabilities)
        metrics.extend(self._collect_safety_metrics())
        
        return metrics
    
    def _collect_bandit_metrics(self) -> List[MetricResult]:
        """
        Collect security metrics using bandit.
        
        Returns:
            List of MetricResult objects
        """
        # Run bandit command with JSON output
        return_code, stdout, stderr = self.run_command(
            ["bandit", "-r", "-f", "json", "."]
        )
        
        # bandit returns 0 for no issues, 1 for issues found
        if return_code not in (0, 1) or not stdout:
            # If bandit isn't installed, we'll set a neutral fallback value (0.5)
            # rather than giving a 0 score for a missing tool
            if return_code == -1 and "No such file or directory" in stderr:
                return [create_error_metric(
                    "security_score", 
                    f"Failed to run bandit: {stderr}",
                    fallback_value=0.5  # Neutral score for missing tool
                )]
            else:
                return [create_error_metric(
                    "security_score", 
                    f"Failed to run bandit: {stderr}"
                )]
        
        try:
            # Parse bandit JSON output
            security_data = json.loads(stdout)
            
            # Get metrics from results
            metrics_data = security_data.get("metrics", {})
            
            # Count issues by severity
            results = security_data.get("results", [])
            issues_by_severity = {
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0
            }
            
            for result in results:
                severity = result.get("issue_severity", "").upper()
                if severity in issues_by_severity:
                    issues_by_severity[severity] += 1
            
            # Calculate security score
            total_issues = sum(issues_by_severity.values())
            weighted_issues = (
                issues_by_severity["HIGH"] * 5 +
                issues_by_severity["MEDIUM"] * 2 +
                issues_by_severity["LOW"]
            )
            
            # Calculate score (10 - weighted issues, min 0)
            raw_score = max(0, 10 - weighted_issues)
            score = normalize_value(raw_score, 0, 10)
            
            return [MetricResult(
                name="security_score",
                raw_value=raw_score,
                normalized_value=score,
                details={
                    "issues_high": issues_by_severity["HIGH"],
                    "issues_medium": issues_by_severity["MEDIUM"],
                    "issues_low": issues_by_severity["LOW"],
                    "total_issues": total_issues
                }
            )]
        except (json.JSONDecodeError, KeyError) as e:
            return [create_error_metric(
                "security_score", 
                f"Error parsing bandit output: {e}"
            )]
            
    def _collect_safety_metrics(self) -> List[MetricResult]:
        """
        Collect dependency safety metrics using safety.
        
        Returns:
            List of MetricResult objects
        """
        # Run safety command with JSON output
        return_code, stdout, stderr = self.run_command(
            ["safety", "check", "--json", "--full-report"]
        )
        
        if return_code not in (0, 64) or not stdout:  # safety returns 0 for no issues, 64 for issues found
            # If safety isn't installed, we'll set a neutral fallback value
            if return_code == -1 and "No such file or directory" in stderr:
                return [create_error_metric(
                    "dependency_vulnerability_score", 
                    f"Failed to run safety: {stderr}",
                    fallback_value=0.5  # Neutral score for missing tool
                )]
            else:
                return [create_error_metric(
                    "dependency_vulnerability_score", 
                    f"Failed to run safety: {stderr}"
                )]
        
        try:
            # Parse safety JSON output
            vulnerabilities_data = json.loads(stdout)
            
            # Count vulnerabilities
            vulnerabilities_count = len(vulnerabilities_data)
            
            # Get total dependencies
            dependencies_count = 0
            requirements_file = self.project_path / "requirements.txt"
            if requirements_file.exists():
                with open(requirements_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            dependencies_count += 1
            
            # Calculate vulnerability percentage
            vulnerability_percentage = vulnerabilities_count / dependencies_count if dependencies_count > 0 else 0
            
            # Normalize: 0% vulnerable = 1.0, 20%+ vulnerable = 0.0
            vuln_norm = normalize_value(vulnerability_percentage, 0, 0.2, invert=True)
            
            # Track vulnerability details
            vulnerability_details = []
            for vuln in vulnerabilities_data:
                if len(vuln) >= 5:  # Safety output format is a list of lists
                    vulnerability_details.append({
                        "dependency": vuln[0],
                        "installed_version": vuln[1],
                        "affected_versions": vuln[2],
                        "vulnerability_id": vuln[3],
                        "advisory": vuln[4]
                    })
            
            return [MetricResult(
                name="dependency_vulnerability_score",
                raw_value=vulnerability_percentage,
                normalized_value=vuln_norm,
                details={
                    "vulnerability_count": vulnerabilities_count,
                    "dependencies_count": dependencies_count,
                    "vulnerability_percentage": vulnerability_percentage * 100,  # as percentage
                    "vulnerabilities": vulnerability_details
                }
            )]
            
        except Exception as e:
            return [create_error_metric(
                "dependency_vulnerability_score", 
                f"Error processing safety data: {str(e)}"
            )]
