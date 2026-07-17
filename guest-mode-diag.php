<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/usa-hero-fix', [
        'methods' => 'POST',
        'callback' => function (WP_REST_Request $req) {
            $dry = $req->get_param('dry') === '1';
            $pid = 1364;
            $data = get_post_meta($pid, '_elementor_data', true);
            if (!$data) return ['error' => 'no _elementor_data found'];

            $old = 'href=\"https:\/\/moneyabroadguide.com\/how-to-build-credit-in-usa-without-ssn\/\" class=\"mag-hero-cta\"';
            $new = 'href=\"https:\/\/moneyabroadguide.com\/ebook-build-your-credit-score-usa\/\" target=\"_blank\" rel=\"noopener\" class=\"mag-hero-cta\"';

            $count = substr_count($data, $old);
            $result = ['pid' => $pid, 'old_count' => $count, 'dry_run' => $dry];
            if ($count !== 1) {
                $result['error'] = 'expected exactly 1, refusing';
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
