
add_action('wp_enqueue_scripts', function () {
    $mag_budget_calc_page_ids = array(1624);
    if (!in_array(get_queried_object_id(), $mag_budget_calc_page_ids, true)) {
        return;
    }
    wp_register_style('mag-budget-calc', false);
    wp_enqueue_style('mag-budget-calc');
    wp_add_inline_style('mag-budget-calc', <<<'MAG_CALC_CSS'
/* ez-TOC is injected as a direct child of .simulator-header, overlapping it,
   illegible white-on-white. Scoped to the direct-child position (not a bare
   class) and to the version-independent #ez-toc-container id -- NOT the
   version-suffixed class (confirmed different between pages: 49285 renders
   ez-toc-v2_0_86, live post 1641 renders ez-toc-v2_0_82_2 -- a bare
   version-class rule would silently stop matching, or later start matching
   1641's own real 56-link table of contents, on a plugin version bump).
   This only ever hides the instance ez-toc injects inside THIS specific
   header div; 1641's real TOC lives elsewhere in the article body, not
   inside .simulator-header, so it is untouched. */
.simulator-header > #ez-toc-container {
  display: none !important;
}

.mag-budget-calc, .mag-budget-calc * {
  box-sizing: border-box;
}
.mag-budget-calc {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 800px;
  width: 100%;
  margin: 24px auto;
  background: white;
  border-radius: 24px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15), 0 5px 15px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  position: relative;
  z-index: 1; /* keeps this widget above a floating/sticky Table of Contents box */
}
.mag-budget-calc .restore-banner {
  background: #fee2e2;
  color: #991b1b;
  text-align: center;
  padding: 8px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.mag-budget-calc .simulator-header {
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important; /* guard against a theme/global rule resetting the background */
  color: white;
  padding: 30px 30px 25px;
  position: relative;
  z-index: 2;
}
.mag-budget-calc .simulator-header h1 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
  color: #ffffff !important; /* fix: theme's own h1 selector was overriding the inherited color from the parent */
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.45);
}
.mag-budget-calc .simulator-header h1 span {
  font-weight: 400;
  font-size: 16px;
  background: rgba(255, 255, 255, 0.2);
  padding: 3px 10px;
  border-radius: 20px;
  margin-left: 12px;
  vertical-align: middle;
}
/* ez-TOC also auto-wraps heading text in anchor spans (ez-toc-section /
   ez-toc-section-end) inside every heading on the page, including this h1 --
   the badge rule above was blindly styling those too, showing as grey pills. */
