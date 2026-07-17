<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/lscache-guest', [
        'methods' => 'GET',
        'callback' => function () {
            $keys = [
                'litespeed.conf.guest',
                'litespeed.conf.guest_optm',
                'litespeed.conf.optm-guest_only',
            ];
            $out = [];
            foreach ($keys as $k) {
                $out[$k] = get_option($k);
            }
            return $out;
        },
        'permission_callback' => '__return_true',
    ]);
});
