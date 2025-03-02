"""
Documentation metrics collection.
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
    """Check if a tool is available."""
    try:
        subprocess.run([tool_name, "--version"], check=True, stdout=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

class DocumentationMetricsCollector(MetricsCollector):
    """Collector for documentation metrics."""
    
    def collect(self) -> List[MetricResult]:
        """
        Collect documentation metrics.
        
        Returns:
            List of MetricResult objects
        """
        metrics = []
        
        # Collect docstring coverage metrics with interrogate
        metrics.extend(self._collect_interrogate_metrics())
        
        # Collect docstring style metrics with pydocstyle
        metrics.extend(self._collect_pydocstyle_metrics())
        
        return metrics
    
    def _collect_interrogate_metrics(self) -> List[MetricResult]:
        """Collect documentation metrics using interrogate."""
        # Check if tool is available
        if not _is_tool_available("interrogate"):
            logger.warning("interrogate not installed, skipping metrics")
            return []
            
        # Skip if no Python files
        if not self._project_has_files():
            logger.warning("No Python files found, skipping interrogate metrics")
            return []
        
        # Run interrogate
        interrogate_output = subprocess.run(
            ["interrogate", "-v", str(self.project_path)],
            capture_output=True, text=True, check=False
        )
        
        # Interrogate returns 0 for passing, 1 for failing
        if interrogate_output.returncode > 1:
            logger.error(f"Error running interrogate: {interrogate_output.stderr}")
            return [create_error_metric("docstring_coverage", f"Error running interrogate: {interrogate_output.stderr}")]
        
        try:
            # Parse interrogate output
            coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+\d+\s+(\d+(?:\.\d+)?)%', interrogate_output.stdout)
            if not coverage_match:
                logger.error("Could not find coverage percentage in interrogate output")
                return [create_error_metric("docstring_coverage", "Could not find coverage percentage in interrogate output")]
            
            coverage_percentage = float(coverage_match.group(1))
            
            # Normalize: 0% = 0.0, 100% = 1.0
            normalized_score = normalize_value(coverage_percentage, 0, 100)
            
            # Extract detailed metrics
            details = {}
            
            # Try to parse module stats
            module_stats = {}
            module_regex = r'([A-Za-z0-9_./]+\.py)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)%'
            module_matches = re.findall(module_regex, interrogate_output.stdout)
            
            for match in module_matches:
                module_path = match[0]
                module_stats[module_path] = {
                    "total": int(match[1]),
                    "missing": int(match[2]),
                    "coverage": float(match[4])
                }
            
            # Find file, class, method and function counts
            files_match = re.search(r'files\s+(\d+)\s+', interrogate_output.stdout)
            classes_match = re.search(r'classes\s+(\d+)\s+', interrogate_output.stdout)
            methods_match = re.search(r'methods\s+(\d+)\s+', interrogate_output.stdout)
            functions_match = re.search(r'functions\s+(\d+)\s+', interrogate_output.stdout)
            
            if files_match:
                details["files_count"] = int(files_match.group(1))
            if classes_match:
                details["classes_count"] = int(classes_match.group(1))
            if methods_match:
                details["methods_count"] = int(methods_match.group(1))
            if functions_match:
                details["functions_count"] = int(functions_match.group(1))
            
            details["module_stats"] = module_stats
            
            return [
                MetricResult(
                    name="docstring_coverage",
                    raw_value=coverage_percentage,
                    normalized_value=normalized_score,
                    success=True,
                    details=details
                )
            ]
        except Exception as e:
            logger.error(f"Error processing interrogate data: {str(e)}")
            return [create_error_metric("docstring_coverage", f"Error processing interrogate data: {str(e)}")]
    
    def _collect_pydocstyle_metrics(self) -> List[MetricResult]:
        """
        Collect docstring style metrics using pydocstyle.
        
        Args:
            python_files: List of Python files to analyze
            
        Returns:
            List of MetricResult objects
        """
        python_files = list(self.project_path.glob("**/*.py"))
        if not python_files:
            return [create_error_metric(
                "docstring_style", 
                "No Python files found to analyze"
            )]
        
        # Run pydocstyle command
        return_code, stdout, stderr = self.run_command(
            ["pydocstyle", "."]
        )
        
        # pydocstyle returns 0 if no errors, 1 if errors
        # We don't check return code since we expect violations
        
        if return_code == -1 and "No such file or directory" in stderr:
            # Tool is missing, return a neutral score instead of 0
            return [create_error_metric(
                "docstring_style", 
                f"Failed to run pydocstyle: {stderr}",
                fallback_value=0.5  # Neutral score for missing tool
            )]
        
        try:
            # Parse and analyze violations
            violations = self._parse_pydocstyle_output(stdout)
            
            # Calculate and return metrics
            return self._create_docstring_style_metrics(violations, python_files)
            
        except Exception as e:
            return [create_error_metric(
                "docstring_style", 
                f"Error processing pydocstyle data: {str(e)}"
            )]
    
    def _parse_pydocstyle_output(self, stdout: str) -> List[Dict[str, Any]]:
        """
        Parse pydocstyle output to extract violations.
        
        Args:
            stdout: Command output from pydocstyle
            
        Returns:
            List of violation dictionaries
        """
        violations = []
        current_violation = None
        
        for line in stdout.split('\n'):
            if line.strip() == "":
                continue
            
            # Start of a new violation
            if re.match(r'^\S+\.py:', line):
                if current_violation:
                    violations.append(current_violation)
                
                # Extract file path and line number
                file_match = re.match(r'^(\S+\.py):(\d+)', line)
                if file_match:
                    file_path = file_match.group(1)
                    line_num = int(file_match.group(2))
                    current_violation = {
                        "file": file_path,
                        "line": line_num,
                        "code": "",
                        "message": ""
                    }
            
            # Violation code and message
            elif current_violation and line.strip().startswith("D"):
                code_match = re.match(r'\s*(D\d+):\s*(.*)', line)
                if code_match:
                    current_violation["code"] = code_match.group(1)
                    current_violation["message"] = code_match.group(2)
        
        # Add the last violation if exists
        if current_violation:
            violations.append(current_violation)
            
        return violations
    
    def _count_violations_by_code(self, violations: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Group violations by error code.
        
        Args:
            violations: List of violation dictionaries
            
        Returns:
            Dictionary mapping error codes to counts
        """
        violations_by_code = {}
        for violation in violations:
            code = violation.get("code", "unknown")
            if code not in violations_by_code:
                violations_by_code[code] = 0
            violations_by_code[code] += 1
            
        return violations_by_code
    
    def _create_docstring_style_metrics(self, 
                                        violations: List[Dict[str, Any]], 
                                        python_files: List[Path]) -> List[MetricResult]:
        """
        Calculate metrics based on pydocstyle violations.
        
        Args:
            violations: List of violation dictionaries
            python_files: List of Python files analyzed
            
        Returns:
            List of MetricResult objects
        """
        # Count violations
        violation_count = len(violations)
        violations_per_file = violation_count / len(python_files) if len(python_files) > 0 else 0
        
        # Group violations by code
        violations_by_code = self._count_violations_by_code(violations)
        
        # 1. Docstring Style Score: Inverse of violations per file
        # Normalize: 0 violations = 1.0, 5+ violations per file = 0.0
        style_score = normalize_value(violations_per_file, 0, 5, invert=True)
        
        # 2. Docstring Style Compliance: Percentage of files without violations
        files_with_violations = set(v.get("file", "") for v in violations)
        files_without_violations = len(python_files) - len(files_with_violations)
        compliance_percentage = files_without_violations / len(python_files) if len(python_files) > 0 else 1.0
        
        return [
            MetricResult(
                name="docstring_style_score",
                raw_value=style_score * 10,  # scale to 0-10
                normalized_value=style_score,
                details={
                    "violations": violation_count,
                    "violations_per_file": violations_per_file,
                    "files_analyzed": len(python_files),
                    "violations_by_code": violations_by_code
                }
            ),
            MetricResult(
                name="docstring_style_compliance",
                raw_value=compliance_percentage * 100,  # as percentage
                normalized_value=compliance_percentage,
                details={
                    "compliant_files": files_without_violations,
                    "non_compliant_files": len(files_with_violations),
                    "total_files": len(python_files)
                }
            )
        ]
