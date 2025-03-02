"""
Base interfaces and utilities for code quality metrics.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import subprocess
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)


class MetricResult:
    """Class to hold and normalize a single metric result."""
    
    def __init__(
        self,
        name: str,
        raw_value: Union[float, int],
        normalized_value: float,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Initialize a metric result.
        
        Args:
            name: Name of the metric
            raw_value: Original value before normalization
            normalized_value: Value normalized to 0-1 range (1 being best)
            details: Additional details about the metric
            success: Whether the metric computation was successful
            error: Error message if not successful
        """
        self.name = name
        self.raw_value = raw_value
        self.normalized_value = max(0.0, min(1.0, normalized_value))  # Ensure 0-1 range
        self.details = details or {}
        self.success = success
        self.error = error
    
    def __repr__(self) -> str:
        """String representation of the metric result."""
        if not self.success:
            return f"MetricResult({self.name}, ERROR: {self.error})"
        return f"MetricResult({self.name}, raw={self.raw_value}, norm={self.normalized_value:.2f})"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the metric result to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the metric result
        """
        return {
            "name": self.name,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "details": self.details,
            "success": self.success,
            "error": self.error
        }
    
    @property
    def needs_improvement(self) -> bool:
        """Check if this metric needs improvement based on threshold."""
        return self.normalized_value < 0.95


class MetricsCollector(ABC):
    """Base abstract class for all metrics collectors."""
    
    def __init__(self, project_path: Union[str, Path]):
        """
        Initialize the metrics collector.
        
        Args:
            project_path: Path to the project to analyze
        """
        self.project_path = Path(project_path)
        if not self.project_path.exists():
            raise ValueError(f"Project path does not exist: {self.project_path}")
    
    @abstractmethod
    def collect(self) -> List[MetricResult]:
        """
        Collect metrics and return normalized results.
        
        Returns:
            List of MetricResult objects
        """
        pass
    
    def run_command(
        self, 
        cmd: List[str], 
        capture_output: bool = True,
        check: bool = False
    ) -> Tuple[int, str, str]:
        """
        Run a shell command and return the results.
        
        Args:
            cmd: Command to run as a list of strings
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise an exception on non-zero exit
        
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=capture_output,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            return e.returncode, e.stdout, e.stderr
        except Exception as e:
            logger.exception(f"Error running command: {e}")
            return -1, "", str(e)


def normalize_value(
    value: float,
    min_val: float, 
    max_val: float, 
    invert: bool = False
) -> float:
    """
    Normalize a value to the range 0-1.
    
    Args:
        value: Raw value to normalize
        min_val: Minimum possible value
        max_val: Maximum possible value
        invert: If True, 1 will represent the minimum value and 0 the maximum
    
    Returns:
        Normalized value in the 0-1 range
    """
    # Handle edge cases
    if min_val == max_val:
        return 1.0
    
    # Clamp value to range
    clamped_value = max(min_val, min(max_val, value))
    
    # Normalize to 0-1
    normalized = (clamped_value - min_val) / (max_val - min_val)
    
    # Invert if needed (for metrics where lower is better)
    if invert:
        normalized = 1.0 - normalized
        
    return normalized


def create_error_metric(name: str, error_message: str) -> MetricResult:
    """
    Create a metric result for an error condition.
    
    Args:
        name: Name of the metric
        error_message: Error message
    
    Returns:
        MetricResult object representing the error
    """
    return MetricResult(
        name=name,
        raw_value=0,
        normalized_value=0,
        success=False,
        error=error_message
    )
