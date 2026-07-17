<?php
add_action('rest_api_init', function () {
    register_rest_route('mag-diag/v1', '/elementor-relabel', [
        'methods' => 'POST',
        'callback' => function (WP_REST_Request $req) {
            $pid = (int) $req->get_param('pid');
            $dry = $req->get_param('dry') === '1';
            if (!$pid) return ['error' => 'missing pid'];
            $data = get_post_meta($pid, '_elementor_data', true);
            if (!$data) return ['error' => 'no _elementor_data found'];

            $ebook = 'https:\/\/moneyabroadguide.com\/ebook-build-your-credit-score-usa\/';

            if ($pid === 1364) {
                $wrong = 'https:\/\/moneyabroadguide.com\/how-to-build-credit-in-usa-without-ssn\/';
                $pairs = [
                    ['old' => 'href=\"' . $wrong . '\">Get the eBook &rarr;',
                     'new' => 'href=\"' . $ebook . '\" target=\"_blank\" rel=\"noopener\">Get the eBook &rarr;'],
                    ['old' => 'href=\"' . $wrong . '\">Get the Credit-Building eBook &rarr;',
                     'new' => 'href=\"' . $ebook . '\" target=\"_blank\" rel=\"noopener\">Get the Credit-Building eBook &rarr;'],
                    ['old' => 'href=\"' . $wrong . '\">Get the eBook Today &rarr;',
                     'new' => 'href=\"' . $ebook . '\" target=\"_blank\" rel=\"noopener\">Get the eBook Today &rarr;'],
                ];
            } elseif ($pid === 1369) {
                $wrong = 'https:\/\/moneyabroadguide.com\/building-credit-canada-newcomers-2026\/';
                $pairs = [
                    ['old' => 'href=\"' . $wrong . '\" class=\"mag-hero-cta\">Get the eBook &rarr;',
                     'new' => 'href=\"' . $ebook . '\" target=\"_blank\" rel=\"noopener\" class=\"mag-hero-cta\">Get the eBook &rarr;'],
                    ['old' => 'href=\"' . $wrong . '\">Get the eBook &rarr;',
                     'new' => 'href=\"' . $ebook . '\" target=\"_blank\" rel=\"noopener\">Get the eBook &rarr;'],
                    ['old' => 'href=\"' . $wrong . '\">Get the Credit-Building eBook &rarr;',
                     'new' => 'href=\"' . $ebook . '\" target=\"_blank\" rel=\"noopener\">Get the Credit-Building eBook &rarr;'],
                    ['old' => 'href=\"' . $wrong . '\">Get the eBook Today &rarr;',
                     'new' => 'href=\"' . $ebook . '\" target=\"_blank\" rel=\"noopener\">Get the eBook Today &rarr;'],
                ];
            } else {
                return ['error' => 'unsupported pid'];
            }

            $result = ['pid' => $pid, 'dry_run' => $dry, 'checks' => []];
            $new_data = $data;
            $all_ok = true;
            foreach ($pairs as $i => $pair) {
                $cnt = substr_count($new_data, $pair['old']);
                $result['checks'][] = ['index' => $i, 'old_count' => $cnt, 'snippet' => substr($pair['old'], -60)];
                if ($cnt !== 1) { $all_ok = false; continue; }
                $new_data = str_replace($pair['old'], $pair['new'], $new_data);
            }
            $result['all_exactly_one'] = $all_ok;
            if (!$all_ok) { $result['error'] = 'not all pairs matched exactly once, refusing to write'; return $result; }

            $result['old_length'] = strlen($data);
            $result['new_length'] = strlen($new_data);

            if (!$dry) {
                $updated = update_post_meta($pid, '_elementor_data', wp_slash($new_data));
                $result['update_post_meta_result'] = $updated;
                delete_post_meta($pid, '_elementor_css');
                if (class_exists('\Elementor\Plugin')) {
                    try {
                        \Elementor\Plugin::$instance->files_manager->clear_cache();
                        $result['elementor_cache_cleared'] = true;
                    } catch (\Throwable $e) {
                        $result['elementor_cache_clear_error'] = $e->getMessage();
                    }
                }
            }

            return $result;
        },
        'permission_callback' => '__return_true',
    ]);
});
