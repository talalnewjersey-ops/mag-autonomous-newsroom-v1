<?php
/**
 * Plugin Name: MAG Performance & Accessibility Fixes
 * Plugin URI:  ***
 * Description: Corrige les erreurs techniques identifiées par Lighthouse sur moneyabroadguide.com — contrastes accessibilité, optimisation des fonts, preconnect, aria-labels sur liens dupliqués, font-display swap. Réversible : désactive le plugin pour tout annuler.
 * Version:     1.0.0
 * Author:      Talal (with Claude)
 * License:     GPL v2 or later
 * Text Domain: mag-perf-fixes
 *
 * Philosophie : tous les fixes sont opt-in via constantes définies en haut du fichier.
 * Aucune modification destructive. Désactiver le plugin = retour à l'état initial.
 */

// Sécurité : empêcher l'accès direct au fichier
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// =========================================================================
// CONFIGURATION — désactive un fix en mettant la valeur à false
// =========================================================================
define( 'MAG_FIX_CONTRAST',      true ); // CSS pour corriger les contrastes (a11y 96→100)
define( 'MAG_FIX_FONT_PRECONNECT', false ); // désactivé 2026-07-15 : fonts auto-hébergées (homepage/Start Here/financial-topics), preconnect Google Fonts devenu inutile
define( 'MAG_FIX_FONT_DISPLAY',  true ); // font-display: swap forcé sur Google Fonts
define( 'MAG_FIX_ARIA_LABELS',   true ); // aria-label sur liens dupliqués "Banking Guide"
define( 'MAG_FIX_DEFER_SCRIPTS', true ); // defer sur les scripts non critiques
define( 'MAG_FIX_LAZY_IFRAMES',  true ); // loading="lazy" sur les iframes
define( 'MAG_FIX_REMOVE_EMOJI',  true ); // Supprime le script emoji WP (économise ~15 KB)


