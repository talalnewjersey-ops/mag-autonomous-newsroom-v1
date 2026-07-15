<?php
/**
 * TEMPORARY READ-ONLY DIAGNOSTIC — dumps the mag-perf-fixes plugin's main
 * PHP file content via a REST route, admin-gated. Deactivate/delete after use.
 */
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/dump-plugin', array(
        'methods' => 'GET',
        'callback' => function () {
            $path = WP_PLUGIN_DIR . '/mag-perf-fixes/mag-perf-fixes.php';
            if (!file_exists($path)) {
                // try to find the actual main file if named differently
                $dir = WP_PLUGIN_DIR . '/mag-perf-fixes/';
                $files = is_dir($dir) ? scandir($dir) : array();
                return new WP_REST_Response(array('error' => 'main file not found', 'dir_listing' => $files), 404);
            }
            return new WP_REST_Response(array(
                'path' => $path,
                'size' => filesize($path),
                'mtime' => filemtime($path),
                'content' => file_get_contents($path),
            ), 200);
        },
        'permission_callback' => function () {
            return current_user_can('manage_options');
        },
    ));
});
