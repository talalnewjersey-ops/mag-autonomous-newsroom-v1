add_action('rest_api_init', function() {
    register_rest_route('mag/v1', '/find-stored-homepage', [
        'methods' => 'GET',
        'callback' => function() {
            global $wpdb;
            $results = [];

            // Search wp_options for the marker text
            $rows = $wpdb->get_results(
                $wpdb->prepare(
                    "SELECT option_name, LENGTH(option_value) AS len FROM {$wpdb->options} WHERE option_value LIKE %s LIMIT 20",
                    '%Helping newcomers navigate%'
                )
            );
            $results['options_matching_marker'] = $rows;

            // Also list any option with "fusion" or "homepage" in its name
            $rows2 = $wpdb->get_results(
                "SELECT option_name, LENGTH(option_value) AS len FROM {$wpdb->options} WHERE option_name LIKE '%fusion%' OR option_name LIKE '%homepage%' LIMIT 30"
            );
            $results['options_matching_name'] = $rows2;

            // Check postmeta too, in case it's stored against post 7203
            $rows3 = $wpdb->get_results(
                $wpdb->prepare(
                    "SELECT meta_key, LENGTH(meta_value) AS len FROM {$wpdb->postmeta} WHERE post_id = %d",
                    7203
                )
            );
            $results['post_7203_meta_keys'] = $rows3;

            return $results;
        },
        'permission_callback' => function() { return current_user_can('manage_options'); },
    ]);
}, 999);
