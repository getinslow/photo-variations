#!/usr/bin/env python3
"""Route agent-provided visual observations; does not read pixels or generate images."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBJECTS = {'landscape', 'architecture', 'person', 'group', 'food', 'object', 'urban_scene'}
FEATURES = {'layered_terrain', 'architectural_layers', 'strong_color_blocks',
            'clear_silhouette', 'visible_action', 'strong_axis', 'repeated_shapes',
            'quiet_regions', 'dense_detail', 'legible_text', 'warm_memory',
            'organic_shapes', 'horizon', 'documentary_text', 'scenic_setting'}
PHOTO_CONTEXTS = {'unknown', 'travel', 'everyday', 'product'}
PURPOSES = {'auto', 'travel_card', 'miniature_art', 'quiet_memory', 'playful_poster',
            'print_poster', 'zine_collage', 'minimal_art', 'crayon_diary'}
BOOLS = {'single_subject', 'image_tool_available', 'preserve_photo_region',
         'preserve_source_pixels', 'pixel_preserving_compositor',
         'remote_workflow_reader_available'}


def load_routes():
    return json.loads((ROOT / 'references' / 'routes.json').read_text(encoding='utf-8'))['routes']


def matches_style(route, style):
    return style in {route['id'], route['display_name']} or style in route['aliases']


def validate(data, routes):
    if not isinstance(data, dict):
        raise ValueError('Input must be a JSON object')
    if data.get('subject_type') not in SUBJECTS:
        raise ValueError('subject_type must describe the photograph using a supported value')
    features = data.get('features', [])
    if not isinstance(features, list) or any(not isinstance(x, str) or x not in FEATURES for x in features):
        raise ValueError('features must be a list of supported visual observations')
    if data.get('purpose', 'auto') not in PURPOSES:
        raise ValueError('Unsupported purpose')
    if data.get('photo_context', 'unknown') not in PHOTO_CONTEXTS:
        raise ValueError('Unsupported photo_context')
    if data.get('use_context', 'unknown') not in {'unknown', 'personal_noncommercial', 'commercial'}:
        raise ValueError('Unsupported use_context')
    if data.get('request_kind', 'style') not in {'style', 'retouch'}:
        raise ValueError('request_kind must be style or retouch')
    for key in BOOLS:
        if key in data and not isinstance(data[key], bool):
            raise ValueError(key + ' must be boolean, not a truthy string')
    ids = {r['id'] for r in routes}
    for key in ('commercial_permissions', 'available_workflows'):
        val = data.get(key, [])
        if not isinstance(val, list) or any(not isinstance(x, str) for x in val):
            raise ValueError(key + ' must be a list of strings')
    if any(x not in ids for x in data.get('commercial_permissions', [])):
        raise ValueError('commercial_permissions contains an unknown workflow')
    if data.get('selected_subject') is not None and not isinstance(data['selected_subject'], str):
        raise ValueError('selected_subject must be a user-selected subject description')
    style = data.get('style')
    if style is not None and not isinstance(style, str):
        raise ValueError('style must be a workflow ID or supported alias')
    if style:
        matches = [r for r in routes if matches_style(r, style)]
        if len(matches) != 1:
            raise ValueError('Unknown or ambiguous style; use an exact workflow ID')


def gates(route, data):
    result = []
    use = data.get('use_context', 'unknown')
    if route['license_class'] != 'mit' and use != 'personal_noncommercial' and route['id'] not in data.get('commercial_permissions', []):
        result.append(('license_required', '这款需要明确个人非商业用途或对应授权'))
    if route.get('requires_remote_reader') and not data.get('remote_workflow_reader_available', False):
        result.append(('dependency_missing', '这款只提供外部引用；需要宿主读取原仓库的固定版本工作流与许可'))
    for required in route.get('required_workflows', []):
        if required not in data.get('available_workflows', []):
            result.append(('dependency_missing', '缺少工作流：' + required))
    if route.get('needs_single_subject') and not data.get('single_subject', False) and not data.get('selected_subject'):
        result.append(('needs_subject', '存在多个独立主体；这款需要用户明确主角'))
    preserve_region = data.get('preserve_photo_region', False) or data.get('preserve_source_pixels', False)
    if preserve_region and not route['preserves_photo_region']:
        result.append(('incompatible_request', '这款会重绘或重新印刷摄影内容，与保留原摄影区冲突'))
    if data.get('preserve_source_pixels', False) and route['preserves_photo_region'] and not data.get('pixel_preserving_compositor', False):
        result.append(('compositor_required', '像素完全保留需要可直接放回原图的拼版能力'))
    return result


def rank(route, data):
    score = route['subject_scores'].get(data['subject_type'], 0)
    reasons = ['主体类型：' + data['subject_type']]
    for feature in sorted(set(data.get('features', []))):
        delta = route['feature_scores'].get(feature, 0)
        score += delta
        if delta > 0:
            reasons.append('适配特征：' + feature)
    purpose = data.get('purpose', 'auto')
    purpose_score = route.get('purpose_scores', {}).get(purpose, 20 if purpose == route['purpose'] else 0)
    if purpose_score:
        score += purpose_score
        reasons.insert(0, '适配用户用途：' + purpose)
    scenic_travel_portrait = (
        purpose == 'auto'
        and data.get('photo_context', 'unknown') == 'travel'
        and data['subject_type'] in {'person', 'group'}
        and 'scenic_setting' in data.get('features', [])
    )
    if scenic_travel_portrait:
        context_score = route.get('context_scores', {}).get('travel_scenic_portrait', 0)
        score += context_score
        if context_score > 0:
            reasons.insert(0, '旅行人像：人物与风景共同构成记忆')
        elif context_score < 0:
            reasons.append('旅行人像：单独突出人物会弱化重要风景')
    if data.get('preserve_photo_region', False) and route['preserves_photo_region']:
        score += 4
    return score, reasons


def route_photo(data):
    routes = load_routes()
    validate(data, routes)
    if data.get('request_kind', 'style') == 'retouch':
        return {'status': 'unsupported_retouch', 'selected': None,
                'reason': '八款属于照片艺术再创作，不把纯修图请求强制变成海报', 'generation_completed': False}
    explicit = data.get('style')
    candidates = [r for r in routes if not explicit or matches_style(r, explicit)]
    ranked, excluded = [], []
    for order, route in enumerate(candidates):
        failures = gates(route, data)
        if failures:
            excluded.append({'id': route['id'], 'status': failures[0][0],
                             'reasons': [x[1] for x in failures]})
        else:
            score, reasons = rank(route, data)
            ranked.append((score, -order, route, reasons))
    if not ranked:
        failure = excluded[0] if explicit and excluded else None
        no_route_status = 'compositor_required' if data.get('preserve_source_pixels', False) and not data.get('pixel_preserving_compositor', False) else 'no_eligible_route'
        return {'status': failure['status'] if failure else no_route_status,
                'selected': None, 'excluded': excluded, 'generation_completed': False}
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    score, _, route, reasons = ranked[0]
    ready = data.get('image_tool_available', False)
    registry = json.loads((ROOT / 'references' / 'creator-registry.json').read_text(encoding='utf-8'))['workflows']
    creator = registry[route['id']]['creator']
    return {
        'status': 'ready' if ready else 'prompt_only',
        'selected': route['id'], 'display_name': route['display_name'],
        'source_path': data.get('source_path'),
        'workflow_entry': route['entry'], 'read_before_generation': route['required_reads'],
        'score': score, 'reasons': ['用户指定风格'] if explicit else reasons,
        'alternatives': [{'id': x[2]['id'], 'score': x[0]} for x in ranked[1:3]],
        'excluded': excluded, 'generation_completed': False,
        'next_action': '读取选中工作流并实际调用宿主图片工具' if ready else '宿主无图片工具，提供提示词并说明未出图',
        'adapter': route.get('adapter'), 'license_file': route['license_file'],
        'postprocess': {
            'required': True, 'performed': False,
            'helper': 'scripts/credit_artwork.py',
            'instructions': 'references/attribution.md',
            'registry': 'references/creator-registry.json',
            'workflow': route['id'], 'creator': creator, 'credit': creator + '×变奏',
            'after': ['generation', 'quality_review', 'compositing_or_optimization_if_needed', 'xxd_cleanup_if_applicable'],
            'verify_before_delivery': True
        }
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='Observation JSON path, or - for stdin')
    parser.add_argument('--out', help='Write a decision JSON without overwriting an existing file')
    args = parser.parse_args()
    try:
        content = sys.stdin.read() if args.input == '-' else Path(args.input).read_text(encoding='utf-8-sig')
        result = route_photo(json.loads(content))
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8') as handle:
                handle.write(rendered)
        else:
            print(rendered, end='')
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'input_error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
