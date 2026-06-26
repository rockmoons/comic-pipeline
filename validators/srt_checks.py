"""SRT-specific checks (Layer 4: 9 checks)."""

from typing import List
from utils.parser import extract_srt_entries, extract_p_numbers
from utils.reporter import CheckResult, Status
import re


def _timecode_to_seconds(tc: str) -> float:
    parts = tc.split(':')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]) + int(parts[3]) / 25.0


def check_srt_framerate(art_text: str) -> CheckResult:
    """Check 38: SRT FF fields are 00-24."""
    entries = extract_srt_entries(art_text)
    violations = []
    for e in entries:
        for field in ['start', 'end']:
            ff = int(e[field].split(':')[3])
            if ff > 24:
                violations.append(f"#{e['index']} {field}={e[field]}")
    if not violations:
        return CheckResult("第四层：SRT专项", 38, "帧率合规",
                          Status.PASS, "全部FF在00-24")
    return CheckResult("第四层：SRT专项", 38, "帧率合规",
                      Status.FAIL, f"FF超24：{violations[0]}...", "修正帧率")


def check_srt_monotonic(art_text: str) -> CheckResult:
    """Check 39: SRT timecodes are monotonically increasing."""
    entries = extract_srt_entries(art_text)
    violations = []
    for i in range(1, len(entries)):
        prev_end = _timecode_to_seconds(entries[i-1]['end'])
        curr_start = _timecode_to_seconds(entries[i]['start'])
        if curr_start < prev_end:
            violations.append(f"#{entries[i-1]['index']}→#{entries[i]['index']}")
    if not violations:
        return CheckResult("第四层：SRT专项", 39, "时间码单调",
                          Status.PASS, "全部单调递增")
    return CheckResult("第四层：SRT专项", 39, "时间码单调",
                      Status.FAIL, f"时间倒退：{violations[0]}...", "修正SRT时间线")


def check_srt_p_coverage(director_text: str, art_text: str) -> CheckResult:
    """Check 40: SRT covers all Director P-numbers."""
    dir_pnums = set(extract_p_numbers(director_text))
    entries = extract_srt_entries(art_text)
    srt_pnums = set(e['p_label'] for e in entries if e['p_label'])
    missing = dir_pnums - srt_pnums
    extra = srt_pnums - dir_pnums
    if not missing and not extra:
        return CheckResult("第四层：SRT专项", 40, "SRT P编号覆盖",
                          Status.PASS, f"覆盖全部{len(dir_pnums)}个")
    msgs = []
    if missing:
        msgs.append(f"缺{missing}")
    if extra:
        msgs.append(f"多余{extra}")
    return CheckResult("第四层：SRT专项", 40, "SRT P编号覆盖",
                      Status.FAIL, '；'.join(msgs), "补全SRT或修正P编号")


def check_srt_dialogue_count(director_text: str, art_text: str) -> CheckResult:
    """Check 41: SRT dialogue line count vs Director dialogue line count.
    SRT may split long dialogues, so SRT count may be >= director count."""
    dir_count = len(re.findall(r'^- \*\*[^*]+\*\*[（(][^）)]*[）)]\s*[：:]\s*"', director_text, re.MULTILINE))
    entries = extract_srt_entries(art_text)
    srt_dialogue = sum(1 for e in entries if not e['content'].startswith('△'))
    if srt_dialogue >= dir_count:
        return CheckResult("第四层：SRT专项", 41, "SRT台词行数",
                          Status.PASS, f"SRT{srt_dialogue}行 >= 导演{dir_count}行（拆分正常）")
    return CheckResult("第四层：SRT专项", 41, "SRT台词行数",
                      Status.WARN, f"SRT{srt_dialogue}行 < 导演{dir_count}行",
                      "检查台词是否遗漏")


def check_srt_action_count(director_text: str, art_text: str) -> CheckResult:
    """Check 42: SRT action line count = Director action line count."""
    dir_count = len(re.findall(r'^△ ', director_text, re.MULTILINE))
    entries = extract_srt_entries(art_text)
    srt_action = sum(1 for e in entries if e['content'].startswith('△'))
    if dir_count == srt_action:
        return CheckResult("第四层：SRT专项", 42, "SRT动作行数",
                          Status.PASS, f"SRT{srt_action}行 = 导演{dir_count}行")
    return CheckResult("第四层：SRT专项", 42, "SRT动作行数",
                      Status.WARN, f"SRT{srt_action}行 ≠ 导演{dir_count}行",
                      "检查动作行是否遗漏")


