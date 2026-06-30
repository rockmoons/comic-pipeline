"""Fatal propagation chain checks (Layer 3: 4 checks)."""

from typing import List
import re
from utils.parser import (
    extract_actor_table, extract_scene_table,
    extract_p_numbers, extract_dialogue_cues,
    extract_voice_table, extract_base_image_refs,
    extract_scene_grid_names, APPEARANCE_CATEGORIES,
)
from utils.reporter import CheckResult, Status


def check_chain_a_appearance_loss(story_text: str, director_text: str) -> CheckResult:
    """Chain A: Story actor appearance keywords < 3 → Director < 3 → FATAL."""
    story_table = extract_actor_table(story_text)
    dir_table = extract_actor_table(director_text)
    categories = APPEARANCE_CATEGORIES
    # Check story table
    story_weak = []
    for row in story_table:
        name = row.get('演员', '')
        keywords = row.get('外观关键词', '')
        matched = sum(1 for cat, keys in categories.items() if any(k in keywords for k in keys))
        if matched < 3:
            story_weak.append(f"{name}({matched}类)")
    # Check director table
    dir_weak = []
    for row in dir_table:
        name = row.get('演员', '')
        keywords = row.get('外观关键词', '')
        matched = sum(1 for cat, keys in categories.items() if any(k in keywords for k in keys))
        if matched < 3:
            dir_weak.append(f"{name}({matched}类)")
    if not story_weak and not dir_weak:
        return CheckResult("第三层：传播链检测", 34, "链A:外观丢失",
                          Status.PASS, "外观信息充足")
    msgs = []
    if story_weak:
        msgs.append(f"故事创作外观不足：{', '.join(story_weak)}")
    if dir_weak:
        msgs.append(f"导演外观不足：{', '.join(dir_weak)}")
    if story_weak and dir_weak:
        return CheckResult("第三层：传播链检测", 34, "链A:外观丢失",
                          Status.FATAL, '；'.join(msgs),
                          "角色外观信息从故事创作到导演持续不足，S1定妆将严重依赖推断")
    return CheckResult("第三层：传播链检测", 34, "链A:外观丢失",
                      Status.WARN, '；'.join(msgs))


def check_chain_b_p_number_gap(director_text: str, art_text: str) -> CheckResult:
    """Chain B: Director P-number gap → Art S6 doesn't cover → FATAL."""
    dir_pnums = set(extract_p_numbers(director_text))
    # Check director for gaps
    base_nums = sorted(set(int(p[1:3]) for p in dir_pnums))
    expected = list(range(base_nums[0], base_nums[-1] + 1))
    dir_missing = [n for n in expected if n not in base_nums]
    # Check SRT coverage
    srt_pnums = set()
    for m in re.finditer(r'\[(P\d{2}(?:_[A-Z])?)\]', art_text):
        srt_pnums.add(m.group(1))
    srt_base = sorted(set(int(p[1:3]) for p in srt_pnums))
    srt_expected = list(range(srt_base[0], srt_base[-1] + 1)) if srt_base else []
    srt_missing = [n for n in srt_expected if n not in srt_base]
    if not dir_missing and not srt_missing:
        return CheckResult("第三层：传播链检测", 35, "链B:P编号跳跃",
                          Status.PASS, "P编号连续，SRT覆盖完整")
    msgs = []
    if dir_missing:
        msgs.append(f"导演P编号跳跃：缺P{dir_missing}")
    if srt_missing:
        msgs.append(f"SRT未覆盖：缺P{srt_missing}")
    return CheckResult("第三层：传播链检测", 35, "链B:P编号跳跃",
                      Status.FATAL, '；'.join(msgs),
                      "缺失场景已永久丢失！补全P编号并重新生成下游")


def check_chain_c_cross_scene_base(art_text: str) -> CheckResult:
    """Chain C: Grid base image belongs to different scene → FATAL."""
    refs = extract_base_image_refs(art_text)
    grid_scene_map = {}
    for num, name in extract_scene_grid_names(art_text):
        base_scene = name.split('-')[0].strip()
        grid_scene_map[num] = base_scene
    fatal_violations = []
    for grid_num, base_num in refs:
        grid_scene = grid_scene_map.get(grid_num, '?')
        base_scene = grid_scene_map.get(base_num, '?')
        if grid_scene != base_scene and base_scene != '?' and grid_scene != '?':
            fatal_violations.append(f"格{grid_num}({grid_scene})垫图@图片{base_num}({base_scene})")
    if not fatal_violations:
        return CheckResult("第三层：传播链检测", 36, "链C:底图跨场景",
                          Status.PASS, "无跨场景底图")
    return CheckResult("第三层：传播链检测", 36, "链C:底图跨场景",
                      Status.FATAL, '；'.join(fatal_violations),
                      "跨场景垫图导致视觉风格污染！修正底图声明为独立冷启动或更换同场景底图")


def check_chain_d_audio_mismatch(cine_text: str, art_text: str) -> CheckResult:
    """Chain D: Dialogue Cue @音频N role ≠ S5 @音频N role → FATAL."""
    voice_table = extract_voice_table(art_text)
    audio_role_map = {}
    for row in voice_table:
        num_str = row.get('@编号', '')
        role = row.get('角色', '').strip()
        m = re.search(r'@音频(\d+)', num_str)
        if m and role:
            audio_role_map[m.group(1)] = role
    cues = extract_dialogue_cues(cine_text)
    mismatches = []
    for cue in cues:
        expected_role = audio_role_map.get(cue['audio_num'], '')
        if expected_role and expected_role != cue['char_name']:
            mismatches.append(
                f"DialogueCue @音频{cue['audio_num']}({expected_role})标为({cue['char_name']})"
            )
    if not mismatches:
        return CheckResult("第三层：传播链检测", 37, "链D:@音频错配",
                          Status.PASS, "@音频全部正确")
    return CheckResult("第三层：传播链检测", 37, "链D:@音频错配",
                      Status.FATAL, '；'.join(mismatches),
                      "配音将张冠李戴！修正Dialogue Cue的@音频编号")


def run_all(story_text: str, director_text: str, art_text: str, cine_text: str) -> List[CheckResult]:
    return [
        check_chain_a_appearance_loss(story_text, director_text),
        check_chain_b_p_number_gap(director_text, art_text),
        check_chain_c_cross_scene_base(art_text),
        check_chain_d_audio_mismatch(cine_text, art_text),
    ]
