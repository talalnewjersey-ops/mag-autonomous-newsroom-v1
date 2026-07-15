<?php
/**
 * TEMPORARY WRITE-ONCE DIAGNOSTIC — safely overwrites a single plugin file
 * ONLY if its current sha256 matches the expected "before" hash supplied in
 * the request, preventing a clobber if the file changed since it was read.
 * Deactivate/delete after use.
 */
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/safe-write-plugin-file', array(
        'methods' => 'POST',
        'callback' => function ($request) {
            $path = WP_PLUGIN_DIR . '/mag-perf-fixes/mag-perf-fixes.php';
            if (!file_exists($path)) {
                return new WP_REST_Response(array('error' => 'file not found'), 404);
            }
            $current = file_get_contents($path);
            $current_hash = hash('sha256', $current);

            $expected_before_hash = $request->get_param('expected_before_hash');
            $new_content_b64 = $request->get_param('new_content_b64');

            if ($current_hash !== $expected_before_hash) {
                return new WP_REST_Response(array(
                    'error' => 'hash mismatch, refusing to write',
                    'current_hash' => $current_hash,
                    'expected' => $expected_before_hash,
                ), 409);
            }

            $new_content = base64_decode($new_content_b64);
            if ($new_content === false || strlen($new_content) < 100) {
                return new WP_REST_Response(array('error' => 'invalid new content'), 400);
            }

            $written = file_put_contents($path, $new_content);
            $after = file_get_contents($path);

            return new WP_REST_Response(array(
                'bytes_written' => $written,
                'before_hash' => $current_hash,
                'after_hash' => hash('sha256', $after),
                'after_size' => strlen($after),
            ), 200);
        },
        'permission_callback' => function () {
            return current_user_can('manage_options');
        },
    ));
});
