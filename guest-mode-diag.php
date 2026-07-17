<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/elementor-fix-cta', [
        'methods' => 'POST',
        'callback' => function (WP_REST_Request $req) {
            $pid = (int) $req->get_param('pid');
            $dry = $req->get_param('dry') === '1';
            if (!$pid) return ['error' => 'missing pid'];
            $data = get_post_meta($pid, '_elementor_data', true);
            if (!$data) return ['error' => 'no _elementor_data found'];

            $old = '<a href=\"#\" class=\"mag-ebook-cta\"';
            $new = '<a href=\"https:\/\/play.google.com\/store\/books\/details\/Talal_Eddaouahiri_Build_Your_Credit_Score_in_the_U?id=2oPjEQAAQBAJ\" target=\"_blank\" rel=\"noopener\" class=\"mag-ebook-cta\"';

            $count = substr_count($data, $old);
            $result = ['pid' => $pid, 'old_count' => $count, 'dry_run' => $dry];

            if ($count !== 1) {
                $result['error'] = 'expected exactly 1 occurrence, refusing to write';
                return $result;
            }

            $new_data = str_replace($old, $new, $data);
            $result['new_length'] = strlen($new_data);
            $result['old_length'] = strlen($data);

            if (!$dry) {
                $updated = update_post_meta($pid, '_elementor_data', wp_slash($new_data));
                $result['update_post_meta_result'] = $updated;
                // Clear Elementor's rendered CSS/HTML cache for this post so it regenerates
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
