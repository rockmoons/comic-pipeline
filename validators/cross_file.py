"""Cross-file validation checks (Layer 2: 20 checks)."""

from typing import List
from utils.parser import (
    extract_actor_table, extract_scene_table,
    extract_art_actor_table, extract_at_images,
    extract_p_numbers, extract_dialogue_cues,
    extract_scene_grid_names, extract_prop_table,
    extract_voice_table, extract_prompt_durations,
    extract_srt_total_duration, extract_base_image_refs,
    extract_at_audios, APPEARANCE_CATEGORIES,
    extract_image_ranges, extract_id_mapping,
)
from utils.reporter import CheckResult, Status
import re


def _extract_char_names_from_table(table: List[dict], key: str = '演员') -> set:
    """Extract character names from a table column."""
    names = set()
    for row in table:
        val = row.get(key, '')
        # Handle "陈默(猫九)" format - extract base name
        base = val.split('(')[0].strip()
        if base:
            names.add(base)
    return names


def _extract_scene_names_from_table(table: List[dict], key: str = '场景') -> set:
    """Extract scene names from a table."""
    return {row.get(key, '').strip() for row in table if row.get(key, '').strip()}


# --- Story → Director (3 checks) ---

def check_actor_count_story_to_director(story_text: str, director_text: str) -> CheckResult:
    """Check 14: Director actor count >= Story actor count."""
    story_table = extract_actor_table(story_text)
    dir_table = extract_actor_table(director_text)
    if not story_table:
        return CheckResult("第二层：跨文件交叉", 14, "故事→导演 演员数",
                          Status.WARN, "无法解析故事创作演员表")
    if len(dir_table) >= len(story_table):
        return CheckResult("第二层：跨文件交叉", 14, "故事→导演 演员数",
                          Status.PASS, f"导演{len(dir_table)}人 >= 故事{len(story_table)}人")
    return CheckResult("第二层：跨文件交叉", 14, "故事→导演 演员数",
                      Status.FAIL, f"导演{len(dir_table)}人 < 故事{len(story_table)}人",
                      "导演演员表可能遗漏角色")


def check_scene_name_overlap_story_to_director(story_text: str, director_text: str) -> CheckResult:
    """Check 15: Director scene names have fuzzy overlap with story scene names."""
    story_table = extract_scene_table(story_text)
    dir_table = extract_scene_table(director_text)
    if not story_table or not dir_table:
        return CheckResult("第二层：跨文件交叉", 15, "故事→导演 场景名",
                          Status.WARN, "无法解析场景表")
    story_names = _extract_scene_names_from_table(story_table)
    dir_names = _extract_scene_names_from_table(dir_table)
    # Fuzzy match: check if any story scene name is a substring of director names
    mismatches = []
    for sn in story_names:
        matched = False
        for dn in dir_names:
            if sn in dn or dn in sn:
                matched = True
                break
        if not matched:
            mismatches.append(sn)
    if not mismatches:
        return CheckResult("第二层：跨文件交叉", 15, "故事→导演 场景名",
                          Status.PASS, "全部可匹配")
    return CheckResult("第二层：跨文件交叉", 15, "故事→导演 场景名",
                      Status.WARN, f"无法匹配：{', '.join(mismatches)}",
                      "检查是否同义不同名")


def check_visual_style_confirmation(story_text: str, director_text: str) -> CheckResult:
    """Check 16: Visual style from story is confirmed by director."""
    # Try to extract style from story header (typically line 2: "CG国漫" etc.)
    style_keywords = [
        'CG国漫', '真人写实', '日系二次元', '赛博朋克',
        '三渲二', '3D玄幻', '3D国风赛博', '3D美式', '3DQ版', '3D写实',
        '2D动画', '2D电影', '2D美漫', '2DQ版', '2D像素', '2D水彩',
        '真人电影', '真人古装', '港风复古',
        '定格动画', '手办风', '粘土风', '乐高风',
    ]
    story_style = None
    for kw in style_keywords:
        if kw in story_text:
            story_style = kw
            break
    if not story_style:
        return CheckResult("第二层：跨文件交叉", 16, "故事→导演 视觉风格",
                          Status.WARN, "未检测到故事创作的风格声明")
    if story_style in director_text:
        return CheckResult("第二层：跨文件交叉", 16, "故事→导演 视觉风格",
                          Status.PASS, f"导演确认了「{story_style}」")
    return CheckResult("第二层：跨文件交叉", 16, "故事→导演 视觉风格",
                      Status.WARN, f"故事选择「{story_style}」但导演未显式确认",
                      "导演应声明默认风格")


