<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/lscache-jsexc2', [
        'methods' => 'GET',
        'callback' => function () {
            $out = [];
            if (class_exists('\LiteSpeed\Base')) {
                $ref = new ReflectionClass('\LiteSpeed\Base');
                $consts = $ref->getConstants();
                foreach ($consts as $k => $v) {
                    if (stripos($k, 'JS') !== false && (stripos($k, 'EXC') !== false || stripos($k, 'DELAY') !== false || stripos($k, 'DEFER') !== false)) {
                        $out['const_' . $k] = $v;
                    }
                }
            }
            if (class_exists('\LiteSpeed\Conf')) {
                $conf = \LiteSpeed\Conf::get_instance();
                foreach ($out as $constName => $optKey) {
                    $shortConst = str_replace('const_', '', $constName);
                    if (defined("\LiteSpeed\Base::$shortConst")) {
                        $val = $conf->conf(constant("\LiteSpeed\Base::$shortConst"));
                        $out['value_' . $shortConst] = $val;
                    }
                }
            }
            return $out;
        },
        'permission_callback' => '__return_true',
    ]);
});
