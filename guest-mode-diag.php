<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/elementor-footer-fix', [
        'methods' => 'POST',
        'callback' => function (WP_REST_Request $req) {
            $pid = (int) $req->get_param('pid');
            $dry = $req->get_param('dry') === '1';
            if (!$pid) return ['error' => 'missing pid'];
            $data = get_post_meta($pid, '_elementor_data', true);
            if (!$data) return ['error' => 'no _elementor_data found'];

            if ($pid === 1364) {
                $old = 'Get the eBook Today &rarr;<\/a>\n<\/section>';
                $new = 'Get the eBook Today &rarr;<\/a>\n<\/section>\n<section id=\"free-starter-kit\">[mag_cv3]<\/section>';
            } elseif ($pid === 1369) {
                $old = 'Get the eBook Today &rarr;<\/a>\n<\/div><\/div>';
                $new = 'Get the eBook Today &rarr;<\/a>\n<\/div><\/div>\n<section id=\"free-starter-kit\">[mag_cv3]<\/section>';
            } else {
                return ['error' => 'unsupported pid'];
            }

            $count = substr_count($data, $old);
            $result = ['pid' => $pid, 'old_count' => $count, 'dry_run' => $dry];
            if ($count !== 1) {
                $result['error'] = 'expected exactly 1 occurrence, refusing to write';
                $result['sample_around_marker'] = null;
                $idx = strpos($data, 'Get the eBook Today');
                if ($idx !== false) $result['sample_around_marker'] = substr($data, $idx, 200);
                return $result;
            }

            $new_data = str_replace($old, $new, $data);
            $result['old_length'] = strlen($data);
            $result['new_length'] = strlen($new_data);

            if (!$dry) {
                $updated = update_post_meta($pid, '_elementor_data', wp_slash($new_data));
                $result['update_post_meta_result'] = $updated;
                delete_post_meta($pid, '_elementor_css');
                if (class_exists('\Elementor\Plugin')) {
                    try {
                        \Elementor\Plugin::$instance->files_manager->clear_cache();
                        $result['elementor_cache_cleared'] = true;
                    } catch (\Throwable $e) {
                        $result['elementor_cache_clear_error'] = $e->getMessage();
                    }
                }
            }

            return $result;
        },
        'permission_callback' => '__return_true',
    ]);
});
