<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/lscache-guest-disable', [
        'methods' => 'POST',
        'callback' => function () {
            $before = [
                'litespeed.conf.guest' => get_option('litespeed.conf.guest'),
                'litespeed.conf.guest_optm' => get_option('litespeed.conf.guest_optm'),
                'litespeed.conf.optm-guest_only' => get_option('litespeed.conf.optm-guest_only'),
            ];
            update_option('litespeed.conf.guest', '0');
            update_option('litespeed.conf.guest_optm', '0');
            update_option('litespeed.conf.optm-guest_only', '0');
            $after = [
                'litespeed.conf.guest' => get_option('litespeed.conf.guest'),
                'litespeed.conf.guest_optm' => get_option('litespeed.conf.guest_optm'),
                'litespeed.conf.optm-guest_only' => get_option('litespeed.conf.optm-guest_only'),
            ];
            return ['before' => $before, 'after' => $after];
        },
        'permission_callback' => '__return_true',
    ]);
});
