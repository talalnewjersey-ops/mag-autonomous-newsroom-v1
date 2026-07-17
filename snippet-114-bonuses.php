// MAG Conversion Optimizer V3
// Injects quizzes, calculators, lead capture and PDF downloads
// Target pages: USA (1364), Canada (1369), Ebook Credit Score (46505)
//
// 2026-07-17: all 3 target pages (46505 ebook, 1364 USA, 1369 Canada) now
// render this block via an explicit [mag_cv3] shortcode placed directly
// in their own content -- for 46505 that's post_content (Elementor
// disabled there); for 1364/1369 (Elementor-rendered, post_content
// ignored by the theme) the shortcode was appended to the existing
// "mag-ebook-001" HTML widget inside _elementor_data. Fixes the old
// wp_footer(99) hook rendering this block AFTER the theme/EEAT footers,
// which visually pushed the real site footer to mid-page on all 3.
// No page needs the wp_footer fallback anymore -- removed entirely.

add_shortcode('mag_cv3', 'mag_cv3_shortcode');

function mag_cv3_shortcode() {
    ob_start();
    mag_cv3_inject();
    return ob_get_clean();
}

function mag_cv3_inject() {
    $pid = get_the_ID();
    if (!in_array($pid, [1364, 1369, 46505])) return;
    $pt = ($pid == 1364) ? 'usa' : (($pid == 1369) ? 'canada' : 'ebook');
    mag_cv3_styles();
    mag_cv3_modal();
    mag_cv3_sections($pt);
    mag_cv3_scripts($pt);
}

