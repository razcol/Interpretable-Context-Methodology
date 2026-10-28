<?php
/**
 * Read-only check: does this WordPress environment already have the layout?
 *
 *   wp eval-file inspect_acf_layout.php /path/to/section.spec.json --url=https://the-environment
 *
 * Prints one JSON object. Does not create or update fields. Field creation is
 * the patched ACF export from patch_acf_export.py, imported on this same environment.
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "Run inside WordPress: wp eval-file inspect_acf_layout.php <spec.json> --url=<site>\n");
    exit(1);
}

if (!function_exists('acf_get_field_groups') || !function_exists('acf_get_fields')) {
    fwrite(STDERR, "ACF is not loaded.\n");
    exit(1);
}

$spec_path = isset($args[0]) ? $args[0] : '';
if ($spec_path === '' || !is_readable($spec_path)) {
    fwrite(STDERR, "Pass a readable spec JSON path as the first argument.\n");
    exit(1);
}

$spec = json_decode(file_get_contents($spec_path), true);
if (!is_array($spec) || empty($spec['layout_name'])) {
    fwrite(STDERR, "Spec must be JSON with layout_name.\n");
    exit(1);
}

$graphql_name = isset($spec['graphql_group']) ? $spec['graphql_group'] : 'fields';
$flexible_name = isset($spec['flexible_field']) ? $spec['flexible_field'] : 'flexible';
$layout_name = $spec['layout_name'];

$matches = array();
foreach (acf_get_field_groups() as $group) {
    $full = acf_get_field_group($group['key']);
    if (!is_array($full)) {
        continue;
    }
    $name = isset($full['graphql_field_name']) ? $full['graphql_field_name'] : '';
    if ($name !== '' && $name !== $graphql_name) {
        continue;
    }
    $fields = acf_get_fields($full['key']);
    if (!is_array($fields)) {
        continue;
    }
    foreach ($fields as $field) {
        if (!is_array($field) || ($field['type'] ?? '') !== 'flexible_content' || ($field['name'] ?? '') !== $flexible_name) {
            continue;
        }
        $matches[] = array('group' => $full, 'field' => $field, 'graphql_named' => $name === $graphql_name);
    }
}

$named = array_values(array_filter($matches, function ($match) {
    return $match['graphql_named'];
}));
$pool = $named ? $named : $matches;

$report = array(
    'blog_id' => function_exists('get_current_blog_id') ? get_current_blog_id() : null,
    'home_url' => home_url(),
    'layout_name' => $layout_name,
    'writes' => false,
);

if (count($pool) !== 1) {
    $report['status'] = 'ambiguous-or-missing-group';
    $report['candidates'] = array_map(function ($match) {
        return array(
            'title' => $match['group']['title'] ?? '',
            'key' => $match['group']['key'] ?? '',
            'graphql_field_name' => $match['group']['graphql_field_name'] ?? '',
        );
    }, $matches);
    echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n";
    exit(1);
}

$field = $pool[0]['field'];
$layouts = isset($field['layouts']) && is_array($field['layouts']) ? $field['layouts'] : array();
$found = null;
foreach ($layouts as $layout) {
    if (is_array($layout) && (($layout['name'] ?? '') === $layout_name)) {
        $found = $layout;
        break;
    }
}

$report['group_key'] = $pool[0]['group']['key'] ?? '';
$report['group_title'] = $pool[0]['group']['title'] ?? '';

if ($found === null) {
    $report['status'] = 'layout-missing';
    $report['existing_layouts'] = array_values(array_filter(array_map(function ($layout) {
        return is_array($layout) ? ($layout['name'] ?? '') : '';
    }, $layouts)));
    echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n";
    exit(2);
}

$have = array();
foreach ($found['sub_fields'] ?? array() as $sub) {
    if (is_array($sub) && isset($sub['name'])) {
        $have[] = $sub['name'];
    }
}
$want = array();
foreach ($spec['fields'] ?? array() as $spec_field) {
    if (is_array($spec_field) && isset($spec_field['name'])) {
        $want[] = $spec_field['name'];
    }
}
$missing = array_values(array_diff($want, $have));
$report['status'] = $missing ? 'layout-missing-fields' : 'layout-present';
$report['subfields'] = $have;
$report['missing_fields'] = $missing;
echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n";
exit($missing ? 2 : 0);
