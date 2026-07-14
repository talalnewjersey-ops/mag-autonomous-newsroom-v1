add_action('rest_api_init', function() {
    register_rest_route('mag/v1', '/list-plugin-dir', [
        'methods' => 'GET',
        'callback' => function() {
            $dir = WP_PLUGIN_DIR . '/moneyabroadguide-fusion-v51-wordpress';
            $result = ['dir' => $dir, 'exists' => is_dir($dir)];
            if (is_dir($dir)) {
                $files = [];
                $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS));
                foreach ($iterator as $file) {
                    $files[] = [
                        'path' => str_replace($dir . '/', '', $file->getPathname()),
                        'size' => $file->getSize(),
                        'mtime' => date('Y-m-d H:i:s', $file->getMTime()),
                    ];
                }
                $result['files'] = $files;
            }
            return $result;
        },
        'permission_callback' => function() { return current_user_can('manage_options'); },
    ]);
}, 999);
