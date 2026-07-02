"""Single-file structure checks (Layer 1: 24 checks, v5.0)."""

from typing import List
from utils.parser import (
    extract_p_numbers, extract_durations, extract_at_images,
    extract_story_word_count, extract_actor_table, extract_image_ranges,
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
    """Check 10: No vague music descriptions in sound effects field (v4.0).
    
    v4.0 allows BGM Cue field with specific musical texture terms.
    This check only flags vague descriptions like '播放动听的音乐'."""
    # Exclude BGM Cue field content from check
    text_without_bgm_cue = re.sub(r'\*\*BGM Cue\*\*[：:].*', '', director_text)
    
    # v4.0: only flag genuinely vague music descriptions, not the BGM Cue header
    vague_patterns = ['播放.*音乐', '响起.*音乐', '此时.*音乐', '动听的音乐']
    found = [w for w in vague_patterns if re.search(w, text_without_bgm_cue)]
    
    if not found:
        return CheckResult("第一层：单文件结构", 10, "音效BGM检测",
                          Status.PASS, "0违规（v4.0: BGM Cue字段允许）")
    return CheckResult("第一层：单文件结构", 10, "音效BGM检测",
                      Status.WARN, f"含模糊音乐描述：{found}",
                      "替换为具体物理音源或使用BGM Cue字段")


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
    nums = [n for n in nums if n < 994]
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


def check_s2b_actor_image_count(art_text: str) -> CheckResult:
    """Check 20 (v4.1): S2a+S2b per actor — @图片 count in actor range = actors × 2."""
    actor_table = extract_actor_table(art_text)
    actor_count = len(actor_table)
    if actor_count == 0:
        return CheckResult("第一层：单文件结构", 20, "S2a+S2b演员@图片数",
                          Status.WARN, "无法解析美术资产演员表", "确认S1演员阵容格式")
    
    ranges = extract_image_ranges(art_text)
    actor_end = ranges.get('actor_end', actor_count * 2)
    
    all_images = extract_at_images(art_text)
    actor_images = [n for n in all_images if n <= actor_end]
    
    expected = actor_count * 2
    actual = len(actor_images)
    
    if actual == expected:
        return CheckResult("第一层：单文件结构", 20, "S2a+S2b演员@图片数",
                          Status.PASS, f"{actual}个 = {actor_count}人×2（S2a+S2b齐全）")
    elif actual < expected:
        missing_count = expected - actual
        return CheckResult("第一层：单文件结构", 20, "S2a+S2b演员@图片数",
                          Status.FAIL, f"{actual}个（缺{missing_count}个——可能漏了S2b）",
                          "检查是否每位演员都有S2a主图+S2b辅视图")
    else:
        extra = actual - expected
        return CheckResult("第一层：单文件结构", 20, "S2a+S2b演员@图片数",
                          Status.WARN, f"{actual}个（多{extra}个——可能有多余@图片）",
                          "检查演员@编号范围是否混杂了非演员资产")


def check_three_block_completeness(cine_text: str) -> CheckResult:
    """Check 21 (v4.1): Each P-number has all three output blocks."""
    pnums = extract_p_numbers(cine_text)
    if not pnums:
        return CheckResult("第一层：单文件结构", 21, "三段式输出完整性",
                          Status.WARN, "未检测到P编号", "确认分镜师输出格式")
    
    missing_blocks = []
    # Split by P-number headers
    sections = re.split(r'(?=\n## P\d{2}(?:_[A-Z])?)', cine_text)
    
    for p in pnums:
        # Find the section for this P-number
        section = ''
        for s in sections:
            if f'## {p}' in s[:20]:
                section = s
                break
        if not section:
            missing_blocks.append(f"{p}:未找到")
            continue
        
        blocks_missing = []
        if '【📋 分镜详情】' not in section:
            blocks_missing.append("分镜详情")
        if '【🎬 Seedance直接输入】' not in section:
            blocks_missing.append("Seedance直接输入")
        if '【🎬 Seedance时间线输入】' not in section:
            blocks_missing.append("Seedance时间线")
        if blocks_missing:
            missing_blocks.append(f"{p}:缺{'/'.join(blocks_missing)}")
    
    if not missing_blocks:
        return CheckResult("第一层：单文件结构", 21, "三段式输出完整性",
                          Status.PASS, f"全部{len(pnums)}条P编号三段齐全")
    return CheckResult("第一层：单文件结构", 21, "三段式输出完整性",
                      Status.FAIL, f"共{len(missing_blocks)}条：{'; '.join(missing_blocks[:3])}",
                      "补全缺失的输出块")


def check_first_frame_continuity(cine_text: str) -> CheckResult:
    """Check 22 (v4.1): P01 has scene-based first frame, P02+ has last-frame continuity."""
    pnums = extract_p_numbers(cine_text)
    if not pnums:
        return CheckResult("第一层：单文件结构", 22, "首帧接力完整性",
                          Status.WARN, "未检测到P编号")
    
    sections = re.split(r'(?=\n## P\d{2}(?:_[A-Z])?)', cine_text)
    violations = []
    
    for p in pnums:
        section = ''
        for s in sections:
            if f'## {p}' in s[:20]:
                section = s
                break
        if not section:
            continue
        
        # Only check Seedance直接输入 blocks
        seedance_block = ''
        m = re.search(r'【🎬 Seedance直接输入】\n(.*?)(?=\n【🎬|$)', section, re.DOTALL)
        if m:
            seedance_block = m.group(1)
        
        if not seedance_block:
            violations.append(f"{p}:缺Seedance直接输入块")
            continue
        
        base_num = int(p[1:3])
        if base_num == 1:
            if '首帧为' not in seedance_block and '首帧' not in seedance_block:
                violations.append(f"{p}:缺场景首帧声明（应为'首帧为@图片X'）")
        else:
            if '末帧截图' not in seedance_block and '首帧' not in seedance_block:
                violations.append(f"{p}:缺末帧接力声明（应为'以@图片(上一段视频末帧截图)为首帧'）")
    
    if not violations:
        return CheckResult("第一层：单文件结构", 22, "首帧接力完整性",
                          Status.PASS, "P01有场景首帧，P02+有末帧接力")
    return CheckResult("第一层：单文件结构", 22, "首帧接力完整性",
                      Status.WARN, f"共{len(violations)}条：{'; '.join(violations[:3])}",
                      "补全首帧/末帧声明")


# v4.3: 美术指导外观描述禁止抽象物理数字
def check_art_no_abstract_numbers(art_text: str) -> CheckResult:
    """§6.0bis: 道具外观描述禁止吨/km/h/倍数等抽象物理数字"""
    patterns = [
        (r'\b\d+\.?\d*\s*吨\b',   '吨'),
        (r'\b\d+\.?\d*\s*公斤\b', '公斤'),
        (r'\b\d+\.?\d*\s*km/h\b', 'km/h'),
        (r'\b\d+\.?\d*\s*倍\b',   '倍数'),
        (r'\b\d+\.?\d*\s*米长\b', 'X米长'),
        (r'\b\d+\.?\d*\s*米宽\b', 'X米宽'),
        (r'\b\d+\.?\d*\s*米高\b', 'X米高'),
        (r'\b时速\s*\d+',         '时速X'),
        (r'\b\d+\.?\d*\s*%\b',    '百分比'),
    ]
    found = []
    for pattern, label in patterns:
        matches = re.findall(pattern, art_text)
        if matches:
            found.extend([f'"{m}"({label})' for m in matches[:3]])
    
    if not found:
        return CheckResult("第一层：单文件结构", 23, "外观描述禁止抽象数字",
                          Status.PASS, "未发现吨/km/h/倍数等抽象物理数字")
    return CheckResult("第一层：单文件结构", 23, "外观描述禁止抽象数字",
                      Status.FAIL, f"发现{len(found)}处：{'; '.join(found[:5])}",
                      "改用视觉化语言替代抽象数字（见§6.0bis）")


# v4.3: L级道具Neg Prompt防宫格
def check_art_lprop_neg_antigrid(art_text: str) -> CheckResult:
    """§6.4: L级大型道具Negative Prompt必须包含防宫格词"""
    anti_grid_terms = ['split screen', 'grid layout', '宫格', '多图拼接']
    
    # Find all L级道具 sections (between "### 6.4" and "### 6.5" or end)
    l_section_match = re.search(r'### 6\.4.*?(?=### 6\.5|$)', art_text, re.DOTALL)
    if not l_section_match:
        return CheckResult("第一层：单文件结构", 24, "L级道具Neg防宫格",
                          Status.PASS, "未检测到L级道具区段")
    
    l_section = l_section_match.group()
    
    # Find Negative Prompt blocks within the L section
    neg_blocks = re.findall(r'Negative Prompt:\s*(.+?)(?=\n\n|\n```|\Z)', l_section, re.DOTALL)
    
    violations = []
    for i, neg in enumerate(neg_blocks):
        neg_clean = neg.strip().replace('\n', ' ')
        missing = [t for t in anti_grid_terms if t not in neg_clean]
        if missing:
            violations.append(f"Neg#{i+1}缺：{', '.join(missing)}")
    
    if not violations:
        return CheckResult("第一层：单文件结构", 24, "L级道具Neg防宫格",
                          Status.PASS, "所有L级道具Neg Prompt含防宫格词")
    return CheckResult("第一层：单文件结构", 24, "L级道具Neg防宫格",
                      Status.WARN, '；'.join(violations[:3]),
                      "Neg Prompt追加split screen/grid layout/宫格/多图拼接")


def check_firstlast_frame_count(cine_text: str) -> CheckResult:
    """v4.8: Check 26 - Each P-number has correct 首尾帧 block count."""
    pnums = extract_p_numbers(cine_text)
    if not pnums:
        return CheckResult("第一层：单文件结构", 26, "首尾帧块数", Status.WARN, "未检测到P编号")
    sections = re.split(r'(?=\n## P\d{2}(?:_[A-Z])?)', cine_text)
    violations = []
    for p in pnums:
        section = ''
        for s in sections:
            if f'## {p}' in s[:20]: section = s; break
        if not section: continue
        is_b2 = '_B2' in section
        frame_blocks = len(re.findall(r'【🖼️ 首帧合成图·|【🖼️ 尾帧合成图·', section))
        expected = 2 if is_b2 else 4
        if frame_blocks != expected:
            violations.append(f"{p}:{frame_blocks}块·期望{expected}块")
    if not violations:
        return CheckResult("第一层：单文件结构", 26, "首尾帧块数", Status.PASS, f"全部正确")
    return CheckResult("第一层：单文件结构", 26, "首尾帧块数", Status.FAIL, f"{len(violations)}条：{'; '.join(violations[:5])}")


def check_lite_version_exists(cine_text: str) -> CheckResult:
    """v4.8: Check 27 - 精简版 exists for every P-number with tail frames."""
    pnums = extract_p_numbers(cine_text)
    if not pnums:
        return CheckResult("第一层：单文件结构", 27, "精简版存在", Status.WARN, "未检测到P编号")
    sections = re.split(r'(?=\n## P\d{2}(?:_[A-Z])?)', cine_text)
    violations = []
    for p in pnums:
        section = ''
        for s in sections:
            if f'## {p}' in s[:20]: section = s; break
        if not section: continue
        is_b2 = '_B2' in section
        has_lite_first = '精简版' in section and '首帧合成图' in section
        has_lite_tail = '精简版' in section and '尾帧合成图' in section
        if not has_lite_first: violations.append(f"{p}:缺精简版首帧")
        if not is_b2 and not has_lite_tail: violations.append(f"{p}:缺精简版尾帧")
    if not violations:
        return CheckResult("第一层：单文件结构", 27, "精简版存在", Status.PASS, "全部含精简版")
    return CheckResult("第一层：单文件结构", 27, "精简版存在", Status.FAIL, f"{len(violations)}条：{'; '.join(violations[:5])}")


def check_firstlast_frame_integrity(cine_text: str) -> CheckResult:
    """v4.8: Check 28 - 首尾帧 3-field integrity."""
    pnums = extract_p_numbers(cine_text)
    if not pnums:
        return CheckResult("第一层：单文件结构", 28, "首尾帧三字段", Status.WARN, "未检测到P编号")
    sections = re.split(r'(?=\n## P\d{2}(?:_[A-Z])?)', cine_text)
    violations = []
    for p in pnums:
        section = ''
        for s in sections:
            if f'## {p}' in s[:20]: section = s; break
        if not section: continue
        frames = re.findall(r'【🖼️ (?:首帧|尾帧)合成图[^】]*】', section)
        for f in frames:
            idx = section.find(f)
            next_idx = section.find('【🖼️', idx + len(f))
            block = section[idx:next_idx if next_idx != -1 else len(section)]
            missing = []
            if '@图片引用：' not in block: missing.append('@图片引用')
            if '保存为：' not in block: missing.append('保存为')
            if '合成提示词：' not in block: missing.append('合成提示词')
            if missing: violations.append(f"{p}{f}:缺{'/'.join(missing)}")
    if not violations:
        return CheckResult("第一层：单文件结构", 28, "首尾帧三字段", Status.PASS, "全部完整")
    return CheckResult("第一层：单文件结构", 28, "首尾帧三字段", Status.FAIL, f"{len(violations)}条：{'; '.join(violations[:5])}")


def check_at_embed_in_synthesis(cine_text: str) -> CheckResult:
    """v4.8: Check 29 - @图片 embedded in synthesis prompts."""
    blocks = re.findall(r'合成提示词：[^\n]+(?:\n(?!【|保存为：|@图片引用：)[^\n]+)*', cine_text)
    violations = [f"#{i+1}" for i, b in enumerate(blocks) if '@图片' not in b]
    if not violations:
        return CheckResult("第一层：单文件结构", 29, "@标记嵌入", Status.PASS, f"全部{len(blocks)}条含@标记")
    return CheckResult("第一层：单文件结构", 29, "@标记嵌入", Status.FAIL, f"{len(violations)}条缺失", "补全@图片N")


def check_branch_label(cine_text: str) -> CheckResult:
    """v4.8: Check 30 - Branch labels _A/_B1/_B2 in save names."""
    save_names = re.findall(r'保存为：(\S+)', cine_text)
    violations = [n for n in save_names if not re.search(r'_(A|B1|B2)$', n.rsplit('_', 1)[-1] if '_' in n else '')]
    if not violations:
        return CheckResult("第一层：单文件结构", 30, "分支标签", Status.PASS, f"全部{len(save_names)}处含标签")
    return CheckResult("第一层：单文件结构", 30, "分支标签", Status.FAIL, f"{len(violations)}处缺失：{'; '.join(violations[:5])}")


def check_b2_no_tail_frame(cine_text: str) -> CheckResult:
    """v4.8: Check 31 - B-2 scenes have no tail frames."""
    pnums = extract_p_numbers(cine_text)
    if not pnums:
        return CheckResult("第一层：单文件结构", 31, "B-2无尾帧", Status.WARN, "未检测到P编号")
    sections = re.split(r'(?=\n## P\d{2}(?:_[A-Z])?)', cine_text)
    violations = []
    for p in pnums:
        section = ''
        for s in sections:
            if f'## {p}' in s[:20]: section = s; break
        if not section: continue
        if '_B2' in section and '尾帧合成图' in section:
            violations.append(p)
    if not violations:
        return CheckResult("第一层：单文件结构", 31, "B-2无尾帧", Status.PASS, "全部B-2无尾帧")
    return CheckResult("第一层：单文件结构", 31, "B-2无尾帧", Status.FAIL, f"{len(violations)}条违规：{'; '.join(violations)}")


def check_time_segmented_block(cine_text: str) -> CheckResult:
    """v4.8: Check 32 - Time-segmented block exists per P-number."""
    pnums = extract_p_numbers(cine_text)
    if not pnums:
        return CheckResult("第一层：单文件结构", 32, "时间分段块", Status.WARN, "未检测到P编号")
    sections = re.split(r'(?=\n## P\d{2}(?:_[A-Z])?)', cine_text)
    violations = []
    for p in pnums:
        section = ''
        for s in sections:
            if f'## {p}' in s[:20]: section = s; break
        if not section: continue
        if '【🎬 Seedance时间分段输入】' not in section:
            violations.append(p)
    if not violations:
        return CheckResult("第一层：单文件结构", 32, "时间分段块", Status.PASS, "全部含时间分段块")
    return CheckResult("第一层：单文件结构", 32, "时间分段块", Status.FAIL, f"{len(violations)}条缺失：{'; '.join(violations[:5])}")


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
    # v4.1 new checks
    results.append(check_s2b_actor_image_count(art_text))
    results.append(check_three_block_completeness(cine_text))
    results.append(check_first_frame_continuity(cine_text))
    # v4.3 new checks
    results.append(check_art_no_abstract_numbers(art_text))
    results.append(check_art_lprop_neg_antigrid(art_text))
    # v4.8 new checks
    results.append(check_firstlast_frame_count(cine_text))
    results.append(check_lite_version_exists(cine_text))
    results.append(check_firstlast_frame_integrity(cine_text))
    results.append(check_at_embed_in_synthesis(cine_text))
    results.append(check_branch_label(cine_text))
    results.append(check_b2_no_tail_frame(cine_text))
    results.append(check_time_segmented_block(cine_text))
    return results
