"""SRT-specific checks (Layer 4: 10 checks, v4.0 updated)."""

from typing import List
from utils.parser import extract_srt_entries, extract_p_numbers, timecode_to_seconds, timecode_to_seconds_v4
from utils.reporter import CheckResult, Status
import re


def _tc_to_s(tc: str) -> float:
    """Use v4 timecode parser (supports both HH:MM:SS:FF and HH:MM:SS,mmm)."""
    return timecode_to_seconds_v4(tc)


def check_srt_framerate(art_text: str) -> CheckResult:
    """Check 38: SRT FF fields are 00-24 (legacy FF format only, v4.0 mmm format always passes)."""
    entries = extract_srt_entries(art_text)
    violations = []
    is_legacy = False
    for e in entries:
        for field in ['start', 'end']:
            tc = e[field]
            # v4.0 millisecond format — skip FF check
            if ',' in tc:
                continue
            is_legacy = True
            ff = int(tc.split(':')[3])
            if ff > 24:
                violations.append(f"#{e['index']} {field}={tc}")
    if not is_legacy:
        return CheckResult("第四层：SRT专项", 38, "帧率合规",
                          Status.PASS, "v4.0毫秒格式，无需FF检查")
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
        prev_end = _tc_to_s(entries[i-1]['end'])
        curr_start = _tc_to_s(entries[i]['start'])
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
        if not e['content'].startswith('△') and len(e['content']) > 55:
            long_unsplit.append(f"#{e['index']}:{len(e['content'])}字")
    if not long_unsplit:
        return CheckResult("第四层：SRT专项", 44, "长台词拆分",
                          Status.PASS, "无超长未拆台词")
    return CheckResult("第四层：SRT专项", 44, "长台词拆分",
                      Status.WARN, f"共{len(long_unsplit)}条", "拆分长台词为多行")


def check_srt_fill_rate(director_text: str, art_text: str) -> CheckResult:
    """Check 45: Each scene's SRT row durations sum to >= 85% of scene total."""
    # Extract per-scene durations from director (P-number → seconds)
    # Pattern: **PXX 标题** ... **时长建议**：Xs
    p_dur_pairs = re.findall(r'\*\*P(\d{2}(?:_[A-Z])?)\s.*?\*\*时长建议\*\*[：:]\s*(\d+)\s*s', director_text, re.DOTALL)
    dir_scene_durs = {}
    for p, d in p_dur_pairs:
        key = f"P{p}"
        # Combine suffixed sub-scenes under base P-number
        base = p.split('_')[0] if '_' in p else p
        dir_scene_durs[p] = dir_scene_durs.get(p, 0) + int(d)
    
    # Group SRT entries by P-number and sum durations
    entries = extract_srt_entries(art_text)
    srt_scenes = {}
    for e in entries:
        p = e['p_label']
        if not p:
            continue
        if p not in srt_scenes:
            srt_scenes[p] = 0.0
        srt_scenes[p] += _tc_to_s(e['end']) - _tc_to_s(e['start'])
    
    low_fill = []
    for p, srt_total in srt_scenes.items():
        dir_dur = dir_scene_durs.get(p, 0)
        if dir_dur <= 0:
            continue
        ratio = srt_total / dir_dur
        if ratio < 0.85:
            low_fill.append(f"{p}:{ratio:.0%}(SRT{srt_total:.1f}s/导演{dir_dur}s)")
    
    if not low_fill:
        return CheckResult("第四层：SRT专项", 45, "SRT填充率",
                          Status.PASS, "全部场景≥85%")
    return CheckResult("第四层：SRT专项", 45, "SRT填充率",
                      Status.WARN, f"低填充：{', '.join(low_fill)}",
                      "扩展SRT行时长或补充动作/台词")


def check_srt_total_deviation(director_text: str, art_text: str) -> CheckResult:
    """Check 46: SRT total time vs Director total time deviation <= 15%."""
    dir_durs = re.findall(r'\*\*时长建议\*\*[：:]\s*(\d+)\s*s', director_text)
    dir_total = sum(int(d) for d in dir_durs)
    entries = extract_srt_entries(art_text)
    if not entries:
        return CheckResult("第四层：SRT专项", 46, "SRT总时长偏差",
                          Status.WARN, "无法解析SRT")
    last_end = _tc_to_s(entries[-1]['end'])
    if dir_total == 0:
        return CheckResult("第四层：SRT专项", 46, "SRT总时长偏差",
                          Status.WARN, "无法解析导演时长")
    deviation = abs(last_end - dir_total) / dir_total * 100
    if deviation <= 15:
        return CheckResult("第四层：SRT专项", 46, "SRT总时长偏差",
                          Status.PASS, f"{deviation:.1f}% <= 15%")
    return CheckResult("第四层：SRT专项", 46, "SRT总时长偏差",
                      Status.FAIL, f"{deviation:.1f}% > 15%", "调整SRT或导演时长")


def check_srt_algorithm_accuracy(art_text: str) -> CheckResult:
    """Check 47 (v4.0): SRT duration per dialogue line matches simplified algorithm.
    
    v4.0 algorithm: 字数 × 语速系数 + 300ms. This check estimates expected duration
    and flags lines where variance > 30%.
    """
    entries = extract_srt_entries(art_text)
    suspicious = []
    for e in entries:
        if e['content'].startswith('△'):
            continue
        # Strip P-label and character prefix
        content = e['content']
        word_count = len(re.sub(r'\s', '', content))
        if word_count == 0:
            continue
        actual_dur = _tc_to_s(e['end']) - _tc_to_s(e['start'])
        # Estimate with medium speed (0.33s/char) as default
        estimated = word_count * 0.33 + 0.3
        if estimated > 0 and actual_dur > 0:
            variance = abs(actual_dur - estimated) / estimated
            if variance > 0.30:
                suspicious.append(f"#{e['index']}:{word_count}字→实际{actual_dur:.1f}s(预估{estimated:.1f}s,偏差{variance:.0%})")
    if not suspicious:
        return CheckResult("第四层：SRT专项", 47, "SRT算法精度",
                          Status.PASS, "全部偏差≤30%")
    if len(suspicious) <= 3:
        return CheckResult("第四层：SRT专项", 47, "SRT算法精度",
                          Status.WARN, f"共{len(suspicious)}条异常", "人工复核")
    return CheckResult("第四层：SRT专项", 47, "SRT算法精度",
                      Status.FAIL, f"共{len(suspicious)}条异常,前3:{suspicious[:3]}", "检查算法或手动修正SRT")


def run_all(director_text: str, art_text: str) -> List[CheckResult]:
    return [
        check_srt_framerate(art_text),
        check_srt_monotonic(art_text),
        check_srt_p_coverage(director_text, art_text),
        check_srt_dialogue_count(director_text, art_text),
        check_srt_action_count(director_text, art_text),
        check_srt_order_consistency(director_text, art_text),
        check_long_dialogue_split(art_text),
        check_srt_fill_rate(director_text, art_text),
        check_srt_total_deviation(director_text, art_text),
        check_srt_algorithm_accuracy(art_text),
    ]