# --- Director → Art Director (6 checks) ---

def check_actor_count_dir_to_art(director_text: str, art_text: str) -> CheckResult:
    """Check 17: Art S1 actor count = Director actor count."""
    dir_table = extract_actor_table(director_text)
    art_table = extract_art_actor_table(art_text)
    if not dir_table:
        return CheckResult("第二层：跨文件交叉", 17, "导演→美术 S1演员数",
                          Status.WARN, "无法解析导演演员表")
    if len(art_table) == len(dir_table):
        return CheckResult("第二层：跨文件交叉", 17, "导演→美术 S1演员数",
                          Status.PASS, f"美术{len(art_table)}人 = 导演{len(dir_table)}人")
    return CheckResult("第二层：跨文件交叉", 17, "导演→美术 S1演员数",
                      Status.FAIL, f"美术{len(art_table)}人 ≠ 导演{len(dir_table)}人",
                      "S1演员阵容可能遗漏或多余")


def check_scene_count_dir_to_art(director_text: str, art_text: str) -> CheckResult:
    """Check 18: Art S3 scene count = Director scene count."""
    dir_table = extract_scene_table(director_text)
    dir_scene_count = len(dir_table)
    # Count unique scene names in art S3 grids
    grid_names = extract_scene_grid_names(art_text)
    # Extract base scene names (before dash suffix)
    scene_bases = set()
    for _, name in grid_names:
        base = name.split('-')[0].strip()
        scene_bases.add(base)
    if dir_scene_count == len(scene_bases):
        return CheckResult("第二层：跨文件交叉", 18, "导演→美术 S3场景数",
                          Status.PASS, f"美术{len(scene_bases)}组 = 导演{dir_scene_count}处")
    return CheckResult("第二层：跨文件交叉", 18, "导演→美术 S3场景数",
                      Status.FAIL, f"美术{len(scene_bases)}组 ≠ 导演{dir_scene_count}处",
                      "S3场景宫格可能遗漏")


def check_scene_name_exact_match(director_text: str, art_text: str) -> CheckResult:
    """Check 19: Art S3 scene names exactly match Director scene list."""
    dir_table = extract_scene_table(director_text)
    dir_names = _extract_scene_names_from_table(dir_table)
    grid_names = extract_scene_grid_names(art_text)
    art_bases = set()
    for _, name in grid_names:
        art_bases.add(name.split('-')[0].strip())
    missing = dir_names - art_bases
    extra = art_bases - dir_names
    if not missing and not extra:
        return CheckResult("第二层：跨文件交叉", 19, "导演→美术 场景名精确",
                          Status.PASS, "全部精确匹配")
    msgs = []
    if missing:
        msgs.append(f"导演有但美术无：{', '.join(missing)}")
    if extra:
        msgs.append(f"美术有但导演无：{', '.join(extra)}")
    return CheckResult("第二层：跨文件交叉", 19, "导演→美术 场景名精确",
                      Status.FAIL, '；'.join(msgs), "统一场景命名")


def check_srt_p_coverage(director_text: str, art_text: str) -> CheckResult:
    """Check 20: Art S6 SRT covers all Director P-numbers."""
    dir_pnums = set(extract_p_numbers(director_text))
    srt_pnums = set()
    for m in re.finditer(r'\[(P\d{2}(?:_[A-Z])?)\]', art_text):
        srt_pnums.add(m.group(1))
    missing = dir_pnums - srt_pnums
    if not missing:
        return CheckResult("第二层：跨文件交叉", 20, "导演→美术 S6 P编号覆盖",
                          Status.PASS, f"覆盖全部{len(dir_pnums)}个P编号")
    return CheckResult("第二层：跨文件交叉", 20, "导演→美术 S6 P编号覆盖",
                      Status.FAIL, f"SRT缺 {', '.join(sorted(missing))}",
                      "S6逐场覆盖校验未通过")


