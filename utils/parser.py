"""Parser: extract structured data from LLM-generated pipeline output text."""

import re
import uuid
from typing import List, Dict, Optional, Set, Tuple


def generate_session_id() -> str:
    """Generate a unique session ID for file isolation in concurrent pipeline runs.
    
    Production orchestrators must use this (or equivalent) to avoid multiple users
    overwriting each other's story.txt / director.txt / art.txt / cine.txt files.
    All intermediate files should be stored as {session_id}_story.txt etc.
    """
    return uuid.uuid4().hex[:12]


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
    matches = re.findall(r'\*\*时长建议\*\*[：:]\s*(\d+(?:\.\d+)?)\s*s', text)
    return [int(float(m)) for m in matches]


def extract_at_images(text: str) -> List[int]:
    """Extract all @图片N numbers (supports both simplified and traditional)."""
    matches = re.findall(r'@[图圖]片(\d+)', text)
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
    """Parse SRT entries. Supports both legacy (HH:MM:SS:FF) and v4.0 (HH:MM:SS,mmm) formats."""
    # SRT format: number\nHH:MM:SS:FF or HH:MM:SS,mmm --> HH:MM:SS:FF or HH:MM:SS,mmm\n[PXX] content
    tc_v4 = r'\d{2}:\d{2}:\d{2},\d{3}'
    tc_legacy = r'\d{2}:\d{2}:\d{2}:\d{2}'
    tc_any = f'(?:{tc_v4}|{tc_legacy})'
    pattern = rf'(\d+)\n({tc_any})\s*-->\s*({tc_any})\n(?:\[(P\d{{2}}(?:_[A-Z])?)\]\s*)?(.+?)(?=\n\d+\n|\(\s*总时长校验|\Z)'
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
    return timecode_to_seconds_v4(tc)


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


def timecode_to_seconds(tc: str) -> float:
    """Convert HH:MM:SS:FF to seconds (25fps)."""
    parts = tc.split(':')
    h = int(parts[0])
    m = int(parts[1])
    s = int(parts[2])
    f = int(parts[3])
    return h * 3600 + m * 60 + s + f / 25.0


def extract_image_ranges(text: str) -> dict:
    """Extract @图片 range boundaries from @编号体系总览 table.
    Returns dict with 'actor_end', 'scene_start', 'scene_end', 'prop_start'.
    Defaults to (4, 5, 20, 21) if table not found."""
    defaults = {'actor_end': 4, 'scene_start': 5, 'scene_end': 20, 'prop_start': 21}
    section = _find_table_section(text, '@编号体系总览')
    if not section:
        return defaults
    rows = _parse_md_table(section)
    result = {}
    for row in rows:
        category = row.get('资产类别', '')
        range_str = row.get('@编号范围', '')
        nums = re.findall(r'@[图圖]片(\d+)', range_str)
        if len(nums) >= 2:
            lo, hi = int(nums[0]), int(nums[-1])
        elif len(nums) == 1:
            lo = hi = int(nums[0])
        else:
            continue
        if '演员' in category:
            result['actor_end'] = hi
        elif '场景' in category:
            result['scene_start'] = lo
            result['scene_end'] = hi
        elif '道具' in category:
            result['prop_start'] = lo
    # Merge with defaults for any missing keys
    for k, v in defaults.items():
        if k not in result:
            result[k] = v
    return result


# --- Shared constants ---

APPEARANCE_CATEGORIES = {
    '发型/发色': ['发', '髻', '辫', '寸头', '短发', '长发', '马尾', '刘海', '秃'],
    '服装/衣着': ['袍', '衣', '服', '装', '甲', '裤', '靴', '鞋', '裙', '衫', '褂', '夹克', 'T恤'],
    '体型/身高': ['体型', '瘦', '胖', '壮', '高', '矮', '精悍', '敦实', '匀称', 'cm'],
    '面容/五官': ['脸', '眼', '眉', '鼻', '唇', '嘴', '面容', '五官', '瞳'],
    '识别标记': ['疤', '痕', '痣', '胎记', '纹身', '雀斑', '痘印', '缺', '伤'],
    '肤色/肤质': ['肤', '白', '黑', '黄', '小麦', '古铜', '苍白', '粗糙', '光滑'],
    '配饰/道具': ['剑', '符', '袋', '令', '珠', '环', '镜', '扇', '刀'],
    '形态/构造（非人）': ['甲壳', '复肢', '复眼', '触手', '胶状', '半透明', '骨刺', '口器', '翅膀', '鳞片', '节肢', '几丁质', '悬浮', '无固定形态',
                     '金属', '机械', '义眼', '义肢', '镜头', '数据', '全息', '能量', '光幕'],
    '体量/尺度（非人）': ['三米', '巨型', '球体', '两米', '直径', '米高'],
    '颜色/光学（非人）': ['暗红', '暗褐', '暗紫', '淡紫', '冷蓝', '淡金', '荧光', '微光', '透明', '半透明', '生物光泽', '星云', '流光', '脉冲', '闪烁'],
}


