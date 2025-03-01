"""
Documentation metrics collection.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from autodev.metrics.base import MetricsCollector, MetricResult, normalize_value, create_error_metric


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
        """
        Collect docstring coverage metrics using interrogate.
        
        Returns:
            List of MetricResult objects
        """
        # Run interrogate command with JSON output
        return_code, stdout, stderr = self.run_command(
            ["interrogate", "-v", "-j", "."]
        )
        
        if return_code not in (0, 1) or not stdout:
            return [create_error_metric(
                "docstring_coverage", 
                f"Failed to run interrogate: {stderr}"
            )]
        
        try:
            # Parse interrogate JSON output
            coverage_data = json.loads(stdout)
            
            # Get summary metrics
            total_coverage = coverage_data.get("total", {}).get("coverage", 0)
            module_coverage = coverage_data.get("total", {}).get("module_coverage", 0)
            class_coverage = coverage_data.get("total", {}).get("class_coverage", 0)
            method_coverage = coverage_data.get("total", {}).get("method_coverage", 0)
            function_coverage = coverage_data.get("total", {}).get("function_coverage", 0)
            
            # Create metrics
            results = []
            
            # Overall docstring coverage
            results.append(MetricResult(
                name="docstring_coverage",
                raw_value=total_coverage,
                normalized_value=total_coverage / 100,  # already in percentage
                details={
                    "module_coverage": module_coverage,
                    "class_coverage": class_coverage,
                    "method_coverage": method_coverage,
                    "function_coverage": function_coverage,
                    "total_analyzed": coverage_data.get("total", {}).get("n", 0)
                }
            ))
            
            # Module coverage
            results.append(MetricResult(
                name="module_docstring_coverage",
                raw_value=module_coverage,
                normalized_value=module_coverage / 100,  # already in percentage
                details={
                    "modules_with_docstrings": coverage_data.get("total", {}).get("module_covered", 0),
                    "total_modules": coverage_data.get("total", {}).get("module", 0)
                }
            ))
            
            # Class coverage
            results.append(MetricResult(
                name="class_docstring_coverage",
                raw_value=class_coverage,
                normalized_value=class_coverage / 100,  # already in percentage
                details={
                    "classes_with_docstrings": coverage_data.get("total", {}).get("class_covered", 0),
                    "total_classes": coverage_data.get("total", {}).get("class", 0)
                }
            ))
            
            # Function/method coverage
            func_method_coverage = (function_coverage + method_coverage) / 2 if method_coverage > 0 else function_coverage
            results.append(MetricResult(
                name="function_docstring_coverage",
                raw_value=func_method_coverage,
                normalized_value=func_method_coverage / 100,  # already in percentage
                details={
                    "functions_with_docstrings": coverage_data.get("total", {}).get("function_covered", 0),
                    "total_functions": coverage_data.get("total", {}).get("function", 0),
                    "methods_with_docstrings": coverage_data.get("total", {}).get("method_covered", 0),
                    "total_methods": coverage_data.get("total", {}).get("method", 0)
                }
            ))
            
            return results
            
        except Exception as e:
            return [create_error_metric(
                "docstring_coverage", 
                f"Error processing interrogate data: {str(e)}"
            )]
    
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
