"""Cross-file validation checks (Layer 2: 20 checks)."""

from typing import List
from utils.parser import (
    extract_actor_table, extract_scene_table,
    extract_art_actor_table, extract_at_images,
    extract_p_numbers, extract_dialogue_cues,
    extract_scene_grid_names, extract_prop_table,
    extract_voice_table, extract_prompt_durations,
    extract_srt_total_duration, extract_base_image_refs,
    extract_at_audios,
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
    style_keywords = ['CG国漫', '真人写实', '日系二次元', '赛博朋克']
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
    if not warnings:
        return CheckResult("第二层：跨文件交叉", 21, "导演→美术 S4门槛",
                          Status.PASS, "全部道具≥2场")
    return CheckResult("第二层：跨文件交叉", 21, "导演→美术 S4门槛",
                      Status.WARN, f"不达标：{', '.join(warnings)}",
                      "确认是否应纳入道具库")


def check_actor_appearance_keywords(director_text: str, art_text: str) -> CheckResult:
    """Check 22: Director actor appearance keywords >= 3 feature categories per actor."""
    dir_table = extract_actor_table(director_text)
    # Feature categories with detection keywords (wider matching)
    categories = {
        '发型/发色': ['发', '髻', '辫', '寸头', '短发', '长发', '马尾', '刘海', '秃'],
        '服装/衣着': ['袍', '衣', '服', '装', '甲', '裤', '靴', '鞋', '裙', '衫', '褂', '夹克', 'T恤'],
        '体型/身高': ['体型', '瘦', '胖', '壮', '高', '矮', '精悍', '敦实', '匀称', 'cm'],
        '面容/五官': ['脸', '眼', '眉', '鼻', '唇', '嘴', '面容', '五官', '瞳'],
        '识别标记': ['疤', '痕', '痣', '胎记', '纹身', '雀斑', '痘印', '缺', '伤'],
        '肤色/肤质': ['肤', '白', '黑', '黄', '小麦', '古铜', '苍白', '粗糙', '光滑'],
        '配饰/道具': ['剑', '符', '袋', '令', '珠', '环', '镜', '扇', '刀'],
        # Non-human entity categories
        '形态/构造（非人）': ['甲壳', '复肢', '复眼', '触手', '胶状', '半透明', '骨刺', '口器', '翅膀', '鳞片', '节肢', '几丁质', '悬浮', '无固定形态',
                         '金属', '机械', '义眼', '义肢', '镜头', '数据', '全息', '能量', '光幕'],
        '体量/尺度（非人）': ['三米', '巨型', '球体', '两米', '直径', '米高'],
        '颜色/光学（非人）': ['暗红', '暗褐', '暗紫', '淡紫', '冷蓝', '淡金', '荧光', '微光', '透明', '半透明', '生物光泽', '星云', '流光', '脉冲', '闪烁'],
    }
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
    Scene references are @图片N where N is in the scene grid range (typically 5-20)."""
    art_scene_nums = set()
    for num, _ in extract_scene_grid_names(art_text):
        art_scene_nums.add(num)
    if not art_scene_nums:
        # Fallback: scan for @图片N declarations after S3 section
        s3_start = art_text.find('S3') 
        if s3_start >= 0:
            for m in re.finditer(r'@图片(\d+)', art_text[s3_start:s3_start+3000]):
                num = int(m.group(1))
                if 5 <= num <= 20:
                    art_scene_nums.add(num)
    # Extract scene-referenced @图片 from cine prompts (numbers 5-20, not actors 1-4 or props 21+)
    cine_scene_refs = set()
    for m in re.finditer(r'@图片(\d+)', cine_text):
        num = int(m.group(1))
        if 5 <= num <= 20:
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
    # Collect all @图片 numbers from art that are in prop range (typically 21+)
    prop_nums = set()
    for m in re.finditer(r'@图片(\d+)', art_text):
        num = int(m.group(1))
        if num >= 21:
            prop_nums.add(num)
    # Extract prop @references from cine prompts (21+)
    cine_prop_refs = set()
    for m in re.finditer(r'@图片(\d+)', cine_text):
        num = int(m.group(1))
        if num >= 21:
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
    if count == 0:
        return CheckResult("第二层：跨文件交叉", 30, "全局 待定妆/待勘景",
                          Status.PASS, "0处（已全部完成）")
    return CheckResult("第二层：跨文件交叉", 30, "全局 待定妆/待勘景",
                      Status.WARN, f"{count}处待处理", "确认是否已生成对应的美术资产")


def check_style_token_every_prompt(cine_text: str) -> CheckResult:
    """Check 31: Every prompt has Style Token keywords."""
    import re
    prompt_blocks = re.split(r'(?:^|\n)(?:##|###)\s*P\d{2}', cine_text)[1:]
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
    results.append(check_srt_p_coverage(director_text, art_text))
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
    return results
