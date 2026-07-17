<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/lscache-jsexc-fix', [
        'methods' => 'POST',
        'callback' => function () {
            $before = get_option('litespeed.conf.optm-js_defer_exc');
            $new = is_array($before) ? $before : [];
            if (!in_array('wp-i18n', $new, true)) {
                $new[] = 'wp-i18n';
            }
            $updated = update_option('litespeed.conf.optm-js_defer_exc', $new);
            $after = get_option('litespeed.conf.optm-js_defer_exc');
            return ['before' => $before, 'after' => $after, 'update_result' => $updated];
        },
        'permission_callback' => '__return_true',
    ]);
});
