"""Single-file structure checks (Layer 1: 13 checks)."""

from typing import List
from utils.parser import (
    extract_p_numbers, extract_durations, extract_at_images,
    extract_story_word_count,
)
from utils.reporter import CheckResult, Status
import re


def check_story_word_count(story_text: str) -> CheckResult:
    """Check 01: Story chapter word count 800-1200."""
    wc = extract_story_word_count(story_text)
    if wc is None:
        return CheckResult("第一层：单文件结构", 1, "正文字数",
                          Status.WARN, f"无法解析字数", "请确认正文是否标注字数")
    if 800 <= wc <= 1200:
        return CheckResult("第一层：单文件结构", 1, "正文字数",
                          Status.PASS, f"{wc}字 [800-1200]")
    return CheckResult("第一层：单文件结构", 1, "正文字数",
                      Status.FAIL, f"{wc}字，超出[800-1200]", "调整字数至区间内")


def check_blueprint_sections(story_text: str) -> CheckResult:
    """Check 02: Story blueprint has all 6 intervals."""
    required = ['开篇引爆', '递进爽点一', '递进爽点二', '递进爽点三', '终极高潮', '收尾钩子']
    missing = [s for s in required if s not in story_text]
    if not missing:
        return CheckResult("第一层：单文件结构", 2, "蓝图6区间",
                          Status.PASS, "齐全")
    return CheckResult("第一层：单文件结构", 2, "蓝图6区间",
                      Status.FAIL, f"缺失：{', '.join(missing)}", "补全缺失区间")


def check_visual_density(story_text: str) -> CheckResult:
    """Check 03: Visual description keyword density >= 3."""
    keywords = ['体积光', '8K', 'C4D', '慢动作', '逆光', '冷暖', '特写', '全景',
                '高精度', '电影级', '光影', '色调', '构图', '镜头']
    count = sum(1 for kw in keywords if kw in story_text)
    if count >= 3:
        return CheckResult("第一层：单文件结构", 3, "视觉描述词密度",
                          Status.PASS, f"{count}处 >= 3")
    return CheckResult("第一层：单文件结构", 3, "视觉描述词密度",
                      Status.WARN, f"{count}处（不足3处）", "需人工复查")


def check_chapter_end_marker(story_text: str) -> CheckResult:
    """Check 04: Chapter has 【第X章 完】 marker."""
    if re.search(r'【第\d+章\s*完】', story_text):
        return CheckResult("第一层：单文件结构", 4, "章末标记",
                          Status.PASS, "含「第X章 完」")
    return CheckResult("第一层：单文件结构", 4, "章末标记",
                      Status.FAIL, "缺失「第X章 完」标记", "补全章末标记")


def check_chapter_title_format(story_text: str) -> CheckResult:
    """Check 05: Chapter title format."""
    if re.search(r'第\d+章[：:]\s*(?:.{4}|.{4}.{4})', story_text):
        return CheckResult("第一层：单文件结构", 5, "章节标题格式",
                          Status.PASS, "格式正确")
    return CheckResult("第一层：单文件结构", 5, "章节标题格式",
                      Status.WARN, "格式可能不匹配", "检查是否为「第X章：标题」")


def check_p_number_continuity(director_text: str) -> CheckResult:
    """Check 06: P-numbers are continuous without gaps."""
    pnums = extract_p_numbers(director_text)
    if not pnums:
        return CheckResult("第一层：单文件结构", 6, "P编号连续性",
                          Status.WARN, "未检测到P编号", "确认导演输出格式")
    # Check base number continuity (ignore suffixes)
    base_nums = sorted(set(int(p[1:3]) for p in pnums))
    expected = list(range(base_nums[0], base_nums[-1] + 1))
    missing = [n for n in expected if n not in base_nums]
    if not missing:
        return CheckResult("第一层：单文件结构", 6, "P编号连续性",
                          Status.PASS, f"{pnums[0]}~{pnums[-1]}，连续无跳跃")
    missing_str = ', '.join(f"P{n:02d}" for n in missing)
    return CheckResult("第一层：单文件结构", 6, "P编号连续性",
                      Status.FAIL, f"缺 {missing_str}", "补全缺失P编号或确认删除")