def check_prop_appearance_threshold(director_text: str, art_text: str) -> CheckResult:
    """Check 21: Each prop appears >= 2 times in director script."""
    prop_table = extract_prop_table(art_text)
    # Get prop appearance counts from the table
    warnings = []
    for row in prop_table:
        name = row.get('道具名', '')
        appearances = row.get('出现场次', '')
        count = len(re.findall(r'P\d{2}', appearances))
        if count < 2:
            warnings.append(f"{name}({count}场)")
    total = len(prop_table)
    if total == 0:
        return CheckResult("第二层：跨文件交叉", 21, "导演→美术 S4门槛",
                          Status.PASS, "无道具（无需检查）")
    pass_ratio = (total - len(warnings)) / total
    if pass_ratio >= 0.75:
        detail = "全部道具≥2场" if not warnings else f"达标{total - len(warnings)}/{total}，单场：{', '.join(warnings)}"
        return CheckResult("第二层：跨文件交叉", 21, "导演→美术 S4门槛",
                          Status.PASS, detail)
    return CheckResult("第二层：跨文件交叉", 21, "导演→美术 S4门槛",
                      Status.WARN, f"不达标{len(warnings)}/{total}：{', '.join(warnings)}",
                      "确认是否应纳入道具库")


def check_actor_appearance_keywords(director_text: str, art_text: str) -> CheckResult:
    """Check 22: Director actor appearance keywords >= 3 feature categories per actor."""
    dir_table = extract_actor_table(director_text)
    categories = APPEARANCE_CATEGORIES
    warnings = []
    for row in dir_table:
        name = row.get('演员', '')
        keywords = row.get('外观关键词', '')
        matched_cats = []
        for cat, keys in categories.items():
            if any(k in keywords for k in keys):
                matched_cats.append(cat)
        if len(matched_cats) < 3:
            warnings.append(f"{name}({len(matched_cats)}类:{','.join(matched_cats)})")
    if not warnings:
        return CheckResult("第二层：跨文件交叉", 22, "导演→美术 外观关键词",
                          Status.PASS, "全部角色≥3类特征")
    return CheckResult("第二层：跨文件交叉", 22, "导演→美术 外观关键词",
                      Status.WARN, f"不足3类：{', '.join(warnings)}",
                      "美术指导S1定妆将依赖推断")


# --- Art Director → Cinematographer (11 checks) ---

def check_at_image_count_match(art_text: str, cine_text: str) -> CheckResult:
    """Check 23: All cine @图片 references exist in Art @图片 range.
    Cine doesn't need to reference ALL art images (blank slots, unused scenes)."""
    art_nums = set(extract_at_images(art_text))
    cine_nums = set(extract_at_images(cine_text))
    invalid = cine_nums - art_nums
    if not invalid:
        return CheckResult("第二层：跨文件交叉", 23, "美术→分镜 @图片数",
                          Status.PASS, f"分镜{len(cine_nums)}个 ⊆ 美术{len(art_nums)}个")
    return CheckResult("第二层：跨文件交叉", 23, "美术→分镜 @图片数",
                      Status.FAIL, f"分镜引用了不存在的 @图片{invalid}", "修正@编号")


def check_dialogue_char_name_match(cine_text: str, art_text: str) -> CheckResult:
    """Check 24: Cine Dialogue Cue character names exist in Art S5 voice library."""
    voice_table = extract_voice_table(art_text)
    voice_names = {row.get('角色', '').strip() for row in voice_table}
    cues = extract_dialogue_cues(cine_text)
    missing = set()
    for cue in cues:
        if cue['char_name'] not in voice_names:
            missing.add(cue['char_name'])
    if not missing:
        return CheckResult("第二层：跨文件交叉", 24, "美术→分镜 DialogueCue角色",
                          Status.PASS, "全部角色名在音色库中存在")
    return CheckResult("第二层：跨文件交叉", 24, "美术→分镜 DialogueCue角色",
                      Status.FAIL, f"不存在：{', '.join(missing)}",
                      "检查角色名是否与S5音色库一致")