.mag-budget-calc .simulator-header h1 span.ez-toc-section,
.mag-budget-calc .simulator-header h1 span.ez-toc-section-end {
  background: none !important;
  padding: 0 !important;
}
.mag-budget-calc .simulator-header p {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.92) !important; /* same override risk as h1 */
  opacity: 0.9;
  line-height: 1.5;
}
.mag-budget-calc .simulator-body {
  padding: 30px;
  background: #ffffff;
}
.mag-budget-calc .section {
  margin-bottom: 28px;
  border-bottom: 1px solid #eef2f6;
  padding-bottom: 20px;
}
.mag-budget-calc .section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.mag-budget-calc .section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}
.mag-budget-calc .section-title h2 {
  font-size: 18px;
  font-weight: 600;
  color: #1e3c72;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.mag-budget-calc .section-title .emoji {
  font-size: 22px;
}
.mag-budget-calc .grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
@media (max-width: 600px) {
  .mag-budget-calc .grid-2 {
    grid-template-columns: 1fr;
    gap: 15px;
  }
}
.mag-budget-calc .input-group {
  margin-bottom: 18px;
}
.mag-budget-calc .input-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 6px;
}
.mag-budget-calc .input-group input,
.mag-budget-calc .input-group select {
  width: 100%;
  padding: 12px 15px;
  border: 1.5px solid #dde2e9;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.4; /* fix: default line-height was clipping descenders/emoji in options */
  min-height: 44px; /* fix: also gives these a real touch target on mobile */
  transition: all 0.2s;
  background: #fafbfc;
}
.mag-budget-calc .input-group input:focus,
.mag-budget-calc .input-group select:focus {
  outline: none;
  border-color: #2a5298;
  background: white;
  box-shadow: 0 0 0 3px rgba(42, 82, 152, 0.1);
}
.mag-budget-calc .input-group input[type="number"] {
  -moz-appearance: textfield;
}
.mag-budget-calc .input-group input[type="number"]::-webkit-outer-spin-button,
.mag-budget-calc .input-group input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.mag-budget-calc .city-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
  margin-bottom: 15px;
}
.mag-budget-calc .city-btn {
  background: #f0f4fa;
  border: 1px solid transparent;
  padding: 10px 18px;
  min-height: 44px; /* fix: was ~31px, below the 44px touch-target minimum */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 30px;
  font-size: 13px;
  font-weight: 500;
  color: #1e3c72;
  cursor: pointer;
  transition: all 0.2s;
}
.mag-budget-calc .city-btn:hover {
  background: #e1e8f2;
  transform: translateY(-1px);
}
.mag-budget-calc .city-btn.active {
  background: #1e3c72;
  color: white;
  border-color: #1e3c72;
}
.mag-budget-calc .reset-btn {
  background: #f0f4fa;
  border: 1.5px solid #dde2e9;
  padding: 10px 20px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 30px;
  font-size: 14px;
  font-weight: 500;
  color: #1e3c72;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 10px;
}
.mag-budget-calc .reset-btn:hover {
  background: #e1e8f2;
  transform: translateY(-1px);
}
.mag-budget-calc .results-panel {
  background: linear-gradient(135deg, #f8faff 0%, #f0f5ff 100%);
  border-radius: 20px;
  padding: 25px;
  margin-top: 20px;
  border: 1px solid #d0dfff;
}
.mag-budget-calc .results-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-bottom: 20px;
}
@media (max-width: 600px) {
  .mag-budget-calc .results-grid {
    grid-template-columns: 1fr;
  }
}
.mag-budget-calc .result-item {
  background: white;
  border-radius: 16px;
  padding: 18px 15px;
  text-align: center;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.03);
  border: 1px solid #e6edf8;
}
.mag-budget-calc .result-label {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #5e6f8d;
  margin-bottom: 8px;
}
.mag-budget-calc .result-value {
  font-size: 28px;
  font-weight: 700;
  color: #1e3c72;
  line-height: 1.2;
}
.mag-budget-calc .result-breakdown {
  background: white;
  border-radius: 16px;
  padding: 20px;
  border: 1px solid #e6edf8;
}
.mag-budget-calc .breakdown-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px dashed #e0e8f2;
}
.mag-budget-calc .breakdown-item:last-child {
  border-bottom: none;
}
.mag-budget-calc .breakdown-label {
  font-weight: 500;
  color: #405b7e;
}
.mag-budget-calc .breakdown-value {
  font-weight: 600;
  color: #1e3c72;
}
.mag-budget-calc .total-row {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 2px solid #1e3c72;
  font-weight: 700;
  font-size: 18px;
  display: flex;
  justify-content: space-between;
  color: #1e3c72;
}
.mag-budget-calc .advice-box {
  padding: 16px 20px;
  border-radius: 12px;
  margin: 20px 0 10px;
  font-size: 15px;
  line-height: 1.6;
}
.mag-budget-calc .advice-box.good {
  background: #eef7ff;
  border-left: 4px solid #2a5298;
  color: #1e3c72;
}
.mag-budget-calc .advice-box.good strong {
  color: #0b2542;
}
.mag-budget-calc .advice-box.over-budget {
  background: #fef2f2;
  border-left: 4px solid #dc2626;
  color: #7f1d1d;
}
.mag-budget-calc .advice-box.over-budget strong {
  color: #991b1b;
}
.mag-budget-calc .footer-note {
  text-align: center;
  margin-top: 20px;
  font-size: 12px;
  color: #8a9bb5;
}

