"""
Complexity metrics collection for code quality analysis.
"""
import json
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional

from autodev.metrics.base import MetricsCollector, MetricResult, normalize_value, create_error_metric


class ComplexityMetricsCollector(MetricsCollector):
    """Collector for code complexity metrics using various tools."""
    
    def collect(self) -> List[MetricResult]:
        """
        Collect complexity metrics using radon and other tools.
        
        Returns:
            List of MetricResult objects
        """
        metrics = []
        
        # Collect cyclomatic complexity (CC) metrics
        metrics.extend(self._collect_cyclomatic_complexity())
        
        # Collect maintainability index (MI) metrics
        metrics.extend(self._collect_maintainability_index())
        
        # Collect raw metrics (SLOC, comment density, etc.)
        metrics.extend(self._collect_raw_metrics())
        
        return metrics
    
    def _collect_cyclomatic_complexity(self) -> List[MetricResult]:
        """
        Collect cyclomatic complexity metrics using radon.
        
        Returns:
            List of MetricResult objects
        """
        results = []
        
        # Run radon cc command
        return_code, stdout, stderr = self.run_command(
            ["radon", "cc", "-j", str(self.project_path)]
        )
        
        if return_code != 0 or not stdout:
            return [create_error_metric(
                "cyclomatic_complexity", 
                f"Failed to run radon: {stderr}"
            )]
        
        try:
            cc_data = json.loads(stdout)
            
            # Calculate average complexity
            all_complexities = []
            function_count = 0
            complex_functions = []
            
            for file_path, functions in cc_data.items():
                for func in functions:
                    complexity = func.get("complexity", 0)
                    all_complexities.append(complexity)
                    function_count += 1
                    
                    # Track functions with high complexity
                    if complexity > 10:
                        complex_functions.append({
                            "file": file_path,
                            "function": func.get("name", "unknown"),
                            "complexity": complexity,
                            "line": func.get("lineno", 0)
                        })
            
            if not all_complexities:
                return [create_error_metric(
                    "cyclomatic_complexity", 
                    "No functions found to analyze"
                )]
            
            # Calculate metrics
            avg_complexity = statistics.mean(all_complexities)
            max_complexity = max(all_complexities)
            min_complexity = min(all_complexities)
            complexity_stdev = statistics.stdev(all_complexities) if len(all_complexities) > 1 else 0
            
            # Create metrics
            
            # 1. Average complexity (lower is better)
            # Normalize: 1 (best) = complexity of 1, 0 (worst) = complexity of 15+
            avg_norm = normalize_value(avg_complexity, 1, 15, invert=True)
            results.append(MetricResult(
                name="avg_cyclomatic_complexity",
                raw_value=avg_complexity,
                normalized_value=avg_norm,
                details={
                    "max_complexity": max_complexity,
                    "min_complexity": min_complexity,
                    "stdev": complexity_stdev,
                    "function_count": function_count
                }
            ))
            
            # 2. Percentage of simple functions (complexity <= 5)
            simple_count = sum(1 for c in all_complexities if c <= 5)
            simple_percentage = simple_count / function_count if function_count else 0
            results.append(MetricResult(
                name="simple_functions_percentage",
                raw_value=simple_percentage * 100,  # as percentage
                normalized_value=simple_percentage,
                details={
                    "simple_count": simple_count,
                    "total_functions": function_count
                }
            ))
            
            # 3. Complex functions ratio (lower is better)
            complex_count = len(complex_functions)
            complex_ratio = complex_count / function_count if function_count else 0
            # Normalize: 0% complex functions = 1.0, 30%+ complex functions = 0.0
            complex_norm = normalize_value(complex_ratio, 0, 0.3, invert=True)
            results.append(MetricResult(
                name="complex_functions_ratio",
                raw_value=complex_ratio * 100,  # as percentage
                normalized_value=complex_norm,
                details={
                    "complex_functions": complex_functions,
                    "complex_count": complex_count,
                    "total_functions": function_count
                }
            ))
            
            return results
            
        except Exception as e:
            return [create_error_metric(
                "cyclomatic_complexity", 
                f"Error processing complexity data: {str(e)}"
            )]
    
    def _collect_maintainability_index(self) -> List[MetricResult]:
        """
        Collect maintainability index metrics using radon.
        
        Returns:
            List of MetricResult objects
        """
        # Run radon mi command
        return_code, stdout, stderr = self.run_command(
            ["radon", "mi", "-j", str(self.project_path)]
        )
        
        if return_code != 0 or not stdout:
            return [create_error_metric(
                "maintainability_index", 
                f"Failed to run radon mi: {stderr}"
            )]
        
        try:
            mi_data = json.loads(stdout)
            
            if not mi_data:
                return [create_error_metric(
                    "maintainability_index", 
                    "No files found to analyze"
                )]
            
            # Collect all MI values
            mi_values = []
            files_by_category = {
                "A": [],  # Excellent (>= 90)
                "B": [],  # Good (>= 80, < 90)
                "C": [],  # Medium (>= 70, < 80)
                "D": []   # Poor (< 70)
            }
            
            for file_path, mi_value in mi_data.items():
                if not isinstance(mi_value, (int, float)):
                    continue
                    
                mi_values.append(mi_value)
                
                # Categorize files
                if mi_value >= 90:
                    files_by_category["A"].append(file_path)
                elif mi_value >= 80:
                    files_by_category["B"].append(file_path)
                elif mi_value >= 70:
                    files_by_category["C"].append(file_path)
                else:
                    files_by_category["D"].append(file_path)
            
            if not mi_values:
                return [create_error_metric(
                    "maintainability_index", 
                    "No valid maintainability index values found"
                )]
            
            # Calculate metrics
            avg_mi = statistics.mean(mi_values)
            
            # Normalize: 100 (perfect) = 1.0, 50 or below = 0.0
            mi_norm = normalize_value(avg_mi, 50, 100)
            
            # Create metric result
            return [MetricResult(
                name="maintainability_index",
                raw_value=avg_mi,
                normalized_value=mi_norm,
                details={
                    "files_by_category": {
                        "excellent": len(files_by_category["A"]),
                        "good": len(files_by_category["B"]),
                        "medium": len(files_by_category["C"]),
                        "poor": len(files_by_category["D"])
                    },
                    "total_files": len(mi_values),
                    "min_mi": min(mi_values),
                    "max_mi": max(mi_values)
                }
            )]
            
        except Exception as e:
            return [create_error_metric(
                "maintainability_index", 
                f"Error processing maintainability index data: {str(e)}"
            )]
    
    def _collect_raw_metrics(self) -> List[MetricResult]:
        """
        Collect raw metrics using radon.
        
        Returns:
            List of MetricResult objects
        """
        # Run radon raw command
        return_code, stdout, stderr = self.run_command(
            ["radon", "raw", "-j", str(self.project_path)]
        )
        
        if return_code != 0 or not stdout:
            return [create_error_metric(
                "raw_metrics", 
                f"Failed to run radon raw: {stderr}"
            )]
        
        try:
            raw_data = json.loads(stdout)
            
            if not raw_data:
                return [create_error_metric(
                    "raw_metrics", 
                    "No files found to analyze"
                )]
            
            # Aggregate metrics
            total_sloc = 0
            total_comments = 0
            total_multi = 0  # Multi-line strings
            total_blank = 0
            total_lines = 0
            
            for file_path, metrics in raw_data.items():
                total_sloc += metrics.get("loc", 0)
                total_comments += metrics.get("comments", 0)
                total_multi += metrics.get("multi", 0)
                total_blank += metrics.get("blank", 0)
                total_lines += metrics.get("sloc", 0)
            
            # Calculate comment density
            comment_density = total_comments / total_sloc if total_sloc else 0
            
            # Normalize: 0.2 (20% comments) or more = 1.0, 0.0 (no comments) = 0.0
            comment_norm = normalize_value(comment_density, 0, 0.2)
            
            return [MetricResult(
                name="comment_density",
                raw_value=comment_density * 100,  # as percentage
                normalized_value=comment_norm,
                details={
                    "total_sloc": total_sloc,
                    "total_comments": total_comments,
                    "total_blank": total_blank,
                    "total_multi": total_multi,
                    "total_lines": total_lines
                }
            )]
            
        except Exception as e:
            return [create_error_metric(
                "raw_metrics", 
                f"Error processing raw metrics data: {str(e)}"
            )]