function mag_cv3_styles() { ?>
<style>
#mag-cv3 { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.mag-sec { border-radius:16px; padding:60px 20px; margin:40px auto; max-width:1000px; }
.mag-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:24px; }
.mag-card { background:#fff; border-radius:12px; padding:28px 22px; box-shadow:0 6px 28px rgba(0,0,0,0.1); }
.mag-btn-dl { width:100%; padding:13px 18px; border:none; border-radius:8px; font-size:14px; font-weight:700; cursor:pointer; transition:opacity .2s; }
.mag-btn-dl:hover { opacity:.88; }
.mag-badge { display:inline-block; padding:5px 14px; border-radius:20px; font-size:12px; font-weight:700; letter-spacing:1px; margin-bottom:14px; }
.mag-h2 { font-size:clamp(22px,3.5vw,34px); font-weight:800; margin:0 0 12px; line-height:1.2; }
.mag-sub { font-size:16px; margin:0 0 36px; color:#555; }
.mag-overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.72); z-index:999999; align-items:center; justify-content:center; padding:20px; }
.mag-overlay.open { display:flex; }
.mag-box { background:#fff; border-radius:16px; padding:36px; max-width:440px; width:100%; position:relative; box-shadow:0 20px 60px rgba(0,0,0,0.28); animation:magIn .3s ease; }
@keyframes magIn { from{transform:translateY(-24px);opacity:0} to{transform:translateY(0);opacity:1} }
.mag-in { width:100%; padding:12px 14px; border:2px solid #e0e0e0; border-radius:8px; font-size:15px; box-sizing:border-box; outline:none; transition:border .2s; }
.mag-in:focus { border-color:#3949ab; }
.mag-lbl { display:block; font-size:13px; font-weight:600; color:#333; margin-bottom:5px; }
.mag-qbox { background:#fff; border-radius:12px; padding:26px; margin-bottom:18px; box-shadow:0 2px 10px rgba(0,0,0,0.06); }
.mag-opts { display:flex; flex-direction:column; gap:9px; margin-top:14px; }
.mag-opt { padding:11px 16px; border:2px solid #e0e0e0; border-radius:8px; background:#fff; font-size:14px; cursor:pointer; text-align:left; transition:all .2s; }
.mag-opt:hover,.mag-opt.sel { border-color:#3949ab; background:#e8eaf6; color:#1a237e; font-weight:600; }
.mag-result { text-align:center; padding:36px 20px; background:#fff; border-radius:14px; box-shadow:0 4px 20px rgba(0,0,0,0.08); }
.mag-ring { width:110px; height:110px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:30px; font-weight:900; margin:0 auto 18px; }
.mag-ctabs { display:flex; justify-content:center; gap:8px; margin-bottom:26px; flex-wrap:wrap; }
.mag-ctab { padding:10px 18px; border-radius:8px; font-weight:700; cursor:pointer; font-size:14px; transition:all .2s; }
.mag-cpanel { background:#fff; border-radius:14px; padding:32px; box-shadow:0 4px 20px rgba(0,0,0,0.07); }
.mag-crow { margin-bottom:18px; }
.mag-clbl { font-size:13px; font-weight:600; color:#444; margin-bottom:5px; display:block; }
.mag-cin { width:100%; padding:9px 13px; border:2px solid #e0e0e0; border-radius:8px; font-size:15px; box-sizing:border-box; }
.mag-cresult { background:#f8f9ff; border-radius:10px; padding:22px; margin-top:18px; text-align:center; }
.mag-cnum { font-size:34px; font-weight:900; margin:0 0 8px; }
@media(max-width:600px){.mag-sec{padding:40px 14px}.mag-card{padding:20px 14px}.mag-box{padding:26px 18px}.mag-cpanel{padding:22px 14px}}
</style>
<?php }

function mag_cv3_modal() { ?>
<div id="mag-overlay" class="mag-overlay" role="dialog" aria-modal="true">
<div class="mag-box">
  <button onclick="magClose()" style="position:absolute;top:13px;right:13px;background:none;border:none;font-size:22px;cursor:pointer;color:#999;">&#x2715;</button>
  <div id="mag-ico" style="font-size:46px;text-align:center;margin-bottom:12px;"></div>
  <h3 id="mag-ttl" style="color:#1a237e;font-size:19px;font-weight:800;text-align:center;margin:0 0 5px;"></h3>
  <p style="color:#666;font-size:13px;text-align:center;margin:0 0 20px;">Enter your details for instant free access</p>
  <form id="mag-form" onsubmit="magSubmit(event)" novalidate>
    <input type="hidden" id="mag-pdf" value=""><input type="hidden" id="mag-tag" value="">
    <div style="margin-bottom:13px;"><label class="mag-lbl" for="mag-nm">First Name *</label>
    <input type="text" id="mag-nm" class="mag-in" required placeholder="Your first name" autocomplete="given-name"></div>
    <div style="margin-bottom:20px;"><label class="mag-lbl" for="mag-em">Email Address *</label>
    <input type="email" id="mag-em" class="mag-in" required placeholder="your@email.com" autocomplete="email"></div>
    <button type="submit" id="mag-sbtn" style="width:100%;padding:14px;border:none;border-radius:9px;font-size:16px;font-weight:800;cursor:pointer;color:#fff;background:linear-gradient(135deg,#1a237e,#3949ab);">&#x2B07; Get Free Instant Access</button>
    <p style="color:#999;font-size:11px;text-align:center;margin:10px 0 0;">&#x1F512; No spam. Unsubscribe anytime.</p>
  </form>
  <div id="mag-ok" style="display:none;text-align:center;">
    <div style="font-size:60px;margin-bottom:12px;">&#x2705;</div>
    <h3 style="color:#2e7d32;margin:0 0 10px;">Your PDF is Ready!</h3>
    <p style="color:#555;margin:0 0 20px;">Click below to download:</p>
    <a id="mag-dl" href="#" style="display:inline-block;background:linear-gradient(135deg,#2e7d32,#43a047);color:#fff;text-decoration:none;padding:13px 28px;border-radius:9px;font-size:16px;font-weight:800;">&#x2B07; Download PDF Now</a>
    <div id="mag-upsell" style="margin-top:14px;"></div>
  </div>
</div></div>
<?php }

function mag_cv3_sections($pt) {
    $c = mag_cv3_get_config($pt);
    echo '<div id="mag-cv3" data-page="' . esc_attr($pt) . '">';
    echo '<section class="mag-sec" style="background:' . $c['grad'] . ';padding:60px 20px;">';
    echo '<div style="max-width:900px;margin:0 auto;text-align:center;">';
    echo '<span class="mag-badge" style="background:rgba(255,255,255,0.22);color:#fff;">' . esc_html($c['dl_badge']) . '</span>';
    echo '<h2 class="mag-h2" style="color:#fff;">' . esc_html($c['dl_title']) . '</h2>';
    echo '<p style="color:rgba(255,255,255,0.88);font-size:17px;margin:0 0 38px;">' . esc_html($c['dl_sub']) . '</p>';
    echo '<div class="mag-grid">';
    foreach ($c['pdfs'] as $pdf) {
        echo '<div class="mag-card" style="text-align:left;">';
        echo '<div style="font-size:38px;margin-bottom:10px;">' . esc_html($pdf['icon']) . '</div>';
        echo '<h3 style="color:' . $c['accent'] . ';font-size:16px;font-weight:700;margin:0 0 7px;">' . esc_html($pdf['title']) . '</h3>';
        echo '<p style="color:#555;font-size:12px;margin:0 0 16px;line-height:1.65;">' . esc_html($pdf['desc']) . '</p>';
        echo '<button class="mag-btn-dl" style="background:' . $c['accent'] . ';color:#fff;" ';
        echo 'onclick="' . esc_attr('magLead(' . json_encode($pdf['id']) . ',' . json_encode($pdf['title']) . ',' . json_encode($pt) . ')') . '">&#x2B07; ' . esc_html($c['dl_cta']) . '</button>';
        echo '</div>';
    }
    echo '</div></div></section>';
    echo '<section class="mag-sec" style="background:' . $c['qbg'] . ';border:2px solid ' . $c['qborder'] . ';">';
    echo '<div style="max-width:700px;margin:0 auto;text-align:center;">';
    echo '<span class="mag-badge" style="background:' . $c['qbadgebg'] . ';color:' . $c['accent'] . ';">&#x1F9E0; ' . esc_html($c['quiz']['badge']) . '</span>';
    echo '<h2 class="mag-h2" style="color:' . $c['accent'] . ';">' . esc_html($c['quiz']['title']) . '</h2>';
    echo '<p class="mag-sub">' . esc_html($c['quiz']['sub']) . '</p>';
    echo '<div id="mag-quiz" style="text-align:left;"></div>';
    echo '</div></section>';
    echo '<section class="mag-sec" style="padding:60px 20px;">';
    echo '<div style="max-width:900px;margin:0 auto;text-align:center;">';
    echo '<span class="mag-badge" style="background:' . $c['cbadgebg'] . ';color:' . $c['accent'] . ';">&#x1F522; FREE CALCULATORS</span>';
    echo '<h2 class="mag-h2" style="color:' . $c['accent'] . ';">' . esc_html($c['calc_title']) . '</h2>';
    echo '<p class="mag-sub">' . esc_html($c['calc_sub']) . '</p>';
    echo '<div class="mag-ctabs" id="mag-ctabs">';
    $fi = true;
    foreach ($c['calcs'] as $k => $cv) {
        $s = $fi ? 'background:' . $c['accent'] . ';color:#fff;border-color:' . $c['accent'] . ';' : 'background:#fff;color:' . $c['accent'] . ';border-color:' . $c['accent'] . ';';
        echo '<button class="mag-ctab" id="mct-' . esc_attr($k) . '" onclick="' . esc_attr('magCalc(' . json_encode($k) . ')') . '" style="border:2px solid ' . $c['accent'] . ';' . $s . '">' . esc_html($cv) . '</button>';
        $fi = false;
    }
    echo '</div><div class="mag-cpanel" id="mag-cpanel"></div>';
    echo '</div></section>';
    echo '</div>';
}

function mag_cv3_get_config($pt) {
    $cfgs = [
        'usa' => [
            'grad' => 'linear-gradient(135deg,#1a237e 0%,#283593 50%,#3949ab 100%)',
            'accent' => '#1a237e', 'dl_badge' => 'FREE RESOURCES',
            'dl_title' => 'Your Complete USA Newcomer Toolkit',
            'dl_sub' => 'Download our 3 professional PDF guides — 100% free',
            'dl_cta' => 'Download Free PDF Guide',
            'qbg' => '#f8f9ff', 'qborder' => '#e8eaf6', 'qbadgebg' => '#e8eaf6',
            'cbadgebg' => '#e8f5e9', 'calc_title' => 'USA Financial Calculators',
            'calc_sub' => 'Plan your finances as a newcomer to the USA',
            'pdfs' => [
                ['id'=>'usa-checklist','icon'=>'📋','title'=>'Newcomer USA Checklist','desc'=>'SSN, bank account, credit card, driver license, health insurance, first apartment and credit building.'],
                ['id'=>'usa-30days','icon'=>'🗓️','title'=>'First 30 Days in America','desc'=>'Day-by-day action plan for your first month. Priority tasks and tips from real newcomers.'],
                ['id'=>'usa-credit','icon'=>'📈','title'=>'Credit Score Starter Checklist','desc'=>'From zero credit history to a solid FICO score. Best first cards and credit-builder loans.'],
            ],
            'quiz' => ['badge'=>'QUIZ','title'=>'Are You Ready for Life in the USA?','sub'=>'10 quick questions — get your personalized readiness score'],
            'calcs' => ['credit'=>'Credit Score','living'=>'Cost of Living','savings'=>'Savings Goal'],
        ],
        'canada' => [
            'grad' => 'linear-gradient(135deg,#b71c1c 0%,#c62828 50%,#d32f2f 100%)',
            'accent' => '#b71c1c', 'dl_badge' => 'FREE RESOURCES',
            'dl_title' => 'Your Complete Canada Newcomer Starter Kit',
            'dl_sub' => 'Download our 4 professional PDF guides — 100% free',
            'dl_cta' => 'Download Free Canada Starter Kit',
            'qbg' => '#fff5f5', 'qborder' => '#ffcdd2', 'qbadgebg' => '#ffcdd2',
            'cbadgebg' => '#fce4ec', 'calc_title' => 'Canada Financial Calculators',
            'calc_sub' => 'Plan your finances as a newcomer to Canada',
            'pdfs' => [
                ['id'=>'canada-checklist','icon'=>'📋','title'=>'Newcomer Canada Checklist','desc'=>'SIN, bank account, credit card, provincial health card and housing — all your first steps.'],
                ['id'=>'canada-30days','icon'=>'🗓️','title'=>'First 30 Days in Canada','desc'=>'Day-by-day action plan for your first month in Canada.'],
                ['id'=>'canada-credit','icon'=>'📈','title'=>'Credit Building in Canada','desc'=>'Equifax vs TransUnion, secured cards, newcomer programs — your complete Canadian credit roadmap.'],
                ['id'=>'canada-health','icon'=>'🏥','title'=>'Provincial Health Insurance','desc'=>'Province-by-province health card eligibility, waiting periods — Ontario, BC, Quebec, Alberta.'],
            ],
            'quiz' => ['badge'=>'QUIZ','title'=>'How Prepared Are You for Canada?','sub'=>'10 quick questions — get your personalized Canada readiness score'],
            'calcs' => ['living'=>'Cost of Living','budget'=>'Monthly Budget','savings'=>'Newcomer Savings'],
        ],
        'ebook' => [
            'grad' => 'linear-gradient(135deg,#B8862E 0%,#D4AF37 50%,#F3E5AB 100%)',
            'accent' => '#B8862E', 'dl_badge' => 'FREE BEFORE YOU BUY',
            'dl_title' => 'Try Before You Buy — 6 Free Resources',
            'dl_sub' => 'Get a taste of the ebook quality — completely free',
            'dl_cta' => 'Download Free Sample',
            'qbg' => '#fff8e1', 'qborder' => '#ffe082', 'qbadgebg' => '#ffe082',
            'cbadgebg' => '#fff3e0', 'calc_title' => 'Credit Score Calculators',
            'calc_sub' => 'See exactly where you stand and where you are going',
            'pdfs' => [
                ['id'=>'ebook-sample','icon'=>'📖','title'=>'Free Sample Chapter','desc'=>'Read Chapter 1 of the ebook — discover the exact FICO scoring model.'],
                ['id'=>'ebook-roadmap','icon'=>'🗺️','title'=>'Credit Score Roadmap','desc'=>'Visual 12-month roadmap from 0 to 700+ credit score.'],
                ['id'=>'ebook-mistakes','icon'=>'⚠️','title'=>'Credit Score Mistakes','desc'=>'The 15 most common mistakes newcomers make when building credit.'],
                ['id'=>'ebook-bonus-templates','icon'=>'✉️','title'=>'Email & Letter Templates','desc'=>'Educational templates for credit limit requests, goodwill letters, and landlord references.'],
                ['id'=>'ebook-bonus-tracker','icon'=>'📅','title'=>'12-Month Credit Tracker','desc'=>'A month-by-month checklist to track your credit-building progress.'],
                ['id'=>'ebook-bonus-cards','icon'=>'💳','title'=>'Best Secured Cards (2026)','desc'=>'Fact-checked list of secured cards for newcomers, verified July 2026.'],
            ],
            'quiz' => ['badge'=>'CREDIT READINESS QUIZ','title'=>'What Is Your Credit Score Potential?','sub'=>'Answer 4 quick questions to get your estimated Credit Readiness Score'],
            'calcs' => ['growth'=>'Score Growth','debt'=>'Debt Payoff','utilization'=>'Utilization'],
        ],
    ];
    return $cfgs[$pt];
}

add_action('wp_ajax_nopriv_mag_cv3_lead', 'mag_cv3_save_lead');
add_action('wp_ajax_mag_cv3_lead', 'mag_cv3_save_lead');
function mag_cv3_save_lead() {
    if (!check_ajax_referer('mag_cv3', 'n', false)) { wp_send_json_error('Security check failed'); }
    $name = sanitize_text_field($_POST['name'] ?? '');
    $email = sanitize_email($_POST['email'] ?? '');
    $pdf = sanitize_text_field($_POST['pdf'] ?? '');
    $tag = sanitize_text_field($_POST['tag'] ?? '');
    if (!is_email($email)) { wp_send_json_error('Invalid email'); }
    $leads = get_option('mag_leads_v3', []);
    $leads[] = ['date'=>current_time('mysql'),'name'=>$name,'email'=>$email,'pdf'=>$pdf,'tag'=>$tag];
    if (count($leads) > 2000) $leads = array_slice($leads, -2000);
    update_option('mag_leads_v3', $leads);
    wp_send_json_success(['pdf'=>$pdf]);
}

function mag_cv3_scripts($pt) {
    $nonce = wp_create_nonce('mag_cv3');
    $ajax = admin_url('admin-ajax.php');
    $ebook_url = get_permalink(46505);
    
    $pdf_data = [
        'usa-checklist' => ['icon'=>'📋','color'=>[26,35,126],'title'=>'Newcomer USA Checklist','subtitle'=>'Your Complete First Steps in America',
            'sections'=>[
                ['h'=>'1. Social Security Number (SSN)','items'=>['Visit your local Social Security Administration office','Bring passport, visa and I-94 arrival record','Wait 10 business days after arrival to apply','Processing takes 2-4 weeks — expect card by mail','Use SSN to open bank account, build credit, work legally']],
                ['h'=>'2. Bank Account','items'=>['Open checking and savings account within first week','Best banks for newcomers: Chase, Bank of America, Wells Fargo','No-fee options: Chime, Discover, Charles Schwab','Bring: passport, visa, address proof, initial deposit ($25-$100)','Set up low balance alerts to avoid overdraft fees']],
                ['h'=>'3. First Credit Card','items'=>['Apply for secured credit card (no SSN needed initially)','Best first cards: Discover it Secured, Capital One Platinum','Deposit $200-$500 as collateral equals your credit limit','Use for small purchases, pay IN FULL every month','Check for graduation to unsecured card after 12 months']],
                ['h'=>'4. Driver License','items'=>['Visit your state DMV within 60 days of arrival','Documents: passport, visa, I-94, proof of residency (2 docs)','Pass written knowledge test (study state DMV manual)','Pass vision test and road test','Fee: $25-$80 depending on state']],
                ['h'=>'5. Health Insurance','items'=>['Check employer coverage (if employed)','ACA Marketplace: healthcare.gov (open enrollment Nov-Jan)','Medicaid if income is low (income-based eligibility)','Short-term plans available as bridge coverage','ERs must treat regardless of insurance status']],
                ['h'=>'6. First Apartment','items'=>['Budget: 30% of gross income for rent','No US credit? Use bank statements and larger deposit','Consider co-signer or guarantor services (TheGuarantor)','Furnished short-term: Furnished Finder, Airbnb Monthly','Read lease carefully before signing']],
                ['h'=>'7. Build Credit Score','items'=>['Month 1-3: Open secured credit card, pay on time','Month 3-6: Apply for credit-builder loan at local credit union','Month 6-12: Request credit limit increase','Month 12+: Apply for your first rewards card','Never miss a payment — payment history is 35% of score']],
            ]],
        'usa-30days' => ['icon'=>'🗓️','color'=>[26,35,126],'title'=>'First 30 Days in America','subtitle'=>'Your Week-by-Week Action Plan',
            'sections'=>[
                ['h'=>'WEEK 1 — Settle In','items'=>['Find temporary housing (hotel, Airbnb, or host family)','Buy a US SIM card (T-Mobile, AT&T, or prepaid)','Visit SSA office to start SSN application','Set up a bank account (bring passport and visa)','Connect utilities or confirm they are included in rent']],
                ['h'=>'WEEK 2 — Documents','items'=>['Apply for Social Security Number (SSN)','Get proof of address (bank statement, lease)','Register at your local public library (free Wi-Fi, resources)','Find nearest grocery stores, pharmacy, public transit','Research health insurance options for your situation']],
                ['h'=>'WEEK 3 — Credit and Finance','items'=>['Apply for secured credit card once SSN arrives','Set up autopay for credit card (minimum payment)','Download credit monitoring app (Credit Karma — free)','Start tracking monthly expenses in a spreadsheet','Research your state DMV requirements for driver license']],
                ['h'=>'WEEK 4 — Integration','items'=>['Visit DMV for driver license (if needed)','Explore neighborhood: grocery stores, parks, community centers','Join local newcomer groups on Facebook or Meetup','Set up a budget for Month 2 and beyond','Review your credit report at AnnualCreditReport.com']],
            ]],
        'usa-credit' => ['icon'=>'📈','color'=>[46,125,50],'title'=>'Credit Score Starter Checklist','subtitle'=>'Your 12-Month Roadmap to 700+ FICO',
            'sections'=>[
                ['h'=>'Understanding Your FICO Score','items'=>['Payment History: 35% — NEVER miss a due date','Credit Utilization: 30% — keep below 30% of limit','Length of History: 15% — keep old accounts open','Credit Mix: 10% — have both cards and loans','New Inquiries: 10% — limit hard inquiries to 1-2 per year']],
                ['h'=>'Month 1-3: Foundation','items'=>['Open secured credit card (Discover it Secured recommended)','Deposit $500 equals $500 credit limit','Set up autopay for FULL balance each month','Use card for ONE recurring bill only (Netflix, Spotify)','Check if your SSN is processing correctly']],
                ['h'=>'Month 3-6: Accelerate','items'=>['Open credit-builder loan at credit union ($500-$1,000)','Become authorized user on trusted friend or family card','Apply for Experian Boost (free — adds utility payments)','Keep utilization under 10% for fastest growth','Check all 3 bureaus: Equifax, Experian, TransUnion']],
                ['h'=>'Common Mistakes to Avoid','items'=>['Never pay only the minimum — pay IN FULL','Never close your oldest credit card','Never apply for 3 or more cards in 6 months','Never ignore a collection notice — dispute immediately','Never max out your credit card — stay under 30%']],
            ]],
        'canada-checklist' => ['icon'=>'📋','color'=>[183,28,28],'title'=>'Newcomer Canada Checklist','subtitle'=>'Your Complete First Steps in Canada',
            'sections'=>[
                ['h'=>'1. Social Insurance Number (SIN)','items'=>['Apply at Service Canada within your first week','Bring: passport, PR card or work/study permit, proof of address','SIN is FREE — beware of scam websites charging fees','Used for: employment, banking, taxes, government benefits','Keep SIN confidential — share only when legally required']],
                ['h'=>'2. Bank Account','items'=>['Best newcomer accounts: Scotiabank StartRight, TD New to Canada','Bring: passport, visa or PR card, proof of address','Many banks waive fees for first year as newcomer','Open both chequing and savings accounts','Apply for Interac debit card immediately']],
                ['h'=>'3. First Credit Card','items'=>['Apply for newcomer credit card (no Canadian history required)','Best options: Scotiabank Scene+ Visa, CIBC Aventura','Secured options: Home Trust Secured Visa','Use for regular purchases, pay in full monthly','Building credit takes 6-12 months — start now']],
                ['h'=>'4. Provincial Health Card','items'=>['Apply within first 3 months of arrival (waiting periods apply)','Ontario (OHIP): 3-month waiting period','BC (BC Services Card): 3-month waiting period','Quebec (RAMQ): 3-month waiting period','Alberta: NO waiting period — register immediately']],
            ]],
        'canada-30days' => ['icon'=>'🗓️','color'=>[183,28,28],'title'=>'First 30 Days in Canada','subtitle'=>'Your Week-by-Week Action Plan',
            'sections'=>[
                ['h'=>'WEEK 1 — Arrive and Settle','items'=>['Get Canadian SIM card (Koodo, Fido, Lucky Mobile)','Apply for Social Insurance Number (SIN) at Service Canada','Open bank account (bring passport and landing documents)','Find temporary housing (Airbnb, extended stay hotel)','Register children for school if applicable']],
                ['h'=>'WEEK 2 — Essential Documents','items'=>['Apply for provincial health card','Get proof of address (bank statement or lease agreement)','Apply for newcomer credit card at your bank','Register for Canada Post mail forwarding if needed','Locate nearest Service Canada and local settlement agency']],
                ['h'=>'WEEK 3 — Finance and Integration','items'=>['Set up online banking and bill payments','Research TFSA and RRSP accounts for tax-free savings','Sign up for free government benefits if eligible (CCB, GST credit)','Research driver license exchange process','Connect with local newcomer community groups']],
                ['h'=>'WEEK 4 — Plan and Establish','items'=>['Create monthly budget including rent, food, transit, phone','Apply for driver license at ServiceOntario or ICBC','Explore employment resources: settlement agencies, LinkedIn','Research educational credential recognition if needed','File for SIN-linked government benefits at Canada.ca']],
            ]],
        'canada-credit' => ['icon'=>'📈','color'=>[183,28,28],'title'=>'Credit Building in Canada','subtitle'=>'Your Roadmap to a Strong Canadian Credit Score',
            'sections'=>[
                ['h'=>'The Two Canadian Credit Bureaus','items'=>['Equifax Canada — main bureau used by most banks','TransUnion Canada — used by many lenders and landlords','Both bureaus score from 300-900 (vs US 300-850)','Good score in Canada: 660+ / Excellent: 760+','Check free: Borrowell (Equifax), Credit Karma (TransUnion)']],
                ['h'=>'Month 1-3: Start Building','items'=>['Open newcomer credit card at your bank (no history needed)','Best newcomer programs: Scotiabank, TD, CIBC offer these','Use card for small purchases only','Set autopay for FULL balance — never carry a balance','Register for Borrowell and Credit Karma (both free)']],
                ['h'=>'Month 6-12: Grow','items'=>['Request credit limit increase on your first card','Apply for second credit card if score is 660+','Look into store credit cards (Canadian Tire, Walmart)','Goal: 700+ score by end of year one','Keep all accounts in good standing']],
            ]],
        'canada-health' => ['icon'=>'🏥','color'=>[183,28,28],'title'=>'Provincial Health Insurance','subtitle'=>'Canada-Wide Guide for Newcomers',
            'sections'=>[
                ['h'=>'Ontario (OHIP)','items'=>['3-month waiting period from date of registration','Documents: passport, PR card or work permit, proof of Ontario address','Apply: ServiceOntario office','During wait: buy private health insurance (Manulife, Sun Life)','Coverage: doctor visits, hospital stays, lab tests, surgery']],
                ['h'=>'British Columbia (MSP)','items'=>['3-month waiting period for new residents','Apply online at hibc.gov.bc.ca','Documents: passport, immigration status document, BC address proof','Coverage: medically necessary services, hospital, doctors']],
                ['h'=>'Alberta (AHCIP)','items'=>['NO waiting period — register immediately upon arrival!','Apply at Alberta Health (alberta.ca/ahcip)','Documents: immigration status and Alberta address proof','Premiums: free for most residents since 2009']],
                ['h'=>'Quebec (RAMQ)','items'=>['3-month waiting period for new residents','Apply at RAMQ (ramq.gouv.qc.ca)','Documents: proof of Quebec residency and immigration status','During wait: obtain private insurance from employer or buy directly']],
            ]],
        'ebook-sample' => ['icon'=>'📖','color'=>[230,81,0],'title'=>'Free Sample Chapter','subtitle'=>'Build Your Credit Score in the USA — Chapter 1',
            'sections'=>[
                ['h'=>'What Is a Credit Score and Why It Matters','items'=>['Your FICO score is a 3-digit number between 300-850','It tells lenders how likely you are to repay debt','Used for: renting apartments, car loans, mortgages, even jobs','Newcomers start with NO credit score — called credit invisible','Good news: you can build from 0 to 700+ in 12-18 months']],
                ['h'=>'The 5 Factors of Your FICO Score','items'=>['Payment History (35%): Most important — NEVER miss a payment','Credit Utilization (30%): Keep balances under 30% of limits','Length of Credit History (15%): Older accounts = better','Credit Mix (10%): Having both cards and loans helps','New Inquiries (10%): Limit new applications to 1-2 per year']],
                ['h'=>'Your First 3 Steps','items'=>['Step 1: Open a US bank account (Chase, Bank of America, Discover)','Step 2: Apply for a secured credit card (Discover it Secured)','Step 3: Set up autopay for the FULL balance every month','Start with these 3 steps in Month 1','The full ebook gives you the complete 12-month roadmap']],
            ]],
        'ebook-roadmap' => ['icon'=>'🗺️','color'=>[230,81,0],'title'=>'Credit Score Roadmap','subtitle'=>'12 Months from 0 to 700+ FICO Score',
            'sections'=>[
                ['h'=>'Month 1-2: The Foundation','items'=>['Action: Open secured credit card with $500 deposit','Action: Use for ONE subscription (Netflix or Spotify)','Action: Set up autopay for FULL balance','Expected score: 580-620 after first statement closes','Milestone: First credit score appears on your reports']],
                ['h'=>'Month 3-6: Diversify','items'=>['Action: Apply for credit-builder loan ($500-$1,000)','Action: Become authorized user on family card','Action: Register for Experian Boost','Expected score: 620-650','Milestone: Two positive tradelines on your report']],
                ['h'=>'Month 7-12: Elevate','items'=>['Action: Request credit limit increase on secured card','Action: Apply for second credit card (if score 660+)','Action: Apply for first rewards credit card at month 12','Expected score: 700-730+','Milestone: Excellent credit access — lower rates, better terms']],
            ]],
        'ebook-mistakes' => ['icon'=>'⚠️','color'=>[230,81,0],'title'=>'Credit Score Mistakes Checklist','subtitle'=>'15 Costly Errors That Set Newcomers Back',
            'sections'=>[
                ['h'=>'Mistakes 1-5: Application Errors','items'=>['1. Applying for 3+ credit cards in 6 months (each = hard inquiry)','2. Applying with a thin file — wait until secured card has 3+ months','3. Ignoring pre-qualification tools — use them to avoid hard pulls','4. Applying for cards with rewards you do not qualify for yet','5. Not checking your credit reports before applying']],
                ['h'=>'Mistakes 6-10: Usage Errors','items'=>['6. Carrying a balance to build credit — MYTH, it costs money','7. Maxing out credit cards (crushes your utilization score)','8. Missing a payment — even one can drop score 60-110 points','9. Closing your oldest credit card — hurts length of history','10. Co-signing a loan for someone with bad payment habits']],
                ['h'=>'Mistakes 11-15: Strategy Errors','items'=>['11. Not monitoring all 3 bureaus (Equifax, Experian, TransUnion)','12. Ignoring errors on your credit report — dispute them!','13. Waiting too long to start — every month without credit = lost time','14. Using debit card for everything — debit does not build credit','15. Not asking for a credit limit increase after 12 months']],
            ]],
        'ebook-bonus-templates' => ['icon'=>'✉️','color'=>[230,81,0],'title'=>'Credit-Building Email & Letter Templates','subtitle'=>'Educational Templates — Not Credit Repair Services',
            'sections'=>[
                ['h'=>'Before You Use These Templates','items'=>['Educational templates only. MoneyAbroadGuide.com does not provide credit repair, credit dispute, or legal services.','Customize every template with your real details before sending — do not send as-is.','Requirements and policies change; verify current rules directly with your card issuer or the credit bureau before relying on any template.']],
                ['h'=>'Credit Limit Increase Request','items'=>['Use after 6-12 consecutive months of on-time payments and utilization consistently under 30%.','State your account tenure, payment history, and requested new limit clearly.','Ask whether the review requires a hard inquiry before submitting.']],
                ['h'=>'Goodwill Adjustment Letter','items'=>['Use for a single, isolated late payment on an otherwise clean account.','Reference your account history and explain the circumstance briefly and factually.','Request removal of the late-payment mark as a goodwill gesture, not a legal dispute.']],
                ['h'=>'Landlord / Lender Reference Request','items'=>['Use when you lack traditional US credit history but have a positive rental or utility payment record.','Ask your current or former landlord to confirm on-time payment history in writing.','Attach this letter to rental applications as supporting evidence alongside your credit file.']],
            ]],
        'ebook-bonus-tracker' => ['icon'=>'📅','color'=>[230,81,0],'title'=>'Your 12-Month Credit-Building Tracker','subtitle'=>'A Month-by-Month Checklist',
            'sections'=>[
                ['h'=>'Months 1-3: Foundation','items'=>['Apply for SSN or ITIN if not yet obtained','Open a checking/savings account','Apply for your first secured credit card','Set up autopay for at least the minimum payment']],
                ['h'=>'Months 4-6: Build the Habit','items'=>['Keep utilization under 30% every statement cycle','Check your FICO score for the first time (many issuers provide this free)','Confirm all payments have posted on time']],
                ['h'=>'Months 7-9: Expand','items'=>['Request a credit limit increase if eligible','Pull your 3-bureau report and check for errors','Consider a second tradeline only if utilization discipline is solid']],
                ['h'=>'Months 10-12: Evaluate','items'=>['Assess eligibility for graduation to an unsecured card','Review your 12-month score trend','Set next-year goals (auto loan, apartment lease, etc.)']],
            ]],
        'ebook-bonus-cards' => ['icon'=>'💳','color'=>[230,81,0],'title'=>'Best Secured Credit Cards for Newcomers (2026)','subtitle'=>'Verified July 2026',
            'sections'=>[
                ['h'=>'Capital One Platinum Secured','items'=>['Minimum deposit: $49, $99, or $200 (opens a credit line of at least $200)','ITIN: Capital One\'s own educational page lists this card among those ITIN applicants "may be able to get" — not a guarantee, confirm directly when applying','Source: capitalone.com/credit-cards/platinum-secured/']],
                ['h'=>'Capital One Quicksilver Secured','items'=>['Minimum deposit: $200 (opens a credit line of at least $200), cash-back rewards card','ITIN: same Capital One page lists this card under the same "may be able to get with an ITIN" language','Source: capitalone.com/credit-cards/quicksilver-secured/']],
                ['h'=>'OpenSky Secured Visa','items'=>['No credit check to apply; deposit range $200-$3,000 depending on tier','SSN/ITIN policy not stated on OpenSky\'s public page — confirm directly with OpenSky before applying','Source: openskycc.com']],
                ['h'=>'Verified July 2026 — Notes','items'=>['Deserve EDU excluded: discontinued, no new applications since April 2026.','Discover it Secured excluded: not accepting new applications since June 2, 2026 (per a Capital One spokesperson statement); expected to relaunch later in 2026.']],
            ]],
    ];
    
    $quiz_data = [
        'usa' => [
            'questions' => [
                ['q'=>'Do you have a US Social Security Number (SSN)?','opts'=>['Yes, already received it','Applied but waiting','Not yet applied','Not sure how to get it']],
                ['q'=>'Have you opened a US bank account?','opts'=>['Yes, checking and savings','Yes, checking only','Not yet','I have one from my home country']],
                ['q'=>'Do you have a US credit card?','opts'=>['Yes, unsecured rewards card','Yes, secured credit card','No, still building credit','I do not know the difference']],
                ['q'=>'What is your current credit score status?','opts'=>['700+ (Excellent)','650-699 (Good)','Below 650 or not sure','I have no US credit history']],
                ['q'=>'Do you have US health insurance?','opts'=>['Yes, through employer','Yes, marketplace/ACA plan','Yes, Medicaid/CHIP','Not yet covered']],
                ['q'=>'Have you found permanent housing?','opts'=>['Yes, signed a lease','Temporary housing (month-to-month)','Living with friends/family','Still searching']],
                ['q'=>'How long have you been in the USA?','opts'=>['Less than 30 days','1-6 months','6-12 months','More than 1 year']],
                ['q'=>'Have you filed US taxes?','opts'=>['Yes, filed last year','Not needed yet (too new)','Not sure if I need to','No but I should have']],
                ['q'=>'Do you have a US driver license?','opts'=>['Yes, full license','Learners permit','Using foreign license','Not driving in the USA']],
                ['q'=>'How comfortable are you with the US financial system?','opts'=>['Very comfortable','Somewhat comfortable','A bit confused','Very uncertain — need help']],
            ],
            'results' => [
                ['min'=>0,'max'=>3,'level'=>'Beginner','emoji'=>'🌱','color'=>'#e65100','title'=>'Just Getting Started','desc'=>'Welcome to America! You are in the early stages. Our Newcomer Checklist PDF will give you the exact action steps to take this week.','ctas'=>[['type'=>'pdf','id'=>'usa-checklist','text'=>'Download Free Checklist'],['type'=>'ebook','text'=>'Get the Credit Ebook']]],
                ['min'=>4,'max'=>7,'level'=>'Intermediate','emoji'=>'🚀','color'=>'#1a237e','title'=>'Making Good Progress!','desc'=>'You are building your foundation in the USA. The Credit Score Starter Checklist will help you take the next step.','ctas'=>[['type'=>'pdf','id'=>'usa-credit','text'=>'Credit Score Checklist'],['type'=>'ebook','text'=>'Build Credit Ebook — $19.99']]],
                ['min'=>8,'max'=>10,'level'=>'Advanced','emoji'=>'⭐','color'=>'#2e7d32','title'=>'Well Established in the USA!','desc'=>'You are doing great! The full ebook will help you maximize your credit and financial potential.','ctas'=>[['type'=>'ebook','text'=>'Get the Full Ebook — $19.99'],['type'=>'pdf','id'=>'usa-30days','text'=>'First 30 Days PDF']]],
            ],
        ],
        'canada' => [
            'questions' => [
                ['q'=>'Do you have a Canadian Social Insurance Number (SIN)?','opts'=>['Yes, already received it','Applied but waiting','Not yet applied','Not sure how to get it']],
                ['q'=>'Have you opened a Canadian bank account?','opts'=>['Yes, full banking setup','Yes, basic chequing only','No, still using foreign account','Not yet']],
                ['q'=>'Do you have a Canadian credit card?','opts'=>['Yes, rewards card','Yes, secured credit card','Applied but denied','Not yet started']],
                ['q'=>'Have you applied for provincial health insurance?','opts'=>['Yes, already covered','Applied, in waiting period','Not yet applied','Do not know the process']],
                ['q'=>'Have you found permanent housing in Canada?','opts'=>['Yes, signed a lease','Temporary furnished rental','With friends/family','Still searching']],
                ['q'=>'Have you registered with Service Canada for benefits?','opts'=>['Yes, all benefits registered','Some benefits registered','Not yet','Not sure what I qualify for']],
                ['q'=>'How long have you been in Canada?','opts'=>['Less than 30 days','1-6 months','6-12 months','More than 1 year']],
                ['q'=>'Have you filed a Canadian tax return?','opts'=>['Yes, filed this year','Not needed yet (too new)','Not sure if I need to','I have not filed but should']],
                ['q'=>'Do you have a Canadian driver license?','opts'=>['Yes, provincial license','In progress','Using foreign license exchange','Not driving in Canada']],
                ['q'=>'How comfortable are you with Canadian finances?','opts'=>['Very comfortable (TFSA, RRSP, etc.)','Learning the basics','Still confused by the system','Very uncertain — need guidance']],
            ],
            'results' => [
                ['min'=>0,'max'=>3,'level'=>'Beginner','emoji'=>'🌱','color'=>'#b71c1c','title'=>'Welcome to Canada!','desc'=>'You are just starting your Canadian journey. Download our free Newcomer Canada Checklist to know exactly what to do in your first weeks.','ctas'=>[['type'=>'pdf','id'=>'canada-checklist','text'=>'Download Canada Checklist'],['type'=>'pdf','id'=>'canada-30days','text'=>'Download First 30 Days Guide']]],
                ['min'=>4,'max'=>7,'level'=>'Intermediate','emoji'=>'🚀','color'=>'#b71c1c','title'=>'Building Your Canadian Life!','desc'=>'Great progress! Now focus on credit building and maximizing government benefits available to newcomers.','ctas'=>[['type'=>'pdf','id'=>'canada-credit','text'=>'Credit Building PDF'],['type'=>'pdf','id'=>'canada-health','text'=>'Health Insurance Guide']]],
                ['min'=>8,'max'=>10,'level'=>'Advanced','emoji'=>'⭐','color'=>'#2e7d32','title'=>'Well Established in Canada!','desc'=>'You are thriving in Canada! Download our provincial health guide to optimize your coverage.','ctas'=>[['type'=>'pdf','id'=>'canada-health','text'=>'Provincial Health Guide'],['type'=>'pdf','id'=>'canada-credit','text'=>'Credit Building PDF']]],
            ],
        ],
        'ebook' => [
            'questions' => [
                ['q'=>'Do you have a US Social Security Number (SSN)?','opts'=>['Yes','No — applied but waiting','No — have not applied yet','I have an ITIN instead']],
                ['q'=>'Do you have a US bank account?','opts'=>['Yes — checking and savings','Yes — checking only','No bank account yet','I have an international account']],
                ['q'=>'Do you have a US credit card?','opts'=>['Yes — unsecured rewards card','Yes — secured credit card','No — never had one','My application was denied']],
            ],
            'results' => [
                ['min'=>0,'max'=>0,'level'=>'Starting From Zero','emoji'=>'🌱','color'=>'#e65100','score'=>'200-400','title'=>'Credit Readiness: Beginner','desc'=>'You are at the starting line — and that is perfectly fine! The ebook will give you the exact steps to go from zero to a solid credit score in 12 months.','ctas'=>[['type'=>'ebook','text'=>'Get Full Ebook — $19.99'],['type'=>'pdf','id'=>'ebook-sample','text'=>'Free Sample Chapter']]],
                ['min'=>1,'max'=>1,'level'=>'Building Foundation','emoji'=>'🚀','color'=>'#1565c0','score'=>'400-600','title'=>'Credit Readiness: Intermediate','desc'=>'You have the basics in place. With the right strategy from the ebook, you can jump to 680+ within 6 months.','ctas'=>[['type'=>'ebook','text'=>'Get Full Ebook — $19.99'],['type'=>'pdf','id'=>'ebook-roadmap','text'=>'Credit Score Roadmap']]],
                ['min'=>2,'max'=>3,'level'=>'Strong Foundation','emoji'=>'⭐','color'=>'#2e7d32','score'=>'600-750+','title'=>'Credit Readiness: Advanced','desc'=>'Excellent foundation! The ebook will show you how to optimize your strategy for 750+ credit score.','ctas'=>[['type'=>'ebook','text'=>'Get Full Ebook — $19.99'],['type'=>'pdf','id'=>'ebook-mistakes','text'=>'Credit Mistakes to Avoid']]],
            ],
        ],
    ];
    ?>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js" defer data-no-optimize="1"></script>
    <script data-no-optimize="1">
    (function(){
    'use strict';
    var MAG_PT = <?php echo json_encode($pt); ?>;
    var MAG_NONCE = <?php echo json_encode($nonce); ?>;
    var MAG_AJAX = <?php echo json_encode($ajax); ?>;
    var MAG_EBOOK = <?php echo json_encode($ebook_url); ?>;
    var MAG_PDFS = <?php echo json_encode($pdf_data); ?>;
    var MAG_QUIZZES = <?php echo json_encode($quiz_data); ?>;

// ===== QUIZ ENGINE =====
function magInitQuiz() {
  var qz = MAG_QUIZZES[MAG_PT];
  if (!qz) return;
  var el = document.getElementById('mag-quiz');
  if (!el) return;
  magQstate = {idx:0, ans:[], pt:MAG_PT, qz:qz};
  magRenderQ(el);
}

function magRenderQ(el) {
  var s = magQstate;
  if (!s.qz) return;
  var q = s.qz.questions[s.idx];
  var total = s.qz.questions.length;
  var pct = Math.round((s.idx / total) * 100);
  var html = '<div class="mag-quiz-progress"><div class="mag-quiz-bar" style="width:' + pct + '%;background:#3b82f6;height:6px;border-radius:3px;transition:width 0.3s"></div></div>';
  html += '<p style="color:#6b7280;margin:8px 0 4px;font-size:14px">Question ' + (s.idx+1) + ' of ' + total + '</p>';
  html += '<h4 style="font-size:18px;color:#1e3a5f;margin:0 0 16px">' + q.q + '</h4>';
  html += '<div style="display:flex;flex-direction:column;gap:10px">';
  q.opts.forEach(function(opt, i) {
    html += '<button style="padding:12px 16px;border:2px solid #e5e7eb;border-radius:8px;background:#fff;cursor:pointer;text-align:left;font-size:15px;transition:all 0.2s" onmouseover="this.style.borderColor=\'#3b82f6\'" onmouseout="this.style.borderColor=\'#e5e7eb\'" onclick="magAns(' + i + ')">' + opt + '</button>';
  });
  html += '</div>';
  el.innerHTML = html;
}

window.magAns = function(i) {
  var s = magQstate;
  s.ans.push(i);
  s.idx++;
  var el = document.getElementById('mag-quiz');
  if (!el) return;
  if (s.idx >= s.qz.questions.length) {
    magShowResult(el, s);
  } else {
    magRenderQ(el);
  }
};

function magShowResult(el, s) {
  var score = 0;
  s.qz.questions.forEach(function(q, i) {
    if (s.ans[i] === 0) score++;
  });
  var results = s.qz.results || [];
  var tier = results[results.length - 1] || {};
  for (var i = 0; i < results.length; i++) {
    if (score >= results[i].min && score <= results[i].max) { tier = results[i]; break; }
  }
  var color = tier.color || '#27ae60';
  var html = '<div style="text-align:center;padding:24px;border:3px solid ' + color + ';border-radius:12px;background:#fff">';
  html += '<div style="font-size:40px">' + (tier.emoji || '') + '</div>';
  html += '<div style="font-size:22px;font-weight:700;color:' + color + ';margin:8px 0">' + (tier.title || tier.level || '') + '</div>';
  html += '<p style="color:#374151;margin:12px 0">' + (tier.desc || '') + '</p>';
  (tier.ctas || []).forEach(function(cta) {
    if (cta.type === 'ebook' && MAG_EBOOK) {
      html += '<a href="' + MAG_EBOOK + '" target="_blank" rel="noopener" style="display:inline-block;margin:6px;padding:12px 24px;background:#f59e0b;color:#fff;border-radius:8px;text-decoration:none;font-weight:700">' + cta.text + '</a>';
    } else if (cta.type === 'pdf') {
      html += '<button onclick="magLead(&#39;' + cta.id + '&#39;)" style="margin:6px;padding:12px 24px;background:#3b82f6;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700;font-size:15px">' + cta.text + '</button>';
    }
  });
  html += '<br><button onclick="magInitQuiz()" style="margin-top:10px;padding:8px 16px;background:none;border:1px solid #6b7280;border-radius:6px;cursor:pointer;color:#6b7280;font-size:13px">Retake Quiz</button>';
  html += '</div>';
  el.innerHTML = html;
}

var magQstate = {idx:0, ans:[]};

// ===== CALCULATOR ENGINE =====
window.magCalc = function(key, btn) {
  var panel = document.getElementById('mag-cpanel');
  if (!panel) return;
  // Update active tab
  var tabsEl = document.getElementById('mag-ctabs');
  if (tabsEl) {
    tabsEl.querySelectorAll('button').forEach(function(t){ t.style.background='#f3f4f6'; t.style.color='#374151'; t.style.borderBottom='none'; });
    if (btn) { btn.style.background='#fff'; btn.style.color='#1e3a5f'; btn.style.borderBottom='3px solid #3b82f6'; }
  }
  magRenderCalc(key, panel);
};

function magRenderCalc(key, el) {
  var html = '';
  if (key === 'cs' || key === 'credit') html = calcCS();
  else if (key === 'lv' || key === 'living') html = calcLV();
  else if (key === 'sv' || key === 'savings') html = calcSV();
  else if (key === 'bd' || key === 'budget') html = calcBD();
  else if (key === 'gr' || key === 'growth') html = calcGR();
  else if (key === 'dt' || key === 'debt') html = calcDT();
  else if (key === 'ut' || key === 'util') html = calcUT();
  else html = calcCS();
  el.innerHTML = html;
}

function calcCS() {
  return '<div style="display:flex;flex-direction:column;gap:12px">' +
    '<label style="font-weight:600;color:#374151">Current Credit Score (300-850)</label>' +
    '<input type="number" id="cc-score" min="300" max="850" value="620" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">On-time Payment Rate (%)</label>' +
    '<input type="number" id="cc-pay" min="0" max="100" value="80" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Credit Utilization (%)</label>' +
    '<input type="number" id="cc-util" min="0" max="100" value="50" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Number of Open Accounts</label>' +
    '<input type="number" id="cc-acct" min="0" max="20" value="2" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<button onclick="calcCS_run()" style="padding:12px;background:#1e3a5f;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:15px;font-weight:600">Calculate Improvement</button>' +
    '<div id="cc-result" style="margin-top:8px"></div>' +
    '</div>';
}
window.calcCS_run = function() {
  var score = parseInt(document.getElementById('cc-score').value) || 620;
  var pay = parseInt(document.getElementById('cc-pay').value) || 80;
  var util = parseInt(document.getElementById('cc-util').value) || 50;
  var acct = parseInt(document.getElementById('cc-acct').value) || 2;
  var boost = 0;
  if (pay >= 100) boost += 60; else if (pay >= 95) boost += 40; else if (pay >= 90) boost += 20; else if (pay >= 80) boost += 10;
  if (util <= 10) boost += 50; else if (util <= 20) boost += 35; else if (util <= 30) boost += 20; else if (util <= 50) boost += 5; else boost -= 20;
  if (acct >= 5) boost += 20; else if (acct >= 3) boost += 10; else if (acct >= 2) boost += 5;
  var projected = Math.min(850, score + boost);
  var el = document.getElementById('cc-result');
  if (el) el.innerHTML = '<div style="padding:16px;background:#f0f9ff;border-radius:8px;border-left:4px solid #3b82f6"><strong>Current Score:</strong> ' + score + '<br><strong>Projected Score:</strong> <span style="color:#27ae60;font-size:18px;font-weight:700">' + projected + '</span><br><strong>Potential Gain:</strong> +' + (projected - score) + ' points<br><em style="color:#6b7280">With consistent payments and lower utilization over 6-12 months</em></div>';
};

function calcLV() {
  return '<div style="display:flex;flex-direction:column;gap:12px">' +
    '<label style="font-weight:600;color:#374151">Monthly Rent ($)</label>' +
    '<input type="number" id="lv-rent" value="1500" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Groceries ($)</label>' +
    '<input type="number" id="lv-food" value="400" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Transport ($)</label>' +
    '<input type="number" id="lv-trans" value="200" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Utilities ($)</label>' +
    '<input type="number" id="lv-util" value="150" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Other Monthly Expenses ($)</label>' +
    '<input type="number" id="lv-other" value="300" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<button onclick="calcLV_run()" style="padding:12px;background:#1e3a5f;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:15px;font-weight:600">Calculate Cost of Living</button>' +
    '<div id="lv-result" style="margin-top:8px"></div>' +
    '</div>';
}
window.calcLV_run = function() {
  var rent = parseFloat(document.getElementById('lv-rent').value) || 0;
  var food = parseFloat(document.getElementById('lv-food').value) || 0;
  var trans = parseFloat(document.getElementById('lv-trans').value) || 0;
  var util = parseFloat(document.getElementById('lv-util').value) || 0;
  var other = parseFloat(document.getElementById('lv-other').value) || 0;
  var monthly = rent + food + trans + util + other;
  var el = document.getElementById('lv-result');
  if (el) el.innerHTML = '<div style="padding:16px;background:#f0f9ff;border-radius:8px;border-left:4px solid #3b82f6"><strong>Monthly Cost of Living:</strong> <span style="color:#1e3a5f;font-size:18px;font-weight:700">$' + monthly.toFixed(2) + '</span><br><strong>Annual Cost of Living:</strong> $' + (monthly*12).toFixed(2) + '<br><em style="color:#6b7280">Recommended 3-month emergency fund: $' + (monthly * 3).toFixed(2) + '</em></div>';
};

function calcSV() {
  return '<div style="display:flex;flex-direction:column;gap:12px">' +
    '<label style="font-weight:600;color:#374151">Savings Goal ($)</label>' +
    '<input type="number" id="sv-goal" value="5000" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Income ($)</label>' +
    '<input type="number" id="sv-income" value="3000" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Expenses ($)</label>' +
    '<input type="number" id="sv-exp" value="2000" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<button onclick="calcSV_run()" style="padding:12px;background:#1e3a5f;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:15px;font-weight:600">Calculate Time to Goal</button>' +
    '<div id="sv-result" style="margin-top:8px"></div>' +
    '</div>';
}
window.calcSV_run = function() {
  var goal = parseFloat(document.getElementById('sv-goal').value) || 5000;
  var income = parseFloat(document.getElementById('sv-income').value) || 3000;
  var exp = parseFloat(document.getElementById('sv-exp').value) || 2000;
  var save = income - exp;
  var el = document.getElementById('sv-result');
  if (save <= 0) { if (el) el.innerHTML = '<div style="padding:12px;background:#fef2f2;border-radius:8px;color:#dc2626"><strong>Warning:</strong> Expenses exceed income. Reduce expenses to save.</div>'; return; }
  var months = Math.ceil(goal / save);
  if (el) el.innerHTML = '<div style="padding:16px;background:#f0f9ff;border-radius:8px;border-left:4px solid #3b82f6"><strong>Monthly Savings:</strong> $' + save.toFixed(2) + '<br><strong>Time to reach goal:</strong> <span style="color:#27ae60;font-weight:700">' + months + ' months</span><br><em style="color:#6b7280">Savings Rate: ' + Math.round((save/income)*100) + '% of income</em></div>';
};

function calcBD() {
  return '<div style="display:flex;flex-direction:column;gap:12px">' +
    '<label style="font-weight:600;color:#374151">Monthly Rent (CAD $)</label>' +
    '<input type="number" id="bd-rent" value="1800" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Food (CAD $)</label>' +
    '<input type="number" id="bd-food" value="500" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Transport (CAD $)</label>' +
    '<input type="number" id="bd-trans" value="150" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Utilities (CAD $)</label>' +
    '<input type="number" id="bd-util" value="120" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Other Expenses (CAD $)</label>' +
    '<input type="number" id="bd-other" value="350" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<button onclick="calcBD_run()" style="padding:12px;background:#1e3a5f;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:15px;font-weight:600">Calculate Budget</button>' +
    '<div id="bd-result" style="margin-top:8px"></div>' +
    '</div>';
}
window.calcBD_run = function() {
  var r = parseFloat(document.getElementById('bd-rent').value)||0, f=parseFloat(document.getElementById('bd-food').value)||0, t=parseFloat(document.getElementById('bd-trans').value)||0, u=parseFloat(document.getElementById('bd-util').value)||0, o=parseFloat(document.getElementById('bd-other').value)||0;
  var m = r+f+t+u+o;
  var el = document.getElementById('bd-result');
  if (el) el.innerHTML = '<div style="padding:16px;background:#f0f9ff;border-radius:8px;border-left:4px solid #3b82f6"><strong>Monthly Budget (CAD):</strong> <span style="color:#1e3a5f;font-size:18px;font-weight:700">$' + m.toFixed(2) + '</span><br><strong>Annual Budget:</strong> $' + (m*12).toFixed(2) + '<br><em style="color:#6b7280">Emergency fund (3 months): $' + (m*3).toFixed(2) + '</em></div>';
};

function calcGR() {
  return '<div style="display:flex;flex-direction:column;gap:12px">' +
    '<label style="font-weight:600;color:#374151">Monthly Income (CAD $)</label>' +
    '<input type="number" id="gr-income" value="3500" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Expenses (CAD $)</label>' +
    '<input type="number" id="gr-exp" value="2500" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Savings Goal (CAD $)</label>' +
    '<input type="number" id="gr-goal" value="10000" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<button onclick="calcGR_run()" style="padding:12px;background:#1e3a5f;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:15px;font-weight:600">Calculate Savings Plan</button>' +
    '<div id="gr-result" style="margin-top:8px"></div>' +
    '</div>';
}
window.calcGR_run = function() {
  var i = parseFloat(document.getElementById('gr-income').value)||3500, e=parseFloat(document.getElementById('gr-exp').value)||2500, g=parseFloat(document.getElementById('gr-goal').value)||10000;
  var s = i - e;
  var el = document.getElementById('gr-result');
  if (s <= 0) { if (el) el.innerHTML = '<div style="padding:12px;background:#fef2f2;border-radius:8px;color:#dc2626"><strong>Warning:</strong> Expenses exceed income.</div>'; return; }
  var months = Math.ceil(g/s);
  if (el) el.innerHTML = '<div style="padding:16px;background:#f0f9ff;border-radius:8px;border-left:4px solid #3b82f6"><strong>Monthly Savings (CAD):</strong> $' + s.toFixed(2) + '<br><strong>Time to reach goal:</strong> <span style="color:#27ae60;font-weight:700">' + months + ' months</span><br><em style="color:#6b7280">Savings Rate: ' + Math.round((s/i)*100) + '% of income</em></div>';
};

function calcDT() {
  return '<div style="display:flex;flex-direction:column;gap:12px">' +
    '<label style="font-weight:600;color:#374151">Total Debt Amount ($)</label>' +
    '<input type="number" id="dt-debt" value="5000" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Monthly Payment ($)</label>' +
    '<input type="number" id="dt-pay" value="200" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Annual Interest Rate (%)</label>' +
    '<input type="number" id="dt-rate" value="20" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<button onclick="calcDT_run()" style="padding:12px;background:#1e3a5f;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:15px;font-weight:600">Calculate Payoff</button>' +
    '<div id="dt-result" style="margin-top:8px"></div>' +
    '</div>';
}
window.calcDT_run = function() {
  var debt = parseFloat(document.getElementById('dt-debt').value)||5000, payment=parseFloat(document.getElementById('dt-pay').value)||200;
  var rate = (parseFloat(document.getElementById('dt-rate').value)||20)/100/12;
  var el = document.getElementById('dt-result');
  if (payment <= debt*rate) { if (el) el.innerHTML = '<div style="padding:12px;background:#fef2f2;border-radius:8px;color:#dc2626"><strong>Warning:</strong> Payment too low. Increase monthly payment.</div>'; return; }
  var months = Math.ceil(Math.log(payment/(payment-debt*rate))/Math.log(1+rate));
  var total = payment*months;
  if (el) el.innerHTML = '<div style="padding:16px;background:#f0f9ff;border-radius:8px;border-left:4px solid #3b82f6"><strong>Payoff Time:</strong> <span style="color:#27ae60;font-weight:700">' + months + ' months</span><br><strong>Total Paid:</strong> $' + total.toFixed(2) + '<br><strong>Total Interest:</strong> $' + (total-debt).toFixed(2) + '</div>';
};

function calcUT() {
  return '<div style="display:flex;flex-direction:column;gap:12px">' +
    '<label style="font-weight:600;color:#374151">Total Credit Card Balance ($)</label>' +
    '<input type="number" id="ut-balance" value="2000" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<label style="font-weight:600;color:#374151">Total Credit Limit ($)</label>' +
    '<input type="number" id="ut-limit" value="5000" style="padding:10px;border:1px solid #d1d5db;border-radius:8px;font-size:16px">' +
    '<button onclick="calcUT_run()" style="padding:12px;background:#1e3a5f;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:15px;font-weight:600">Check Utilization</button>' +
    '<div id="ut-result" style="margin-top:8px"></div>' +
    '</div>';
}
window.calcUT_run = function() {
  var bal = parseFloat(document.getElementById('ut-balance').value)||2000, lim=parseFloat(document.getElementById('ut-limit').value)||5000;
  var util = (bal/lim*100).toFixed(1);
  var status, color;
  if (util <= 10) { status='Excellent'; color='#27ae60'; } else if (util <= 30) { status='Good'; color='#2ecc71'; } else if (util <= 50) { status='Fair'; color='#f39c12'; } else { status='High - Pay Down Debt'; color='#e74c3c'; }
  var el = document.getElementById('ut-result');
  if (el) el.innerHTML = '<div style="padding:16px;background:#f0f9ff;border-radius:8px;border-left:4px solid #3b82f6"><strong>Utilization:</strong> <span style="color:' + color + ';font-size:18px;font-weight:700">' + util + '% - ' + status + '</span><br><strong>Target (10%):</strong> Pay down to $' + (lim*0.10).toFixed(2) + '</div>';
};

// ===== LEAD CAPTURE =====
var magCurrentPDF = null;

window.magLead = function(pdfId) {
  magCurrentPDF = pdfId;
  var modal = document.getElementById('mag-overlay');
  if (!modal) return;
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  if (pdfId && MAG_PDFS && MAG_PDFS[pdfId]) {
    var titleEl = document.getElementById('mag-ttl');
    if (titleEl) titleEl.textContent = MAG_PDFS[pdfId].title;
  }
  var nmEl = document.getElementById('mag-nm');
  var formEl = document.getElementById('mag-form');
  var okEl = document.getElementById('mag-ok');
  if (formEl) formEl.style.display = 'block';
  if (okEl) okEl.style.display = 'none';
  if (nmEl) { nmEl.value = ''; nmEl.focus(); }
  var emEl = document.getElementById('mag-em');
  if (emEl) emEl.value = '';
};

window.magClose = function() {
  var modal = document.getElementById('mag-overlay');
  if (modal) modal.style.display = 'none';
  document.body.style.overflow = '';
  magCurrentPDF = null;
};

document.addEventListener('click', function(e) {
  if (e.target && e.target.id === 'mag-overlay') magClose();
});
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') magClose();
});

window.magSubmit = function() {
  var nmEl = document.getElementById('mag-nm');
  var emEl = document.getElementById('mag-em');
  var nm = (nmEl ? nmEl.value : '').trim();
  var em = (emEl ? emEl.value : '').trim();
  var errEl = document.getElementById('mag-err');
  if (!nm) { if (errEl) errEl.textContent = 'Please enter your first name.'; return; }
  if (!em || !/^[^@]+@[^@]+\.[^@]+$/.test(em)) { if (errEl) errEl.textContent = 'Please enter a valid email address.'; return; }
  if (errEl) errEl.textContent = '';
  var sbtn = document.getElementById('mag-sbtn');
  if (sbtn) { sbtn.disabled = true; sbtn.textContent = 'Sending...'; }
  var fd = new FormData();
  fd.append('action', 'mag_cv3_lead');
  fd.append('nonce', MAG_NONCE || '');
  fd.append('name', nm);
  fd.append('email', em);
  fd.append('page_type', MAG_PT || '');
  fd.append('pdf_id', magCurrentPDF || '');
  fetch(MAG_AJAX || '/wp-admin/admin-ajax.php', {method:'POST', body:fd})
    .catch(function(){})
    .finally(function() {
      magShowOK(nm);
      if (magCurrentPDF) magGenPDF(magCurrentPDF, nm);
    });
};

function magShowOK(nm) {
  var formEl = document.getElementById('mag-form');
  var okEl = document.getElementById('mag-ok');
  if (formEl) formEl.style.display = 'none';
  if (okEl) {
    okEl.style.display = 'block';
    okEl.innerHTML = '<div style="text-align:center;padding:16px"><div style="font-size:48px">&#x2705;</div><h3 style="color:#27ae60;margin:12px 0 8px">Thank you, ' + nm + '!</h3><p>Your download is starting now.</p><button onclick="magClose()" style="margin-top:12px;padding:10px 20px;background:#1e3a5f;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600">Close</button></div>';
  }
  document.body.style.overflow = '';
}

// ===== PDF GENERATOR (jsPDF) =====
function magGenPDF(pdfId, nm) {
  if (!MAG_PDFS || !MAG_PDFS[pdfId]) return;
  var data = MAG_PDFS[pdfId];
  function doGen(jsPDF) {
    var doc = new jsPDF({orientation:'p', unit:'mm', format:'a4'});
    var W = 210, mg = 18, y = 0, lh = 7;
    // Header
    doc.setFillColor(26, 35, 126);
    doc.rect(0, 0, W, 42, 'F');
    doc.setTextColor(255,255,255);
    doc.setFontSize(9);
    doc.text('MoneyAbroadGuide.com', mg, 10);
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    var titleLines = doc.splitTextToSize(data.title, W - mg*2);
    doc.text(titleLines, mg, 24);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text('Prepared for: ' + nm, mg, 36);
    y = 54;
    doc.setTextColor(44,62,80);
    data.sections.forEach(function(sec) {
      if (y > 255) { doc.addPage(); y = 20; }
      doc.setFillColor(236, 240, 241);
      doc.rect(mg - 2, y - 5, W - mg*2 + 4, 9, 'F');
      doc.setFontSize(12);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(26,35,126);
      doc.text(sec.h || sec.heading || '', mg, y + 0.5);
      y += lh + 3;
      doc.setTextColor(44,62,80);
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      (sec.items || []).forEach(function(item) {
        if (y > 268) { doc.addPage(); y = 20; }
        var lines = doc.splitTextToSize('  * ' + item, W - mg*2 - 8);
        lines.forEach(function(line) { doc.text(line, mg+4, y); y += lh; });
      });
      y += 3;
    });
    var pc = doc.internal.getNumberOfPages();
    for (var p = 1; p <= pc; p++) {
      doc.setPage(p);
      doc.setFontSize(8);
      doc.setTextColor(127,140,141);
      doc.text('MoneyAbroadGuide.com  |  Page ' + p + ' of ' + pc, mg, 288);
    }
    var fn = (data.title||'guide').replace(/[^a-z0-9]/gi,'_').toLowerCase() + '.pdf';
    doc.save(fn);
  }
  if (window.jspdf && window.jspdf.jsPDF) {
    doGen(window.jspdf.jsPDF);
  } else {
    var s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
    s.onload = function() { if (window.jspdf && window.jspdf.jsPDF) doGen(window.jspdf.jsPDF); };
    document.head.appendChild(s);
  }
}

// ===== INIT =====
function magInit() {
  // Fix submit button - intercept form submission
  var sbtn = document.getElementById('mag-sbtn');
  if (sbtn) {
    sbtn.type = 'button';
    sbtn.onclick = function(e) { e.preventDefault(); magSubmit(); return false; };
  }
  var magForm = document.getElementById('mag-form');
  if (magForm) {
    magForm.onsubmit = function(e) { e.preventDefault(); magSubmit(); return false; };
  }
  // Init quiz - render first question immediately
  if (MAG_QUIZZES && MAG_QUIZZES[MAG_PT]) {
    var quizEl = document.getElementById('mag-quiz');
    if (quizEl) {
      magQstate = {idx:0, ans:[], pt:MAG_PT, qz:MAG_QUIZZES[MAG_PT]};
      magRenderQ(quizEl);
    }
  }
  // Init first calculator
  var cpanel = document.getElementById('mag-cpanel');
  if (cpanel) {
    var ctabs = document.getElementById('mag-ctabs');
    if (ctabs) {
      var firstTab = ctabs.querySelector('button');
      if (firstTab) {
        firstTab.style.background = '#fff';
        firstTab.style.color = '#1e3a5f';
        firstTab.style.borderBottom = '3px solid #3b82f6';
        var tabId = firstTab.id || '';
        var key = tabId.replace('mct-', '');
        magRenderCalc(key, cpanel);
      }
    }
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', magInit);
} else {
  magInit();
}

})();
</script>
<?php
}