// =========================================================================
// FIX 1 — CSS contrastes (Lighthouse a11y 96→100)
// =========================================================================
if ( MAG_FIX_CONTRAST ) {
    add_action( 'wp_head', 'mag_fix_contrast_css', 999 );
    function mag_fix_contrast_css() {
        ?>
        <style id="mag-contrast-fixes">
        /* MAG Performance Plugin — Fix Lighthouse contrast issues */
        .h-badge { color: #1a1a1a !important; }
        .sbar .sbl { color: #2d2d2d !important; }
        .prow-tag { color: #1a1a1a !important; }
        .prow-save { color: #0d6b3f !important; }
        .nt { color: #4a4a4a !important; }
        footer .nav a,
        footer span { color: #2d2d2d !important; }
        </style>
        <?php
    }
}


// =========================================================================
// FIX 2 — Preconnect vers fonts.gstatic.com (gain LCP ~200-400ms)
// =========================================================================
if ( MAG_FIX_FONT_PRECONNECT ) {
    add_action( 'wp_head', 'mag_add_font_preconnect', 1 );
    function mag_add_font_preconnect() {
        echo '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>' . "\n";
        // googleapis est probablement déjà preconnecté par Astra, on l'ajoute par sécurité
        echo '<link rel="preconnect" href="https://fonts.googleapis.com">' . "\n";
        // dns-prefetch en fallback pour les vieux navigateurs
        echo '<link rel="dns-prefetch" href="https://fonts.gstatic.com">' . "\n";
    }
}


// =========================================================================
// FIX 3 — Force font-display: swap sur les Google Fonts
// (évite le FOIT et améliore le LCP)
// =========================================================================
if ( MAG_FIX_FONT_DISPLAY ) {
    add_filter( 'style_loader_src', 'mag_add_font_display_swap', 10, 2 );
    function mag_add_font_display_swap( $src, $handle ) {
        if ( strpos( $src, 'fonts.googleapis.com' ) !== false ) {
            // Si display=swap n'est pas déjà dans l'URL, on l'ajoute
            if ( strpos( $src, 'display=' ) === false ) {
                $src = add_query_arg( 'display', 'swap', $src );
            }
        }
        return $src;
    }
}


// =========================================================================
// FIX 4 — aria-label sur les liens dupliqués "Read Full Banking Guide"
// (Lighthouse signale "Identical links same purpose")
// =========================================================================
if ( MAG_FIX_ARIA_LABELS ) {
    add_filter( 'the_content', 'mag_fix_duplicate_links', 999 );
    add_action( 'wp_footer', 'mag_fix_duplicate_links_js' );

    function mag_fix_duplicate_links( $content ) {
        // Fix pour les liens dans le contenu de page
        $content = preg_replace_callback(
            '/<a([^>]*?)href="([^"]*banking-newcomers-(usa|canada)[^"]*)"([^>]*?)>(.*?)<\/a>/is',
            function( $matches ) {
                $href    = $matches[2];
                $country = strtoupper( $matches[3] );
                $attrs1  = $matches[1];
                $attrs2  = $matches[4];
                $text    = $matches[5];

                // Si aria-label déjà présent, on ne touche pas
                if ( strpos( $attrs1 . $attrs2, 'aria-label' ) !== false ) {
                    return $matches[0];
                }

                $aria = ' aria-label="Read Full Banking Guide for ' . $country . '"';
                return '<a' . $attrs1 . 'href="' . $href . '"' . $attrs2 . $aria . '>' . $text . '</a>';
            },
            $content
        );
        return $content;
    }

    // Fallback JS pour les liens hors contenu (header, footer, widgets, blocs)
    function mag_fix_duplicate_links_js() {
        ?>
        <script id="mag-aria-labels">
        (function(){
            document.querySelectorAll('a[href*="banking-newcomers-usa"]').forEach(function(a){
                if (!a.hasAttribute('aria-label')) {
                    a.setAttribute('aria-label', 'Read Full Banking Guide for USA');
                }
            });
            document.querySelectorAll('a[href*="banking-newcomers-canada"]').forEach(function(a){
                if (!a.hasAttribute('aria-label')) {
                    a.setAttribute('aria-label', 'Read Full Banking Guide for Canada');
                }
            });
        })();
        </script>
        <?php
    }
}


// =========================================================================
// FIX 5 — Defer des scripts non critiques (réduit le TBT et le render-blocking)
// On exclut jQuery et les scripts qui pourraient casser
// =========================================================================
if ( MAG_FIX_DEFER_SCRIPTS ) {
    add_filter( 'script_loader_tag', 'mag_defer_scripts', 10, 3 );
    function mag_defer_scripts( $tag, $handle, $src ) {
        // Liste des scripts à NE PAS defer (critiques ou dépendances)
        $exclude = array(
            'jquery',
            'jquery-core',
            'jquery-migrate',
            'wp-polyfill',
        );

        if ( in_array( $handle, $exclude, true ) ) {
            return $tag;
        }

        // Pas de defer dans l'admin
        if ( is_admin() ) {
            return $tag;
        }

        // Si déjà defer/async présent, on ne touche pas
        if ( strpos( $tag, ' defer' ) !== false || strpos( $tag, ' async' ) !== false ) {
            return $tag;
        }

        return str_replace( '<script ', '<script defer ', $tag );
    }
}


// =========================================================================
// FIX 6 — loading="lazy" sur tous les iframes (YouTube, embeds, etc.)
// =========================================================================
if ( MAG_FIX_LAZY_IFRAMES ) {
    add_filter( 'the_content', 'mag_lazy_iframes', 999 );
    function mag_lazy_iframes( $content ) {
        if ( is_admin() || is_feed() ) {
            return $content;
        }
        // Ajoute loading="lazy" aux iframes qui n'en ont pas
        $content = preg_replace_callback(
            '/<iframe([^>]*?)>/i',
            function( $m ) {
                if ( strpos( $m[1], 'loading=' ) !== false ) {
                    return $m[0];
                }
                return '<iframe loading="lazy"' . $m[1] . '>';
            },
            $content
        );
        return $content;
    }
}


// =========================================================================
// FIX 7 — Supprimer le script emoji WordPress (~15 KB économisés)
// Si tu utilises beaucoup d'emojis natifs, mets MAG_FIX_REMOVE_EMOJI à false
// =========================================================================
if ( MAG_FIX_REMOVE_EMOJI ) {
    add_action( 'init', 'mag_disable_emojis' );
    function mag_disable_emojis() {
        remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
        remove_action( 'admin_print_scripts', 'print_emoji_detection_script' );
        remove_action( 'wp_print_styles', 'print_emoji_styles' );
        remove_action( 'admin_print_styles', 'print_emoji_styles' );
        remove_filter( 'the_content_feed', 'wp_staticize_emoji' );
        remove_filter( 'comment_text_rss', 'wp_staticize_emoji' );
        remove_filter( 'wp_mail', 'wp_staticize_emoji_for_email' );
        add_filter( 'tiny_mce_plugins', 'mag_disable_emojis_tinymce' );
        add_filter( 'wp_resource_hints', 'mag_disable_emojis_remove_dns_prefetch', 10, 2 );
    }
    function mag_disable_emojis_tinymce( $plugins ) {
        if ( is_array( $plugins ) ) {
            return array_diff( $plugins, array( 'wpemoji' ) );
        }
        return array();
    }
    function mag_disable_emojis_remove_dns_prefetch( $urls, $relation_type ) {
        if ( 'dns-prefetch' === $relation_type ) {
            $urls = array_diff( $urls, array( 'https://s.w.org/images/core/emoji/' ) );
        }
        return $urls;
    }
}


// =========================================================================
// PAGE D'ADMIN — pour voir l'état des fixes appliqués
// =========================================================================
add_action( 'admin_menu', 'mag_perf_admin_menu' );
function mag_perf_admin_menu() {
    add_options_page(
        'MAG Performance Fixes',
        'MAG Perf Fixes',
        'manage_options',
        'mag-perf-fixes',
        'mag_perf_admin_page'
    );
}

function mag_perf_admin_page() {
    $fixes = array(
        'MAG_FIX_CONTRAST'       => array( 'Contrast CSS (a11y)',       MAG_FIX_CONTRAST ),
        'MAG_FIX_FONT_PRECONNECT'=> array( 'Font preconnect (LCP)',     MAG_FIX_FONT_PRECONNECT ),
        'MAG_FIX_FONT_DISPLAY'   => array( 'Font-display: swap',        MAG_FIX_FONT_DISPLAY ),
        'MAG_FIX_ARIA_LABELS'    => array( 'aria-label sur liens dupliqués', MAG_FIX_ARIA_LABELS ),
        'MAG_FIX_DEFER_SCRIPTS'  => array( 'Defer scripts non critiques',    MAG_FIX_DEFER_SCRIPTS ),
        'MAG_FIX_LAZY_IFRAMES'   => array( 'Lazy load iframes',         MAG_FIX_LAZY_IFRAMES ),
        'MAG_FIX_REMOVE_EMOJI'   => array( 'Désactiver script emoji WP',MAG_FIX_REMOVE_EMOJI ),
    );
    ?>
    <div class="wrap">
        <h1>MAG Performance &amp; Accessibility Fixes</h1>
        <p>Plugin custom pour <strong>moneyabroadguide.com</strong>. Tous les fixes sont activés par défaut. Pour désactiver un fix individuellement, édite le fichier <code>mag-perf-fixes.php</code> et passe la constante correspondante à <code>false</code>.</p>

        <h2>État des fixes</h2>
        <table class="widefat striped" style="max-width:700px">
            <thead>
                <tr><th>Fix</th><th>Constante</th><th>État</th></tr>
            </thead>
            <tbody>
                <?php foreach ( $fixes as $const => $info ) : ?>
                    <tr>
                        <td><?php echo esc_html( $info[0] ); ?></td>
                        <td><code><?php echo esc_html( $const ); ?></code></td>
                        <td>
                            <?php if ( $info[1] ) : ?>
                                <span style="color:#0d6b3f;font-weight:600">✓ Actif</span>
                            <?php else : ?>
                                <span style="color:#999">— Désactivé</span>
                            <?php endif; ?>
                        </td>
                    </tr>
                <?php endforeach; ?>
            </tbody>
        </table>

        <h2 style="margin-top:30px">Ce que ce plugin ne fait PAS</h2>
        <p>Certains fixes nécessitent une action manuelle hors du code :</p>
        <ul style="list-style:disc;padding-left:20px">
            <li><strong>Logo en base64</strong> : à corriger dans <em>Apparence → Personnaliser → Identité du site</em>, ou en désactivant l'option "inline images" du plugin de cache/optimisation.</li>
            <li><strong>Self-host des Google Fonts</strong> : à activer dans <em>Astra → Settings → Performance → Load Google Fonts Locally</em>.</li>
            <li><strong>Réduction des graisses de fonts</strong> : à régler dans <em>Personnaliser → Typographie globale</em>.</li>
            <li><strong>Headers HTTP de sécurité</strong> (HSTS, CSP, X-Frame-Options) : à configurer dans Cloudflare → Rules → Transform Rules.</li>
        </ul>

        <h2 style="margin-top:30px">Test après activation</h2>
        <ol>
            <li>Vide tous tes caches (Cloudflare + LiteSpeed Cache si actif).</li>
            <li>Lance <a href="https://pagespeed.web.dev/analysis?url=***" target="_blank">PageSpeed Insights</a>.</li>
            <li>Compare avec le score précédent (82 mobile, baseline).</li>
            <li>Si quelque chose casse, désactive le plugin → tout revient à l'état initial.</li>
        </ol>
    </div>
    <?php
}


// =========================================================================
// ACTIVATION HOOK — message de bienvenue
// =========================================================================
register_activation_hook( __FILE__, 'mag_perf_activate' );
function mag_perf_activate() {
    set_transient( 'mag_perf_activated', true, 30 );
}

add_action( 'admin_notices', 'mag_perf_admin_notice' );
function mag_perf_admin_notice() {
    if ( get_transient( 'mag_perf_activated' ) ) {
        delete_transient( 'mag_perf_activated' );
        ?>
        <div class="notice notice-success is-dismissible">
            <p><strong>MAG Performance Fixes activé.</strong> Va voir <a href="<?php echo esc_url( admin_url( 'options-general.php?page=mag-perf-fixes' ) ); ?>">Réglages → MAG Perf Fixes</a> pour vérifier l'état des fixes. N'oublie pas de vider tes caches.</p>
        </div>
        <?php
    }
}
