#!/usr/bin/env python3
"""Comic Pipeline Validator - Main Entry Point.

Usage:
    python validate_pipeline.py <story.txt> <director.txt> <art.txt> <cine.txt>
    
    Or read from stdin if files are piped:
    cat output.txt | python validate_pipeline.py --stdin

Reads the 4 Agent pipeline outputs and runs deterministic checks
across 4 layers: single-file structure, cross-file cross-reference,
fatal propagation chains, and SRT-specific checks.

v4.0: Added Layer 0 — JSON pre-validation with auto-healing and retry-guard.
"""

import sys
import os
import re
import json as _json
from datetime import datetime
from typing import Optional, List, Tuple

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import single_file, cross_file, propagation, srt_checks
from utils.reporter import ValidationReport, format_report, format_json, CheckResult, Status


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


def _heal_json(text: str) -> str:
    """Attempt to auto-heal common JSON errors from LLM output."""
    # Strip markdown code fence artifacts
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    
    # Step 1: Add missing closing brackets using stack-based tracking
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            stack.append('}')
        elif ch == '[':
            stack.append(']')
        elif ch == '}':
            if stack and stack[-1] == '}':
                stack.pop()
            elif '}' in stack:
                # Interleaved close: find and remove the matching brace
                stack.reverse()
                stack.remove('}')
                stack.reverse()
        elif ch == ']':
            if stack and stack[-1] == ']':
                stack.pop()
            elif ']' in stack:
                stack.reverse()
                stack.remove(']')
                stack.reverse()
    
    # Close in reverse order (inner brackets first)
    text += ''.join(reversed(stack))
    
    # Step 2: Strip trailing commas before closing brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    text = re.sub(r',\s*$', '', text)
    
    return text


def prevalidate_json(story_text: str, director_text: str,
                     art_text: str, cine_text: str) -> Tuple[str, str, str, str, List[CheckResult]]:
    """Layer 0: Pre-validate and self-heal JSON blocks in all agent outputs.
    
    LLMs have a ~0.1% probability of dropping a trailing `}` in JSON blocks.
    This function detects parse failures, attempts auto-healing, and emits
    retry-guard warnings for unfixable cases.
    
    Returns:
        (healed_story, healed_director, healed_art, healed_cine, precheck_results)
    """
    results = []
    healed = {}
    
    agent_labels = [
        ('story', story_text, '故事创作 Agent'),
        ('director', director_text, '导演漫改 Agent'),
        ('art', art_text, '美术资产 Agent'),
        ('cine', cine_text, '分镜生成 Agent'),
    ]
    
    for key, text, label in agent_labels:
        json_blocks = re.findall(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if not json_blocks:
            healed[key] = text
            results.append(CheckResult(
                "第零层：JSON预检", 0, f"{label} JSON",
                Status.PASS, "无JSON block（v3.0兼容模式，纯Markdown传递）"
            ))
            continue
        
        fixed_count = 0
        failed = False
        healed_text = text
        
        for i, block in enumerate(json_blocks):
            try:
                _json.loads(block)
            except _json.JSONDecodeError:
                # Attempt self-healing
                healed_block = _heal_json(block)
                try:
                    _json.loads(healed_block)
                    healed_text = healed_text.replace(block, healed_block, 1)
                    fixed_count += 1
                except _json.JSONDecodeError:
                    failed = True
        
        healed[key] = healed_text
        
        if failed:
            results.append(CheckResult(
                "第零层：JSON预检", 0, f"{label} JSON",
                Status.WARN,
                f"{len(json_blocks)}个block, {fixed_count}个自愈成功, 仍有不可修复项",
                "【Retry-Guard】外部系统应对该Agent输出执行LLM重试（上限3次）。"
                "LLM JSON尾部缺括号属已知低概率事件（~0.1%），重试通常可恢复。"
            ))
        elif fixed_count > 0:
            results.append(CheckResult(
                "第零层：JSON预检", 0, f"{label} JSON",
                Status.PASS,
                f"{len(json_blocks)}个block, {fixed_count}个自愈成功（尾部括号补全）"
            ))
        else:
            results.append(CheckResult(
                "第零层：JSON预检", 0, f"{label} JSON",
                Status.PASS, f"{len(json_blocks)}个block全部合法"
            ))
    
    return healed['story'], healed['director'], healed['art'], healed['cine'], results


def run_validation(story_text: str, director_text: str, art_text: str, cine_text: str,
                   style: str = "CG国漫", chapter: str = "第1章") -> ValidationReport:
    """Run all checks (Layer 0–4) and return ValidationReport object."""
    report = ValidationReport(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        style=style,
        chapter=chapter,
    )
    
    # Layer 0: JSON pre-validation + self-healing (v4.0)
    story_text, director_text, art_text, cine_text, precheck_results = \
        prevalidate_json(story_text, director_text, art_text, cine_text)
    for r in precheck_results:
        report.results.append(r)
    
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