def check_p_number_count(director_text: str) -> CheckResult:
    """Check 06b: P-number count is 12-20 per chapter."""
    pnums = extract_p_numbers(director_text)
    if not pnums:
        return CheckResult("第一层：单文件结构", 6, "P编号数量",
                          Status.WARN, "未检测到P编号")
    count = len(pnums)
    if 12 <= count <= 20:
        return CheckResult("第一层：单文件结构", 6, "P编号数量",
                          Status.PASS, f"{count}个 [12-20]")
    elif count < 12:
        return CheckResult("第一层：单文件结构", 6, "P编号数量",
                          Status.WARN, f"{count}个（不足12）", "从原文补充被跳过的场景")
    else:
        return CheckResult("第一层：单文件结构", 6, "P编号数量",
                          Status.WARN, f"{count}个（超过20）", "合并相邻同场景场次")


def check_total_duration(director_text: str) -> CheckResult:
    """Check 07: Total duration 50-90s."""
    durations = extract_durations(director_text)
    total = sum(durations)
    if 50 <= total <= 90:
        return CheckResult("第一层：单文件结构", 7, "总时长",
                          Status.PASS, f"{total}s [50-90]")
    elif total < 50:
        return CheckResult("第一层：单文件结构", 7, "总时长",
                          Status.FAIL, f"{total}s（不足50s）", "从原文补充场景")
    else:
        return CheckResult("第一层：单文件结构", 7, "总时长",
                          Status.WARN, f"{total}s（超过90s）", "合并或缩减场次")


def check_transition_count(director_text: str) -> CheckResult:
    """Check 08: Transition/empty shots <= 2."""
    # Count only transition scenes (importance=transition), not the word in other contexts
    count = len(re.findall(r'\*\*重要性\*\*[：:]\s*transition', director_text))
    if count <= 2:
        return CheckResult("第一层：单文件结构", 8, "空镜计数",
                          Status.PASS, f"{count}个 <= 2")
    return CheckResult("第一层：单文件结构", 8, "空镜计数",
                      Status.FAIL, f"{count}个 > 2", "裁撤最次要空镜")


def check_shot_variety(director_text: str) -> CheckResult:
    """Check 09: No 3 consecutive same shot types."""
    shot_types = re.findall(r'景别[：:]\s*(\S+?)(?:→|[（(]|\s|$)', director_text)
    for i in range(len(shot_types) - 2):
        if shot_types[i] == shot_types[i+1] == shot_types[i+2]:
            return CheckResult("第一层：单文件结构", 9, "景别递进",
                              Status.FAIL, f"连续3场{shot_types[i]}", "调整中间场次景别")
    return CheckResult("第一层：单文件结构", 9, "景别递进",
                      Status.PASS, "无连续3场相同景别")


def check_bgm_forbidden(director_text: str) -> CheckResult:
    """Check 10: No BGM/music keywords in sound effects."""
    forbidden = ['BGM', '配乐', '旋律', '背景音乐', '管弦', '钢琴', '竖笛']
    found = [w for w in forbidden if w in director_text]
    if not found:
        return CheckResult("第一层：单文件结构", 10, "音效BGM检测",
                          Status.PASS, "0违规")
    return CheckResult("第一层：单文件结构", 10, "音效BGM检测",
                      Status.FAIL, f"含禁用词：{', '.join(found)}", "替换为物理音源")


def check_cite_start_forbidden(director_text: str) -> CheckResult:
    """Check 11: No [cite_start] tags."""
    if '[cite_start' in director_text:
        return CheckResult("第一层：单文件结构", 11, "cite_start检测",
                          Status.FAIL, "含 [cite_start]", "替换为 [cite: X]")
    return CheckResult("第一层：单文件结构", 11, "cite_start检测",
                      Status.PASS, "未发现")


def check_at_image_continuity(art_text: str) -> CheckResult:
    """Check 12: @图片 numbers are continuous from 1."""
    nums = extract_at_images(art_text)
    if not nums:
        return CheckResult("第一层：单文件结构", 12, "@图片连续性",
                          Status.WARN, "未检测到@图片引用", "确认美术指导输出")
    expected = list(range(1, nums[-1] + 1))
    missing = [n for n in expected if n not in nums]
    if not missing:
        return CheckResult("第一层：单文件结构", 12, "@图片连续性",
                          Status.PASS, f"@图片1~{nums[-1]}，连续")
    return CheckResult("第一层：单文件结构", 12, "@图片连续性",
                      Status.FAIL, f"缺 @图片{missing}", "补全缺失编号")


def check_prompt_count_match(director_text: str, cine_text: str) -> CheckResult:
    """Check 13: Number of prompts = number of P-numbers."""
    pnums = extract_p_numbers(director_text)
    # Count prompt sections in cine output
    prompt_sections = re.findall(r'(?:^|\n)(?:##|###)\s*P\d{2}(?:_[A-Z])?', cine_text)
    if len(prompt_sections) == len(pnums):
        return CheckResult("第一层：单文件结构", 13, "提示词条数",
                          Status.PASS, f"{len(prompt_sections)}条 = {len(pnums)}个P编号")
    return CheckResult("第一层：单文件结构", 13, "提示词条数",
                      Status.FAIL, f"{len(prompt_sections)}条 ≠ {len(pnums)}个P编号",
                      "补全或删除多余提示词")


