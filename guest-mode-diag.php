<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/lscache-guest2', [
        'methods' => 'GET',
        'callback' => function () {
            $out = [];
            $out['LiteSpeed_Conf_class_exists'] = class_exists('\LiteSpeed\Conf');
            $out['LiteSpeed_Base_class_exists'] = class_exists('\LiteSpeed\Base');
            if (class_exists('\LiteSpeed\Base')) {
                $ref = new ReflectionClass('\LiteSpeed\Base');
                $consts = $ref->getConstants();
                foreach ($consts as $k => $v) {
                    if (stripos($k, 'GUEST') !== false) {
                        $out['const_' . $k] = $v;
                    }
                }
            }
            if (class_exists('\LiteSpeed\Conf')) {
                try {
                    $conf = \LiteSpeed\Conf::get_instance();
                    $out['conf_instance_ok'] = true;
                    if (defined('\LiteSpeed\Base::O_GUEST')) {
                        $out['live_value_via_class'] = $conf->conf(\LiteSpeed\Base::O_GUEST);
                        $out['O_GUEST_constant_value'] = \LiteSpeed\Base::O_GUEST;
                    }
                } catch (\Throwable $e) {
                    $out['conf_error'] = $e->getMessage();
                }
            }
            return $out;
        },
        'permission_callback' => '__return_true',
    ]);
});