# --- v4.0 JSON parsing utilities ---

import json as _json

def extract_json_block(text: str, label: Optional[str] = None) -> Optional[dict]:
    """Extract the first ```json code block from text and parse it.
    
    If label is provided, searches for a block preceded by that label (e.g. 'scenes_metadata').
    Returns parsed dict on success, None on failure (missing block / parse error).
    """
    # Try labeled block first
    if label:
        pattern = rf'{re.escape(label)}.*?\n```json\s*\n(.*?)\n```'
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return _json.loads(m.group(1))
            except _json.JSONDecodeError:
                pass

    # Fallback: any ```json block
    m = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if m:
        try:
            return _json.loads(m.group(1))
        except _json.JSONDecodeError:
            pass
    return None


def extract_id_mapping(text: str) -> dict:
    """Extract @编号↔ID mapping table from art director output.
    
    Returns dict with keys:
        'image_map': {int: {'type': str, 'id': str, 'name': str}}
        'audio_map': {int: {'id': str, 'name': str}}
    Empty dicts if JSON not found.
    """
    mapping = extract_json_block(text, label='@image_mapping')
    result = {'image_map': {}, 'audio_map': {}}
    
    if mapping and '@image_mapping' in mapping:
        for item in mapping['@image_mapping']:
            num = int(item.get('@image', '').replace('@图片', ''))
            result['image_map'][num] = {
                'type': item.get('type', ''),
                'id': item.get('id', ''),
                'name': item.get('name', ''),
            }
    
    if mapping and '@audio_mapping' in mapping:
        for item in mapping['@audio_mapping']:
            num = int(item.get('@audio', '').replace('@音频', ''))
            result['audio_map'][num] = {
                'id': item.get('id', ''),
                'name': item.get('name', ''),
            }
    
    return result


def extract_state_snapshot(text: str) -> Optional[dict]:
    """Extract story agent's 章末状态快照 JSON."""
    return extract_json_block(text, label='chapter')


def timecode_to_seconds_v4(tc: str) -> float:
    """Convert timecode to seconds, supporting both legacy FF (25fps) and v4.0 millisecond formats.
    
    HH:MM:SS:FF  → legacy frame format, FF ÷ 25
    HH:MM:SS,mmm → v4.0 millisecond format, mmm ÷ 1000
    """
    # Try millisecond format first (v4.0)
    m = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', tc)
    if m:
        h, mi, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        return h * 3600 + mi * 60 + s + ms / 1000.0
    
    # Fallback to legacy FF format
    parts = tc.split(':')
    h = int(parts[0])
    mi = int(parts[1])
    s = int(parts[2])
    f = int(parts[3])
    return h * 3600 + mi * 60 + s + f / 25.0


# --- v4.0 API retry utility (for future Orchestrator use) ---

import time as _time

def retry_with_backoff(func, max_retries=5, base_delay=2.0, max_delay=60.0):
    """Exponential backoff retry wrapper for LLM API calls.
    
    Handles transient failures common with LLM APIs:
    - 429 Rate Limit Exceeded
    - 503 Service Unavailable
    - Network timeouts / Connection errors
    
    Delay progression: 2s → 4s → 8s → 16s → 32s (capped at max_delay).
    After max_retries, re-raises the last exception.
    
    Usage:
        result = retry_with_backoff(lambda: openai.chat.completions.create(...))
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                break
            delay = min(base_delay * (2 ** attempt), max_delay)
            _time.sleep(delay)
    raise last_exception
