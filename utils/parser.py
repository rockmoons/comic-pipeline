"""Parser: extract structured data from LLM-generated pipeline output text."""

import re
from typing import List, Dict, Optional, Set, Tuple


def extract_p_numbers(text: str) -> List[str]:
    """Extract all P-numbers from text, e.g. P01, P04_A, P15."""
    matches = re.findall(r'\bP(\d{2}(?:_[A-Z])?)\b', text)
    seen = set()
    result = []
    for m in matches:
        pnum = f"P{m}"
        if pnum not in seen:
            seen.add(pnum)
            result.append(pnum)
    return sorted(result, key=_p_sort_key)


def _p_sort_key(p: str) -> Tuple[int, str]:
    """Sort key for P-numbers: P01 < P01_A < P02."""
    num = int(p[1:3])
    suffix = p[4:] if len(p) > 3 else ''
    return (num, suffix)


def extract_durations(text: str) -> List[int]:
    """Extract duration values only from director's **时长建议** fields (not camera specs)."""
    matches = re.findall(r'\*\*时长建议\*\*[：:]\s*(\d+)\s*s', text)
    return [int(m) for m in matches]


def extract_all_durations(text: str) -> List[int]:
    """Extract ALL duration values (including camera specs, for prompt checks)."""
    matches = re.findall(r'(?:时长\S*\s*[：:]\s*)?(\d+)\s*s', text)
    return [int(m) for m in matches]


def extract_at_images(text: str) -> List[int]:
    """Extract all @图片N numbers."""
    matches = re.findall(r'@图片(\d+)', text)
    return sorted(set(int(m) for m in matches))


def extract_at_audios(text: str) -> List[int]:
    """Extract all @音频N numbers."""
    matches = re.findall(r'@音频(\d+)', text)
    return sorted(set(int(m) for m in matches))


def extract_dialogue_cues(text: str) -> List[Dict[str, str]]:
    """Extract Dialogue Cue lines: returns list of {audio_num, char_name, tone, line}."""
    pattern = r'Dialogue Cue:\s*@音频(\d+)\s*[（(]([^）)]+)[）)]\s*([^：:]+)[：:]\s*"([^"]*)"'
    results = []
    for m in re.finditer(pattern, text):
        results.append({
            'audio_num': m.group(1),
            'char_name': m.group(2).strip(),
            'tone': m.group(3).strip(),
            'line': m.group(4),
        })
    return results


def extract_actor_table(text: str) -> List[Dict[str, str]]:
    """Parse the director's actor table (markdown format). Returns list of actor dicts."""
    # Find the actor table section
    section = _find_table_section(text, '演员表')
    if not section:
        return []
    return _parse_md_table(section)


def extract_scene_table(text: str) -> List[Dict[str, str]]:
    """Parse the director's scene table."""
    section = _find_table_section(text, '场景列表')
    if not section:
        return []
    return _parse_md_table(section)


def extract_art_actor_table(text: str) -> List[Dict[str, str]]:
    """Parse the art director's S1 actor roster table."""
    section = _find_table_section(text, '演员阵容总览')
    if not section:
        return []
    return _parse_md_table(section)


def extract_srt_entries(text: str) -> List[Dict]:
    """Parse SRT entries. Returns list of {index, start, end, p_label, content}."""
    # SRT format: number\nHH:MM:SS:FF --> HH:MM:SS:FF\n[PXX] content
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2}:\d{2})\s*-->\s*(\d{2}:\d{2}:\d{2}:\d{2})\n(?:\[(P\d{2}(?:_[A-Z])?)\]\s*)?(.+?)(?=\n\d+\n|\Z)'
    results = []
    for m in re.finditer(pattern, text, re.DOTALL):
        results.append({
            'index': int(m.group(1)),
            'start': m.group(2),
            'end': m.group(3),
            'p_label': m.group(4) or '',
            'content': m.group(5).strip(),
        })
    return results


def extract_srt_total_duration(text: str) -> Optional[float]:
    """Extract total duration from SRT timecode validation line."""
    m = re.search(r'SRT时间线截止于\[([^\]]+)\]', text)
    if not m:
        return None
    tc = m.group(1)
    return _timecode_to_seconds(tc)


def extract_story_word_count(text: str) -> Optional[int]:
    """Try to extract the chapter word count from story output."""
    # Multiple patterns for word count
    m = re.search(r'字数[：:]\s*约?\s*(\d+)\s*字', text)
    if m: return int(m.group(1))
    m = re.search(r'(\d{3,4})\s*字.*区间', text)
    if m: return int(m.group(1))
    m = re.search(r'正文[约]?\s*(\d{3,4})\s*字', text)
    if m: return int(m.group(1))
    m = re.search(r'[约共]\s*(\d{3,4})\s*字', text)
    if m: return int(m.group(1))
    return None


