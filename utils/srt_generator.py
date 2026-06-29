"""SRT Generator (v4.3): Read JSON timestamp data → output standard SRT file.

Usage:
    python utils/srt_generator.py <input.json> [output.srt]
    python utils/srt_generator.py --stdin [output.srt]

Reads §7.3bis JSON block produced by Agent 3 (美术指导) S6 SRT section.
Generates standard SRT with 100% correct zero-padded millisecond timestamps.
"""

import json
import sys
import re
import os
from typing import List, Dict, Optional


def ms_to_srt_timestamp(ms: int) -> str:
    """Convert milliseconds to SRT timestamp format HH:MM:SS,mmm.
    
    Args:
        ms: Integer milliseconds (e.g., 50, 1500, 83500)
    
    Returns:
        SRT timestamp string with zero-padded milliseconds (e.g., '00:00:00,050')
    """
    ms = max(0, ms)
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def validate_entry(entry: dict, index: int) -> List[str]:
    """Validate a single SRT entry. Returns list of error messages."""
    errors = []
    
    # Required fields
    for field in ['p', 'start_ms', 'end_ms', 'type']:
        if field not in entry:
            errors.append(f"Entry #{index}: 缺少必填字段 '{field}'")
    
    if errors:
        return errors
    
    # Type-specific fields
    if entry['type'] == 'dialogue':
        if 'character' not in entry or not entry.get('character'):
            errors.append(f"Entry #{index} ({entry.get('p','?')}): dialogue 类型缺少 'character'")
        if 'line' not in entry or not entry.get('line'):
            errors.append(f"Entry #{index} ({entry.get('p','?')}): dialogue 类型缺少 'line'")
    elif entry['type'] in ('action', 'transition'):
        if 'content' not in entry or not entry.get('content'):
            errors.append(f"Entry #{index} ({entry.get('p','?')}): {entry['type']} 类型缺少 'content'")
    else:
        valid_types = {'action', 'dialogue', 'transition'}
        if entry['type'] not in valid_types:
            errors.append(f"Entry #{index} ({entry.get('p','?')}): 无效 type '{entry['type']}' —— 应为 {valid_types}")
    
    # Time sanity
    if entry['start_ms'] < 0:
        errors.append(f"Entry #{index} ({entry.get('p','?')}): start_ms 不能为负数")
    if entry['end_ms'] <= entry['start_ms']:
        errors.append(f"Entry #{index} ({entry.get('p','?')}): end_ms({entry['end_ms']}) 必须 > start_ms({entry['start_ms']})")
    
    return errors


def validate_continuity(entries: List[dict]) -> List[str]:
    """Validate time continuity between entries."""
    errors = []
    for i in range(len(entries) - 1):
        curr_end = entries[i]['end_ms']
        next_start = entries[i + 1]['start_ms']
        if next_start < curr_end:
            errors.append(
                f"时间重叠: Entry #{i}({entries[i].get('p','?')}) end={curr_end}ms "
                f"> Entry #{i+1}({entries[i+1].get('p','?')}) start={next_start}ms"
            )
    return errors


def generate_srt(entries: List[dict], validate: bool = True) -> str:
    """Generate standard SRT content from structured entries.
    
    Args:
        entries: List of SRT entry dicts with fields:
            p: P-number label
            start_ms: Start time in milliseconds (integer)
            end_ms: End time in milliseconds (integer)
            type: 'action' | 'dialogue' | 'transition'
            content: Text content (for action/transition)
            character: Character name (for dialogue)
            line: Dialogue text (for dialogue)
            tone: Tone word (for dialogue, optional)
        validate: If True, validate entries before generation
    
    Returns:
        Standard SRT string (SRT format) ready for import into editing software.
    
    Raises:
        ValueError: If validation fails and validate=True
    """
    if validate:
        all_errors = []
        for i, entry in enumerate(entries):
            all_errors.extend(validate_entry(entry, i + 1))
        all_errors.extend(validate_continuity(entries))
        if all_errors:
            raise ValueError("SRT 数据校验失败:\n  " + "\n  ".join(all_errors))
    
    lines = []
    for i, entry in enumerate(entries, 1):
        start_ts = ms_to_srt_timestamp(entry['start_ms'])
        end_ts = ms_to_srt_timestamp(entry['end_ms'])
        
        # Build SRT content line
        if entry['type'] == 'dialogue':
            character = entry.get('character', '?')
            line_text = entry.get('line', '')
            content = f"{character}：{line_text}"
        elif entry['type'] == 'transition':
            content = f"△ {entry.get('content', '黑场转场')}"
        else:  # action
            content = f"△ {entry['content']}"
        
        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(content)
        lines.append("")  # blank line between entries
    
    return "\n".join(lines)


def parse_art_srt_json(text: str) -> Optional[List[dict]]:
    """Extract SRT JSON from Agent 3 (美术指导) output.
    
    Searches for the §7.3bis JSON block in the art text.
    
    Args:
        text: Full Agent 3 output text
    
    Returns:
        List of SRT entry dicts, or None if no JSON block found
    """
    # Find JSON block containing "srt" key
    # Pattern: ```json ... ``` with "srt" object
    json_blocks = re.findall(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    
    for block in json_blocks:
        try:
            data = json.loads(block)
            if 'srt' in data and 'entries' in data['srt']:
                return data['srt']['entries']
        except json.JSONDecodeError:
            continue
    
    return None


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    # Read input
    if input_path == '--stdin':
        text = sys.stdin.read()
        entries = parse_art_srt_json(text)
    else:
        if not os.path.exists(input_path):
            print(f"Error: 文件不存在: {input_path}", file=sys.stderr)
            sys.exit(1)
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
        entries = parse_art_srt_json(text)
    
    if entries is None:
        print("Error: 未在输入中找到 §7.3bis SRT JSON block", file=sys.stderr)
        sys.exit(1)
    
    # Generate SRT
    try:
        srt_text = generate_srt(entries)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Output
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_text)
        print(f"✅ SRT 文件已生成: {output_path} ({len(entries)} 条)")
    else:
        print(srt_text)


if __name__ == '__main__':
    main()
