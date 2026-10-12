#!/usr/bin/env python3
"""Verify portable resources, immutable upstream hashes, and behavioral route invariants."""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from route_photo import load_routes, route_photo

EXTERNAL_ID = 'photo-abstract-editorial'
EXTERNAL_ENTRY = 'references/external/photo-abstract-editorial.md'
EXTERNAL_BASE_URL = ('https://raw.githubusercontent.com/ZzzLc0405/photo-abstract-editorial/'
                     '49e55073d6d0330274d31f75d27f5dd6eb35fd6d/')
EXTERNAL_LICENSE_URL = EXTERNAL_BASE_URL + 'LICENSE.md'
EXTERNAL_READS = [EXTERNAL_BASE_URL + 'SKILL.md',
                  EXTERNAL_BASE_URL + 'references/photo-abstract-editorial-prompt.zh-CN.md']
TRUSTED_REMOTE_RESOURCES = {EXTERNAL_LICENSE_URL, *EXTERNAL_READS}
DISPLAY_NAMES = {
    'watercolor-travel-card': '水彩旅行卡',
    'impasto-miniature-landscape': '厚涂油画',
    'photo-relic-editorial': '纸上留影',
    'heytea-doodle-poster': '小人涂鸦',
    'mono-color': '单色/双色印刷',
    'scenes-gathered-zine-v1-3': '拾景拼贴',
    'photo-abstract-editorial': '极简抽象',
    'xxd-panel-115': '粉彩拼贴',
}
LEGACY_DISPLAY_NAMES = {
    'watercolor-travel-card': '水彩旅行卡',
    'impasto-miniature-landscape': '厚涂微缩油画',
    'photo-relic-editorial': '纸上留影',
    'heytea-doodle-poster': '实物与小人互动',
    'mono-color': '单色或双色印刷',
    'scenes-gathered-zine-v1-3': '拾景杂志拼贴',
    'photo-abstract-editorial': '照片极简抽象',
    'xxd-panel-115': '蜡笔材料拼贴',
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_bundle():
    routes = load_routes()
    require(len(routes) == 8 and len({x['id'] for x in routes}) == 8, 'Must have eight unique routes')
    require(list(ROOT.rglob('SKILL.md')) == [ROOT / 'SKILL.md'], 'Only one discoverable skill entry')
    manifest = json.loads((ROOT / 'bundle-manifest.json').read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'references' / 'creator-registry.json').read_text(encoding='utf-8'))
    require(set(registry['workflows']) == {x['id'] for x in routes}, 'Every route must have source-based credit')
    require((ROOT / 'scripts' / 'credit_artwork.py').is_file(), 'Missing metadata credit helper')
    require((ROOT / 'references' / 'attribution.md').is_file(), 'Missing attribution instructions')
    for item in routes:
        require(bool(registry['workflows'][item['id']].get('creator')), 'Credit name missing')
    require({x['id'] for x in manifest['upstream']} == {x['id'] for x in routes}, 'Manifest and routes differ')
    external_items = [x for x in manifest['upstream'] if x.get('distribution') == 'external_reference']
    require(len(external_items) == 1 and external_items[0]['id'] == EXTERNAL_ID,
            'Only photo-abstract-editorial may be an external reference')
    require(external_items[0]['files'] == [], 'External reference must not vendor source files')
    require(not (ROOT / 'references' / 'workflows' / EXTERNAL_ID).exists(),
            'External workflow source must not be bundled')
    files_checked = 0
    for item in manifest['upstream'] + manifest.get('helpers', []):
        if item.get('distribution') == 'external_reference':
            require(item['id'] == EXTERNAL_ID and item['files'] == [], 'Unexpected external reference')
            continue
        for file in item['files']:
            path = (ROOT / file['path']).resolve()
            require(path.is_relative_to(ROOT.resolve()), 'Manifest path escapes package')
            require(path.is_file(), 'Missing vendored file: ' + file['path'])
            require(hashlib.sha256(path.read_bytes()).hexdigest() == file['sha256'], 'Hash mismatch: ' + file['path'])
            files_checked += 1
        if 'source_entry_sha256' in item:
            entry = ROOT / 'references' / 'workflows' / item['id'] / 'UPSTREAM.md'
            require(hashlib.sha256(entry.read_bytes()).hexdigest() == item['source_entry_sha256'], 'Original entry changed')
    remote_urls_checked = 0
    style_owners = {}
    for route in routes:
        require(route.get('requires_remote_reader', False) == (route['id'] == EXTERNAL_ID),
                'Remote reader requirement must match the external route')
        for name in {route['id'], route['display_name'], *route['aliases']}:
            require(name not in style_owners or style_owners[name] == route['id'], 'Ambiguous style name: ' + name)
            style_owners[name] = route['id']
        if route['id'] == EXTERNAL_ID:
            require(route['entry'] == EXTERNAL_ENTRY, 'External route must use its local bridge')
            require(route['license_file'] == EXTERNAL_LICENSE_URL and route['required_reads'] == EXTERNAL_READS,
                    'External resource URLs must use the trusted pinned commit')
        for relative in [route['entry'], route['license_file']] + route['required_reads']:
            if '://' in relative:
                require(route['id'] == EXTERNAL_ID and relative in TRUSTED_REMOTE_RESOURCES,
                        'Untrusted or unpinned remote resource: ' + relative)
                remote_urls_checked += 1
                continue
            path = (ROOT / relative).resolve()
            require(path.is_relative_to(ROOT.resolve()) and path.is_file(), 'Required resource missing: ' + relative)
    forbidden_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.mp4', '.mov', '.zip'}
    for path in ROOT.rglob('*'):
        if path.is_file():
            require(path.suffix.lower() not in forbidden_extensions, 'Unexpected personal or upstream image/media: ' + str(path))
            require('private-assets' not in path.parts and 'examples' not in path.parts, 'Restricted asset directory present')
            if path.suffix.lower() in {'.md', '.json', '.yaml', '.py', '.txt', '.svg'} or path.name == 'LICENSE':
                path.read_text(encoding='utf-8-sig')

    behavior_checks = 0

    def check(condition, message):
        nonlocal behavior_checks
        require(condition, message)
        behavior_checks += 1

    base = {'subject_type': 'landscape', 'features': ['layered_terrain', 'strong_color_blocks'],
            'single_subject': True, 'image_tool_available': True}
    for item in routes:
        credit_case = dict(base, style=item['id'], use_context='personal_noncommercial', single_subject=True,
                          remote_workflow_reader_available=True, available_workflows=['xxd-strip-ai-meta'])
        plan = route_photo(credit_case)
        check(plan['postprocess']['credit'] == registry['workflows'][item['id']]['creator'] + '×变奏', 'Wrong workflow credit')
        check(plan['postprocess']['required'] and not plan['postprocess']['performed'], 'Route decision must require, not falsely attest credit')
    check(route_photo(base)['selected'] == 'impasto-miniature-landscape', 'Layered landscape should reach miniature route')
    check(route_photo(dict(base, purpose='travel_card'))['selected'] == 'watercolor-travel-card', 'Use should override subject preference')
    check(route_photo(dict(base, style='纸上留影'))['selected'] == 'photo-relic-editorial', 'Explicit style must win')
    group = {'subject_type': 'group', 'features': ['clear_silhouette'], 'single_subject': False, 'image_tool_available': True}
    check(route_photo(group)['selected'] != 'heytea-doodle-poster', 'Auto must not silently choose one group member')
    check(route_photo(dict(group, style='小人涂鸦'))['status'] == 'needs_subject', 'Explicit doodle needs a selected subject')
    check(route_photo(dict(group, style='小人涂鸦', selected_subject='user-selected person'))['status'] == 'ready', 'User-selected target must be respected')
    check(route_photo(dict(base, style='photo-abstract-editorial', use_context='commercial'))['status'] == 'license_required', 'Commercial license gate')
    check(route_photo(dict(base, purpose='minimal_art', use_context='commercial'))['selected'] != 'photo-abstract-editorial', 'Automatic commercial route must exclude restricted style')
    check(route_photo(dict(base, purpose='minimal_art', use_context='commercial'))['selected'] in {'mono-color', 'photo-relic-editorial'}, 'Fallback must retain minimal intent')
    check(route_photo(dict(base, style='photo-abstract-editorial', use_context='personal_noncommercial', remote_workflow_reader_available=True))['status'] == 'ready', 'Personal route should permit restricted style')
    check(route_photo(dict(base, style='xxd-panel-115', use_context='personal_noncommercial'))['status'] == 'dependency_missing', 'XXD external dependency cannot disappear')
    check(route_photo(dict(base, style='xxd-panel-115', use_context='personal_noncommercial', available_workflows=['xxd-strip-ai-meta']))['status'] == 'ready', 'XXD route must work once prerequisites exist')
    check(route_photo(dict(base, preserve_photo_region=True))['selected'] == 'photo-relic-editorial', 'Keep photo should not redraw it')
    check(route_photo(dict(base, style='watercolor-travel-card', preserve_photo_region=True))['status'] == 'incompatible_request', 'Explicit redraw conflicts must be reported')
    check(route_photo(dict(base, style='留影', preserve_source_pixels=True))['status'] == 'compositor_required', 'Pixel preservation requires actual compositor')
    check(route_photo(dict(base, preserve_source_pixels=True))['status'] == 'compositor_required', 'Automatic exact-pixel request must expose actionable missing capability')
    check(route_photo(dict(base, style='留影', preserve_source_pixels=True, pixel_preserving_compositor=True))['status'] == 'ready', 'Pixel-preserving host should be usable')
    missing = route_photo(dict(base, image_tool_available=False))
    check(missing['status'] == 'prompt_only' and not missing['generation_completed'], 'No image tool must not claim image generation')
    check(route_photo(dict(base, request_kind='retouch'))['status'] == 'unsupported_retouch', 'Retouch must not be forced into a poster')
    portrait = {'subject_type': 'person', 'features': ['visible_action', 'clear_silhouette', 'quiet_regions', 'horizon', 'scenic_setting'],
                'single_subject': True, 'purpose': 'auto', 'photo_context': 'travel', 'image_tool_available': True}
    check(route_photo(portrait)['selected'] == 'watercolor-travel-card', 'Scenic travel portrait should retain its environment')
    check(route_photo(dict(portrait, photo_context='unknown'))['selected'] == 'heytea-doodle-poster', 'Scenery alone must not invent travel intent')
    check(route_photo(dict(portrait, photo_context='product'))['selected'] == 'heytea-doodle-poster', 'Product context must not receive travel preference')
    check(route_photo(dict(portrait, features=['visible_action', 'clear_silhouette', 'quiet_regions', 'horizon']))['selected'] == 'heytea-doodle-poster', 'Travel context alone must not claim important scenery')
    check(route_photo(dict(portrait, purpose='playful_poster'))['selected'] == 'heytea-doodle-poster', 'Explicit playful purpose must win over inferred context')
    check(route_photo(dict(portrait, style='小人互动'))['selected'] == 'heytea-doodle-poster', 'Explicit style must win over scenic travel preference')
    forest_group = dict(portrait, subject_type='group', single_subject=False, features=['clear_silhouette', 'scenic_setting'])
    check(route_photo(forest_group)['selected'] == 'watercolor-travel-card', 'Scenic travel groups do not require a horizon or selected member')
    check(route_photo(dict(base, photo_context='travel', features=base['features'] + ['scenic_setting']))['selected'] == 'impasto-miniature-landscape', 'Travel landscapes must retain their own composition routing')
    check(route_photo(dict(portrait, preserve_photo_region=True))['selected'] == 'photo-relic-editorial', 'Scenic preference cannot override photo preservation')
    check(route_photo(dict(portrait, features=portrait['features'] + ['documentary_text', 'legible_text']))['selected'] == 'photo-relic-editorial', 'Important documentary text must retain its preference')
    explicit_base = dict(base, use_context='personal_noncommercial',
                         remote_workflow_reader_available=True,
                         available_workflows=['xxd-strip-ai-meta'])
    explicit_name_checks = 0
    explicit_names_checked = set()
    routes_by_id = {route['id']: route for route in routes}
    for route_id, name in DISPLAY_NAMES.items():
        decision = route_photo(dict(explicit_base, style=name))
        check(decision['selected'] == route_id and decision['display_name'] == name,
              'Display name must explicitly select its route: ' + name)
        explicit_name_checks += 1
        explicit_names_checked.add(name)
    for route_id, name in LEGACY_DISPLAY_NAMES.items():
        check(name in routes_by_id[route_id]['aliases']
              and route_photo(dict(explicit_base, style=name))['selected'] == route_id,
              'Legacy display name must remain an alias: ' + name)
        explicit_name_checks += 1
        explicit_names_checked.add(name)
    for name in ['厚涂微缩景观', '浮雕感厚涂油画']:
        check(name in routes_by_id['impasto-miniature-landscape']['aliases']
              and route_photo(dict(explicit_base, style=name))['selected'] == 'impasto-miniature-landscape',
              'Additional impasto alias must work: ' + name)
        explicit_name_checks += 1
        explicit_names_checked.add(name)
    external = dict(base, style=EXTERNAL_ID, use_context='personal_noncommercial')
    check(route_photo(external)['status'] == 'dependency_missing',
          'Explicit external route needs a verified remote reader')
    check(route_photo(dict(external, remote_workflow_reader_available=False))['status'] == 'dependency_missing',
          'A false remote-reader flag must not enable the external route')
    check(route_photo(dict(external, use_context='unknown'))['status'] == 'license_required',
          'License must have priority when remote reader is also missing')
    check(route_photo(dict(external, use_context='unknown', remote_workflow_reader_available=True))['status'] == 'license_required',
          'Remote reader cannot replace a permitted use context')
    check(route_photo(dict(external, use_context='commercial', commercial_permissions=[EXTERNAL_ID]))['status'] == 'dependency_missing',
          'Commercial permission cannot replace a remote reader')
    check(route_photo(dict(external, use_context='commercial', commercial_permissions=[EXTERNAL_ID],
                           remote_workflow_reader_available=True))['status'] == 'ready',
          'Authorized commercial external route should work with its reader')
    check(route_photo(dict(base, purpose='minimal_art', use_context='personal_noncommercial'))['selected'] != EXTERNAL_ID,
          'Auto must exclude the external route when the reader is unavailable')
    check(route_photo(dict(base, purpose='minimal_art', use_context='personal_noncommercial',
                           remote_workflow_reader_available=True))['selected'] == EXTERNAL_ID,
          'Auto may choose the external route once license and reader are satisfied')
    check(route_photo(dict(external, image_tool_available=False,
                           remote_workflow_reader_available=True))['status'] == 'prompt_only',
          'External route without an image tool must not claim generation')
    for invalid in [dict(base, image_tool_available='false'), dict(base, features=['made_up']), dict(base, style='not-a-style'), dict(base, photo_context='inferred-from-filename'), dict(base, remote_workflow_reader_available='false')]:
        rejected = False
        try:
            route_photo(invalid)
        except ValueError:
            rejected = True
        check(rejected, 'Invalid observations must fail')
    return {'status': 'passed', 'routes': len(routes), 'upstream_files_hash_checked': files_checked,
            'bundled_workflows': len(manifest['upstream']) - len(external_items),
            'external_reference_workflows': len(external_items),
            'remote_resource_urls_checked': remote_urls_checked,
            'explicit_name_checks': explicit_name_checks,
            'unique_explicit_names_checked': len(explicit_names_checked),
            'route_invariants': behavior_checks, 'only_one_skill_entry': True,
            'image_generation_tested_by_this_script': False,
            'bundled_cleanup_helper': 'xxd-strip-ai-meta',
            'cleanup_runtime_requires': ['Python 3.10+', 'ExifTool']}


if __name__ == '__main__':
    try:
        print(json.dumps(validate_bundle(), ensure_ascii=False, indent=2))
    except (AssertionError, OSError, ValueError) as exc:
        print(json.dumps({'status': 'failed', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
