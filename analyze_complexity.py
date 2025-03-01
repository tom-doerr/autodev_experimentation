#!/usr/bin/env python3
"""
Script to analyze code complexity in the AutoDev project.
Identifies high-complexity areas and suggests improvements.
"""
import os
import sys
import argparse
from pathlib import Path

from autodev.metrics.manager import MetricsManager


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze code complexity in the AutoDev project')
    parser.add_argument('--project-path', type=str, default='.', 
                      help='Path to the project root (default: current directory)')
    parser.add_argument('--threshold', type=float, default=0.95,
                      help='Quality threshold (0-1, default: 0.95)')
    parser.add_argument('--export', type=str, default='metrics_report.json',
                      help='Export results to JSON file')
    parser.add_argument('--focus', type=str, choices=['all', 'complexity', 'style', 'documentation', 'coverage', 'security'],
                      default='all', help='Focus on specific metrics')
    return parser.parse_args()


def main():
    """Main function to analyze code complexity."""
    args = parse_args()
    
    # Resolve project path
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"Error: Project path '{project_path}' does not exist")
        return 1
    
    print(f"Analyzing code complexity in {project_path}...")
    
    # Initialize metrics manager
    manager = MetricsManager(project_path, threshold=args.threshold)
    
    # Collect metrics
    if args.focus == 'all':
        print("Collecting all metrics (this may take a while)...")
        metrics = manager.collect_all_metrics()
    else:
        print(f"Collecting {args.focus} metrics...")
        metrics = manager.collect_specific_metrics([args.focus])
    
    # Aggregate metrics
    print("Aggregating metrics...")
    aggregated = manager.aggregate_metrics()
    
    # Print summary
    manager.print_summary()
    
    # Export results
    if args.export:
        export_path = manager.export_metrics(args.export)
        print(f"Exported metrics report to {export_path}")
    
    # Get improvement recommendations
    print("\nTop improvement recommendations:")
    recommendations = manager.get_improvement_recommendations(max_recommendations=5)
    for i, rec in enumerate(recommendations):
        print(f"{i+1}. {rec['advice']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
