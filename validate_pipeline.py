#!/usr/bin/env python3
"""Comic Pipeline Validator - Main Entry Point.

Usage:
    python validate_pipeline.py <story.txt> <director.txt> <art.txt> <cine.txt>
    
    Or read from stdin if files are piped:
    cat output.txt | python validate_pipeline.py --stdin

Reads the 4 Agent pipeline outputs and runs 46 deterministic checks
across 4 layers: single-file structure, cross-file cross-reference,
fatal propagation chains, and SRT-specific checks.
"""

import sys
import os
from datetime import datetime
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import single_file, cross_file, propagation, srt_checks
from utils.reporter import ValidationReport, format_report, format_json


def read_file(path: str) -> str:
    """Read file with encoding fallback."""
    for enc in ['utf-8', 'gbk', 'utf-8-sig']:
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot read file {path} with any encoding")


def parse_stdin_input(text: str) -> tuple:
    """Parse pipeline output from a single concatenated text.
    Splits on Agent boundary markers."""
    # Try to detect individual agent outputs
    story = director = art = cine = ""
    
    # Look for agent markers
    story_markers = ['故事创作Agent', '故事蓝图', '第1章', '第1章：']
    dir_markers = ['导演', '分场剧本', '**P01']
    art_markers = ['美术指导', 'S1：演员定妆', '@图片1']
    cine_markers = ['分镜师', '素材对应表', 'Seedance', '视频提示词']
    
    lines = text.split('\n')
    current = None
    buffers = {'story': [], 'director': [], 'art': [], 'cine': []}
    
    for line in lines:
        # Detect agent switches
        if any(m in line for m in story_markers) and not any(m in line for m in dir_markers + art_markers + cine_markers):
            if '故事创作' in line or '故事蓝图' in line:
                current = 'story'
        if any(m in line for m in dir_markers) and '导演' in line:
            if '美术指导' not in line:
                current = 'director'
        if any(m in line for m in art_markers) and '美术指导' in line:
            current = 'art'
        if any(m in line for m in cine_markers) and '分镜师' in line:
            current = 'cine'
        
        if current:
            buffers[current].append(line)
    
    story = '\n'.join(buffers['story']) if buffers['story'] else text
    director = '\n'.join(buffers['director']) if buffers['director'] else text
    art = '\n'.join(buffers['art']) if buffers['art'] else text
    cine = '\n'.join(buffers['cine']) if buffers['cine'] else text
    
    return story, director, art, cine


def run_validation(story_text: str, director_text: str, art_text: str, cine_text: str,
                   style: str = "CG国漫", chapter: str = "第1章") -> ValidationReport:
    """Run all 46 checks and return ValidationReport object."""
    report = ValidationReport(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        style=style,
        chapter=chapter,
    )
    
    # Layer 1: Single-file structure (13 checks)
    for r in single_file.run_all(story_text, director_text, art_text, cine_text):
        report.results.append(r)
    
    # Layer 2: Cross-file cross-reference (20 checks)
    for r in cross_file.run_all(story_text, director_text, art_text, cine_text):
        report.results.append(r)
    
    # Layer 3: Fatal propagation chains (4 checks)
    for r in propagation.run_all(story_text, director_text, art_text, cine_text):
        report.results.append(r)
    
    # Layer 4: SRT-specific (9 checks)
    for r in srt_checks.run_all(director_text, art_text):
        report.results.append(r)
    
    return report


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    json_mode = '--json' in sys.argv
    
    if len(args) >= 4:
        # File mode: 4 file paths
        story_text = read_file(args[0])
        director_text = read_file(args[1])
        art_text = read_file(args[2])
        cine_text = read_file(args[3])
    elif '--stdin' in sys.argv or len(args) == 0:
        # Stdin mode: read concatenated pipeline output
        text = sys.stdin.read()
        story_text, director_text, art_text, cine_text = parse_stdin_input(text)
    else:
        print("Usage: python validate_pipeline.py [--json] <story.txt> <director.txt> <art.txt> <cine.txt>")
        print("   or: cat pipeline_output.txt | python validate_pipeline.py --stdin [--json]")
        sys.exit(1)
    
    report = run_validation(story_text, director_text, art_text, cine_text)
    
    if json_mode:
        print(format_json(report))
    else:
        print(format_report(report))


if __name__ == '__main__':
    main()
