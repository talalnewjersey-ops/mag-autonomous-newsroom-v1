add_action('rest_api_init', function() {
    register_rest_route('mag/v1', '/diag-front-page', [
        'methods' => 'GET',
        'callback' => function() {
            global $wp_filter;
            $hooks_info = [];
            foreach (['template_redirect', 'template_include', 'the_content', 'init'] as $hook_name) {
                $entries = [];
                if (isset($wp_filter[$hook_name])) {
                    foreach ($wp_filter[$hook_name]->callbacks as $priority => $callbacks) {
                        foreach ($callbacks as $cb) {
                            $fn = $cb['function'];
                            if (is_string($fn)) {
                                $label = $fn;
                            } elseif (is_array($fn)) {
                                $obj = $fn[0];
                                $label = (is_object($obj) ? get_class($obj) : $obj) . '::' . $fn[1];
                            } elseif ($fn instanceof Closure) {
                                try {
                                    $ref = new ReflectionFunction($fn);
                                    $label = 'Closure @ ' . str_replace(ABSPATH, '', $ref->getFileName()) . ':' . $ref->getStartLine();
                                } catch (Exception $e) {
                                    $label = 'Closure (unreflectable)';
                                }
                            } else {
                                $label = 'unknown';
                            }
                            $entries[] = ['priority' => $priority, 'callback' => $label];
                        }
                    }
                }
                $hooks_info[$hook_name] = $entries;
            }
            return [
                'show_on_front' => get_option('show_on_front'),
                'page_on_front' => get_option('page_on_front'),
                'page_on_front_title' => get_the_title((int) get_option('page_on_front')),
                'active_plugins' => get_option('active_plugins'),
                'hooks' => $hooks_info,
            ];
        },
        'permission_callback' => function() { return current_user_can('manage_options'); },
    ]);
}, 999);