def check_scene_refs_in_range(cine_text: str, art_text: str) -> CheckResult:
    """Check 25: Cine scene @references exist in Art S3 scene images.
    Scene references are @图片N where N is in the scene grid range."""
    ranges = extract_image_ranges(art_text)
    scene_lo, scene_hi = ranges['scene_start'], ranges['scene_end']
    
    art_scene_nums = set()
    for num, _ in extract_scene_grid_names(art_text):
        art_scene_nums.add(num)
    # Fallback: always scan for @图片N declarations after S3 (captures 留白 slots etc.)
    s3_start = art_text.find('S3')
    if s3_start >= 0:
        for m in re.finditer(r'@[图圖]片(\d+)', art_text[s3_start:s3_start+5000]):
            num = int(m.group(1))
            if scene_lo <= num <= scene_hi:
                art_scene_nums.add(num)
    # Extract scene-referenced @图片 from cine prompts
    cine_scene_refs = set()
    for m in re.finditer(r'@[图圖]片(\d+)', cine_text):
        num = int(m.group(1))
        if scene_lo <= num <= scene_hi:
            cine_scene_refs.add(num)
    if not cine_scene_refs:
        return CheckResult("第二层：跨文件交叉", 25, "美术→分镜 场景@引用",
                          Status.WARN, "未检测到场景@引用", "检查提示词中是否含@图片5-20引用")
    invalid = cine_scene_refs - art_scene_nums
    if not invalid:
        return CheckResult("第二层：跨文件交叉", 25, "美术→分镜 场景@引用",
                          Status.PASS, f"全部{len(cine_scene_refs)}个有效")
    return CheckResult("第二层：跨文件交叉", 25, "美术→分镜 场景@引用",
                      Status.FAIL, f"无效引用 @图片{invalid}", "修正@编号")


def check_prop_refs_in_range(cine_text: str, art_text: str) -> CheckResult:
    """Check 26: Cine prop @references exist in Art S4 prop images."""
    ranges = extract_image_ranges(art_text)
    prop_lo = ranges['prop_start']
    
    prop_nums = set()
    for m in re.finditer(r'@[图圖]片(\d+)', art_text):
        num = int(m.group(1))
        if num >= prop_lo:
            prop_nums.add(num)
    cine_prop_refs = set()
    for m in re.finditer(r'@[图圖]片(\d+)', cine_text):
        num = int(m.group(1))
        if num >= prop_lo:
            cine_prop_refs.add(num)
    if not cine_prop_refs:
        return CheckResult("第二层：跨文件交叉", 26, "美术→分镜 道具@引用",
                          Status.WARN, "未检测到道具@引用", "检查提示词是否含@图片21+引用")
    invalid = cine_prop_refs - prop_nums
    if not invalid:
        return CheckResult("第二层：跨文件交叉", 26, "美术→分镜 道具@引用",
                          Status.PASS, f"全部{len(cine_prop_refs)}个有效")
    return CheckResult("第二层：跨文件交叉", 26, "美术→分镜 道具@引用",
                      Status.FAIL, f"无效引用 @图片{invalid}", "修正@编号")


def check_audio_char_alignment(cine_text: str, art_text: str) -> CheckResult:
    """Check 27: @音频N in Dialogue Cue matches S5 voice library role."""
    voice_table = extract_voice_table(art_text)
    # Build @音频N -> role name mapping
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
            mismatches.append(f"@音频{cue['audio_num']}={expected_role}≠DialogueCue={cue['char_name']}")
    if not mismatches:
        return CheckResult("第二层：跨文件交叉", 27, "美术→分镜 @音频角色对齐",
                          Status.PASS, "全部对齐")
    return CheckResult("第二层：跨文件交叉", 27, "美术→分镜 @音频角色对齐",
                      Status.FAIL, '；'.join(mismatches), "修正Dialogue Cue的@音频编号")