def extract_scene_grid_names(text: str) -> List[Tuple[int, str]]:
    """Extract scene grid names from art director S3 output.
    Returns list of (image_num, scene_name).
    Only matches grid entries with dash-separated scene-region format."""
    results = []
    # Find the S3 section first - try multiple markers
    s3_start = -1
    for marker in ['场景勘景', 'S3：', '宫格图', 'S3：场景']:
        idx = text.find(marker)
        if idx >= 0:
            s3_start = idx
            break
    search_text = text[s3_start:] if s3_start >= 0 else text
    
    # Match: 格N——[@图片N SceneName-RegionSuffix] format
    # The bracket content may have spaces: [@图片5 雷暴天空-云层深处]
    pattern = r'格\d+——\s*\[@图片(\d+)\s+([^\]]+)\]'
    for m in re.finditer(pattern, search_text):
        num = int(m.group(1))
        name = m.group(2).strip()
        if len(name) >= 3:
            results.append((num, name))
    return results


def extract_base_image_refs(text: str) -> List[Tuple[int, Optional[int]]]:
    """Extract base image references from S3 grid descriptions.
    Returns list of (grid_image_num, base_image_num).
    Parses grid-by-grid to avoid cross-grid matching."""
    results = []
    # Split by grid markers: 格N—— or 格N—
    grid_blocks = re.split(r'\n?(?:格\d+[—–-]{1,2}|格\d+\s*$)', text)
    for block in grid_blocks:
        # For each block, find the grid's @图片N number and any base image ref
        grid_match = re.search(r'\[@图片(\d+)\s', block)
        base_match = re.search(r'以\s*@图片(\d+)\s*作为参考底图', block)
        if grid_match and base_match:
            results.append((int(grid_match.group(1)), int(base_match.group(1))))
    return results


def extract_prop_table(text: str) -> List[Dict[str, str]]:
    """Parse S4 prop table."""
    section = _find_table_section(text, '道具总览')
    if not section:
        return []
    return _parse_md_table(section)


def extract_voice_table(text: str) -> List[Dict[str, str]]:
    """Parse S5 voice library table."""
    section = _find_table_section(text, '音色库')
    if not section:
        return []
    return _parse_md_table(section)


def extract_prompt_durations(text: str) -> List[Tuple[str, int]]:
    """Extract prompt durations paired with P-numbers from 分镜师 output.
    Returns list of (p_label, seconds)."""
    # Pattern: "### PXX ..." then later "**时长**：Xs"
    results = []
    # Find P sections and their durations
    p_blocks = re.split(r'(?:^|\n)(?:##|###)\s*P(\d{2}(?:_[A-Z])?)\s', text)
    for i in range(1, len(p_blocks), 2):
        p_label = f"P{p_blocks[i]}"
        block = p_blocks[i+1] if i+1 < len(p_blocks) else ''
        m = re.search(r'\*\*时长\*\*[：:]\s*(\d+)\s*s', block)
        if m:
            results.append((p_label, int(m.group(1))))
    return results


def extract_style_token_presence(text: str) -> bool:
    """Check if Style Token keywords are present."""
    keywords = ['best quality', 'masterpiece', '8k', 'high detailed']
    return any(kw.lower() in text.lower() for kw in keywords)


def extract_forbidden_words(text: str) -> List[str]:
    """Check for forbidden quality-degrading words."""
    forbidden = [
        'film grain', '胶片颗粒', '失焦', 'imperfect focus',
        '柔焦', '朦胧感', 'hazy', 'blurry background',
    ]
    found = []
    for word in forbidden:
        if word.lower() in text.lower():
            found.append(word)
    return found


# --- Helper functions ---

def _find_table_section(text: str, header: str) -> Optional[str]:
    """Find a markdown table section after a heading."""
    # Find the heading
    idx = text.find(header)
    if idx == -1:
        return None
    # Find the table start after the heading
    rest = text[idx:]
    table_start = rest.find('|')
    if table_start == -1:
        return None
    # Find the table end (first blank line after table rows)
    table_text = rest[table_start:]
    lines = table_text.split('\n')
    table_lines = []
    in_table = False
    for line in lines:
        if line.strip().startswith('|'):
            table_lines.append(line)
            in_table = True
        elif in_table and not line.strip():
            break
        elif in_table and not line.strip().startswith('|'):
            break
    return '\n'.join(table_lines) if table_lines else None


def _parse_md_table(table_text: str) -> List[Dict[str, str]]:
    """Parse a markdown table into list of dicts."""
    lines = [l.strip() for l in table_text.split('\n') if l.strip().startswith('|')]
    if len(lines) < 2:
        return []
    # Header row
    headers = [h.strip() for h in lines[0].split('|')[1:-1]]
    # Skip separator row (lines[1])
    results = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) >= len(headers):
            row = {headers[i]: cells[i] for i in range(len(headers))}
            results.append(row)
    return results


def _timecode_to_seconds(tc: str) -> float:
    """Convert HH:MM:SS:FF to seconds (25fps)."""
    parts = tc.split(':')
    h = int(parts[0])
    m = int(parts[1])
    s = int(parts[2])
    f = int(parts[3])
    return h * 3600 + m * 60 + s + f / 25.0