def check_hidden_agent_split(director_text: str) -> CheckResult:
    """Check D1: Multi-character scenes with passive verbs must split into single-person shots."""
    passive_kw = ['被推', '被泼', '被打', '被拽', '被踢', '被撞', '被拉', '被按', '被扔', '被追']
    # Find all 人物 fields (per scene)
    person_blocks = re.findall(r'\*\*人物\*\*[：:]\s*(.+?)(?=\n\*\*|$)', director_text)
    violations = []
    for i, block in enumerate(person_blocks):
        actors_raw = block.strip()
        scene_text = director_text.split(block)[1][:500] if i < len(person_blocks) else ''
        has_passive = any(kw in scene_text for kw in passive_kw)
        actor_count = len([a for a in actors_raw.split('、') if a.strip() and a.strip() != '无'])
        if has_passive and actor_count < 2:
            violations.append(f"P{actor_count}人+被动动词")
    if not violations:
        return CheckResult("第一层：单文件结构", 14, "隐式施动者拆分",
                          Status.PASS, "无遗漏")
    return CheckResult("第一层：单文件结构", 14, "隐式施动者拆分",
                      Status.WARN, f"可能遗漏：{len(violations)}处", "检查是否需拆分为单人切镜")


def check_black_field_transition(director_text: str) -> CheckResult:
    """Check D2: Time-space jumps must use 黑场 transition."""
    time_jump_kw = ['闪回', '梦境', '预兆', '异空间', '回忆', '穿越', '幻觉', '恍惚']
    scenes = re.split(r'\*\*P\d{2}(?:_[A-Z])?\s', director_text)[1:]
    violations = []
    for scene in scenes:
        has_jump = any(kw in scene for kw in time_jump_kw)
        if has_jump and '**转场**：黑场' not in scene:
            title = scene.split('\n')[0][:20] if scene else '?'
            violations.append(title)
    if not violations:
        return CheckResult("第一层：单文件结构", 15, "黑场规则",
                          Status.PASS, "全部时空跳跃使用黑场")
    return CheckResult("第一层：单文件结构", 15, "黑场规则",
                      Status.WARN, f"未用黑场：{', '.join(violations)}",
                      "时空跳跃场景应使用黑场转场")


def check_cite_completeness(director_text: str) -> CheckResult:
    """Check D3: Every scene's 画面描述 and △ action lines must have [cite: X]."""
    scenes = re.split(r'\*\*P\d{2}(?:_[A-Z])?\s', director_text)[1:]
    missing_cite = []
    missing_action_cite = []
    for scene in scenes:
        title = scene.split('\n')[0][:20] if scene else '?'
        lines = scene.split('\n')
        has_desc = False
        for line in lines:
            if '画面描述' in line or line.strip().startswith('画面描述'):
                has_desc = True
                if '[cite' not in scene:
                    missing_cite.append(title)
                break
        action_lines = [l for l in lines if l.strip().startswith('△')]
        if action_lines and not any('[cite' in a for a in action_lines):
            missing_action_cite.append(title)
    detail_parts = []
    if missing_cite:
        detail_parts.append(f"画面描述缺cite:{len(missing_cite)}场")
    if missing_action_cite:
        detail_parts.append(f"动作行缺cite:{len(missing_action_cite)}场")
    if not detail_parts:
        return CheckResult("第一层：单文件结构", 16, "cite引用完整性",
                          Status.PASS, "全部场景含cite标记")
    return CheckResult("第一层：单文件结构", 16, "cite引用完整性",
                      Status.WARN, '；'.join(detail_parts), "补全[cite: X]标记")


