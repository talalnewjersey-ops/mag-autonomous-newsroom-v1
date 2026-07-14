add_action('rest_api_init', function() {
    register_rest_route('mag/v1', '/check-plugin-file', [
        'methods' => 'GET',
        'callback' => function() {
            $path = WP_PLUGIN_DIR . '/moneyabroadguide-fusion-v51-wordpress/moneyabroadguide-fusion-v51-wordpress.php';
            $result = ['path' => $path, 'exists' => file_exists($path)];
            if (file_exists($path)) {
                $result['filesize'] = filesize($path);
                $result['filemtime'] = date('Y-m-d H:i:s', filemtime($path));
                $content = file_get_contents($path);
                $result['contains_cls_marker'] = strpos($content, 'CLS FIX 2026-07-14') !== false;
                $result['contains_hero_results_rule'] = strpos($content, '#hero-results') !== false;
                $result['first_500_chars'] = substr($content, 0, 500);
            }
            return $result;
        },
        'permission_callback' => function() { return current_user_can('manage_options'); },
    ]);
}, 999);
