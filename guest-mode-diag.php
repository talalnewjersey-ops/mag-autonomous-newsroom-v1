<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/lscache-guest3', [
        'methods' => 'GET',
        'callback' => function () {
            $out = [];
            if (class_exists('\LiteSpeed\Conf') && class_exists('\LiteSpeed\Base')) {
                $conf = \LiteSpeed\Conf::get_instance();
                $keys = [
                    'O_GUEST', 'O_GUEST_OPTM', 'O_GUEST_UAS', 'O_GUEST_IPS', 'O_OPTM_GUEST_ONLY',
                ];
                foreach ($keys as $k) {
                    if (defined("\LiteSpeed\Base::$k")) {
                        $const = constant("\LiteSpeed\Base::$k");
                        $out[$k] = $conf->conf($const);
                    }
                }
            }
            // Also check the raw cookie name LiteSpeed expects
            $out['request_cookies'] = array_keys($_COOKIE);
            return $out;
        },
        'permission_callback' => '__return_true',
    ]);
});
