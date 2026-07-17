<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/lscache-jsexc-verify', [
        'methods' => 'GET',
        'callback' => function () {
            $raw = get_option('litespeed.conf.optm-js_defer_exc');
            $out = ['raw_type' => gettype($raw), 'raw_value' => $raw];
            if (class_exists('\LiteSpeed\Conf') && defined('\LiteSpeed\Base::O_OPTM_JS_DEFER_EXC')) {
                $conf = \LiteSpeed\Conf::get_instance();
                $out['via_class'] = $conf->conf(\LiteSpeed\Base::O_OPTM_JS_DEFER_EXC);
            }
            return $out;
        },
        'permission_callback' => '__return_true',
    ]);
});
