<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/elementor-widget-end', [
        'methods' => 'GET',
        'callback' => function (WP_REST_Request $req) {
            $pid = (int) $req->get_param('pid');
            if (!$pid) return ['error' => 'missing pid'];
            $data = get_post_meta($pid, '_elementor_data', true);
            $decoded = json_decode($data, true);
            if (json_last_error() !== JSON_ERROR_NONE) {
                return ['error' => 'json decode failed: ' . json_last_error_msg()];
            }
            $out = [];
            $walk = function ($elements, $depth = 0) use (&$walk, &$out) {
                foreach ($elements as $el) {
                    $widgetType = $el['widgetType'] ?? null;
                    if ($widgetType === 'html' && isset($el['settings']['html'])) {
                        $html = $el['settings']['html'];
                        if (strpos($html, 'mag-ebook-cta') !== false || strpos($html, 'magcta2') !== false) {
                            $out[] = [
                                'id' => $el['id'] ?? null,
                                'html_length' => strlen($html),
                                'html_tail' => substr($html, -400),
                                'html_head' => substr($html, 0, 200),
                            ];
                        }
                    }
                    if (!empty($el['elements'])) {
                        $walk($el['elements'], $depth + 1);
                    }
                }
            };
            $walk($decoded);
            return ['pid' => $pid, 'widgets_found' => count($out), 'widgets' => $out];
        },
        'permission_callback' => '__return_true',
    ]);
});
