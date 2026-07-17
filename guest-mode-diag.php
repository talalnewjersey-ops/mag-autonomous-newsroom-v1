<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/lscache-jsexc', [
        'methods' => 'GET',
        'callback' => function () {
            $out = [];
            $keys = ['optm-js_exc', 'optm-js_defer_exc', 'optm-js_delay_exc'];
            foreach ($keys as $k) {
                $out[$k] = get_option("litespeed.conf.$k");
            }
            return $out;
        },
        'permission_callback' => '__return_true',
    ]);
});
