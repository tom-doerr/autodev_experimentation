"""
Security and vulnerability metrics collection.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import logging

from autodev.metrics.base import MetricsCollector, MetricResult, normalize_value, create_error_metric

logger = logging.getLogger(__name__)

def _is_tool_available(tool_name: str) -> bool:
    """Check if a tool is available on the system."""
    try:
        subprocess.run([tool_name, "--version"], check=True, stdout=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

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
        """Collect security metrics for dependencies using safety."""
        # Check if tool is available
        if not _is_tool_available("safety"):
            logger.warning("safety not installed, skipping metrics")
            return []
            
        # Run safety check
        safety_output = subprocess.run(
            ["safety", "check", "--json", "-r", f"{self.project_path}/requirements.txt"],
            capture_output=True, text=True, check=False
        )
        
        # Safety returns 0 for no vulnerabilities, 1 for vulnerabilities found
        if safety_output.returncode > 1:
            logger.error(f"Error running safety: {safety_output.stderr}")
            return [create_error_metric("dependency_vulnerabilities", f"Error running safety: {safety_output.stderr}")]
        
        try:
            # Parse safety output
            try:
                results = json.loads(safety_output.stdout)
                vulnerabilities = results.get("vulnerabilities", [])
            except json.JSONDecodeError:
                # This might be an older version with a different output format
                if "No vulnerable packages found" in safety_output.stdout:
                    vulnerabilities = []
                else:
                    raise ValueError("Unable to parse safety output")

            # Count vulnerabilities by severity
            severity_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
            
            vuln_details = []
            for vuln in vulnerabilities:
                severity = vuln.get("severity", "").lower()
                if severity in severity_counts:
                    severity_counts[severity] += 1
                
                vuln_details.append({
                    "dependency": vuln.get("package_name", "unknown"),
                    "installed_version": vuln.get("installed_version", "unknown"),
                    "affected_versions": vuln.get("vulnerable_spec", "unknown"),
                    "severity": severity,
                    "description": vuln.get("advisory", "")
                })
            
            # Calculate score - 0 vulnerabilities = 1.0, 5+ vulnerabilities = 0.0
            total_vulnerabilities = sum(severity_counts.values())
            
            # Apply severity weighting
            weighted_score = (
                severity_counts["critical"] * 10 +
                severity_counts["high"] * 5 +
                severity_counts["medium"] * 2 +
                severity_counts["low"] * 1
            )
            
            # Normalize: 0 weighted vulns = 1.0, 20+ weighted vulns = 0.0
            normalized_score = normalize_value(weighted_score, 0, 20, invert=True)
            
            return [
                MetricResult(
                    name="dependency_vulnerabilities",
                    raw_value=total_vulnerabilities,
                    normalized_value=normalized_score,
                    success=True,
                    details={
                        "severity_counts": severity_counts,
                        "vulnerabilities": vuln_details
                    }
                )
            ]
        except Exception as e:
            logger.error(f"Error processing safety data: {str(e)}")
            return [create_error_metric("dependency_vulnerabilities", f"Error processing safety data: {str(e)}")]
