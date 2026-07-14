<?php

// 301 Redirect: /home/ → homepage
add_action('template_redirect', function() {
    if (is_page('home')) {
        wp_redirect(home_url('/'), 301);
        exit;
    }
});


// Dynamic Sitemap
add_action('init', function() {
    if (isset($_GET['sitemap']) && $_GET['sitemap'] === 'xml') {
        header('Content-Type: application/xml; charset=UTF-8');
        $pages = get_pages(['post_status' => 'publish']);
        $posts = get_posts(['numberposts' => -1, 'post_status' => 'publish']);
        echo '<?xml version="1.0" encoding="UTF-8"?>';
        echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">';
        echo '<url><loc>' . home_url('/') . '</loc><priority>1.0</priority></url>';
        foreach($pages as $page) {
            $page_priority = (get_page_uri($page->ID) === 'financial-topics') ? '0.9' : '0.8';
            echo '<url><loc>' . get_permalink($page->ID) . '</loc>
                  <lastmod>' . date('Y-m-d', strtotime($page->post_modified)) . '</lastmod>
                  <priority>' . $page_priority . '</priority></url>';
        }
        foreach($posts as $post) {
            echo '<url><loc>' . get_permalink($post->ID) . '</loc>
                  <lastmod>' . date('Y-m-d', strtotime($post->post_modified)) . '</lastmod>
                  <priority>0.6</priority></url>';
        }
        echo '</urlset>';
        exit;
    }
});

// Explicit robots index signal for /financial-topics/
add_action('wp_head', function() {
    if (is_page('financial-topics')) {
        echo '<meta name="robots" content="index, follow" />' . "\n";
    }
}, 1);

// Redirect about-us to about
add_action('template_redirect', function() {
    if (is_page('about-us')) {
        wp_redirect(home_url('/about/'), 301);
        exit;
    }
});

// 301 Redirects for missing URLs referenced in sitemap
add_action('template_redirect', function() {
    $redirects = [
        '/best-banks-newcomers-canada/' =>
            '/best-bank-for-newcomers-to-canada-how-to-open-your-first-account-step-by-step-2026-guide/',
    ];
    $current = $_SERVER['REQUEST_URI'];
    foreach ($redirects as $from => $to) {
        if (strpos($current, $from) !== false) {
            wp_redirect(home_url($to), 301);
            exit;
        }
    }
});


/**
 * Plugin Name: MoneyAbroadGuide Fusion Uploaded HTML
 * Description: Installe la landing page complète depuis le fichier HTML fourni et la définit comme page d'accueil.
 * Version: 5.1.0
 * Requires at least: 6.0
 * Requires PHP: 8.0
 */
