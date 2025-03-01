"""
Normalization utilities for metrics.
"""
from typing import Dict, List, Any, Optional, Tuple


def normalize_value(value: float, min_value: float, max_value: float, invert: bool = False) -> float:
    """
    Normalize a value to the range [0, 1].
    
    Args:
        value: The value to normalize
        min_value: The minimum expected value
        max_value: The maximum expected value
        invert: Whether to invert the normalization (1 - norm)
    
    Returns:
        A value between 0 and 1
    """
    # Clamp value to [min_value, max_value]
    clamped_value = max(min_value, min(max_value, value))
    
    # Calculate normalized value
    if max_value == min_value:
        normalized = 0.5  # Avoid division by zero
    else:
        normalized = (clamped_value - min_value) / (max_value - min_value)
    
    # Invert if requested
    if invert:
        normalized = 1 - normalized
    
    return normalized


def apply_threshold(normalized_value: float, threshold: float = 0.95) -> Tuple[bool, float]:
    """
    Apply a threshold to a normalized value.
    
    Args:
        normalized_value: A value between 0 and 1
        threshold: The threshold to apply
    
    Returns:
        A tuple of (meets_threshold, distance_to_threshold)
    """
    meets_threshold = normalized_value >= threshold
    distance = normalized_value - threshold
    
    return meets_threshold, distance


def calculate_weight(normalized_value: float, threshold: float = 0.95, exponential: float = 2.0) -> float:
    """
    Calculate a weight for a metric based on how far it is from the threshold.
    
    The weight increases exponentially as the value gets further from the threshold.
    
    Args:
        normalized_value: A value between 0 and 1
        threshold: The target threshold
        exponential: The exponential factor
    
    Returns:
        A weight value, with higher values indicating more importance
    """
    if normalized_value >= threshold:
        return 0.0  # Already meeting threshold
    
    # Calculate distance from threshold
    distance = threshold - normalized_value
    
    # Apply exponential weighting
    return distance ** exponential


def aggregate_metrics(metrics: List[Dict[str, Any]], 
                     threshold: float = 0.95,
                     weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    Aggregate metrics into an overall score and identify areas for improvement.
    
    Args:
        metrics: List of metric dictionaries with 'name' and 'normalized_value'
        threshold: The target threshold for all metrics
        weights: Optional custom weights for specific metrics
    
    Returns:
        Dictionary with aggregated metrics and improvement areas
    """
    if not metrics:
        return {
            "overall_score": 0.0,
            "metrics_count": 0,
            "metrics_above_threshold": 0,
            "metrics_below_threshold": 0,
            "improvement_areas": []
        }
    
    # Calculate overall score and counts
    total_score = 0.0
    metrics_above_threshold = 0
    metrics_below_threshold = 0
    
    # Prepare improvement areas
    improvement_areas = []
    
    # Process each metric
    for metric in metrics:
        name = metric.get("name", "unknown")
        value = metric.get("normalized_value", 0.0)
        
        # Add to total score
        total_score += value
        
        # Check threshold
        meets_threshold, distance = apply_threshold(value, threshold)
        
        if meets_threshold:
            metrics_above_threshold += 1
        else:
            metrics_below_threshold += 1
            
            # Calculate weight
            custom_weight = weights.get(name, 1.0) if weights else 1.0
            improvement_weight = calculate_weight(value, threshold) * custom_weight
            
            # Add to improvement areas
            improvement_areas.append({
                "name": name,
                "current_value": value,
                "distance_to_threshold": abs(distance),
                "improvement_weight": improvement_weight,
                "details": metric.get("details", {})
            })
    
    # Sort improvement areas by weight (descending)
    improvement_areas.sort(key=lambda x: x["improvement_weight"], reverse=True)
    
    # Calculate overall score
    overall_score = total_score / len(metrics) if metrics else 0.0
    
    return {
        "overall_score": overall_score,
        "metrics_count": len(metrics),
        "metrics_above_threshold": metrics_above_threshold,
        "metrics_below_threshold": metrics_below_threshold,
        "improvement_areas": improvement_areas
    }