MAG_CALC_CSS
    );
    wp_register_script('mag-budget-calc', false, array(), '1.3', true);
    wp_enqueue_script('mag-budget-calc');
    wp_add_inline_script('mag-budget-calc', <<<'MAG_CALC_JS'
(function () {
  // City cost data (monthly estimates in USD) — recovered verbatim from post 1624 revision 46062 / post 1641 current content
  var cityData = {
    nyc: { rent: 2800, food: 600, utilities: 200, transport: 130, phone: 100, health: 350, other: 350, name: "New York City" },
    sf: { rent: 3000, food: 650, utilities: 180, transport: 120, phone: 100, health: 350, other: 350, name: "San Francisco" },
    la: { rent: 2200, food: 550, utilities: 180, transport: 140, phone: 95, health: 320, other: 300, name: "Los Angeles" },
    boston: { rent: 2300, food: 550, utilities: 190, transport: 110, phone: 95, health: 320, other: 300, name: "Boston" },
    chicago: { rent: 1700, food: 500, utilities: 160, transport: 100, phone: 90, health: 300, other: 280, name: "Chicago" },
    dc: { rent: 2100, food: 550, utilities: 170, transport: 120, phone: 95, health: 320, other: 300, name: "Washington D.C." },
    seattle: { rent: 2100, food: 550, utilities: 170, transport: 120, phone: 95, health: 320, other: 300, name: "Seattle" },
    miami: { rent: 1800, food: 520, utilities: 180, transport: 130, phone: 90, health: 300, other: 280, name: "Miami" },
    denver: { rent: 1600, food: 480, utilities: 150, transport: 110, phone: 85, health: 280, other: 250, name: "Denver" },
    austin: { rent: 1500, food: 470, utilities: 160, transport: 110, phone: 85, health: 280, other: 250, name: "Austin" },
    phoenix: { rent: 1400, food: 450, utilities: 170, transport: 110, phone: 85, health: 270, other: 240, name: "Phoenix" },
    atlanta: { rent: 1400, food: 460, utilities: 160, transport: 120, phone: 85, health: 270, other: 240, name: "Atlanta" },
    dallas: { rent: 1300, food: 450, utilities: 160, transport: 120, phone: 85, health: 270, other: 240, name: "Dallas" },
    orlando: { rent: 1300, food: 450, utilities: 170, transport: 120, phone: 85, health: 270, other: 230, name: "Orlando" },
    detroit: { rent: 900, food: 400, utilities: 150, transport: 100, phone: 80, health: 250, other: 200, name: "Detroit" },
    cleveland: { rent: 850, food: 400, utilities: 150, transport: 100, phone: 80, health: 250, other: 200, name: "Cleveland" },
    custom: { rent: 1200, food: 450, utilities: 150, transport: 100, phone: 80, health: 250, other: 220, name: "Custom" }
  };

  var lifestyleMult = {
    frugal: { food: 0.8, other: 0.6 },
    moderate: { food: 1.0, other: 1.0 },
    comfortable: { food: 1.3, other: 1.5 }
  };

  var housingMult = { studio: 1.0, shared: 0.6, family: 1.4 };

  // NOTE: the recovered original source literally had housing: 'moderate' here,
  // which is not a valid #housingType option (studio/shared/family only) --
  // a pre-existing bug in the source, not introduced by this restoration.
  // Fixed to 'studio' (the field's own default option) per explicit instruction,
  // no more precise value was specified anywhere in the recovered content.
  var defaultValues = { city: 'nyc', housing: 'studio', lifestyle: 'moderate', income: 4000, car: 'no' };

  function init() {
    var root = document.querySelector('.mag-budget-calc');
    if (!root) return; // this page has no calculator widget -- nothing to do

    var citySelect = root.querySelector('#citySelect');
    var housingType = root.querySelector('#housingType');
    var lifestyle = root.querySelector('#lifestyle');
    var income = root.querySelector('#income');
    var carStatus = root.querySelector('#carStatus');

    var rentInput = root.querySelector('#rent');
    var foodInput = root.querySelector('#food');
    var utilitiesInput = root.querySelector('#utilities');
    var transportInput = root.querySelector('#transport');
    var phoneInput = root.querySelector('#phone');
    var healthInput = root.querySelector('#health');

    var resultIncome = root.querySelector('#resultIncome');
    var resultExpenses = root.querySelector('#resultExpenses');
    var resultRemaining = root.querySelector('#resultRemaining');

    var breakdownRent = root.querySelector('#breakdownRent');
    var breakdownFood = root.querySelector('#breakdownFood');
    var breakdownUtilities = root.querySelector('#breakdownUtilities');
    var breakdownTransport = root.querySelector('#breakdownTransport');
    var breakdownPhone = root.querySelector('#breakdownPhone');
    var breakdownHealth = root.querySelector('#breakdownHealth');
    var breakdownOther = root.querySelector('#breakdownOther');
    var totalExpenses = root.querySelector('#totalExpenses');
    var adviceBox = root.querySelector('#adviceBox');
    var resetBtn = root.querySelector('.reset-btn');

    function resetToDefaults() {
      citySelect.value = defaultValues.city;
      housingType.value = defaultValues.housing;
      lifestyle.value = defaultValues.lifestyle;
      income.value = defaultValues.income;
      carStatus.value = defaultValues.car;

      root.querySelectorAll('.city-btn').forEach(function (b) { b.classList.remove('active'); });
      var activeBtn = root.querySelector('.city-btn[data-city="' + defaultValues.city + '"]');
      if (activeBtn) activeBtn.classList.add('active');

      updateCalculator(false);
    }

    root.querySelectorAll('.city-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var city = this.getAttribute('data-city');
        citySelect.value = city;
        updateCalculator(false);
        root.querySelectorAll('.city-btn').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
      });
    });

    // City/Housing/Lifestyle/Car genuinely change the underlying cost structure --
    // changing them recomputes AND overwrites the Fine-Tune fields (manualMode=false).
    [citySelect, housingType, lifestyle, carStatus].forEach(function (el) {
      el.addEventListener('input', function () { updateCalculator(false); });
    });

    // Income does NOT affect any cost line -- it only affects Total/Remaining.
    // Must behave like the manual-fields group (manualMode=true: read whatever
    // is currently displayed, never overwrite Fine-Tune) or editing Income wipes
    // out manual Rent/Food/etc. edits. This was the bug: it was previously
    // grouped with city/housing/lifestyle/car above.
    income.addEventListener('input', function () { updateCalculator(true); });

    [rentInput, foodInput, utilitiesInput, transportInput, phoneInput, healthInput].forEach(function (el) {
      el.addEventListener('input', function () { updateCalculator(true); });
    });

    if (resetBtn) resetBtn.addEventListener('click', resetToDefaults);

    function updateCalculator(manualMode) {
      manualMode = manualMode || false;

      var city = cityData[citySelect.value] || cityData.nyc;

      var housingMultVal = housingMult[housingType.value] || 1.0;
      var lifestyleVal = lifestyleMult[lifestyle.value] || lifestyleMult.moderate;
      var hasCar = carStatus.value === 'yes';

      var baseRent = city.rent * housingMultVal;
      var baseFood = city.food * lifestyleVal.food;
      var baseUtilities = city.utilities;
      var baseTransport = hasCar ? city.transport * 1.8 : city.transport;
      var basePhone = city.phone;
      var baseHealth = city.health;
      var baseOther = city.other * lifestyleVal.other;

      if (manualMode) {
        baseRent = rentInput.value ? parseFloat(rentInput.value) : baseRent;
        baseFood = foodInput.value ? parseFloat(foodInput.value) : baseFood;
        baseUtilities = utilitiesInput.value ? parseFloat(utilitiesInput.value) : baseUtilities;
        baseTransport = transportInput.value ? parseFloat(transportInput.value) : baseTransport;
        basePhone = phoneInput.value ? parseFloat(phoneInput.value) : basePhone;
        baseHealth = healthInput.value ? parseFloat(healthInput.value) : baseHealth;
      } else {
        rentInput.value = Math.round(baseRent);
        foodInput.value = Math.round(baseFood);
        utilitiesInput.value = Math.round(baseUtilities);
        transportInput.value = Math.round(baseTransport);
        phoneInput.value = Math.round(basePhone);
        healthInput.value = Math.round(baseHealth);
      }

      // Entertainment/Other is intentionally NOT a manual field (matches the recovered
      // original design) -- it is always derived from city.other x lifestyle multiplier.
      var total = baseRent + baseFood + baseUtilities + baseTransport + basePhone + baseHealth + baseOther;
      var monthlyIncome = parseFloat(income.value) || 0;
      var remaining = monthlyIncome - total;

      resultIncome.textContent = '$' + monthlyIncome.toLocaleString();
      resultExpenses.textContent = '$' + Math.round(total).toLocaleString();
      resultRemaining.textContent = (remaining >= 0 ? '+' : '-') + '$' + Math.round(Math.abs(remaining)).toLocaleString();

      breakdownRent.textContent = '$' + Math.round(baseRent).toLocaleString();
      breakdownFood.textContent = '$' + Math.round(baseFood).toLocaleString();
      breakdownUtilities.textContent = '$' + Math.round(baseUtilities).toLocaleString();
      breakdownTransport.textContent = '$' + Math.round(baseTransport).toLocaleString();
      breakdownPhone.textContent = '$' + Math.round(basePhone).toLocaleString();
      breakdownHealth.textContent = '$' + Math.round(baseHealth).toLocaleString();
      breakdownOther.textContent = '$' + Math.round(baseOther).toLocaleString();
      totalExpenses.textContent = '$' + Math.round(total).toLocaleString();

      var advice = '';
      var isOverBudget = remaining < 0;
      if (remaining > 500) {
        advice = '<strong>✅ Excellent!</strong> You have <strong>$' + Math.round(remaining).toLocaleString() + '</strong> left each month. Consider investing in a Roth IRA or building an emergency fund.';
      } else if (remaining >= 0) {
        advice = '<strong>✅ Good job!</strong> Your estimated expenses are within your income. Consider putting the remaining <strong>$' + Math.round(remaining).toLocaleString() + '</strong> into a High-Yield Savings Account (HYSA) or Roth IRA.';
      } else {
        /* PROPOSED COPY -- not recovered from source, pending validation (no dollar figure invented, value is computed) */
        advice = '<strong>⚠️ Over budget.</strong> Your estimated expenses exceed your income by <strong>$' + Math.round(Math.abs(remaining)).toLocaleString() + '</strong>. Consider a lower-cost city, a shared apartment, or adjusting your lifestyle level.';
      }
      adviceBox.innerHTML = advice;
      adviceBox.classList.toggle('over-budget', isOverBudget);
      adviceBox.classList.toggle('good', !isOverBudget);
    }

    updateCalculator(false);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

MAG_CALC_JS
    );
});
add_filter('ez_toc_should_display', function ($display) {
    if (in_array(get_queried_object_id(), array(49285), true)) {
        return false;
    }
    return $display;
});
