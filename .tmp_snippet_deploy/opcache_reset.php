add_action('rest_api_init', function() {
    register_rest_route('mag/v1', '/opcache-reset', [
        'methods' => 'POST',
        'callback' => function() {
            $result = ['opcache_available' => function_exists('opcache_reset')];
            if (function_exists('opcache_reset')) {
                $result['opcache_reset_result'] = opcache_reset();
            }
            if (function_exists('opcache_get_status')) {
                $status = opcache_get_status(false);
                $result['opcache_enabled'] = $status !== false;
            }
            return $result;
        },
        'permission_callback' => function() { return current_user_can('manage_options'); },
    ]);
}, 999);
