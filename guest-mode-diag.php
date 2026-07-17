<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/elementor-cta', [
        'methods' => 'GET',
        'callback' => function (WP_REST_Request $req) {
            $pid = (int) $req->get_param('pid');
            if (!$pid) return ['error' => 'missing pid'];
            $data = get_post_meta($pid, '_elementor_data', true);
            $out = ['pid' => $pid, 'data_length' => strlen($data), 'data_type' => gettype($data)];
            // find every occurrence of "19.99" and show 200 chars around it
            $matches = [];
            $offset = 0;
            while (($idx = strpos($data, '19.99', $offset)) !== false) {
                $matches[] = substr($data, max(0, $idx - 250), 500);
                $offset = $idx + 1;
            }
            $out['matches_around_1999'] = $matches;
            return $out;
        },
        'permission_callback' => '__return_true',
    ]);
});
