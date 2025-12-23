"""
Phase 5: Parameter Tuning Utility for DP-Based Reading Order Fix

This script helps tune DP alignment parameters based on test results.
Provides visual feedback and recommendations for parameter adjustments.

Usage:
    python tune_dp_parameters.py --test-image <path_to_image>
    python tune_dp_parameters.py --analyze-results <results_file>
"""

import argparse
import logging
from typing import Dict, List, Tuple, Optional
import json

from ocr_fusion import (
    group_into_lines,
    align_lines,
    detect_line_breaks,
    calculate_avg_char_height,
    BREAK_NONE,
    BREAK_LINE,
    BREAK_PARAGRAPH,
)

logger = logging.getLogger(__name__)


# ============================================================================
# PARAMETER TUNING CONFIGURATION
# ============================================================================

class DPParameterConfig:
    """Configuration for DP alignment parameters."""
    
    def __init__(self):
        # Line grouping parameters
        self.line_threshold_ratio: float = 0.3  # 30% of char height
        
        # Break detection parameters
        self.line_break_gap_ratio: float = 0.5  # 50% of char height
        self.para_break_gap_ratio: float = 2.0  # 200% of char height
        
        # DP alignment parameters
        self.iou_threshold: float = 0.5  # IoU threshold for character alignment
        self.skip_penalty: float = -0.1   # Penalty for skipping characters
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {
            "line_threshold_ratio": self.line_threshold_ratio,
            "line_break_gap_ratio": self.line_break_gap_ratio,
            "para_break_gap_ratio": self.para_break_gap_ratio,
            "iou_threshold": self.iou_threshold,
            "skip_penalty": self.skip_penalty,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'DPParameterConfig':
        """Create from dictionary."""
        config = cls()
        config.line_threshold_ratio = data.get("line_threshold_ratio", 0.3)
        config.line_break_gap_ratio = data.get("line_break_gap_ratio", 0.5)
        config.para_break_gap_ratio = data.get("para_break_gap_ratio", 2.0)
        config.iou_threshold = data.get("iou_threshold", 0.5)
        config.skip_penalty = data.get("skip_penalty", -0.1)
        return config


# ============================================================================
# PARAMETER ANALYSIS
# ============================================================================

def analyze_line_grouping(
    characters: List,
    line_threshold_ratio: float = 0.3
) -> Dict[str, any]:
    """
    Analyze line grouping results and provide tuning recommendations.
    
    Args:
        characters: List of OCR characters
        line_threshold_ratio: Current threshold ratio
        
    Returns:
        Analysis results with recommendations
    """
    lines = group_into_lines(characters, line_threshold_ratio)
    
    # Calculate statistics
    line_lengths = [len(line) for line in lines]
    avg_line_length = sum(line_lengths) / len(line_lengths) if line_lengths else 0
    
    # Analyze vertical spacing
    if len(lines) > 1:
        gaps = []
        for i in range(1, len(lines)):
            prev_bottom = max(c.bbox[3] for c in lines[i-1])
            curr_top = min(c.bbox[1] for c in lines[i])
            gaps.append(curr_top - prev_bottom)
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        min_gap = min(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0
    else:
        avg_gap = min_gap = max_gap = 0
    
    # Recommendations
    recommendations = []
    if len(lines) == 1 and len(characters) > 10:
        recommendations.append(
            "Consider increasing line_threshold_ratio (e.g., 0.4) - "
            "all characters grouped into single line"
        )
    if len(lines) > len(characters) * 0.8:
        recommendations.append(
            "Consider decreasing line_threshold_ratio (e.g., 0.2) - "
            "too many lines detected"
        )
    
    return {
        "num_lines": len(lines),
        "avg_line_length": avg_line_length,
        "avg_gap": avg_gap,
        "min_gap": min_gap,
        "max_gap": max_gap,
        "recommendations": recommendations,
    }


def analyze_break_detection(
    fused_lines: List[List],
    line_break_gap_ratio: float = 0.5,
    para_break_gap_ratio: float = 2.0
) -> Dict[str, any]:
    """
    Analyze break detection results and provide tuning recommendations.
    
    Args:
        fused_lines: List of fused lines
        line_break_gap_ratio: Current line break gap ratio
        para_break_gap_ratio: Current paragraph break gap ratio
        
    Returns:
        Analysis results with recommendations
    """
    break_markers = detect_line_breaks(fused_lines, line_break_gap_ratio, para_break_gap_ratio)
    
    # Count break types
    num_none = sum(1 for m in break_markers if m == BREAK_NONE)
    num_line = sum(1 for m in break_markers if m == BREAK_LINE)
    num_para = sum(1 for m in break_markers if m == BREAK_PARAGRAPH)
    
    # Calculate gaps
    if len(fused_lines) > 1:
        gaps = []
        for i in range(1, len(fused_lines)):
            prev_bottom = max(c.bbox[3] for c in fused_lines[i-1])
            curr_top = min(c.bbox[1] for c in fused_lines[i])
            gaps.append(curr_top - prev_bottom)
        
        avg_char_height = calculate_avg_char_height(fused_lines)
        line_break_gap = avg_char_height * line_break_gap_ratio
        para_break_gap = avg_char_height * para_break_gap_ratio
        
        gaps_below_line_threshold = sum(1 for g in gaps if g < line_break_gap)
        gaps_between_thresholds = sum(1 for g in gaps if line_break_gap <= g < para_break_gap)
        gaps_above_para_threshold = sum(1 for g in gaps if g >= para_break_gap)
    else:
        gaps = []
        gaps_below_line_threshold = gaps_between_thresholds = gaps_above_para_threshold = 0
    
    # Recommendations
    recommendations = []
    if num_para == 0 and len(fused_lines) > 3:
        recommendations.append(
            f"Consider decreasing para_break_gap_ratio (e.g., {para_break_gap_ratio * 0.8:.2f}) - "
            "no paragraph breaks detected in multi-line document"
        )
    if num_line == 0 and len(fused_lines) > 1:
        recommendations.append(
            f"Consider decreasing line_break_gap_ratio (e.g., {line_break_gap_ratio * 0.8:.2f}) - "
            "no line breaks detected"
        )
    if num_para > len(fused_lines) * 0.5:
        recommendations.append(
            f"Consider increasing para_break_gap_ratio (e.g., {para_break_gap_ratio * 1.2:.2f}) - "
            "too many paragraph breaks detected"
        )
    
    return {
        "num_breaks": {
            "none": num_none,
            "line": num_line,
            "paragraph": num_para,
        },
        "gap_statistics": {
            "below_line_threshold": gaps_below_line_threshold,
            "between_thresholds": gaps_between_thresholds,
            "above_para_threshold": gaps_above_para_threshold,
        },
        "recommendations": recommendations,
    }


def generate_tuning_report(
    config: DPParameterConfig,
    line_analysis: Dict[str, any],
    break_analysis: Dict[str, any]
) -> str:
    """
    Generate a human-readable tuning report.
    
    Args:
        config: Current parameter configuration
        line_analysis: Line grouping analysis results
        break_analysis: Break detection analysis results
        
    Returns:
        Formatted report string
    """
    report = []
    report.append("=" * 70)
    report.append("DP ALIGNMENT PARAMETER TUNING REPORT")
    report.append("=" * 70)
    report.append("")
    
    report.append("CURRENT PARAMETERS:")
    report.append(f"  Line threshold ratio: {config.line_threshold_ratio}")
    report.append(f"  Line break gap ratio: {config.line_break_gap_ratio}")
    report.append(f"  Paragraph break gap ratio: {config.para_break_gap_ratio}")
    report.append(f"  IoU threshold: {config.iou_threshold}")
    report.append(f"  Skip penalty: {config.skip_penalty}")
    report.append("")
    
    report.append("LINE GROUPING ANALYSIS:")
    report.append(f"  Number of lines detected: {line_analysis['num_lines']}")
    report.append(f"  Average line length: {line_analysis['avg_line_length']:.1f} characters")
    if line_analysis['avg_gap'] > 0:
        report.append(f"  Average gap between lines: {line_analysis['avg_gap']:.1f}px")
        report.append(f"  Gap range: {line_analysis['min_gap']:.1f}px - {line_analysis['max_gap']:.1f}px")
    report.append("")
    
    if line_analysis['recommendations']:
        report.append("LINE GROUPING RECOMMENDATIONS:")
        for rec in line_analysis['recommendations']:
            report.append(f"  - {rec}")
        report.append("")
    
    report.append("BREAK DETECTION ANALYSIS:")
    breaks = break_analysis['num_breaks']
    report.append(f"  No break: {breaks['none']}")
    report.append(f"  Line breaks: {breaks['line']}")
    report.append(f"  Paragraph breaks: {breaks['paragraph']}")
    report.append("")
    
    if break_analysis['recommendations']:
        report.append("BREAK DETECTION RECOMMENDATIONS:")
        for rec in break_analysis['recommendations']:
            report.append(f"  - {rec}")
        report.append("")
    
    report.append("=" * 70)
    
    return "\n".join(report)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point for parameter tuning utility."""
    parser = argparse.ArgumentParser(
        description="Tune DP alignment parameters for reading order fix"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to parameter configuration JSON file"
    )
    parser.add_argument(
        "--save-config",
        type=str,
        help="Path to save tuned configuration"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Load or create default config
    if args.config:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
        config = DPParameterConfig.from_dict(config_data)
        logger.info(f"Loaded configuration from {args.config}")
    else:
        config = DPParameterConfig()
        logger.info("Using default configuration")
    
    # Print current configuration
    print("\nCurrent DP Alignment Parameters:")
    print(json.dumps(config.to_dict(), indent=2))
    
    # Save configuration if requested
    if args.save_config:
        with open(args.save_config, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        logger.info(f"Saved configuration to {args.save_config}")
    
    print("\nNote: Use this utility with actual OCR results to get tuning recommendations.")
    print("Run tests/test_dp_alignment_phase5.py to validate parameter settings.")


if __name__ == "__main__":
    main()