def check_camera_triple(director_text: str) -> CheckResult:
    """Check D4: Every scene's 调度 field must have movement + position + gaze."""
    movement_kw = ['推', '拉', '摇', '移', '跟', '固定', '跟踪', '环绕', '变焦', '俯拍', '仰拍']
    position_kw = ['画左', '画右', '画上', '画下', '画面中央', '画面右侧', '画面左侧']
    gaze_kw = ['视线看向', '目光投向', '正对镜头', '视线紧盯', '视线看向']
    
    scenes = re.split(r'\*\*P\d{2}(?:_[A-Z])?\s', director_text)[1:]
    violations = []
    for scene in scenes:
        title = scene.split('\n')[0][:20] if scene else '?'
        sched_match = re.search(r'调度[：:]\s*(.+?)(?:\||$)', scene)
        if not sched_match:
            continue
        sched = sched_match.group(1)
        has_move = any(kw in sched for kw in movement_kw)
        has_pos = any(kw in sched for kw in position_kw)
        has_gaze = any(kw in sched for kw in gaze_kw)
        missing = []
        if not has_move: missing.append('运镜')
        if not has_pos: missing.append('位置')
        if not has_gaze: missing.append('视线')
        if missing:
            violations.append(f"{title}(缺{','.join(missing)})")
    if not violations:
        return CheckResult("第一层：单文件结构", 17, "调度三要素",
                          Status.PASS, "全部场景三要素齐全")
    return CheckResult("第一层：单文件结构", 17, "调度三要素",
                      Status.WARN, f"缺要素：{'; '.join(violations[:3])}",
                      "补全运镜/画面位置/视线方向")


def check_sound_format(director_text: str) -> CheckResult:
    """Check D5: Sound effects must use correct format (瞬时音 with brackets, 持续音 with Seedance)."""
    scenes = re.split(r'\*\*P\d{2}(?:_[A-Z])?\s', director_text)[1:]
    violations = []
    for scene in scenes:
        title = scene.split('\n')[0][:20] if scene else '?'
        sound_match = re.search(r'\*\*音效\*\*[：:]\s*(.+?)(?=\n\*\*|$)', scene)
        if not sound_match or not sound_match.group(1).strip():
            continue
        sound = sound_match.group(1)
        # Check for 第N秒 forbidden pattern
        if re.search(r'第\d+秒', sound):
            violations.append(f"{title}(含'第X秒')")
            continue
    if not violations:
        return CheckResult("第一层：单文件结构", 18, "音效格式",
                          Status.PASS, "音效格式合规")
    return CheckResult("第一层：单文件结构", 18, "音效格式",
                      Status.WARN, f"格式问题：{'; '.join(violations[:3])}",
                      "删除'第X秒'描述，改用Seedance逻辑词")


def check_p_number_explosion_risk(director_text: str) -> CheckResult:
    """Check 19 (v4.0): P-number count exceeds safe single-pass threshold.
    
    When P-numbers exceed ~30, the downstream Art/Cine agents risk token overflow
    and output truncation. The orchestrator should batch the scenes into groups
    of ~20 before feeding to downstream agents.
    """
    pnums = extract_p_numbers(director_text)
    count = len(pnums)
    if count <= 30:
        return CheckResult("第一层：单文件结构", 19, "分镜数爆炸风险",
                          Status.PASS, f"{count}个 ≤ 30（安全）")
    elif count <= 50:
        return CheckResult("第一层：单文件结构", 19, "分镜数爆炸风险",
                          Status.WARN,
                          f"{count}个 > 30，下游Agent存在Token溢出风险",
                          "【Orchestrator】建议按每20个P编号一组分批次喂给美术和分镜Agent")
    else:
        return CheckResult("第一层：单文件结构", 19, "分镜数爆炸风险",
                          Status.FAIL,
                          f"{count}个 >> 30，单次传递极可能导致下游Agent输出截断",
                          "【Orchestrator】必须启用滑动窗口切片器，分批次传递")


# Run all single-file checks
def run_all(story_text: str, director_text: str, art_text: str, cine_text: str) -> List[CheckResult]:
    results = []
    # Story checks (1-5)
    results.append(check_story_word_count(story_text))
    results.append(check_blueprint_sections(story_text))
    results.append(check_visual_density(story_text))
    results.append(check_chapter_end_marker(story_text))
    results.append(check_chapter_title_format(story_text))
    # Director checks (6-11)
    results.append(check_p_number_continuity(director_text))
    results.append(check_p_number_count(director_text))
    results.append(check_total_duration(director_text))
    results.append(check_transition_count(director_text))
    results.append(check_shot_variety(director_text))
    results.append(check_bgm_forbidden(director_text))
    results.append(check_cite_start_forbidden(director_text))
    # Art check (12)
    results.append(check_at_image_continuity(art_text))
    # Cine check (13)
    results.append(check_prompt_count_match(director_text, cine_text))
    # Director quality checks (D1-D5)
    results.append(check_hidden_agent_split(director_text))
    results.append(check_black_field_transition(director_text))
    results.append(check_cite_completeness(director_text))
    results.append(check_camera_triple(director_text))
    results.append(check_sound_format(director_text))
    results.append(check_p_number_explosion_risk(director_text))
    return results