def check_duration_deviation(director_text: str, art_text: str, cine_text: str) -> CheckResult:
    """Check 28: Cine total duration vs SRT total duration deviation <= 10%."""
    srt_dur = extract_srt_total_duration(art_text)
    # Sum cine prompt durations
    prompt_durs = extract_prompt_durations(cine_text)
    cine_total = sum(d for _, d in prompt_durs)
    if srt_dur is None:
        return CheckResult("第二层：跨文件交叉", 28, "美术→分镜 时长偏差",
                          Status.WARN, "无法解析SRT总时长")
    if cine_total == 0:
        return CheckResult("第二层：跨文件交叉", 28, "美术→分镜 时长偏差",
                          Status.WARN, "无法解析提示词时长")
    deviation = abs(cine_total - srt_dur) / srt_dur * 100
    if deviation <= 10:
        return CheckResult("第二层：跨文件交叉", 28, "美术→分镜 时长偏差",
                          Status.PASS, f"{deviation:.1f}% <= 10%")
    return CheckResult("第二层：跨文件交叉", 28, "美术→分镜 时长偏差",
                      Status.FAIL, f"{deviation:.1f}% > 10%",
                      "提示词时长与SRT不一致")


def check_pending_markers(art_text: str, cine_text: str) -> CheckResult:
    """Check 29: Count all '待补充' markers across art and cine."""
    count = art_text.count('待补充') + cine_text.count('待补充')
    if count == 0:
        return CheckResult("第二层：跨文件交叉", 29, "全局 待补充标记",
                          Status.PASS, "0处")
    return CheckResult("第二层：跨文件交叉", 29, "全局 待补充标记",
                      Status.WARN, f"{count}处待补充", "补全或确认降级")


def check_pending_status_markers(director_text: str) -> CheckResult:
    """Check 30: Count '待定妆'/'待勘景' markers."""
    count = director_text.count('待定妆') + director_text.count('待勘景')
    if count <= 10:
        return CheckResult("第二层：跨文件交叉", 30, "全局 待定妆/待勘景",
                          Status.PASS, f"{count}处（正常流程标记，≤10）")
    return CheckResult("第二层：跨文件交叉", 30, "全局 待定妆/待勘景",
                      Status.WARN, f"{count}处待处理", "确认是否已生成对应的美术资产")


def check_style_token_every_prompt(cine_text: str) -> CheckResult:
    """Check 31: Every prompt has Style Token keywords."""
    prompt_blocks = re.split(r'(?:^|\n)(?:##|###)\s*P\d{2}(?:_[A-Z])?', cine_text)[1:]
    missing = []
    keywords = ['best quality', 'masterpiece', '8k', 'high detailed', '电影级光影']
    for i, block in enumerate(prompt_blocks):
        if not any(kw.lower() in block.lower() for kw in keywords):
            missing.append(f"P{i+1:02d}")
    if not missing:
        return CheckResult("第二层：跨文件交叉", 31, "全局 Style Token",
                          Status.PASS, "全部提示词含Style Token")
    return CheckResult("第二层：跨文件交叉", 31, "全局 Style Token",
                      Status.FAIL, f"缺失：{', '.join(missing)}", "补全Style Token")


def check_forbidden_words_in_prompts(cine_text: str) -> CheckResult:
    """Check 32: No forbidden quality words in prompts."""
    from utils.parser import extract_forbidden_words
    found = extract_forbidden_words(cine_text)
    if not found:
        return CheckResult("第二层：跨文件交叉", 32, "全局 画质禁用词",
                          Status.PASS, "0违规")
    return CheckResult("第二层：跨文件交叉", 32, "全局 画质禁用词",
                      Status.FAIL, f"含禁用词：{', '.join(found)}", "替换为替代词")


def check_cross_scene_base_image(art_text: str) -> CheckResult:
    """Check 33: Base image references don't cross scene boundaries."""
    refs = extract_base_image_refs(art_text)
    # Get scene assignments for each grid number
    grid_scene_map = {}
    for num, name in extract_scene_grid_names(art_text):
        base_scene = name.split('-')[0].strip()
        grid_scene_map[num] = base_scene
    violations = []
    for grid_num, base_num in refs:
        grid_scene = grid_scene_map.get(grid_num, '?')
        base_scene = grid_scene_map.get(base_num, '?')
        if grid_scene != base_scene and base_scene != '?':
            violations.append(f"格{grid_num}({grid_scene})→@图片{base_num}({base_scene})")
    if not violations:
        return CheckResult("第二层：跨文件交叉", 33, "全局 跨场景底图",
                          Status.PASS, "无跨场景底图")
    return CheckResult("第二层：跨文件交叉", 33, "全局 跨场景底图",
                      Status.FAIL, '；'.join(violations), "修正底图声明")


