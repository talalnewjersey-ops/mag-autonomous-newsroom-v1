// Add EEAT footer navigation sitewide
add_action('wp_footer', 'mag_eeat_footer_nav', 20);
function mag_eeat_footer_nav() {
	echo '<div id="mag-eeat-footer" style="background:#1a1a2e;color:#fff;padding:20px;text-align:center;font-family:sans-serif;font-size:13px;line-height:2;">';
	echo '<p style="margin:0 0 8px;">
	<a href="/about/" style="color:#9ca3af;margin:0 10px;">About</a>';
	echo '<a href="/contact/" style="color:#9ca3af;margin:0 10px;">Contact</a>';
	echo '<a href="/privacy-policy/" style="color:#9ca3af;margin:0 10px;">Privacy Policy</a>';
	echo '<a href="/terms-and-conditions/" style="color:#9ca3af;margin:0 10px;">Terms</a>';
	echo '<a href="/legal-disclaimer/" style="color:#9ca3af;margin:0 10px;">Disclaimer</a>';
	echo '<a href="/affiliate-disclosure/" style="color:#9ca3af;margin:0 10px;">Affiliate Disclosure</a>';
	echo '<a href="/editorial-policy/" style="color:#9ca3af;margin:0 10px;">Editorial Policy</a>';
	echo '<a href="/fact-checking-process/" style="color:#9ca3af;margin:0 10px;">Fact Checking</a>';
	echo '<a href="/how-we-test/" style="color:#9ca3af;margin:0 10px;">How We Test</a>';
	echo '<a href="/review-process/" style="color:#9ca3af;margin:0 10px;">Review Process</a>';
	echo '<a href="/corrections-policy/" style="color:#9ca3af;margin:0 10px;">Corrections Policy</a>';
	echo '<a href="/team/" style="color:#9ca3af;margin:0 10px;">Team</a></p>';
	echo '<p style="color:#6b7280;font-size:12px;margin:4px 0 0;">© 2026 Money Abroad Guide — Helping newcomers navigate financial life in the USA & Canada</p>';
	echo '</div>';
}