if (!defined('ABSPATH')) exit;
class MoneyAbroadGuideFusionUploadedHtml {
    const PAGE_SLUG = 'moneyabroadguide-fusion-home';
    public function __construct() {
        add_action('init', [$this, 'ensure_homepage_exists']);
        add_filter('template_include', [$this, 'use_blank_template'], 999);
    }
    public static function activate() {
        $instance = new self();
        $instance->ensure_homepage_exists();
        flush_rewrite_rules();
    }
    public static function deactivate() {
        flush_rewrite_rules();
    }
    public function ensure_homepage_exists() {
        $page = get_page_by_path(self::PAGE_SLUG);
        $page_data = [
            'post_title' => 'Home',
            'post_name' => self::PAGE_SLUG,
            'post_type' => 'page',
            'post_status' => 'publish',
            'post_content' => 'MoneyAbroadGuide landing page',
        ];
        if ($page) {
            $page_data['ID'] = $page->ID;
            $page_id = wp_update_post($page_data, true);
        } else {
            $page_id = wp_insert_post($page_data, true);
        }
        if (!is_wp_error($page_id) && $page_id) {
            update_option('show_on_front', 'page');
            update_option('page_on_front', $page_id);
            update_option('page_for_posts', 0);
            wp_cache_flush();
        }
        return $page_id;
    }
    public function use_blank_template($template) {
        if (is_admin() || !(is_front_page() || is_page(self::PAGE_SLUG))) return $template;
        status_header(200);
        $wpforms_probe = do_shortcode('[wpforms id="48766"]');
        $wpforms_token = '';
        $wpforms_token_time = '';
        if (preg_match('/data-token="([^"]+)"/', $wpforms_probe, $wpforms_m)) { $wpforms_token = $wpforms_m[1]; }
        if (preg_match('/data-token-time="([^"]+)"/', $wpforms_probe, $wpforms_m2)) { $wpforms_token_time = $wpforms_m2[1]; }
        // nocache_headers(); // désactivé le 11/07/2026 — forçait no-store sur la homepage (TTFB 10s).
        // À reporter dans le projet source Fusion (sera écrasé si ré-upload).
        echo '<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover">
<title>Money Abroad Guide — Free Finance Guides for Newcomers</title>
<meta name="description" content="Independent financial guides for newcomers to the USA & Canada. Compare money transfer fees, build credit, and access free guides.">
<meta name="author" content="MoneyAbroadGuide Financial Guides">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preload" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Lora:wght@600;700&display=swap" as="style" onload="this.onload=null;this.rel=\'stylesheet\'">
<noscript><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Lora:wght@600;700&display=swap" rel="stylesheet"></noscript>
<style>
/* CLS FIX 2026-07-14 -- reserve space for hero calculator JS-populated results (prevents layout shift) */
#hero-results{min-height:290px}
#hero-save-banner{min-height:80px;display:flex;align-items:center;justify-content:center}
@font-face{font-family:"Inter-fallback";src:local("Segoe UI"),local("Roboto"),local("Helvetica Neue"),local("Arial");ascent-override:96.88%;descent-override:24.12%;line-gap-override:0%;size-adjust:100%}
@font-face{font-family:"Lora-fallback";src:local("Georgia");ascent-override:100.6%;descent-override:27.4%;line-gap-override:0%;size-adjust:100%}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}html,body{overflow-x:hidden}
:root{
  --marine:#001f3f;--marine-md:#0a2d52;--marine-dk:#001429;--marine-lt:#e8f1f8;
  --green:#05825f;--green-md:#07a076;--green-lt:#e3f5ef;--green-br:#0ac489;
  --gold:#f5a623;--gold-lt:#fff8ed;
  --g50:#f9fafb;--g100:#f3f4f6;--g200:#e5e7eb;--g300:#d1d5db;
  --g400:#9ca3af;--g500:#6b7280;--g600:#4b5563;--g700:#374151;--g900:#111827;
  --sh-sm:0 1px 2px rgba(0,0,0,.05);
  --sh-md:0 4px 6px -1px rgba(0,0,0,.1);
  --sh-lg:0 10px 15px -3px rgba(0,0,0,.1);
  --sh-xl:0 20px 25px -5px rgba(0,0,0,.1);
  --sh-2xl:0 25px 50px -12px rgba(0,0,0,.25);
  --fn:"Inter","Inter-fallback",system-ui,sans-serif;--fs:"Lora","Lora-fallback",Georgia,serif;
}
html{scroll-behavior:smooth}
body{font-family:var(--fn);background:#fff;color:var(--g900);line-height:1.55;font-size:15px;overflow-x:hidden}
/* TOP STRIP */
.ts{background:var(--marine-dk);padding:7px 4%;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:5px;font-size:11px;color:rgba(255,255,255,.65)}
.ts a{color:#7ec8a0;text-decoration:none;font-weight:700}
.ts-b{background:rgba(255,255,255,.12);padding:2px 9px;border-radius:20px;font-size:10px;font-weight:700}
/* NAV */
.nav{position:sticky;top:0;z-index:500;background:rgba(255,255,255,.98);backdrop-filter:blur(12px);border-bottom:1px solid var(--g200);box-shadow:var(--sh-sm)}
.nv{max-width:1300px;margin:0 auto;padding:0 20px;height:64px;display:flex;align-items:center}
.logo-a{display:flex;flex-direction:column;text-decoration:none;margin-right:22px;flex-shrink:0}
.logo-a img{height:50px;width:auto;display:block}
.nav-list{display:flex;align-items:stretch;list-style:none;height:64px;flex:1}
.ni{position:relative;display:flex;align-items:stretch}
.na{display:flex;align-items:center;gap:4px;padding:0 11px;height:100%;font-size:12.5px;font-weight:600;color:var(--g600);text-decoration:none;cursor:pointer;border:none;border-bottom:3px solid transparent;background:transparent;font-family:var(--fn);transition:color .18s,border-color .18s;white-space:nowrap}
.na:hover,.na.act{color:var(--green);border-bottom-color:var(--green)}
.na svg{width:11px;height:11px;opacity:.4;transition:transform .18s}

.dr{position:absolute;top:calc(100% + 1px);left:50%;transform:translateX(-50%);background:#fff;border:1px solid var(--g200);border-radius:14px;box-shadow:var(--sh-xl);padding:7px;display:none;z-index:600;animation:df .14s ease;will-change:transform}
@keyframes df{from{opacity:0;transform:translateX(-50%) translateY(-5px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}

.mg{padding:20px;min-width:640px}
.mg3{grid-template-columns:1fr 1fr 1fr;gap:16px}
.mg2{grid-template-columns:1fr 1fr;gap:16px;min-width:460px}
.dc{font-size:9px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--g400);margin-bottom:9px;padding-bottom:6px;border-bottom:1px solid var(--g200)}
.dl{display:flex;align-items:flex-start;gap:8px;padding:8px;border-radius:8px;text-decoration:none;transition:background .13s;margin-bottom:1px}
.dl:hover{background:var(--g50)}
.dic{width:30px;height:30px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.dt2{font-size:12.5px;font-weight:700;color:var(--g900);display:block;line-height:1.3}
.dd2{font-size:10.5px;color:var(--g500);display:block;margin-top:1px}
.dfeat{background:linear-gradient(135deg,var(--green-lt),#d4f0e6);border-radius:10px;padding:14px;border:1px solid rgba(5,130,95,.15)}
.dfeat-tag{font-size:9px;font-weight:800;letter-spacing:.07em;text-transform:uppercase;color:var(--green);margin-bottom:5px}
.dfeat-h{font-size:12.5px;font-weight:800;color:var(--g900);margin-bottom:4px;line-height:1.3}
.dfeat-p{font-size:10.5px;color:var(--g500);line-height:1.5;margin-bottom:9px}
.dfeat-btn{display:inline-block;background:var(--green);color:#fff;padding:6px 12px;border-radius:50px;font-size:11px;font-weight:700;text-decoration:none}
.ds{display:flex;align-items:center;gap:9px;padding:9px 12px;border-radius:8px;text-decoration:none;font-size:12.5px;font-weight:600;color:var(--g900);transition:background .13s}
.ds:hover{background:var(--g50);color:var(--green)}
.nr{display:flex;align-items:center;gap:8px;margin-left:auto;flex-shrink:0}
.ng{padding:7px 14px;border-radius:8px;border:1.5px solid var(--g200);font-size:12px;font-weight:700;color:var(--marine);text-decoration:none;transition:all .18s;white-space:nowrap}
.ng:hover{background:var(--marine-lt);border-color:var(--marine)}
.nc{padding:8px 18px;border-radius:50px;background:var(--green);color:#fff;font-size:12.5px;font-weight:800;text-decoration:none;box-shadow:0 3px 10px rgba(5,130,95,.28);transition:all .18s;white-space:nowrap}
.nc:hover{background:var(--green-md);transform:translateY(-1px)}
.ham{display:none;flex-direction:column;gap:5px;cursor:pointer;background:none;border:none;padding:8px;margin-left:auto}
.ham span{display:block;width:22px;height:2px;background:var(--g900);border-radius:2px;transition:all .28s}
.ham.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}
.ham.open span:nth-child(2){opacity:0}
.ham.open span:nth-child(3){transform:rotate(-45deg) translate(5px,-5px)}
.mob{display:none;background:#fff;border-top:1px solid var(--g200);padding:14px 20px 20px}
.mob.open{display:block}
.mh{font-size:10px;font-weight:800;color:var(--g400);text-transform:uppercase;letter-spacing:.08em;margin:12px 0 7px;padding-bottom:4px;border-bottom:1px solid var(--g200)}
.mob a{display:block;padding:9px 0;font-size:13px;font-weight:600;color:var(--g900);text-decoration:none;border-bottom:1px solid var(--g200)}
.mob a:hover{color:var(--green)}
@media(max-width:1020px){.ts{display:none}.nav-list,.nr{display:none}.ham{display:flex}.nv{padding:0 14px;height:56px}.logo-a img{height:40px}}
@media(min-width:1021px){.mob{display:none!important}}
/* HERO - slider style from new page */
.hero{background:linear-gradient(135deg,var(--g50) 0%,#fff 100%);padding:24px 4% 44px}
.hero-grid{max-width:1280px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:start}
@media(max-width:880px){.hero-grid{grid-template-columns:1fr}.hero-calc{display:none}}
@media(max-width:880px){.hero{min-height:460px}}
@media(max-width:650px){.hero{min-height:510px}}
@media(max-width:480px){.hero{min-height:580px}}
@media(max-width:340px){.hero{min-height:650px}}
.h-badge{display:inline-flex;align-items:center;gap:7px;background:var(--green-lt);color:var(--green);padding:5px 14px;border-radius:50px;font-size:11px;font-weight:800;letter-spacing:.04em;margin-bottom:16px;border:1px solid rgba(5,130,95,.2)}
.pl{width:7px;height:7px;background:#22c55e;border-radius:50%;position:relative;will-change:transform}
.pl::after{content:"";position:absolute;inset:0;border-radius:50%;background:rgba(34,197,94,.4);animation:blink 2s infinite}
@keyframes blink{0%,100%{transform:scale(1);opacity:.6}60%{transform:scale(2.2);opacity:0}}
h1{font-family:var(--fs);font-size:clamp(28px,4.2vw,50px);font-weight:700;line-height:1.1;letter-spacing:-.3px;color:var(--g900);margin-bottom:14px}
h1 .em{color:var(--green)}
.hero-sub{font-size:15.5px;color:var(--g600);line-height:1.7;margin-bottom:18px;max-width:480px}
.trust-row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px}
.trust-b{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--g500);font-weight:500}
.stars{color:#fbbf24;font-weight:700}
.ctas{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:0}
.btn-pill{background:var(--green);color:#fff;padding:12px 26px;border-radius:50px;font-size:14px;font-weight:800;text-decoration:none;display:inline-flex;align-items:center;gap:7px;transition:all .22s;box-shadow:0 4px 14px rgba(5,130,95,.3)}
.btn-pill:hover{background:var(--green-md);transform:translateY(-2px)}
.btn-ghost{background:#fff;color:var(--g900);padding:12px 22px;border-radius:50px;font-size:14px;font-weight:700;text-decoration:none;border:1.5px solid var(--g200);transition:all .2s}
.btn-ghost:hover{border-color:var(--green);color:var(--green)}
/* HERO CALCULATOR - slider style */
.hero-calc{background:#fff;border-radius:24px;box-shadow:var(--sh-2xl);padding:22px;border:1px solid var(--g200)}
.hc-amt-box{background:var(--g50);border-radius:16px;padding:16px;margin-bottom:14px;text-align:center}
.hc-lbl{color:var(--g500);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px}
.hc-amt{font-size:2.4rem;font-weight:800;color:var(--marine);letter-spacing:-.5px;font-family:var(--fs)}
.hc-slider{width:100%;height:5px;-webkit-appearance:none;appearance:none;background:var(--g200);border-radius:3px;outline:none;margin:12px 0 5px;cursor:pointer}
.hc-slider::-webkit-slider-thumb{-webkit-appearance:none;width:22px;height:22px;background:var(--green);border-radius:50%;cursor:pointer;box-shadow:var(--sh-md);border:2px solid #fff}
.hc-slider::-moz-range-thumb{width:22px;height:22px;background:var(--green);border-radius:50%;cursor:pointer;border:none}
.hc-range-lbls{display:flex;justify-content:space-between;font-size:10px;color:var(--g400)}
.hc-dest{margin-bottom:12px}
.hc-dest label{font-size:9.5px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:var(--g500);display:block;margin-bottom:3px}
.hc-dest select{width:100%;padding:9px 12px;border-radius:9px;border:1.5px solid var(--g200);font-size:13px;font-weight:600;font-family:var(--fn);color:var(--g900);background:var(--g50);outline:none;transition:border-color .18s}
.hc-dest select:focus{border-color:var(--green)}
/* PROVIDER ROWS - shared between hero calc and tools */
.prow{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 12px;border-radius:10px;background:var(--g50);border:1.5px solid transparent;margin-bottom:5px;transition:all .18s;cursor:pointer}
.prow:hover{background:#fff;border-color:var(--g200);transform:translateX(3px)}
.prow.prow-best{background:var(--green-lt);border-left:3px solid var(--green)}
.prow-l{flex:1}
.prow-name{font-size:13px;font-weight:700;color:var(--g900);display:flex;align-items:center;gap:6px}
.prow-tag{font-size:10px;color:var(--g500);margin-top:1px}
.prow-r{text-align:right;flex-shrink:0}
.prow-recv{font-size:13.5px;font-weight:800;color:var(--marine);font-family:var(--fs)}
.prow-fee{font-size:10px;color:var(--g500);margin-top:1px}
.prow-save{font-size:10px;color:var(--green);font-weight:700;margin-top:2px}
.best-tag{background:var(--green);color:#fff;font-size:9px;font-weight:800;padding:2px 7px;border-radius:4px}
.best-tag2{background:var(--gold);color:#451a03;font-size:9px;font-weight:800;padding:2px 7px;border-radius:4px}
.save-banner{background:linear-gradient(135deg,var(--marine),var(--marine-dk));color:#fff;border-radius:10px;padding:12px 14px;text-align:center;font-size:12.5px;line-height:1.6;margin-top:10px}
/* STATS BAR */
.sbar{background:var(--marine);display:flex;justify-content:center;flex-wrap:wrap;min-height:94px}
@media(max-width:880px){.sbar{min-height:116px}}
@media(max-width:554px){.sbar{min-height:200px}}
.sbc{flex:1;min-width:110px;max-width:170px;text-align:center;padding:18px 10px;border-right:1px solid rgba(255,255,255,.08)}
.sbc:last-child{border-right:none}
.sbn{font-family:var(--fs);font-size:26px;font-weight:700;color:var(--green-br);letter-spacing:-.6px}
.sbl{font-size:10px;color:rgba(255,255,255,.44);margin-top:2px;font-weight:600;line-height:1.4}
/* BEFORE/AFTER */
.ba-sec{padding:32px 4%}
.ba-block{max-width:900px;margin:0 auto;background:#fff;border-radius:24px;padding:28px;box-shadow:var(--sh-lg);border:1px solid var(--g200);display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:640px){.ba-block{grid-template-columns:1fr}}
.ba-card{text-align:center;padding:18px;border-radius:16px;background:var(--g50)}
.ba-before{border-left:4px solid var(--g400)}
.ba-after{border-left:4px solid var(--green)}
.ba-title{font-weight:800;font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--g600);margin-bottom:10px}
.ba-big{font-size:2rem;font-weight:800;color:var(--green);font-family:var(--fs)}
.ba-p{font-size:12.5px;color:var(--g500);line-height:1.65;margin-top:6px}
/* SECTIONS */
.sec{padding:44px 4%}
.co{max-width:1300px;margin:0 auto}
.bg-w{background:#fff}
.bg-s{background:var(--g50)}
.bg-dk{background:var(--marine)}
.sec-hd{text-align:center;max-width:680px;margin:0 auto 28px}
.sec-hd h2{font-family:var(--fs);font-size:clamp(21px,3vw,34px);font-weight:700;line-height:1.14;letter-spacing:-.2px;color:var(--g900);margin-bottom:8px}
.sec-hd p{font-size:14px;color:var(--g500);line-height:1.7}
.stag{font-size:10px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--green);margin-bottom:7px;display:flex;align-items:center;gap:6px;justify-content:center}
.stag::before{content:"";width:14px;height:3px;background:var(--green);border-radius:2px;display:block}
/* PATH CARDS */
.path-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:24px}
@media(max-width:760px){.path-grid{grid-template-columns:1fr}}
.path-card{background:#fff;border-radius:18px;padding:20px 16px;border:1.5px solid var(--g200);transition:all .22s;display:flex;flex-direction:column}
.path-card:hover{transform:translateY(-4px);box-shadow:var(--sh-lg);border-color:var(--green)}
.path-card.feat{border:2px solid var(--green);box-shadow:0 4px 16px rgba(5,130,95,.12)}
.path-ico{font-size:2rem;margin-bottom:10px}
.path-badge{display:inline-block;background:var(--green-lt);color:var(--green);font-size:9px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;padding:3px 11px;border-radius:50px;border:1px solid rgba(5,130,95,.2);margin-bottom:10px}
.path-badge-s{background:var(--green);color:#fff;border:none}
.path-h{font-family:var(--fs);font-size:17px;font-weight:700;color:var(--g900);margin-bottom:8px;text-align:center}
.path-p{font-size:12.5px;color:var(--g500);line-height:1.7;flex:1;margin-bottom:16px;text-align:center}
.path-links{display:flex;flex-direction:column;gap:6px}
.path-lnk{display:flex;align-items:center;justify-content:center;padding:9px 14px;border-radius:50px;border:1.5px solid var(--g200);font-size:12.5px;font-weight:700;color:var(--g900);text-decoration:none;transition:all .18s}
.path-lnk:hover{border-color:var(--green);color:var(--green);background:var(--green-lt)}
.path-lnk-p{background:var(--green);color:#fff;border-color:var(--green)}
.path-lnk-p:hover{background:var(--green-md);color:#fff}
.path-lnk-o{border-color:var(--green);color:var(--green)}
.path-lnk-o:hover{background:var(--green-lt)}
/* ARTICLES */
.art-wrap{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:24px}
@media(max-width:760px){.art-wrap{grid-template-columns:1fr}}
.art-col{background:#fff;border:1.5px solid var(--g200);border-radius:18px;overflow:hidden}
.art-head{padding:13px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--g200);background:linear-gradient(135deg,var(--green-lt),#edfaf5)}
.art-flag{font-size:20px}
.art-t2{font-size:14px;font-weight:800;color:var(--g900)}
.art-s2{font-size:10px;color:var(--g500);margin-top:1px}
.art-cta-btn{margin-left:auto;background:var(--green);color:#fff;padding:5px 13px;border-radius:50px;font-size:11px;font-weight:800;text-decoration:none;white-space:nowrap;transition:background .18s}
.art-cta-btn:hover{background:var(--green-md)}
.art-list{padding:7px}
.art-item{display:flex;align-items:center;gap:10px;padding:9px 9px;border-radius:8px;text-decoration:none;transition:background .13s;border-bottom:1px solid var(--g200)}
.art-item:last-child{border-bottom:none}
.art-item:hover{background:var(--g50)}
.art-ico{width:32px;height:32px;border-radius:8px;background:var(--green-lt);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.art-tt{font-size:12.5px;font-weight:700;color:var(--g900);display:block;line-height:1.3}
.art-tg{font-size:10px;color:var(--g500);display:block;margin-top:1px;font-weight:600}
.art-arr{margin-left:auto;color:var(--g300);font-size:14px;font-weight:800;transition:color .13s}
.art-item:hover .art-arr{color:var(--green)}
/* TOOLS */
.tools-layout{display:grid;grid-template-columns:1fr;gap:16px;max-width:900px;margin:20px auto 0;align-items:start}
@media(max-width:960px){.tools-layout{grid-template-columns:1fr}.ad-col{display:none}}
.ttabs{display:flex;justify-content:center;gap:7px;flex-wrap:wrap;margin-bottom:18px}
.ttab{padding:8px 15px;border-radius:50px;border:1.5px solid var(--g200);font-size:12.5px;font-weight:700;cursor:pointer;background:#fff;color:var(--g600);font-family:var(--fn);transition:all .18s}
.ttab.on,.ttab:hover{background:var(--green);border-color:var(--green);color:#fff}
.tp{background:#fff;border:1.5px solid var(--g200);border-radius:18px;overflow:hidden;box-shadow:var(--sh-md)}
.th{padding:15px 20px 12px;border-bottom:1px solid var(--g200);background:linear-gradient(135deg,#f6fffc,#edfaf5)}
.th-h{font-size:15px;font-weight:800;color:var(--g900);margin-bottom:2px}
.th-s{font-size:11px;color:var(--g500)}
.tb{padding:18px 20px}
.fg{display:grid;grid-template-columns:1fr 1fr;gap:11px;margin-bottom:14px}
@media(max-width:500px){.fg{grid-template-columns:1fr}}
.fl label{font-size:9.5px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:var(--g500);display:block;margin-bottom:3px}
.finp,.fsel{width:100%;padding:9px 12px;border-radius:9px;border:1.5px solid var(--g200);font-size:12.5px;font-weight:600;font-family:var(--fn);color:var(--g900);background:var(--g50);outline:none;transition:border-color .18s}
.finp:focus,.fsel:focus{border-color:var(--green)}
.svb{background:linear-gradient(135deg,var(--green),var(--green-md));border-radius:10px;padding:11px 15px;color:#fff;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-top:11px}
.sv-l{font-size:10px;font-weight:700;opacity:.85;margin-bottom:2px}
.sv-a{font-family:var(--fs);font-size:19px;font-weight:700}
.sv-btn{background:#fff;color:var(--green);padding:7px 15px;border-radius:50px;font-size:11px;font-weight:800;text-decoration:none}
.sv-btn:hover{background:var(--green-lt)}
.cpills{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:13px}
.cpill{padding:5px 11px;border-radius:50px;border:1.5px solid var(--g200);font-size:11px;font-weight:700;cursor:pointer;background:#fff;color:var(--g600);font-family:var(--fn);transition:all .18s}
.cpill.on,.cpill:hover{background:var(--marine);border-color:var(--marine);color:#fff}
.srow{margin-bottom:10px}
.stop2{display:flex;justify-content:space-between;margin-bottom:3px}
.slbl2{font-size:12px;font-weight:600;color:var(--g600)}
.sval2{font-size:12px;font-weight:800;color:var(--marine);background:var(--marine-lt);padding:1px 8px;border-radius:5px}
input[type=range]{width:100%;-webkit-appearance:none;appearance:none;height:4px;border-radius:3px;background:var(--g200);outline:none}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;border-radius:50%;background:var(--green);cursor:pointer;box-shadow:var(--sh-sm);border:2px solid #fff}
input[type=range]::-moz-range-thumb{width:18px;height:18px;border-radius:50%;background:var(--green);cursor:pointer;border:none}
.bstats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:11px}
.bx{background:var(--g50);border-radius:8px;padding:9px;text-align:center;border:1px solid var(--g200)}
.bxl{font-size:9px;font-weight:700;color:var(--g400);text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px}
.bxv{font-size:14px;font-weight:800;color:var(--g900);font-family:var(--fs)}
.bxv.g{color:var(--green)}
.btip{background:linear-gradient(135deg,var(--marine-lt),var(--green-lt));border-radius:8px;padding:9px 12px;margin-top:9px;font-size:12px;font-weight:600;color:var(--marine);line-height:1.55}
.crb{margin-bottom:9px}
.crt2{display:flex;justify-content:space-between;margin-bottom:3px;font-size:11.5px;font-weight:600}
.crg2{height:9px;background:var(--g100);border-radius:5px;overflow:hidden}
.crf2{height:100%;border-radius:5px;transition:width .45s ease}
.crm2-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:11px}
.crm2{background:var(--g50);border-radius:8px;padding:9px;text-align:center;border:1px solid var(--g200)}
.cms2{font-family:var(--fs);font-size:16px;font-weight:700;color:var(--green)}
.cml2{font-size:10.5px;color:var(--g500);margin-top:2px;font-weight:600}
.cmt2{font-size:9.5px;color:var(--marine);font-weight:800;margin-top:2px;text-transform:uppercase;letter-spacing:.03em}
.ftbl{width:100%;border-collapse:collapse;font-size:12.5px}
.ftbl thead tr{background:var(--marine);color:#fff}
.ftbl th{padding:9px 12px;text-align:left;font-size:9px;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.ftbl td{padding:10px 12px;border-bottom:1px solid var(--g200);color:var(--g600);font-weight:600}
.ftbl tr:last-child td{border-bottom:none}
.ftbl .fb td{background:var(--green-lt)}
.fbb{display:inline-block;background:var(--green);color:#fff;font-size:8.5px;font-weight:800;padding:1px 5px;border-radius:3px;margin-left:3px}
.mr{background:linear-gradient(135deg,var(--marine-lt),var(--green-lt));border-radius:10px;padding:13px;margin-top:11px;text-align:center}
.mrl{font-size:9.5px;font-weight:800;color:var(--marine);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
.mrv{font-family:var(--fs);font-size:27px;font-weight:700;color:var(--green);letter-spacing:-.5px}
.mrs{font-size:10.5px;color:var(--g600);margin-top:3px}
/* AD COL */
.ad-col{position:sticky;top:74px}
.adl{font-size:8.5px;font-weight:700;color:var(--g400);text-transform:uppercase;letter-spacing:.07em;text-align:center;margin-bottom:5px}
.adb{background:var(--g50);border:1px dashed var(--g300);border-radius:10px;display:flex;align-items:center;justify-content:center;height:250px;margin-bottom:10px}
.adbi{text-align:center;padding:12px}
.aff{background:#fff;border:1.5px solid var(--g200);border-radius:10px;padding:11px;text-align:center;margin-bottom:8px}
.afft{font-size:8.5px;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:var(--green);margin-bottom:4px}
.affn{font-size:12.5px;font-weight:800;color:var(--g900);margin-bottom:4px}
.affd{font-size:10.5px;color:var(--g500);line-height:1.45;margin-bottom:7px}
.affb{display:block;background:var(--green);color:#fff;padding:7px;border-radius:50px;font-size:11.5px;font-weight:800;text-decoration:none;transition:background .18s}
.affb:hover{background:var(--green-md)}
/* STORIES */
.stories-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:24px}
.story-card{background:var(--g50);border-radius:18px;padding:20px;border:1px solid var(--g200);transition:all .2s}
.story-card:hover{box-shadow:var(--sh-md);border-color:var(--green);transform:translateY(-2px)}
.story-saved{color:var(--green);font-weight:800;font-size:1.05rem;margin-bottom:10px}
.story-q{font-size:13px;color:var(--g600);line-height:1.75;font-style:italic;margin-bottom:10px}
.story-who{font-weight:700;font-size:13px;color:var(--g900)}
.story-detail{font-size:11px;color:var(--g400);margin-top:3px}
/* EXPERT */
.expert-card{display:flex;gap:22px;background:var(--g50);border-radius:24px;padding:26px;align-items:flex-start;flex-wrap:wrap;border:1px solid var(--g200)}
.expert-avatar{width:120px;height:120px;background:var(--marine);border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-size:2.2rem;font-weight:700;font-family:var(--fs);flex-shrink:0;overflow:hidden;box-shadow:0 4px 16px rgba(0,31,63,.18)}
.expert-avatar img{width:100%;height:100%;min-width:120px;max-width:120px;aspect-ratio:1/1;object-fit:cover;object-position:center 28%;border-radius:50%;display:block}
.expert-avatar{overflow:hidden;flex-shrink:0}
.expert-name{font-size:1.3rem;font-weight:800;color:var(--g900);margin-bottom:3px}
.expert-role{color:var(--green);font-weight:700;font-size:13px;margin-bottom:9px}
.expert-bio{font-size:13px;color:var(--g600);line-height:1.72;margin-bottom:13px}
.cred-badges{display:flex;gap:7px;flex-wrap:wrap}
.cred-b{background:#fff;padding:4px 11px;border-radius:50px;font-size:11px;font-weight:700;color:var(--marine);border:1px solid var(--g200)}
/* TOPICS */
.tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:10px;margin-top:24px}
.tc{background:#fff;border:1.5px solid var(--g200);border-radius:12px;padding:13px 11px;text-decoration:none;display:flex;flex-direction:column;gap:6px;transition:all .2s}
.tc:hover{border-color:var(--green);transform:translateY(-2px);box-shadow:var(--sh-md)}
.tc.tf{background:linear-gradient(135deg,var(--green-lt),#d4f0e6);border-color:var(--green)}
.tce{font-size:19px}
.tct{font-size:12px;font-weight:800;color:var(--g900)}
.tcs{font-size:10px;color:var(--g500);font-weight:600}
.tca{font-weight:800;font-size:13px;color:var(--g300);margin-top:auto;transition:color .18s}
.tc:hover .tca{color:var(--green)}
/* RESOURCES */
.res-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px;margin-top:22px}
.res-card{background:#fff;border-radius:12px;padding:15px;text-align:center;border:1px solid var(--g200);transition:all .2s}
.res-card:hover{transform:translateY(-3px);box-shadow:var(--sh-md);border-color:var(--green)}
.res-icon{font-size:1.6rem;margin-bottom:7px}
.res-title{font-weight:700;font-size:12px;color:var(--g900);margin-bottom:4px}
.res-link{font-size:11px;color:var(--green);text-decoration:none;font-weight:600}
/* RATES TABS */
.rtabs{display:flex;gap:0;margin-bottom:16px;border-bottom:2px solid var(--g200)}
.rtab{font-weight:700;padding:9px 18px;cursor:pointer;color:var(--g500);font-size:13.5px;border-bottom:2px solid transparent;margin-bottom:-2px;font-family:var(--fn);background:transparent;border-top:none;border-left:none;border-right:none;transition:color .18s}
.rtab.on{color:var(--green);border-bottom-color:var(--green)}
.rpanel{display:none}
.rrow{display:flex;justify-content:space-between;align-items:center;padding:11px 0;border-bottom:1px solid var(--g100)}
.rrow:last-child{border-bottom:none}
.rlbl{font-weight:500;font-size:13px;color:var(--g700)}
.rval{font-weight:700;font-size:13px;color:var(--marine)}
.rnote{font-size:10.5px;color:var(--g400);margin-top:10px;line-height:1.6}
/* CTA SECTION */
.cta-sec{background:linear-gradient(135deg,var(--marine) 0%,var(--marine-dk) 100%);padding:52px 4%;text-align:center;color:#fff}
.cta-sec h2{font-family:var(--fs);font-size:clamp(22px,3.5vw,36px);font-weight:700;margin-bottom:10px}
.cta-sec p{color:rgba(255,255,255,.7);font-size:15px;line-height:1.7;max-width:580px;margin:0 auto 8px}
.cta-btns{display:flex;gap:13px;justify-content:center;flex-wrap:wrap;margin-top:20px}
.btn-cta-w{background:#fff;color:var(--marine);padding:12px 26px;border-radius:50px;text-decoration:none;font-weight:800;font-size:14px;transition:all .2s}
.btn-cta-w:hover{transform:translateY(-2px);box-shadow:var(--sh-lg)}
.btn-cta-ol{border:2px solid #fff;color:#fff;padding:12px 26px;border-radius:50px;text-decoration:none;font-weight:700;font-size:14px;transition:all .2s}
.btn-cta-ol:hover{background:#fff;color:var(--marine)}
/* NEWSLETTER */
.nl-sec{padding:44px 4%;background:var(--g50)}
.nl-card{background:#fff;border-radius:24px;padding:32px;text-align:center;border:1px solid var(--g200);box-shadow:var(--sh-xl);max-width:660px;margin:0 auto}
.nl-card h2{font-family:var(--fs);font-size:clamp(19px,2.8vw,26px);font-weight:700;color:var(--g900);margin-bottom:7px}
.nl-card p{color:var(--g500);font-size:13.5px;max-width:420px;margin:0 auto 20px}
.nl-form{display:flex;gap:9px;justify-content:center;flex-wrap:wrap}
.nl-inp{padding:11px 18px;border-radius:50px;border:1.5px solid var(--g200);font-size:13.5px;font-family:var(--fn);width:260px;outline:none;transition:border-color .18s}
.nl-inp:focus{border-color:var(--green)}
.nl-note{font-size:10.5px;color:var(--g400);margin-top:11px}

/* EDU */
.edu{background:var(--gold-lt);border-top:2px solid #fcd34d;padding:13px 4%;text-align:center;font-size:11.5px;color:#78350f;line-height:1.8;font-weight:600}
.edu strong{color:#451a03}
.edu a{color:var(--green);font-weight:800}
/* FOOTER */
footer{padding:36px 4% 20px;border-top:1px solid var(--g200)}
.ftop{max-width:1300px;margin:0 auto;display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:26px;margin-bottom:22px}
@media(max-width:680px){.ftop{grid-template-columns:1fr 1fr}}
.fh{font-size:10.5px;font-weight:800;color:var(--g900);margin-bottom:10px;text-transform:uppercase;letter-spacing:.06em}
.fli{list-style:none}
.fli li{margin-bottom:6px}
.fli a{font-size:11.5px;color:var(--g500);text-decoration:none;transition:color .18s;font-weight:500}
.fli a:hover{color:var(--green)}
.fbot{max-width:1300px;margin:0 auto;border-top:1px solid var(--g200);padding-top:13px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:7px;font-size:10.5px;color:var(--g400);font-weight:500}
.fbot a{color:var(--g400);text-decoration:none;margin-left:10px}
.fbot a:hover{color:var(--green)}
/* STICKY */
@keyframes sup{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.sticky-cta{position:fixed;bottom:18px;right:18px;z-index:999;animation:sup .4s ease;will-change:transform}
.sticky-cta a{display:flex;align-items:center;gap:7px;background:var(--green);color:#fff;padding:11px 20px;border-radius:50px;font-size:13px;font-weight:800;text-decoration:none;box-shadow:0 6px 22px rgba(5,130,95,.38);transition:all .2s}
.sticky-cta a:hover{background:var(--green-md);transform:translateY(-2px)}
@media(max-width:600px){.sticky-cta a{font-size:12px;padding:10px 15px}}
.nt{font-size:10.5px;color:var(--g400);text-align:center;margin-top:9px;font-style:italic;line-height:1.6}
.rv{opacity:0;transform:translateY(14px);transition:opacity .5s ease,transform .5s ease}
.rv.in{opacity:1;transform:none}

/* ── ACCESSIBILITY: Focus styles ── */
a:focus-visible,button:focus-visible,.ttab:focus-visible,.cpill:focus-visible,.rtab:focus-visible{
  outline:3px solid var(--g);outline-offset:2px;border-radius:4px;
}
input:focus-visible,select:focus-visible{
  outline:3px solid var(--g);outline-offset:1px;
}
.btn-primary:focus-visible,.btn-outline:focus-visible,.nav-cta:focus-visible{
  outline:3px solid var(--g);outline-offset:3px;
}
/* Skip to main content for screen readers */
.skip-link{
  position:absolute;top:-40px;left:0;background:var(--g);color:#fff;
  padding:8px 16px;border-radius:0 0 8px 0;font-weight:700;font-size:13px;
  text-decoration:none;z-index:9999;transition:top .2s;
}
.skip-link:focus{top:0;}


@media(min-width:861px) and (max-width:1060px){
  .tools-layout{grid-template-columns:1fr}
  .ad-col .adb{height:200px}
  .ad-col .aff{padding:9px}
  .affn{font-size:12px}
  .affd{font-size:10px}
}

/* ===================================================
   MOBILE RESPONSIVE FIXES - Applied 2026-04-05
   =================================================== */

/* 1. Section padding tighter on small screens */
@media(max-width:480px){
  .sec{padding:32px 5%}
  .cta-sec{padding:36px 5%}
  .nl-sec{padding:32px 5%}
}

/* 2. Hero fixes for small mobile */
@media(max-width:480px){
  .hero{padding:32px 5% 28px}
  h1{font-size:clamp(26px,8vw,36px);line-height:1.15}
  .hero-sub{font-size:14px}
  .h-badge{font-size:11px;padding:5px 10px}
  .trust-row{gap:10px}
  .trust-b{font-size:12px}
  .cta-row{flex-direction:column;gap:10px}
  .cta-row a,.cta-row button{width:100%;text-align:center;justify-content:center}
}

/* 3. Stats bar full width on mobile */
@media(max-width:480px){
  .sbar{flex-direction:column;min-height:436px}
  .sbc{border-right:none!important;border-bottom:1px solid rgba(255,255,255,.15);min-width:100%;max-width:100%;padding:14px 5%}
  .sbc:last-child{border-bottom:none}
}

/* 4. Transfer comparison table - horizontal scroll on mobile */
@media(max-width:760px){
  .ctool-wrap,.comp-table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
  .ctool-wrap table,.comp-table-wrap table{min-width:520px}
}

/* 5. Provider rows stacked on small mobile */
@media(max-width:480px){
  .crow{flex-wrap:wrap;gap:6px;padding:12px 10px}
  .crow-logo{min-width:80px}
  .crow-rate{font-size:15px}
  .crow-badge{font-size:10px;padding:2px 7px}
}

/* 6. Tools section - remove side ads col on mobile */
@media(max-width:960px){
  .ad-col{display:none!important}
}

/* 7. Nav bar on mobile - ensure proper height and centering */
@media(max-width:1020px){
  .nv{padding:0 16px;height:56px;gap:0}
  .logo-a img{height:38px;max-width:180px}
  .ham{width:40px;height:40px;padding:8px}
}

/* 8. Section headings on mobile */
@media(max-width:480px){
  .sec-hd h2{font-size:clamp(20px,6vw,26px)}
  .sec-hd p{font-size:14px}
}

/* 9. Article grid - single column on small mobile */
@media(max-width:480px){
  .art-wrap{grid-template-columns:1fr!important;gap:12px}
  .art-col{border-radius:12px}
}

/* 10. Path cards - full width on mobile */
@media(max-width:480px){
  .path-grid{grid-template-columns:1fr!important;gap:12px}
  .path-card{padding:18px}
}

/* 11. Comparison pills wrap correctly */
@media(max-width:480px){
  .cpills,.ttabs{gap:5px}
  .cpill,.ttab{font-size:10.5px;padding:5px 9px}
}

/* 12. Sticky CTA smaller on mobile */
@media(max-width:480px){
  .sticky-cta{bottom:12px;right:12px}
  .sticky-cta a{font-size:12px;padding:10px 14px}
}

/* 13. Footer grid on small mobile */
@media(max-width:480px){
  .ftop{grid-template-columns:1fr!important}
  .fbrand{margin-bottom:8px}
}

/* 14. Fix overflow on comparison widget */
@media(max-width:640px){
  .cw,.ctool{padding:14px 12px}
  .cw{border-radius:12px}
}

/* 15. Expert section */
@media(max-width:480px){
  .expert-block{flex-direction:column;text-align:center;gap:16px}
  .expert-avatar{margin:0 auto}
}

/* === DROPDOWN FIX 2026-04-05 ===
   Pure CSS :hover removed. Controlled by JS .open class.
   Closes on mouseleave, outside click, Escape key. */
#nav-overlay{display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:499;background:transparent;cursor:default}
.ni.open>.dr{display:block;animation:df .14s ease;will-change:transform}.ni.open>.dr.mg3{display:grid}.ni.open>.dr.mg2{display:grid}
.ni.open>.na{color:var(--green);border-bottom-color:var(--green)}
.ni.open>button.na svg{transform:rotate(180deg)}
.dr{display:none;transition:none!important}

/* ===== MOBILE FIXES: HERO, EXPERT, FOOTER ===== */

/* PROBLEM 1 - Hero section centering on mobile */
@media (max-width: 880px) {
  .hero > .hero-grid > div:first-child { text-align: center; }
  .h-badge { margin-left: auto; margin-right: auto; }
  h1 { text-align: center; }
  .hero-sub { max-width: 100%; text-align: center; margin-left: auto; margin-right: auto; }
  .trust-row { justify-content: center; }
  .ctas { justify-content: center; }
}

/* PROBLEM 2 - Expert card stacking on mobile */
@media (max-width: 600px) {
  .expert-avatar {
    width: 120px !important;
    height: 120px !important;
    min-width: 120px !important;
    min-height: 120px !important;
    border-radius: 50% !important;
    overflow: hidden !important;
    align-self: center;
    margin: 0 auto;
  }
  .expert-avatar img {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
    object-position: center 28% !important;
    border-radius: 50% !important;
    display: block !important;
  }
  .expert-card { flex-direction: column !important; align-items: center !important; text-align: center !important; }
  .expert-card > div[style] { flex: unset !important; width: 100% !important; }
  .expert-bio { text-align: left !important; }
  .cred-badges { justify-content: center !important; }
  .cred-b { text-align: center; }
}

/* PROBLEM 3 - Footer centering on mobile */
@media (max-width: 480px) {
  .ftop { grid-template-columns: 1fr !important; text-align: center; gap: 20px; }
  .ftop > div > p, .ftop > div > div { margin-left: auto; margin-right: auto; max-width: 100% !important; }
  .fh { text-align: center; }
  .fli { padding: 0; text-align: center; }
  .fbot { flex-direction: column; align-items: center; text-align: center; gap: 6px; }
  .fbot a { margin-left: 5px; margin-right: 5px; }
}

@media (max-width: 680px) and (min-width: 481px) {
  .ftop { text-align: center; }
  .fli { padding: 0; text-align: center; }
  .fbot { flex-direction: column; align-items: center; gap: 6px; }
}
</style>

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "MoneyAbroadGuide",
  "url": "https://moneyabroadguide.com",
  "description": "Free educational financial guides for newcomers to Canada and the USA.",
  "author": {
    "@type": "Person",
    "name": "Talal Eddaouahiri",
    "jobTitle": "Founder & Financial Writer"
  },
  "publisher": {
    "@type": "Organization",
    "name": "MoneyAbroadGuide.com",
    "url": "https://moneyabroadguide.com"
  },
  "dateModified": "2026-03-28",
  "inLanguage": "en",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://moneyabroadguide.com/?s={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FinancialService",
  "name": "MoneyAbroadGuide Transfer Comparison",
  "url": "https://moneyabroadguide.com",
  "description": "Compare international money transfer fees for newcomers to Canada and USA",
  "areaServed": ["CA", "US"],
  "dateModified": "2026-03-28"
}
</script>


<meta property="og:title" content="Money Abroad Guide — Save on International Money Transfers">
<meta property="og:description" content="Free educational guides for newcomers to  Canada and the USA. Compare real-time transfer fees, build credit, file taxes,  and manage money smarter as an expat.">
<meta property="og:image" content="https://moneyabroadguide.com/wp-content/uploads/2026/04/mag-logo.jpg" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:image" content="https://moneyabroadguide.com/wp-content/uploads/2026/04/mag-logo.jpg" />
<meta property="og:type" content="website">
<meta property="og:url" content="https://moneyabroadguide.com">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="MoneyAbroadGuide.com &#8212; Free Guides for Newcomers">
<meta name="twitter:description" content="Compare transfer fees, build credit, plan your budget in Canada or the USA.">
<link rel="canonical" href="https://moneyabroadguide.com">

</head>
<body>
<div class="ts">
  <div style="display:flex;align-items:center;gap:9px"><span class="ts-b">&#128218; Educational Resource</span><span>All content is for informational purposes only &#8212; not financial advice.</span></div>
  <div><a href="/disclaimer/">Disclaimer</a> &nbsp;&#183;&nbsp; <a href="/editorial-policy/">Editorial Policy</a> &nbsp;&#183;&nbsp; <a href="/about-us/">About</a></div>
</div>
<nav class="nav">
  <div class="nv">
    <a href="/" class="logo-a"><img loading="eager" fetchpriority="high" width="180" height="45" src="https://moneyabroadguide.com/wp-content/uploads/2026/04/mag-logo-300x113.jpg" alt="MoneyAbroadGuide.com" style="height:50px;width:auto;display:block"></a>
    <ul class="nav-list">
      <li class="ni"><a href="/" class="na act">Home</a></li>
      <li class="ni">
        <button class="na">Start Here <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
        <div class="dr" style="left:0;transform:none;min-width:200px">
          <a href="/start-here/" class="ds">&#128640; I just arrived &#8212; start here</a>
          <a href="/newcomers-to-canada/" class="ds">&#127464;&#127462; Moving to Canada</a>
          <a href="/newcomers-to-the-usa/" class="ds">&#127482;&#127480; Moving to the USA</a>
          <a href="#tools" class="ds">&#128184; Transfer Calculator</a>
          <a href="#tools" class="ds">&#128290; Budget Planner</a>
        </div>
      </li>
      <li class="ni">
        <button class="na">&#127464;&#127462; Canada <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
        <div class="dr mg mg3">
          <div>
            <div class="dc">&#127981; Banking &amp; Credit</div>
            <a href="/best-banks-newcomers-canada/" class="dl"><div class="dic" style="background:var(--green-lt)">&#127981;</div><div><span class="dt2">Best Banks for Newcomers</span><span class="dd2">Compare TD, RBC, Scotiabank</span></div></a>
            <a href="/building-credit-canada-newcomers-2026/" class="dl"><div class="dic" style="background:var(--g50)">&#128200;</div><div><span class="dt2">Build Credit from Zero</span><span class="dd2">12-month step-by-step roadmap</span></div></a>
            <a href="/best-credit-cards-newcomers-canada/" class="dl"><div class="dic" style="background:var(--g50)">&#128179;</div><div><span class="dt2">Best Credit Cards</span><span class="dd2">No credit history required</span></div></a>
            <a href="/bank-account-canada-no-sin/" class="dl"><div class="dic" style="background:var(--green-lt)">&#128203;</div><div><span class="dt2">Open Account Without SIN</span><span class="dd2">Before receiving your SIN</span></div></a>
          </div>
          <div>
            <div class="dc">&#128188; Finance &amp; Life</div>
            <a href="/cost-of-living-canada-2026/" class="dl"><div class="dic" style="background:var(--g50)">&#128202;</div><div><span class="dt2">Cost of Living 2026</span><span class="dd2">Budget breakdown by city</span></div></a>
            <a href="/rent-without-credit-canada/" class="dl"><div class="dic" style="background:var(--green-lt)">&#127968;</div><div><span class="dt2">Renting Without Credit</span><span class="dd2">How to get approved</span></div></a>
            <a href="/file-taxes-canada-first-year-newcomer/" class="dl"><div class="dic" style="background:var(--g50)">&#129534;</div><div><span class="dt2">File Your First Tax Return</span><span class="dd2">Credits &amp; deductions</span></div></a>
            <a href="/health-insurance-newcomers-canada-2026/" class="dl"><div class="dic" style="background:#fef2f2">&#127973;</div><div><span class="dt2">Healthcare &amp; OHIP</span><span class="dd2">Provincial coverage guide</span></div></a>
          </div>
          <div>
            <div class="dfeat"><div class="dfeat-tag">&#11088; Most Popular</div><div class="dfeat-h">Banking for Newcomers to Canada &#8212; 2026 Guide</div><div class="dfeat-p">Open your first account, build credit, manage money step by step.</div><a href="/best-banks-newcomers-canada-2026/" class="dfeat-btn">Read the Guide &#8594;</a></div>
            <div style="margin-top:11px"><div class="dc" style="margin-top:8px">&#128296; Tools</div>
              <a href="#tools" class="dl"><div class="dic" style="background:var(--green-lt)">&#128184;</div><div><span class="dt2">Transfer Calculator</span><span class="dd2">Compare fees live</span></div></a>
              <a href="#tools" class="dl"><div class="dic" style="background:var(--g50)">&#128290;</div><div><span class="dt2">Budget Planner</span><span class="dd2">Monthly cost estimate</span></div></a>
            </div>
          </div>
        </div>
      </li>
      <li class="ni">
        <button class="na">&#127482;&#127480; USA <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
        <div class="dr mg mg3">
          <div>
            <div class="dc">&#127981; Banking &amp; Credit</div>
            <a href="/bank-account-immigrants-usa-no-ssn/" class="dl"><div class="dic" style="background:var(--green-lt)">&#127981;</div><div><span class="dt2">Banks Without SSN</span><span class="dd2">Open as a newcomer</span></div></a>
            <a href="/build-credit-international-student-usa/" class="dl"><div class="dic" style="background:var(--g50)">&#128200;</div><div><span class="dt2">Build US Credit</span><span class="dd2">From zero to 700+</span></div></a>
            <a href="/best-savings-accounts-immigrants-usa/" class="dl"><div class="dic" style="background:var(--g50)">&#128176;</div><div><span class="dt2">Best Savings Accounts</span><span class="dd2">High-yield for immigrants</span></div></a>
          </div>
          <div>
            <div class="dc">&#128203; Taxes &amp; Legal</div>
            <a href="/how-to-get-itin-number-usa-2026/" class="dl"><div class="dic" style="background:var(--g50)">&#128290;</div><div><span class="dt2">Get an ITIN Number</span><span class="dd2">Step-by-step guide</span></div></a>
            <a href="/nonresident-alien-taxes-usa-guide/" class="dl"><div class="dic" style="background:var(--g50)">&#129534;</div><div><span class="dt2">File US Taxes</span><span class="dd2">Form 1040-NR explained</span></div></a>
            
          </div>
          <div>
            <div class="dfeat"><div class="dfeat-tag">&#11088; Guide</div><div class="dfeat-h">Best Banks for Immigrants USA &#8212; No SSN Required</div><div class="dfeat-p">Compare top banks that welcome newcomers before they have an SSN.</div><a href="/banking-newcomers-usa/" class="dfeat-btn">Read the Guide &#8594;</a></div>
          </div>
        </div>
      </li>
      <li class="ni">
        <button class="na">&#128184; Transfers <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
        <div class="dr mg mg2">
          <div>
            <div class="dc">&#9878; Compare &amp; Save</div>
            <a href="/best-apps-to-send-money-internationally-from-canada-2026/" class="dl"><div class="dic" style="background:var(--green-lt)">&#127942;</div><div><span class="dt2">Best Transfer Apps 2026</span><span class="dd2">Wise, Remitly, OFX &amp; more</span></div></a>
            <a href="/wise-vs-remitly-canada-2026/" class="dl"><div class="dic" style="background:var(--g50)">&#9878;</div><div><span class="dt2">Wise vs Remitly vs OFX</span><span class="dd2">Side-by-side comparison</span></div></a>
            <a href="/best-way-to-send-money-usa-to-canada-2026/" class="dl"><div class="dic" style="background:var(--g50)">&#128161;</div><div><span class="dt2">Cheapest Way to Send</span><span class="dd2">Updated monthly</span></div></a>
          </div>
          <div>
            <div class="dc">&#128296; Free Tool</div>
            <a href="#tools" class="dl"><div class="dic" style="background:var(--green-lt)">&#128290;</div><div><span class="dt2">Live Fee Comparator</span><span class="dd2">Best rate today</span></div></a>
            <div style="margin-top:10px;padding:10px;background:var(--g50);border-radius:8px;border:1px solid var(--g200)">
              <div style="font-size:9px;font-weight:700;color:var(--g400);margin-bottom:3px">&#9889; Quick example</div>
              <div style="font-size:12px;color:var(--g600);line-height:1.55">$1,000 CAD &#8594; Morocco via <strong style="color:var(--green)">Wise</strong>: <strong style="color:var(--marine)">9,820 MAD</strong> vs 8,780 via bank.</div>
              <a href="#tools" style="display:inline-block;margin-top:6px;font-size:11.5px;font-weight:800;color:var(--green);text-decoration:none">Try full calculator &#8594;</a>
            </div>
          </div>
        </div>
      </li>
      <li class="ni">
        <button class="na">About <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
        <div class="dr" style="left:auto;right:0;transform:none;min-width:190px">
          <a href="/about-us/" class="ds">&#128100; About Us</a>
          <a href="/team/" class="ds">&#9997; Our Team &amp; Authors</a>
          <a href="/editorial-policy/" class="ds">&#128203; Editorial Policy</a>
          <a href="/contact/" class="ds">&#9993; Contact</a>
          <a href="/privacy-policy/" class="ds">&#128274; Privacy Policy</a>
        </div>
      </li>
    </ul>
    <div class="nr">
      <a href="https://moneyabroadguide.com/ebook-build-your-credit-score-usa/" class="ng">📘 Get the eBook</a>
      <a href="#tools" class="nc">&#128184; Compare Fees</a>
    </div>
    <button class="ham" id="ham" onclick="toggleMob()" aria-label="Toggle mobile menu" aria-expanded="false" aria-controls="mob"><span></span><span></span><span></span></button>
  </div>
  <nav class="mob" id="mob" aria-label="Mobile navigation">
    <div class="mh">Quick</div><a href="/">&#127968; Home</a><a href="/start-here/">&#128640; Start Here</a>
    <div class="mh">&#127464;&#127462; Canada</div>
    <a href="/best-banks-newcomers-canada-2026/">Banking Guide Canada</a>
    <a href="/best-banks-newcomers-canada/">Best Banks Canada</a>
    <a href="/building-credit-canada-newcomers-2026/">Build Credit Canada</a>
    <a href="/cost-of-living-canada-2026/">Cost of Living</a>
    <a href="/rent-without-credit-canada/">Renting Without Credit</a>
    <a href="/file-taxes-canada-first-year-newcomer/">File Taxes Canada</a>
    <div class="mh">&#127482;&#127480; USA</div>
    <a href="/banking-newcomers-usa/">Banking Guide USA</a>
    <a href="/bank-account-immigrants-usa-no-ssn/">Banks Without SSN</a>
    <a href="/build-credit-international-student-usa/">Build US Credit</a>
    <a href="/nonresident-alien-taxes-usa-guide/">File US Taxes</a>
    <div class="mh">&#128184; Transfers</div>
    <a href="/best-apps-to-send-money-internationally-from-canada-2026/">Best Transfer Apps</a>
    <a href="#tools">Fee Calculator</a>
    <div class="mh">Info</div>
    <a href="/about-us/">About</a><a href="/contact/">Contact</a><a href="/privacy-policy/">Privacy Policy</a>
  </div>
</nav>
<main id="main-content">
<section class="hero" aria-label="Hero section with transfer calculator" id="calculator">
  <div class="hero-grid">
    <div>
      <div class="h-badge"><div class="pl"></div>Independent Financial Guides for Newcomers</div>
      <h1>Helping newcomers navigate money in the <span class="em">USA &amp; Canada</span></h1>
      <p class="hero-sub">Practical guides on banking, credit, transfers &amp; budgeting &#8212; clear information to help you make informed choices.</p>
      <div class="trust-row">
        <div class="trust-b"><span class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</span> Independently written content</div>
        <div class="trust-b">&#10003; Transparent fees</div>
        <div class="trust-b">&#10003; Editorially reviewed</div>
        <div class="trust-b">&#10003; Free always</div>
      </div>
      <div class="ctas">
        <a href="https://moneyabroadguide.com/ebook-build-your-credit-score-usa/" class="btn-pill" id="mag-ebook-cta">📘 Discover the Credit Score Guide</a><a href="#tools" class="btn-pill">&#128184; Compare Fees Now</a>
        <a href="/start-here/" class="btn-ghost">Read Our Free USA & Canada Guides &#8594;</a>
      </div>
    </div>
    <div class="hero-calc">
      <div class="hc-amt-box">
        <div class="hc-lbl">Transfer amount</div>
        <div class="hc-amt" id="hero-amt-display">$1,000</div>
        <input type="range" class="hc-slider" id="hero-slider" min="100" max="10000" step="100" value="1000" aria-label="Transfer amount in dollars" aria-valuemin="100" aria-valuemax="10000" aria-valuenow="1000">
        <div class="hc-range-lbls"><span>$100</span><span>$5,000</span><span>$10,000</span></div>
      </div>
      <div class="hc-dest">
        <label>Sending to</label>
        <select id="hero-dest" aria-label="Select money transfer destination">
          <option value="MAD">&#127474;&#127462; Morocco (MAD)</option>
          <option value="DZD">&#127465;&#127487; Algeria (DZD)</option>
          <option value="INR">&#127470;&#127475; India (INR)</option>
          <option value="NGN">&#127475;&#127468; Nigeria (NGN)</option>
          <option value="BRL">&#127463;&#127479; Brazil (BRL)</option>
          <option value="MXN">&#127474;&#127485; Mexico (MXN)</option>
          <option value="PHP">&#127477;&#127469; Philippines (PHP)</option>
          <option value="PKR">&#127477;&#127472; Pakistan (PKR)</option>
          <option value="EGP">&#127466;&#127468; Egypt (EGP)</option>
        </select>
      </div>
      <div id="hero-results"></div>
      <div class="save-banner" id="hero-save-banner">Loading best rates&#8230;</div>
      <p style="font-size:10px;color:var(--g400);text-align:center;margin-top:8px">Educational estimates &#8212; verify directly with providers before sending.</p>
    </div>
  </div>
</section>
<div class="sbar">
  <div class="sbc"><div class="sbn" data-to="21">21</div><div class="sbl">Canada financial guides</div></div>
  <div class="sbc"><div class="sbn" data-to="31">31</div><div class="sbl">USA financial guides</div></div>
  <div class="sbc"><div class="sbn" data-to="50">50</div><div class="sbl">Free educational guides</div></div>
  <div class="sbc"><div class="sbn" data-to="4">4</div><div class="sbl">Money transfer guides</div></div>
  <div class="sbc"><div class="sbn" data-to="100">100</div><div class="sbl">% Free content, always</div></div>
</div>
<div class="ba-sec bg-w">
  <div class="co">
    <div class="ba-block rv">
      <div class="ba-card ba-before">
        <div class="ba-title">EDUCATIONAL EXAMPLE — SCENARIO A</div>
        <div style="font-size:2rem"></div>
        <div class="ba-p" style="margin-top:8px">Higher fees and a weaker exchange rate. Monthly transfers looked fine on the surface, but hidden spread costs kept reducing the received amount every month.</div>
      </div>
      <div class="ba-card ba-after">
        <div class="ba-title">EDUCATIONAL EXAMPLE — SCENARIO B</div>
        <div class="ba-big">A different fee and exchange-rate structure</div>
        <div class="ba-p">Different providers apply different fees and exchange rates, which can change the final amount received for the same amount sent. Always compare current terms before deciding.</div>
      </div>
    </div>
  </div>
</div>
<section class="sec bg-s">
  <div class="co">
    <div class="sec-hd">
      <div class="stag">Choose Your Path</div>
      <h2>Guides Designed for Your Situation</h2>
      <p>Whether moving to Canada or the USA &#8212; start with the right guide and access tools and comparisons faster.</p>
    </div>
    <div class="path-grid">
      <div class="path-card rv">
        <div class="path-ico">&#127482;&#127480;</div>
        <div style="text-align:center"><span class="path-badge">USA</span></div>
        <div class="path-h">Newcomers to the USA</div>
        <p class="path-p">Educational guides on U.S. banking, credit building, taxes, ITIN numbers, and financial basics for immigrants and newcomers.</p>
        <div class="path-links">
          <a href="/banking-newcomers-usa/" class="path-lnk">&#128216; Read Full Banking Guide</a>
          <a href="/bank-account-immigrants-usa-no-ssn/" class="path-lnk">&#127981; Banks Without SSN &#8594;</a>
          <a href="/build-credit-international-student-usa/" class="path-lnk">&#128200; Build US Credit &#8594;</a>
          <a href="/nonresident-alien-taxes-usa-guide/" class="path-lnk">&#129534; File US Taxes &#8594;</a>
        </div>
      </div>
      <div class="path-card rv">
        <div class="path-ico">&#127464;&#127462;</div>
        <div style="text-align:center"><span class="path-badge">CANADA</span></div>
        <div class="path-h">Newcomers to Canada</div>
        <p class="path-p">Educational information on Canadian banking, savings, credit scores, housing, OHIP healthcare, and tax filing for newcomers.</p>
        <div class="path-links">
          <a href="/best-banks-newcomers-canada-2026/" class="path-lnk">&#128216; Read Full Banking Guide</a>
          <a href="/best-banks-newcomers-canada/" class="path-lnk">&#127981; Best Banks Canada &#8594;</a>
          <a href="/building-credit-canada-newcomers-2026/" class="path-lnk">&#128200; Build Credit &#8594;</a>
          <a href="/rent-without-credit-canada/" class="path-lnk">&#127968; Rent Without Credit &#8594;</a>
        </div>
      </div>
      <div class="path-card feat rv">
        <div class="path-ico">&#128216;</div>
        <div style="text-align:center"><span class="path-badge path-badge-s">START HERE</span></div>
        <div class="path-h">Start Here for Newcomers</div>
        <p class="path-p">A practical starting point to understand transfers, banking, budgeting, and your first financial setup in North America &#8212; from day one.</p>
        <div class="path-links">
          <a href="/start-here/" class="path-lnk path-lnk-p">&#128640; Start Here Guide &#8594;</a>
          <a href="/cost-of-living-canada-2026/" class="path-lnk path-lnk-o">&#128202; Cost of Living 2026 &#8594;</a>
          <a href="#tools" class="path-lnk path-lnk-o">&#128184; Compare Transfer Fees &#8594;</a>
        </div>
      </div>
    </div>
    <div style="text-align:center;margin-top:22px">
      <a href="#tools" class="btn-pill">Find the Cheapest Transfer Now &#8594;</a>
    </div>
  </div>
</section>
<section class="sec bg-w" id="articles">
  <div class="co">
    <div class="sec-hd">
      <div class="stag">Free Articles &#8212; Click to Read</div>
      <h2>Top Guides for Canada &amp; USA Newcomers</h2>
      <p>Full free educational guides &#8212; click any title to read instantly, no sign-up required.</p>
    </div>
    <div class="art-wrap">
      <div class="art-col rv">
        <div class="art-head">
          <div class="art-flag">&#127464;&#127462;</div>
          <div><div class="art-t2">Newcomers to Canada</div><div class="art-s2">11 free guides</div></div>
          <a href="/newcomers-to-canada/" class="art-cta-btn">View All &#8594;</a>
        </div>
        <div class="art-list">
          <a href="/best-banks-newcomers-canada/" class="art-item"><div class="art-ico">&#127981;</div><div><span class="art-tt">Best Banks for Newcomers to Canada 2026</span><span class="art-tg">Banking &middot; 12 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/building-credit-canada-newcomers-2026/" class="art-item"><div class="art-ico">&#128200;</div><div><span class="art-tt">How to Build Credit in Canada from Zero</span><span class="art-tg">Credit &middot; 10 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/bank-account-canada-no-sin/" class="art-item"><div class="art-ico">&#128203;</div><div><span class="art-tt">Open a Bank Account Without a SIN</span><span class="art-tg">Banking &middot; 6 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/rent-without-credit-canada/" class="art-item"><div class="art-ico">&#127968;</div><div><span class="art-tt">How to Rent Without Credit in Canada</span><span class="art-tg">Housing &middot; 8 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/cost-of-living-canada-2026/" class="art-item"><div class="art-ico">&#128202;</div><div><span class="art-tt">True Cost of Living in Canada 2026</span><span class="art-tg">Budget &middot; 15 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/file-taxes-canada-first-year-newcomer/" class="art-item"><div class="art-ico">&#129534;</div><div><span class="art-tt">File Your First Tax Return in Canada</span><span class="art-tg">Taxes &middot; 9 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/health-insurance-newcomers-canada-2026/" class="art-item"><div class="art-ico">&#127973;</div><div><span class="art-tt">Healthcare for Newcomers &#8212; OHIP Guide</span><span class="art-tg">Healthcare &middot; 7 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/best-credit-cards-newcomers-canada/" class="art-item"><div class="art-ico">&#128179;</div><div><span class="art-tt">Best Credit Cards for Newcomers Canada</span><span class="art-tg">Credit &middot; 8 min</span></div><div class="art-arr">&#8250;</div></a>
        </div>
      </div>
      <div class="art-col rv">
        <div class="art-head">
          <div class="art-flag">&#127482;&#127480;</div>
          <div><div class="art-t2">Newcomers to the USA</div><div class="art-s2">8 free guides</div></div>
          <a href="/newcomers-to-the-usa/" class="art-cta-btn">View All &#8594;</a>
        </div>
        <div class="art-list">
          <a href="/banking-newcomers-usa/" class="art-item"><div class="art-ico">&#127981;</div><div><span class="art-tt">Banking for Immigrants in the USA 2026</span><span class="art-tg">Banking &middot; 11 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/bank-account-immigrants-usa-no-ssn/" class="art-item"><div class="art-ico">&#128179;</div><div><span class="art-tt">Best Banks for Immigrants &#8212; No SSN</span><span class="art-tg">Banking &middot; 9 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/build-credit-international-student-usa/" class="art-item"><div class="art-ico">&#128200;</div><div><span class="art-tt">Build Your US Credit Score from Scratch</span><span class="art-tg">Credit &middot; 10 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/how-to-get-itin-number-usa-2026/" class="art-item"><div class="art-ico">&#128290;</div><div><span class="art-tt">How to Get an ITIN Number in the USA</span><span class="art-tg">Taxes &middot; 7 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/nonresident-alien-taxes-usa-guide/" class="art-item"><div class="art-ico">&#129534;</div><div><span class="art-tt">File US Taxes as a Nonresident Alien</span><span class="art-tg">Taxes &middot; 12 min</span></div><div class="art-arr">&#8250;</div></a>
          <a href="/best-savings-accounts-immigrants-usa/" class="art-item"><div class="art-ico">&#128176;</div><div><span class="art-tt">Best Savings Accounts for Immigrants USA</span><span class="art-tg">Banking &middot; 7 min</span></div><div class="art-arr">&#8250;</div></a>
          
          
        </div>
      </div>
    </div>
  </div>
</section>
<section class="sec bg-s" id="tools">
  <div class="co">
    <div class="sec-hd">
      <div class="stag">5 Free Interactive Tools</div>
      <h2>Smart Financial Tools for Newcomers</h2>
      <p>Calculate, compare, and plan &#8212; all updated with real 2026 data. No sign-up needed.</p>
    </div>
    <div class="ttabs">
      <button class="ttab on" onclick="switchTool(\'transfer\',this)">&#128184; Transfer Calc</button>
      <button class="ttab" onclick="switchTool(\'budget\',this)">&#127968; Budget Planner</button>
      <button class="ttab" onclick="switchTool(\'credit\',this)">&#128200; Credit Builder</button>
      <button class="ttab" onclick="switchTool(\'fee\',this)">&#9878; Fee Comparator</button>
      <button class="ttab" onclick="switchTool(\'mortgage\',this)">&#127968; Mortgage Calc</button>
    </div>
    <div class="tools-layout">
      
      <div>
        <div class="tp" id="tp-transfer">
          <div class="th"><div class="th-h">&#128184; Full Transfer Calculator</div><div class="th-s">Compare all 6 providers &#8212; see who gives your family the most</div></div>
          <div class="tb">
            <div class="fg">
              <div class="fl"><label>Sending amount (CAD)</label><input type="number" id="t-amt" value="1000" min="1" class="finp" oninput="calcTransfer()" aria-label="Enter transfer amount"></div>
              <div class="fl"><label>To country</label><select id="t-dest" class="fsel" onchange="calcTransfer()" aria-label="Select destination country"><option value="MAD">&#127474;&#127462; Morocco</option><option value="DZD">&#127465;&#127487; Algeria</option><option value="INR">&#127470;&#127475; India</option><option value="NGN">&#127475;&#127468; Nigeria</option><option value="BRL">&#127463;&#127479; Brazil</option><option value="MXN">&#127474;&#127485; Mexico</option><option value="PHP">&#127477;&#127469; Philippines</option><option value="PKR">&#127477;&#127472; Pakistan</option><option value="EGP">&#127466;&#127468; Egypt</option></select></div>
            </div>
            <div id="t-results"></div>
            <div class="svb"><div><div class="sv-l">Best deal saves your family</div><div class="sv-a" id="t-save">&#8212;</div></div><a href="https://wise.com" target="_blank" rel="noopener nofollow sponsored" aria-label="Open Wise money transfer service" class="sv-btn">Use Best Rate &#8594;</a></div>
            <p class="nt">Indicative estimates for educational purposes. Verify directly with providers before transferring.</p>
          </div>
        </div>
        <div class="tp" id="tp-budget" style="display:none">
          <div class="th"><div class="th-h">&#127968; Monthly Budget Planner</div><div class="th-s">Estimate your real cost of living before you arrive &#8212; 7 cities</div></div>
          <div class="tb">
            <div class="cpills"><button class="cpill on" data-c="toronto" onclick="setCity(this)">Toronto</button><button class="cpill" data-c="vancouver" onclick="setCity(this)">Vancouver</button><button class="cpill" data-c="montreal" onclick="setCity(this)">Montreal</button><button class="cpill" data-c="calgary" onclick="setCity(this)">Calgary</button><button class="cpill" data-c="nyc" onclick="setCity(this)">New York</button><button class="cpill" data-c="houston" onclick="setCity(this)">Houston</button><button class="cpill" data-c="miami" onclick="setCity(this)">Miami</button></div>
            <div id="bs-sliders"></div>
            <div class="bstats"><div class="bx"><div class="bxl">Monthly</div><div class="bxv" id="b-tot">$3,400</div></div><div class="bx"><div class="bxl">Annual</div><div class="bxv" id="b-ann">$40,800</div></div><div class="bx"><div class="bxl">Min. Salary</div><div class="bxv g" id="b-sal">$55K</div></div></div>
            <div class="btip" id="b-tip">Select a city to see local cost breakdown and money-saving tips.</div>
            <p class="nt">Indicative estimates for educational planning. Costs vary by lifestyle and neighbourhood.</p>
          </div>
        </div>
        <div class="tp" id="tp-credit" style="display:none">
          <div class="th"><div class="th-h">&#128200; Credit Score Builder</div><div class="th-s">See your projected credit score month by month in Canada &amp; USA</div></div>
          <div class="tb">
            <div class="fg">
              <div class="fl"><label>Current situation</label><select id="cr-start" class="fsel" onchange="calcCredit()" aria-label="Select your current credit situation"><option value="0">No score (just arrived)</option><option value="300">300 &#8212; Very Poor</option><option value="500">500 &#8212; Poor</option><option value="600">600 &#8212; Fair</option></select></div>
              <div class="fl"><label>Your strategy</label><select id="cr-strat" class="fsel" onchange="calcCredit()" aria-label="Select your credit building strategy"><option value="a">Secured card + on-time payments</option><option value="m">Basic card, occasional use</option><option value="p">No active credit building</option></select></div>
            </div>
            <div id="cr-bars" style="margin-top:12px"></div>
            <div class="crm2-grid" id="cr-ms"></div>
            <p class="nt">Scores are estimates for educational purposes only. Individual results vary.</p>
          </div>
        </div>
        <div class="tp" id="tp-fee" style="display:none">
          <div class="th"><div class="th-h">&#9878; Full Fee Comparator</div><div class="th-s">Transfer fee + FX margin + total recipient amount for every provider</div></div>
          <div class="tb">
            <div class="fg">
              <div class="fl"><label>Amount (CAD)</label><input type="number" id="f-amt" value="1000" class="finp" oninput="calcFee()" aria-label="Enter transfer amount in CAD"></div>
              <div class="fl"><label>Destination</label><select id="f-dest" class="fsel" onchange="calcFee()" aria-label="Select destination country"><option value="MAD">&#127474;&#127462; Morocco</option><option value="DZD">&#127465;&#127487; Algeria</option><option value="INR">&#127470;&#127475; India</option><option value="NGN">&#127475;&#127468; Nigeria</option><option value="BRL">&#127463;&#127479; Brazil</option><option value="MXN">&#127474;&#127485; Mexico</option><option value="PHP">&#127477;&#127469; Philippines</option></select></div>
            </div>
            <div style="overflow-x:auto;margin-top:12px"><table class="ftbl"><thead><tr><th>Provider</th><th>Fee</th><th>FX Margin</th><th>Recipient Gets</th><th>Speed</th></tr></thead><tbody id="f-body"></tbody></table></div>
            <p class="nt">Indicative educational data. Verify current rates on each provider website before sending.</p>
          </div>
        </div>
        <div class="tp" id="tp-mortgage" style="display:none">
          <div class="th"><div class="th-h">&#127968; Mortgage Calculator</div><div class="th-s">Estimate monthly payments in Canada or the USA</div></div>
          <div class="tb">
            <div class="fg">
              <div class="fl"><label>Property Price ($)</label><input type="number" id="m-price" value="500000" class="finp" oninput="calcMortgage()" aria-label="Enter property price"></div>
              <div class="fl"><label>Down Payment (%)</label><input type="number" id="m-down" value="10" min="5" max="50" class="finp" oninput="calcMortgage()" aria-label="Enter down payment percentage"></div>
              <div class="fl"><label>Interest Rate (%)</label><input type="number" id="m-rate" value="5.5" step="0.1" class="finp" oninput="calcMortgage()" aria-label="Enter interest rate percentage"></div>
              <div class="fl"><label>Amortization</label><select id="m-years" class="fsel" onchange="calcMortgage()" aria-label="Select amortization period in years"><option value="25">25 years</option><option value="20">20 years</option><option value="15">15 years</option><option value="30">30 years</option></select></div>
            </div>
            <div class="mr"><div class="mrl">Estimated Monthly Payment</div><div class="mrv" id="m-monthly">$2,847</div><div class="mrs" id="m-sub">On a $450K mortgage at 5.5% over 25 years</div></div>
            <div class="bstats" style="margin-top:10px"><div class="bx"><div class="bxl">Down Payment</div><div class="bxv" id="m-dp">$50,000</div></div><div class="bx"><div class="bxl">Loan Amount</div><div class="bxv" id="m-loan">$450,000</div></div><div class="bx"><div class="bxl">Total Interest</div><div class="bxv" id="m-int">$404,100</div></div></div>
            <p class="nt">For educational purposes only. Consult a licensed mortgage advisor for personalized advice.</p>
          </div>
        </div>
      </div>
      
    </div>
  </div>
</section>
<section class="sec bg-w" id="stories">
  <div class="co">
    <div class="sec-hd">
      <div class="stag">Educational Case Studies</div>
      <h2>Illustrative educational examples</h2>
      <p>Illustrative examples showing how comparing providers can reduce fees.</p>
    </div>
    <div class="stories-grid">
      <div class="story-card rv"><div class="story-saved">Illustrative example</div><p class="story-q">"I was sending $1,500 monthly to my family in Egypt. I assumed my bank had competitive rates. After using MoneyAbroadGuide, I switched to Wise and saw how much newcomers can save on transfer fees by comparing providers."</p><div class="story-who">&#8212; Illustrative example, educational purposes only</div><div class="story-detail">Before: $28 fees | After: $4.10 fees</div></div>
      <div class="story-card rv"><div class="story-saved">Illustrative example</div><p class="story-q">"As a newcomer with family in Europe, I was losing money on currency conversion. The comparison tool showed me how much OFX could save me on large transfers. It showed me that comparison tools can highlight real potential savings."</p><div class="story-who">&#8212; Illustrative example, educational purposes only</div></div>
      <div class="story-card rv"><div class="story-saved">Illustrative example</div><p class="story-q">"Moving to the US from India, I had to transfer my savings. The bank wanted $75 in fees plus a terrible exchange rate. Remitly gave me a promo rate and comparing options can reveal lower-cost transfers."</p><div class="story-who">&#8212; Illustrative example, educational purposes only</div></div>
      <div class="story-card rv"><div class="story-saved">Illustrative example</div><p class="story-q">"The first-year tax guide here was invaluable. I claimed $1,200 in newcomer credits I did not even know existed. Simple language, no jargon &#8212; exactly what I needed after arriving in Calgary."</p><div class="story-who">&#8212; Illustrative example, educational purposes only</div></div>
    </div>
  </div>
</section>
<section class="sec bg-s">
  <div class="co">
    <div class="sec-hd">
      <div class="stag">About the Editor</div>
      <h2>Written and edited by the founder of MoneyAbroadGuide</h2>
      <p>Researched and written by the founder and editor of MoneyAbroadGuide, based on publicly available information.</p>
    </div>
    <div class="expert-card rv">
      <div class="expert-avatar" style="background:none;padding:0;overflow:hidden"><img loading="lazy" width="80" height="80" src="https://moneyabroadguide.com/wp-content/uploads/2026/04/talal-eddaouahiri.jpg" alt="Talal Eddaouahiri" style="width:100%;height:100%;object-fit:cover;border-radius:50%;display:block"></div>
      <div style="flex:1">
        <div class="expert-name">Talal Eddaouahiri, Financial Writer</div>
        <div class="expert-role">Founder & Financial Writer &amp; Founder &#8212; MoneyAbroadGuide.com</div>
        <p class="expert-bio">A Moroccan immigrant who settled in the United States in 2015, Talal draws on a background in retail banking, customer relations and financial services. As an immigrant himself, he opened bank accounts in both Canada and the USA without a local credit history, and built this resource to share what he wished he had known on day one. All guides are written and reviewed to reflect the real challenges newcomers face.</p>
        <div class="cred-badges">
          <span class="cred-b">Founder & Editor</span>
          <span class="cred-b">Independent Newcomer-Finance Guides</span>
          <span class="cred-b">Hands-On Provider Comparisons</span>
          <span class="cred-b">Immigrant &#8594; Canada &amp; USA</span>
        </div>
      </div>
    </div>
  </div>
</section>
<section class="sec bg-w" id="topics">
  <div class="co">
    <div class="sec-hd">
      <div class="stag">All Topics</div>
      <h2>Every Financial Topic for Newcomers</h2>
      <p>Jargon-free guides written by people who lived the same experience.</p>
    </div>
    <div class="tgrid">
      <a href="/best-banks-newcomers-canada-2026/" class="tc tf rv"><div class="tce">&#127981;</div><div class="tct">Banking Canada</div><div class="tcs">12 guides</div><div class="tca">&#8594;</div></a>
      <a href="/banking-newcomers-usa/" class="tc tf rv"><div class="tce">&#127482;&#127480;</div><div class="tct">Banking USA</div><div class="tcs">8 guides</div><div class="tca">&#8594;</div></a>
      <a href="/best-apps-to-send-money-internationally-from-canada-2026/" class="tc rv"><div class="tce">&#128184;</div><div class="tct">Money Transfers</div><div class="tcs">10 guides</div><div class="tca">&#8594;</div></a>
      <a href="/building-credit-canada-newcomers-2026/" class="tc rv"><div class="tce">&#128200;</div><div class="tct">Build Credit</div><div class="tcs">7 guides</div><div class="tca">&#8594;</div></a>
      <a href="/rent-without-credit-canada/" class="tc rv"><div class="tce">&#127968;</div><div class="tct">Housing</div><div class="tcs">6 guides</div><div class="tca">&#8594;</div></a>
      <a href="/file-taxes-canada-first-year-newcomer/" class="tc rv"><div class="tce">&#129534;</div><div class="tct">Taxes</div><div class="tcs">5 guides</div><div class="tca">&#8594;</div></a>
      <a href="/health-insurance-newcomers-canada-2026/" class="tc rv"><div class="tce">&#127973;</div><div class="tct">Healthcare</div><div class="tcs">4 guides</div><div class="tca">&#8594;</div></a>
      
      <a href="/cost-of-living-canada-2026/" class="tc rv"><div class="tce">&#128202;</div><div class="tct">Cost of Living</div><div class="tcs">6 guides</div><div class="tca">&#8594;</div></a>
      <a href="/moving-to-canada-checklist-2026/" class="tc rv"><div class="tce">&#128203;</div><div class="tct">Moving to Canada</div><div class="tca">&#8594;</div></a>
      
      <a href="#tools" class="tc rv"><div class="tce">&#128290;</div><div class="tct">Calculators</div><div class="tcs">5 free tools</div><div class="tca">&#8594;</div></a>
    </div>
  </div>
</section>
<section class="sec bg-s">
  <div class="co">
    <div class="sec-hd">
      <div class="stag">More Resources</div>
      <h2>Find smarter rates today</h2>
      <p>Quickly compare rates across financial products and make your next money move with confidence.</p>
    </div>
    <div class="res-grid">
      <div class="res-card rv"><div class="res-icon">&#128179;</div><div class="res-title">Credit Cards</div><a href="/best-credit-cards-newcomers-canada/" class="res-link">Best cards &#8594;</a></div>
      <div class="res-card rv"><div class="res-icon">&#127968;</div><div class="res-title">Mortgages</div><a href="#tools" class="res-link">Calculate &#8594;</a></div>
      <div class="res-card rv"><div class="res-icon">&#128200;</div><div class="res-title">Credit Building</div><a href="/building-credit-canada-newcomers-2026/" class="res-link">Start here &#8594;</a></div>
      <div class="res-card rv"><div class="res-icon">&#127981;</div><div class="res-title">Banking</div><a href="/best-banks-newcomers-canada/" class="res-link">Best accounts &#8594;</a></div>
      <div class="res-card rv"><div class="res-icon">&#128176;</div><div class="res-title">Savings</div><a href="/best-savings-accounts-immigrants-usa/" class="res-link">High-yield &#8594;</a></div>
      <div class="res-card rv"><div class="res-icon">&#128184;</div><div class="res-title">Transfers</div><a href="/best-apps-to-send-money-internationally-from-canada-2026/" class="res-link">Compare apps &#8594;</a></div>
      <div class="res-card rv"><div class="res-icon">&#129534;</div><div class="res-title">Taxes</div><a href="/file-taxes-canada-first-year-newcomer/" class="res-link">File guide &#8594;</a></div>
      <div class="res-card rv"><div class="res-icon">&#127973;</div><div class="res-title">Healthcare</div><a href="/health-insurance-newcomers-canada-2026/" class="res-link">OHIP guide &#8594;</a></div>
      <div class="res-card rv"><div class="res-icon">&#128290;</div><div class="res-title">ITIN / SIN</div><a href="/how-to-get-itin-number-usa-2026/" class="res-link">Get yours &#8594;</a></div>
      <div class="res-card rv"><div class="res-icon">&#128203;</div><div class="res-title">Immigration</div><a href="/moving-to-canada-checklist-2026/" class="res-link">See checklist &#8594;</a></div>
      
      <div class="res-card rv"><div class="res-icon">&#128202;</div><div class="res-title">Cost of Living</div><a href="/cost-of-living-canada-2026/" class="res-link">By city &#8594;</a></div>
    </div>
  </div>
</section>
<section class="sec bg-w">
  <div class="co">
    <div class="sec-hd">
      <div class="stag">Current Rates</div>
      <h2>Start Saving on Every Transfer</h2>
      <p>Compare mortgages or banking rates and see how they stack up to national averages.</p>
    </div>
    <div style="max-width:720px;margin:0 auto" class="rv">
      <div class="rtabs">
        <button class="rtab on" data-panel="r-mortgage">Mortgages</button>
        <button class="rtab" data-panel="r-banking">Banking</button>
      </div>
      <div id="r-mortgage" class="rpanel" style="display:block">
        <div class="rrow"><span class="rlbl">Refinance (30-Year Fixed)</span><span class="rval">Best rate: 6.33%</span></div>
        <div class="rrow"><span class="rlbl">Refinance (30-Year Fixed)</span><span class="rval">National avg: 5.74%</span></div>
        <div class="rrow"><span class="rlbl">30-Year Fixed</span><span class="rval">Best rate: 6.27%</span></div>
        <div class="rrow"><span class="rlbl">30-Year Fixed</span><span class="rval">National avg: 6.50%</span></div>
        <div class="rrow"><span class="rlbl">15-Year Fixed</span><span class="rval">Best rate: 5.17%</span></div>
        <div class="rrow"><span class="rlbl">15-Year Fixed</span><span class="rval">National avg: 5.93%</span></div>
        <p class="rnote">Average rates sourced from public data. Terms apply and vary depending on qualifications. Rates subject to change without notice.</p>
      </div>
      <div id="r-banking" class="rpanel">
        <div class="rrow"><span class="rlbl">High-Yield Savings Account</span><span class="rval">Best APY: 4.75%</span></div>
        <div class="rrow"><span class="rlbl">High-Yield Savings Account</span><span class="rval">National avg: 0.45%</span></div>
        <div class="rrow"><span class="rlbl">Money Market Account</span><span class="rval">Best rate: 4.50%</span></div>
        <div class="rrow"><span class="rlbl">CD (12-month)</span><span class="rval">Best rate: 5.10%</span></div>
        <p class="rnote">Rates updated weekly and may vary by institution. See provider websites for current details.</p>
      </div>
      <div style="text-align:center;margin-top:18px"><a href="#tools" class="btn-pill">Use Our Free Calculator &#8594;</a></div>
    </div>
  </div>
</section>
<section class="cta-sec">
  <div class="co">
    <h2>Ready to save more?</h2>
    <p>Compare fees, protect your money, and choose a better transfer today. MoneyAbroadGuide helps users avoid hidden markups, compare rates faster, and move money with confidence.</p>
    <div class="cta-btns">
      <a href="#calculator" class="btn-cta-w">Compare Fees Now &#8594;</a>
      <a href="#newsletter" class="btn-cta-ol">Get Free Guide &#8594;</a>
    </div>
  </div>
</section>
<section class="nl-sec" id="newsletter">
  <div class="co">
    <div class="nl-card rv">
      <h2>&#128218; Free: The Expat Financial Survival Kit</h2>
      <p>Join our growing community of newcomers saving money on transfers, banking, and taxes. Weekly tips, free always.</p>
      <form class="nl-form" id="nl-form" data-token="' . esc_attr($wpforms_token) . '" data-token-time="' . esc_attr($wpforms_token_time) . '">
        <input type="email" class="nl-inp" id="nl-email-visible" placeholder="your@email.com" required>
        <button type="submit" class="btn-pill">Get Free Guide &#8594;</button>
      </form>
      <p class="nl-note" id="nl-success-msg" style="display:none;color:var(--green);font-weight:700;margin-top:8px">&#10003; Thanks &#8212; you are on the list!</p>
      <p class="nl-note" id="nl-error-msg" style="display:none;color:#dc2626;margin-top:8px">Something went wrong. Please try again.</p>
      <p class="nl-note">100% free &#183; No spam &#183; Unsubscribe anytime &#183; Educational only</p>
    </div>
  </div>
</section>
<div class="edu"><strong>&#128218; Educational Disclosure:</strong> MoneyAbroadGuide.com is an independent educational website. All content is for informational purposes only and does not constitute financial, legal, or tax advice. Rates change constantly &#8212; always verify with providers. Some links are affiliate links; we may earn a commission at no cost to you. <a href="/disclaimer/">Full Disclaimer</a> &#183; <a href="/editorial-policy/">Editorial Policy</a> &#183; <a href="/privacy-policy/">Privacy Policy</a></div>

</main>
</main>
</main>
</main>
<footer role="contentinfo">
  <div class="ftop">
    <div><div style="font-size:13px;font-weight:800;color:var(--g900);margin-bottom:9px">MoneyAbroadGuide<span style="color:var(--green)">.com</span></div><p style="font-size:11.5px;color:var(--g500);line-height:1.8;max-width:220px">Independent educational financial guides for newcomers in Canada and the USA.</p><div style="margin-top:8px;font-size:10.5px;color:var(--g400)">&#9733; Independent financial education for newcomers</div></div>
    <div><div class="fh">Canada</div><ul class="fli"><li><a href="/best-banks-newcomers-canada/">Best Banks</a></li><li><a href="/building-credit-canada-newcomers-2026/">Build Credit</a></li><li><a href="/cost-of-living-canada-2026/">Cost of Living</a></li><li><a href="/rent-without-credit-canada/">Renting Guide</a></li><li><a href="/file-taxes-canada-first-year-newcomer/">File Taxes</a></li></ul></div>
    <div><div class="fh">USA</div><ul class="fli"><li><a href="/banking-newcomers-usa/">Banking USA</a></li><li><a href="/bank-account-immigrants-usa-no-ssn/">No SSN Banks</a></li><li><a href="/nonresident-alien-taxes-usa-guide/">File US Taxes</a></li><li><a href="/how-to-get-itin-number-usa-2026/">ITIN Guide</a></li></ul></div>
    <div><div class="fh">Transfers</div><ul class="fli"><li><a href="/best-apps-to-send-money-internationally-from-canada-2026/">Compare Apps</a></li><li><a href="/wise-vs-remitly-canada-2026/">Wise vs Remitly</a></li><li><a href="#tools">Fee Calculator</a></li><li><a href="/about-us/">About Us</a></li><li><a href="/contact/">Contact</a></li></ul></div>
  </div>
  <div class="fbot">
    <span>&#169; 2026 MoneyAbroadGuide.com &#8212; Educational purposes only &#183; Not financial advice</span>
    <span><a href="/privacy-policy/">Privacy</a><a href="/disclaimer/">Disclaimer</a><a href="/about-us/">About</a></span>
  </div>
</footer>

<div class="sticky-cta"><a href="#calculator">&#128184; Find Cheapest Transfer &#8594;</a></div><script>
/* ══ DATA ══ */
var RATES = {
  MAD:{wise:9.82,remitly:9.65,ofx:9.48,xe:9.55,wu:9.12,bank:8.78},
  DZD:{wise:95.8,remitly:94.2,ofx:92.5,xe:93.1,wu:90.2,bank:86.1},
  INR:{wise:61.5,remitly:60.9,ofx:59.8,xe:60.2,wu:58.4,bank:56.0},
  NGN:{wise:1218,remitly:1200,ofx:1182,xe:1190,wu:1148,bank:1092},
  BRL:{wise:3.75,remitly:3.69,ofx:3.62,xe:3.65,wu:3.53,bank:3.38},
  MXN:{wise:12.48,remitly:12.32,ofx:12.08,xe:12.18,wu:11.76,bank:11.22},
  PHP:{wise:41.0,remitly:40.4,ofx:39.6,xe:39.9,wu:38.7,bank:37.1},
  PKR:{wise:197,remitly:194,ofx:190,xe:191,wu:185,bank:178},
  EGP:{wise:21.9,remitly:21.6,ofx:21.2,xe:21.3,wu:20.6,bank:19.5}
};
var FEES = {wise:1.5,remitly:2.99,ofx:0,xe:2.0,wu:4.99,bank:15};
var FX_MARGIN = {wise:0.4,remitly:0.8,ofx:0.5,xe:0.6,wu:1.2,bank:2.5};
var PROVIDERS = [
  {k:"wise",   n:"Wise",          s:"Instant",   tag:"Mid-market rate"},
  {k:"remitly",n:"Remitly",       s:"Same day",  tag:"Promo available"},
  {k:"ofx",   n:"OFX",           s:"1-2 days",  tag:"No fixed fee"},
  {k:"xe",    n:"Xe",            s:"1-2 days",  tag:"Best FX margin"},
  {k:"wu",    n:"Western Union", s:"Instant",   tag:"Cash pickup option"},
  {k:"bank",  n:"Bank Wire",     s:"3-5 days",  tag:"Traditional bank"}
];

/* ══ HERO SLIDER CALCULATOR (from new page) ══ */
function initSlider() {
  var slider = document.getElementById("hero-slider");
  var destSel = document.getElementById("hero-dest");
  if (!slider || !destSel) return;
  function updateSlider() {
    var amt = parseFloat(slider.value) || 1000;
    var dest = destSel.value || "MAD";
    var dr = RATES[dest] || RATES.MAD;
    document.getElementById("hero-amt-display").textContent = "$" + Math.round(amt).toLocaleString("en-CA");
    var rows = PROVIDERS.filter(function(p){return p.k !== "bank";}).map(function(p) {
      var fee = FEES[p.k] || 3;
      var recv = Math.max(0, amt - fee) * (dr[p.k] || 9);
      var bankRecv = Math.max(0, amt - FEES.bank) * (dr.bank || 8.5);
      return {n:p.n, k:p.k, tag:p.tag, s:p.s, fee:fee, recv:recv, saving:recv - bankRecv};
    }).sort(function(a,b){return b.recv - a.recv;});
    var html = "";
    rows.forEach(function(p, i) {
      var isBest = i === 0;
      html += "<div class=\\"prow" + (isBest ? " prow-best" : "") + "\\">";
      html += "<div class=\\"prow-l\\">";
      html += "<div class=\\"prow-name\\">" + p.n + (isBest ? " <span class=\\"best-tag\\">BEST</span>" : "") + "</div>";
      html += "<div class=\\"prow-tag\\">" + p.tag + " &middot; " + p.s + "</div></div>";
      html += "<div class=\\"prow-r\\">";
      html += "<div class=\\"prow-recv\\">" + Math.round(p.recv).toLocaleString("en-CA") + " " + dest + "</div>";
      html += "<div class=\\"prow-fee\\">" + (p.fee === 0 ? "No fee" : "$" + p.fee.toFixed(2) + " fee") + "</div>";
      if (p.saving > 0) {
        html += "<div class=\\"prow-save\\">+" + Math.round(p.saving).toLocaleString("en-CA") + " " + dest + " vs bank</div>";
      }
      html += "</div></div>";
    });
    document.getElementById("hero-results").innerHTML = html;
    var best = rows[0];
    var worst = rows[rows.length - 1];
    var saved = Math.round(best.recv - worst.recv);
    document.getElementById("hero-save-banner").innerHTML =
      "<strong>" + best.n + "</strong> shows the highest amount received in this illustrative comparison &mdash; based on the figures you entered, the recipient would get <strong>" +
      Math.round(best.recv).toLocaleString("en-CA") + " " + dest + "</strong>. You save <strong>" +
      saved.toLocaleString("en-CA") + " " + dest + "</strong> vs the worst option.";
  }
  slider.addEventListener("input", updateSlider);
  destSel.addEventListener("change", updateSlider);
  updateSlider();
}

/* ══ TOOLS TABS ══ */
var budgetInit = false;
var curCity = "toronto";
var CD = {
  toronto:{r:2100,f:500,t:180,p:120,m:300,x:200,tip:"Toronto is expensive but offers strong employment. Shared housing saves $800-1,200/month in year 1."},
  vancouver:{r:2450,f:520,t:170,p:120,m:300,x:200,tip:"Vancouver is Canada\'s priciest city. Burnaby or Surrey cuts rent by 20-30%."},
  montreal:{r:1600,f:460,t:110,p:110,m:300,x:180,tip:"Montreal is the most affordable major Canadian city."},
  calgary:{r:1850,f:490,t:160,p:115,m:300,x:190,tip:"No provincial income tax and lower rents than Toronto."},
  nyc:{r:3200,f:600,t:140,p:100,m:400,x:250,tip:"New York is the most expensive US city. Queens or Bronx offer lower costs."},
  houston:{r:1400,f:500,t:200,p:100,m:350,x:180,tip:"No state income tax and affordable rents — great for newcomers."},
  miami:{r:2400,f:540,t:180,p:100,m:380,x:220,tip:"Broward County offers 20-30% lower housing costs nearby."}
};
var BS = [
  {id:"bs-rent",lbl:"Rent (1 bed)",k:"r",min:800,max:4000,step:50},
  {id:"bs-food",lbl:"Groceries",k:"f",min:200,max:1200,step:25},
  {id:"bs-tr",lbl:"Transport",k:"t",min:0,max:600,step:10},
  {id:"bs-ph",lbl:"Phone + Internet",k:"p",min:40,max:300,step:5},
  {id:"bs-rm",lbl:"Money sent home",k:"m",min:0,max:2000,step:50},
  {id:"bs-mx",lbl:"Leisure & misc.",k:"x",min:0,max:800,step:25}
];

function fm(n){return "$" + Math.round(n).toLocaleString("en-CA");}

function switchTool(id, btn) {
  document.querySelectorAll(".ttab").forEach(function(t){t.classList.remove("on");});
  btn.classList.add("on");
  ["transfer","budget","credit","fee","mortgage"].forEach(function(k){
    var p = document.getElementById("tp-" + k);
    if (p) p.style.display = k === id ? "block" : "none";
  });
  if (id === "transfer") calcTransfer();
  if (id === "budget")   { if(!budgetInit) initBudget(); else calcBudget(); }
  if (id === "credit")   calcCredit();
  if (id === "fee")      calcFee();
  if (id === "mortgage") calcMortgage();
}

function calcTransfer() {
  var amt = parseFloat(document.getElementById("t-amt").value) || 1000;
  var dest = document.getElementById("t-dest").value;
  var dr = RATES[dest] || RATES.MAD;
  var rows = PROVIDERS.map(function(p){
    var fee = FEES[p.k] || 3;
    var recv = Math.max(0, amt - fee) * (dr[p.k] || 9);
    var bankR = Math.max(0, amt - FEES.bank) * (dr.bank || 8.5);
    return {n:p.n, k:p.k, s:p.s, fee:fee, recv:recv, saving:recv - bankR};
  }).sort(function(a,b){return b.recv - a.recv;});
  var c = document.getElementById("t-results");
  if (!c) return;
  c.innerHTML = "";
  rows.forEach(function(p, i){
    var d = document.createElement("div");
    d.className = "prow" + (i === 0 ? " prow-best" : "");
    var badge = i === 0 ? "<span class=\\"best-tag\\">BEST</span>" : i === 1 ? "<span class=\\"best-tag2\\">2ND</span>" : "";
    d.innerHTML = "<div class=\\"prow-l\\"><div class=\\"prow-name\\">" + p.n + " " + badge + "</div><div class=\\"prow-tag\\">" + (p.fee === 0 ? "No fee" : "$" + p.fee.toFixed(2) + " fee") + " &middot; " + p.s + "</div></div>" +
      "<div class=\\"prow-r\\"><div class=\\"prow-recv\\">" + Math.round(p.recv).toLocaleString("en-CA") + " " + dest + "</div>" +
      (p.saving > 0 ? "<div class=\\"prow-save\\">+" + Math.round(p.saving).toLocaleString("en-CA") + " " + dest + " vs bank</div>" : "") + "</div>";
    c.appendChild(d);
  });
  var sa = document.getElementById("t-save");
  if (sa) sa.textContent = Math.round(rows[0].recv - rows[rows.length-1].recv).toLocaleString("en-CA") + " " + dest;
}

function initBudget() {
  budgetInit = true;
  var c = document.getElementById("bs-sliders");
  if (!c) return;
  BS.forEach(function(s){
    var d = CD[curCity];
    var row = document.createElement("div");
    row.className = "srow";
    row.innerHTML = "<div class=\\"stop2\\"><span class=\\"slbl2\\">" + s.lbl + "</span><span class=\\"sval2\\" id=\\"bv-" + s.k + "\\">" + fm(d[s.k]) + "</span></div>" +
      "<input type=\\"range\\" id=\\"" + s.id + "\\" min=\\"" + s.min + "\\" max=\\"" + s.max + "\\" value=\\"" + d[s.k] + "\\" step=\\"" + s.step + "\\" oninput=\\"calcBudget()\\">";
    c.appendChild(row);
  });
  calcBudget();
}

function setCity(btn) {
  document.querySelectorAll(".cpill").forEach(function(b){b.classList.remove("on");});
  btn.classList.add("on");
  curCity = btn.dataset.c;
  var d = CD[curCity];
  BS.forEach(function(s){
    var el = document.getElementById(s.id);
    if (el) { el.value = d[s.k]; var vl = document.getElementById("bv-" + s.k); if (vl) vl.textContent = fm(d[s.k]); }
  });
  calcBudget();
}

function calcBudget() {
  var tot = 0;
  BS.forEach(function(s){
    var el = document.getElementById(s.id);
    if (el) { var v = +el.value; tot += v; var vl = document.getElementById("bv-" + s.k); if (vl) vl.textContent = fm(v); }
  });
  var ann = tot * 12, sal = Math.round(ann * 1.32 / 1000) * 1000;
  var bt = document.getElementById("b-tot"), ba = document.getElementById("b-ann"), bs2 = document.getElementById("b-sal"), btp = document.getElementById("b-tip");
  if (bt) bt.textContent = fm(tot);
  if (ba) ba.textContent = fm(ann);
  if (bs2) bs2.textContent = fm(sal);
  if (btp && CD[curCity]) btp.textContent = CD[curCity].tip;
}

function calcCredit() {
  var start = parseInt(document.getElementById("cr-start").value) || 0;
  var strat = document.getElementById("cr-strat").value;
  var g = {a:[0,180,200,160,120,120,80], m:[0,80,100,80,70,80,70], p:[0,20,30,20,20,30,20]};
  var gains = g[strat] || g.a;
  var months = [0,3,6,9,12,18,24];
  var scores = [];
  var cur = start;
  gains.forEach(function(gn){cur = Math.min(900, cur + gn); scores.push(cur);});
  var cb = document.getElementById("cr-bars");
  if (!cb) return;
  cb.innerHTML = "";
  months.forEach(function(mo, i){
    var sc = scores[i], pct = Math.min(100, Math.round((sc / 900) * 100));
    var col = sc < 500 ? "#c62828" : sc < 650 ? "#f5a623" : sc < 720 ? "#07a076" : "#05825f";
    var div = document.createElement("div");
    div.className = "crb";
    div.innerHTML = "<div class=\\"crt2\\"><span>Month " + mo + "</span><span style=\\"font-weight:700;color:" + col + "\\">" + sc + "</span></div>" +
      "<div class=\\"crg2\\"><div class=\\"crf2\\" style=\\"width:" + pct + "%;background:" + col + "\\"></div></div>";
    cb.appendChild(div);
  });
  var cms = document.getElementById("cr-ms");
  if (!cms) return;
  cms.innerHTML = "";
  [{sc:scores[2],lbl:"6 months",t:"Unsecured card eligible"},{sc:scores[4],lbl:"12 months",t:"Better rates available"},{sc:scores[6],lbl:"24 months",t:"Mortgage-ready"}].forEach(function(ms){
    var div = document.createElement("div");
    div.className = "crm2";
    div.innerHTML = "<div class=\\"cms2\\">" + ms.sc + "</div><div class=\\"cml2\\">" + ms.lbl + "</div><div class=\\"cmt2\\">" + ms.t + "</div>";
    cms.appendChild(div);
  });
}

function calcFee() {
  var amt = parseFloat(document.getElementById("f-amt").value) || 1000;
  var dest = document.getElementById("f-dest").value;
  var dr = RATES[dest] || RATES.MAD;
  var rows = PROVIDERS.map(function(p){
    var fee = FEES[p.k] || 3;
    var recv = Math.max(0, amt - fee) * (dr[p.k] || 9);
    return {n:p.n, s:p.s, fee:fee, fx:FX_MARGIN[p.k] || 1, recv:recv};
  }).sort(function(a,b){return b.recv - a.recv;});
  var tb = document.getElementById("f-body");
  if (!tb) return;
  tb.innerHTML = "";
  rows.forEach(function(p, i){
    var tr = document.createElement("tr");
    tr.className = i === 0 ? "fb" : "";
    var badge = i === 0 ? "<span class=\\"fbb\\">BEST</span>" : "";
    tr.innerHTML = "<td><strong>" + p.n + "</strong>" + badge + "</td>" +
      "<td>" + (p.fee === 0 ? "<span style=\\"color:#05825f;font-weight:700\\">No fee</span>" : "$" + p.fee.toFixed(2)) + "</td>" +
      "<td>" + p.fx + "%</td>" +
      "<td style=\\"font-weight:700;color:#001f3f\\">" + Math.round(p.recv).toLocaleString("en-CA") + " " + dest + "</td>" +
      "<td style=\\"font-size:11px;color:#5c7a8a\\">" + p.s + "</td>";
    tb.appendChild(tr);
  });
}

function calcMortgage() {
  var price = parseFloat(document.getElementById("m-price").value) || 500000;
  var down = parseFloat(document.getElementById("m-down").value) || 10;
  var rate = parseFloat(document.getElementById("m-rate").value) || 5.5;
  var years = parseInt(document.getElementById("m-years").value) || 25;
  var dp = price * (down / 100), loan = price - dp;
  var r = rate / 100 / 12, n = years * 12;
  var mp = r === 0 ? loan / n : loan * (r * Math.pow(1+r,n)) / (Math.pow(1+r,n) - 1);
  var totalInt = mp * n - loan;
  var mm = document.getElementById("m-monthly"),
      mdp = document.getElementById("m-dp"),
      ml = document.getElementById("m-loan"),
      mi = document.getElementById("m-int"),
      ms = document.getElementById("m-sub");
  if (mm) mm.textContent = "$" + Math.round(mp).toLocaleString("en-CA");
  if (mdp) mdp.textContent = "$" + Math.round(dp).toLocaleString("en-CA");
  if (ml) ml.textContent = "$" + Math.round(loan).toLocaleString("en-CA");
  if (mi) mi.textContent = "$" + Math.round(totalInt).toLocaleString("en-CA");
  if (ms) ms.textContent = "On a $" + Math.round(loan/1000) + "K mortgage at " + rate + "% over " + years + " years";
}

/* ══ RATES TABS (from new page) ══ */
function initRatesTabs() {
  var tabs = document.querySelectorAll(".rtab");
  tabs.forEach(function(tab){
    tab.addEventListener("click", function(){
      tabs.forEach(function(t){t.classList.remove("on");});
      tab.classList.add("on");
      var target = tab.dataset.panel;
      document.querySelectorAll(".rpanel").forEach(function(p){
        p.style.display = p.id === target ? "block" : "none";
      });
    });
  });
}

/* ══ STATS COUNTER ══ */
function initCounters() {
  var ob = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if (!e.isIntersecting) return;
      var el = e.target, target = parseInt(el.dataset.to, 10), cur = 0;
      var step = Math.max(1, Math.round(target / 50));
      var ti = setInterval(function(){
        cur = Math.min(cur + step, target);
        el.textContent = cur + (target > 100 ? "K+" : "+");
        if (cur >= target) clearInterval(ti);
      }, 28);
      ob.unobserve(el);
    });
  }, {threshold:0.3});
  document.querySelectorAll("[data-to]").forEach(function(el){ob.observe(el);});
}

/* ══ REVEAL ON SCROLL ══ */
function initReveal() {
  var ob = new IntersectionObserver(function(entries){
    entries.forEach(function(e, i){
      if (e.isIntersecting){
        setTimeout(function(){e.target.classList.add("in");}, i * 60);
        ob.unobserve(e.target);
      }
    });
  }, {threshold:0.05});
  document.querySelectorAll(".rv").forEach(function(el){ob.observe(el);});
}

/* ══ MOBILE NAV ══ */
function toggleMob() {
  var h = document.getElementById("ham");
  var m = document.getElementById("mob");
  if (h) h.classList.toggle("open");
  if (m) m.classList.toggle("open");
}

/* == NEWSLETTER -- wired to WPForms 48766 via manual fetch(), no WPForms JS dependency 2026-07-14 == */
function initNewsletter() {
  var form = document.getElementById("nl-form");
  if (!form) return;
  var successEl = document.getElementById("nl-success-msg");
  var errorEl = document.getElementById("nl-error-msg");
  form.addEventListener("submit", function(e){
    e.preventDefault();
    var emailInput = document.getElementById("nl-email-visible");
    var btn = form.querySelector("button");
    var email = emailInput ? emailInput.value : "";
    if (errorEl) errorEl.style.display = "none";
    if (successEl) successEl.style.display = "none";
    var original = btn.textContent;
    btn.textContent = "Sending...";
    btn.disabled = true;
    var fd = new FormData();
    fd.append("action", "wpforms_submit");
    fd.append("wpforms[id]", "48766");
    fd.append("wpforms[fields][1]", "");
    fd.append("wpforms[fields][2]", email);
    fd.append("page_title", "Home");
    fd.append("page_url", window.location.href);
    fd.append("url_referer", "");
    fd.append("page_id", "7203");
    fd.append("wpforms[post_id]", "7203");
    fd.append("wpforms[submit]", "wpforms-submit");
    fd.append("wpforms[token]", form.dataset.token || "");
    fd.append("wpforms[token_time]", form.dataset.tokenTime || "");
    fetch("/wp-admin/admin-ajax.php", { method: "POST", body: fd, credentials: "same-origin" })
      .then(function(r){ return r.json(); })
      .then(function(data){
        btn.disabled = false;
        btn.textContent = original;
        if (data && data.success) {
          form.style.display = "none";
          if (successEl) successEl.style.display = "block";
        } else {
          if (errorEl) errorEl.style.display = "block";
        }
      })
      .catch(function(){
        btn.disabled = false;
        btn.textContent = original;
        if (errorEl) errorEl.style.display = "block";
      });
  });
}


/* == DESKTOP MEGA MENU definitive fix 2026-04-05 == */
function initDesktopMenu() {
  var overlay = document.createElement("div");
  overlay.id = "nav-overlay";
  document.body.appendChild(overlay);
  var navItems = document.querySelectorAll(".nav-list > .ni");

  function closeAll() {
    navItems.forEach(function(item) { item.classList.remove("open"); });
    overlay.style.display = "none";
  }

  // Fermer tout au chargement (évite les états bloqués)
  closeAll();

  navItems.forEach(function(item) {
    if (!item.querySelector(".dr")) return;
    var trigger = item.querySelector(".na");

    // Hover pour ouvrir
    item.addEventListener("mouseenter", function() {
      closeAll();
      item.classList.add("open");
      overlay.style.display = "block";
    });

    // Quitter le dropdown = fermer
    item.addEventListener("mouseleave", function() {
      closeAll();
    });

    // Garder le clic aussi pour mobile/accessibilité
    if (trigger) {
      trigger.addEventListener("click", function(e) {
        e.stopPropagation();
        var isOpen = item.classList.contains("open");
        closeAll();
        if (!isOpen) {
          item.classList.add("open");
          overlay.style.display = "block";
        }
      });
    }
  });

  overlay.addEventListener("click", closeAll);
  document.addEventListener("keydown", function(e) {
    if (e.key === "Escape") closeAll();
  });
  document.addEventListener("click", function(e) {
    var navList = document.querySelector(".nav-list");
    if (navList && !navList.contains(e.target)) closeAll();
  });
}

/* ══ INIT ALL ══ */
document.addEventListener("DOMContentLoaded", function(){
  initDesktopMenu();
  initSlider();
  calcTransfer();
  calcCredit();
  calcFee();
  calcMortgage();
  initRatesTabs();
  var idleFn = function(){initCounters();initReveal();initNewsletter();};
  if(window.requestIdleCallback){requestIdleCallback(idleFn);}else{setTimeout(idleFn,0);}
});

</script>
</body>
</html>';
        exit;
    }
}
register_activation_hook(__FILE__, ['MoneyAbroadGuideFusionUploadedHtml', 'activate']);
register_deactivation_hook(__FILE__, ['MoneyAbroadGuideFusionUploadedHtml', 'deactivate']);
new MoneyAbroadGuideFusionUploadedHtml();