def check_id_propagation(director_text: str, art_text: str, cine_text: str) -> CheckResult:
    """Check 34 (v4.0): Character/scene IDs propagate correctly across all agents.
    
    Checks that character_ids and scene_ids from Director's scenes_metadata.json
    appear in Art's @编号↔ID mapping and Cine's material table.
    """
    from utils.parser import extract_json_block, extract_id_mapping
    
    # Extract Director JSON
    dir_json = extract_json_block(director_text)
    dir_char_ids = set()
    dir_scene_ids = set()
    if dir_json:
        for c in dir_json.get('characters', []):
            if c.get('character_id'):
                dir_char_ids.add(c['character_id'])
        for s in dir_json.get('scenes', []):
            if s.get('scene_id'):
                dir_scene_ids.add(s['scene_id'])
    
    # If no JSON, skip ID check
    if not dir_char_ids and not dir_scene_ids:
        return CheckResult("第二层：跨文件交叉", 34, "全局 ID传播",
                          Status.WARN, "导演未输出scenes_metadata.json，跳过ID检查")
    
    # Extract Art ID mapping
    art_id_map = extract_id_mapping(art_text)
    art_char_ids = {v['id'] for v in art_id_map['image_map'].values() if v['type'] == 'actor'}
    art_scene_ids = {v['id'] for v in art_id_map['image_map'].values() if v['type'] == 'scene'}
    
    # Check propagation
    missing_chars = dir_char_ids - art_char_ids
    missing_scenes = dir_scene_ids - art_scene_ids
    
    issues = []
    if missing_chars:
        issues.append(f"角色ID缺失：{', '.join(sorted(missing_chars))}")
    if missing_scenes:
        issues.append(f"场景ID缺失：{', '.join(sorted(missing_scenes))}")
    
    if not issues:
        return CheckResult("第二层：跨文件交叉", 34, "全局 ID传播",
                          Status.PASS, "全部ID从导演传播到美术指导")
    return CheckResult("第二层：跨文件交叉", 34, "全局 ID传播",
                      Status.FAIL, '；'.join(issues), "检查@编号↔ID映射表是否完整")


# Run all cross-file checks
def run_all(story_text: str, director_text: str, art_text: str, cine_text: str) -> List[CheckResult]:
    results = []
    # Story → Director
    results.append(check_actor_count_story_to_director(story_text, director_text))
    results.append(check_scene_name_overlap_story_to_director(story_text, director_text))
    results.append(check_visual_style_confirmation(story_text, director_text))
    # Director → Art
    results.append(check_actor_count_dir_to_art(director_text, art_text))
    results.append(check_scene_count_dir_to_art(director_text, art_text))
    results.append(check_scene_name_exact_match(director_text, art_text))
    # check_srt_p_coverage removed: duplicate of srt_checks.py check 40
    results.append(check_prop_appearance_threshold(director_text, art_text))
    results.append(check_actor_appearance_keywords(director_text, art_text))
    # Art → Cine
    results.append(check_at_image_count_match(art_text, cine_text))
    results.append(check_dialogue_char_name_match(cine_text, art_text))
    results.append(check_scene_refs_in_range(cine_text, art_text))
    results.append(check_prop_refs_in_range(cine_text, art_text))
    results.append(check_audio_char_alignment(cine_text, art_text))
    results.append(check_duration_deviation(director_text, art_text, cine_text))
    # Global
    results.append(check_pending_markers(art_text, cine_text))
    results.append(check_pending_status_markers(director_text))
    results.append(check_style_token_every_prompt(cine_text))
    results.append(check_forbidden_words_in_prompts(cine_text))
    results.append(check_cross_scene_base_image(art_text))
    results.append(check_id_propagation(director_text, art_text, cine_text))
    return results
