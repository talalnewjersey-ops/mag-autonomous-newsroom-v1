<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/lscache-guest', [
        'methods' => 'GET',
        'callback' => function () {
            $out = [];
            if (class_exists('\LiteSpeed\Conf')) {
                $conf = \LiteSpeed\Conf::get_instance();
                if (method_exists($conf, 'is_option_true') && defined('\LiteSpeed\Base::O_GUEST')) {
                    $out['guest_via_Base_O_GUEST'] = $conf->is_option_true(\LiteSpeed\Base::O_GUEST);
                }
            }
            $raw = get_option('litespeed-cache-conf');
            $out['option_litespeed-cache-conf_exists'] = $raw !== false;
            if (is_array($raw)) {
                foreach ($raw as $k => $v) {
                    if (stripos($k, 'guest') !== false || stripos($k, 'vary') !== false) {
                        $out['raw_match_' . $k] = $v;
                    }
                }
                $out['raw_key_count'] = count($raw);
            } else {
                $out['raw_type'] = gettype($raw);
            }
            // also scan all options with 'litespeed' + 'guest' in the name
            global $wpdb;
            $rows = $wpdb->get_results("SELECT option_name FROM {$wpdb->options} WHERE option_name LIKE '%litespeed%guest%' OR option_name LIKE '%guest%litespeed%'");
            $out['matching_option_names'] = wp_list_pluck($rows, 'option_name');
            return $out;
        },
        'permission_callback' => '__return_true',
    ]);
});