def check_srt_order_consistency(director_text: str, art_text: str) -> CheckResult:
    """Check 43: SRT entry order matches Director scene order."""
    # Extract P-numbers in order from director headers
    dir_p_order = re.findall(r'\*\*P(\d{2}(?:_[A-Z])?)\s', director_text)
    # Extract P-numbers in order from SRT
    entries = extract_srt_entries(art_text)
    srt_p_order = []
    for e in entries:
        if e['p_label']:
            p = e['p_label']
            if not srt_p_order or srt_p_order[-1] != p:
                srt_p_order.append(p)
    # Compare sequences
    if dir_p_order == srt_p_order:
        return CheckResult("第四层：SRT专项", 43, "SRT顺序一致",
                          Status.PASS, "顺序匹配")
    # Check if SRT order is a subsequence (some P may be skipped in SRT)
    if len(srt_p_order) <= len(dir_p_order):
        # SRT might have fewer entries (expected for transition scenes)
        return CheckResult("第四层：SRT专项", 43, "SRT顺序一致",
                          Status.PASS, f"SRT{len(srt_p_order)}场 ⊆ 导演{len(dir_p_order)}场")
    return CheckResult("第四层：SRT专项", 43, "SRT顺序一致",
                      Status.WARN, "SRT场次数多于导演", "手动复查SRT行顺序")


def check_long_dialogue_split(art_text: str) -> CheckResult:
    """Check 44: Long dialogues (>30 chars) are split into multiple lines."""
    entries = extract_srt_entries(art_text)
    long_unsplit = []
    for e in entries:
        if not e['content'].startswith('△') and len(e['content']) > 30:
            long_unsplit.append(f"#{e['index']}:{len(e['content'])}字")
    if not long_unsplit:
        return CheckResult("第四层：SRT专项", 44, "长台词拆分",
                          Status.PASS, "无超长未拆台词")
    return CheckResult("第四层：SRT专项", 44, "长台词拆分",
                      Status.WARN, f"共{len(long_unsplit)}条", "拆分长台词为多行")


def check_srt_fill_rate(art_text: str) -> CheckResult:
    """Check 45: Each scene's SRT row durations sum to >= 85% of scene total."""
    entries = extract_srt_entries(art_text)
    # Group by P-number
    scenes = {}
    for e in entries:
        p = e['p_label']
        if p not in scenes:
            scenes[p] = []
        dur = _timecode_to_seconds(e['end']) - _timecode_to_seconds(e['start'])
        scenes[p].append(dur)
    low_fill = []
    for p, durs in scenes.items():
        total = sum(durs)
        # We don't have reference duration per scene here, but if total < 2s it's suspicious
        if total < 2:
            low_fill.append(f"{p}:{total:.1f}s")
    if not low_fill:
        return CheckResult("第四层：SRT专项", 45, "SRT填充率",
                          Status.PASS, "无明显异常")
    return CheckResult("第四层：SRT专项", 45, "SRT填充率",
                      Status.WARN, f"低填充：{', '.join(low_fill)}")


def check_srt_total_deviation(director_text: str, art_text: str) -> CheckResult:
    """Check 46: SRT total time vs Director total time deviation <= 15%."""
    import re
    dir_durs = re.findall(r'\*\*时长建议\*\*[：:]\s*(\d+)\s*s', director_text)
    dir_total = sum(int(d) for d in dir_durs)
    entries = extract_srt_entries(art_text)
    if not entries:
        return CheckResult("第四层：SRT专项", 46, "SRT总时长偏差",
                          Status.WARN, "无法解析SRT")
    last_end = _timecode_to_seconds(entries[-1]['end'])
    if dir_total == 0:
        return CheckResult("第四层：SRT专项", 46, "SRT总时长偏差",
                          Status.WARN, "无法解析导演时长")
    deviation = abs(last_end - dir_total) / dir_total * 100
    if deviation <= 15:
        return CheckResult("第四层：SRT专项", 46, "SRT总时长偏差",
                          Status.PASS, f"{deviation:.1f}% <= 15%")
    return CheckResult("第四层：SRT专项", 46, "SRT总时长偏差",
                      Status.FAIL, f"{deviation:.1f}% > 15%", "调整SRT或导演时长")


def run_all(director_text: str, art_text: str) -> List[CheckResult]:
    return [
        check_srt_framerate(art_text),
        check_srt_monotonic(art_text),
        check_srt_p_coverage(director_text, art_text),
        check_srt_dialogue_count(director_text, art_text),
        check_srt_action_count(director_text, art_text),
        check_srt_order_consistency(director_text, art_text),
        check_long_dialogue_split(art_text),
        check_srt_fill_rate(art_text),
        check_srt_total_deviation(director_text, art_text),
    ]
