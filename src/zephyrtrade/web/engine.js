/* ZephyrTrade numerical browser engine. Pure functions; no network or DOM. */
(function (root) {
  'use strict';
  const finite = (x, name) => {
    if (typeof x !== 'number' || !Number.isFinite(x)) throw new Error(`${name} must be finite.`);
    return x;
  };
  function priceOrder(da, up, down) {
    [da, up, down].forEach(x => finite(x, 'Price'));
    if (!(down <= da && da <= up && down < up))
      throw new Error('Use down-regulation ≤ day-ahead ≤ up-regulation, with a positive spread.');
  }
  function revenue(offer, actual, da, up, down, hours = 1) {
    [offer, actual, da, up, down, hours].forEach(x => finite(x, 'Value'));
    if (hours <= 0 || offer < 0 || actual < 0) throw new Error('Use nonnegative MW and a positive duration.');
    return hours * (da * offer + down * Math.max(actual - offer, 0) - up * Math.max(offer - actual, 0));
  }
  function statistics(actual, offers, da, up, down, hours = 1) {
    if (!actual.length || ![offers, da, up, down].every(a => a.length === actual.length))
      throw new Error('Statistics require nonempty aligned vectors.');
    const n = actual.length, mean = actual.reduce((a,b) => a+b,0) / n;
    let total = 0, oracle = 0, sq = 0, absolute = 0, variance = 0, offerSum = 0, signed = 0;
    const values = actual.map((a, i) => {
      const r = revenue(offers[i], a, da[i], up[i], down[i], hours);
      total += r; oracle += hours * a * da[i]; sq += (a - offers[i]) ** 2;
      absolute += Math.abs(a - offers[i]); signed += a - offers[i];
      variance += (a - mean) ** 2; offerSum += offers[i]; return r;
    });
    return {rows:n, total, oracle, capture: oracle > 0 ? total / oracle * 100 : null,
      regret:oracle-total, rmse:Math.sqrt(sq/n), mae:absolute/n,
      r2:n < 2 ? null : variance === 0 ? (sq === 0 ? 1 : 0) : 1-sq/variance,
      imbalance:absolute*hours, meanOffer:offerSum/n, meanActual:mean, signed:signed/n, values};
  }
  function optimize(input) {
    const {capacity, da, up, down, hours = 1} = input;
    finite(capacity,'Capacity'); finite(hours,'Duration'); priceOrder(da, up, down);
    if (capacity <= 0 || hours <= 0) throw new Error('Capacity and duration must be positive.');
    const scenarios = input.scenarios;
    if (!Array.isArray(scenarios) || !scenarios.length || scenarios.length > 100)
      throw new Error('Enter between 1 and 100 production scenarios.');
    let probs = input.probabilities;
    if (probs == null || probs.length === 0) probs = scenarios.map(() => 1/scenarios.length);
    if (!Array.isArray(probs) || probs.length !== scenarios.length) throw new Error('Probabilities must align with the scenarios.');
    scenarios.forEach(x => { finite(x,'Scenario'); if (x < 0 || x > capacity) throw new Error('Every scenario must be between zero and capacity.'); });
    probs.forEach(x => { finite(x,'Probability'); if (x < 0) throw new Error('Probabilities must be nonnegative.'); });
    const sum = probs.reduce((a,b)=>a+b,0);
    if (Math.abs(sum-1)>1e-7) throw new Error('Scenario probabilities must sum to 1 (within 0.0000001).');
    probs = probs.map(p => p/sum);
    const pairs = scenarios.map((x,i) => [x,probs[i]]).filter(p => p[1]>0).sort((a,b) => a[0]-b[0]);
    const quantile = (da-down)/(up-down);
    let cumulative = 0, offer = pairs[pairs.length-1][0];
    for (const [x,p] of pairs) { cumulative += p; if (cumulative+1e-12 >= quantile) {offer=x; break;} }
    const expected = q => scenarios.reduce((s,x,i) => s+probs[i]*revenue(q,x,da,up,down,hours),0);
    const candidates = [...new Set([0, capacity, ...scenarios])].sort((a,b)=>a-b);
    const curve = candidates.map(x=>({offer:x, revenue:expected(x)}));
    return {offer, quantile, expected:expected(offer), probabilities:probs,
      mean:scenarios.reduce((s,x,i)=>s+x*probs[i],0),
      meanOfferRevenue:expected(scenarios.reduce((s,x,i)=>s+x*probs[i],0)), curve,
      scenarioRevenues:scenarios.map(x=>revenue(offer,x,da,up,down,hours))};
  }
  function verifyLPResult(result, expected, capacity) {
    if (!result || !Number.isFinite(result.offer_mw) || !Number.isFinite(result.expected_revenue_dkk))
      throw new Error('The local solver returned an invalid result. Your inputs are retained.');
    finite(expected, 'Expected objective'); finite(capacity, 'Capacity');
    if (result.offer_mw < -1e-8 || result.offer_mw > capacity + 1e-8 || Math.abs(result.expected_revenue_dkk - expected) > 1e-6)
      throw new Error('The Python and browser objectives disagree. Do not rely on this result.');
    return true;
  }
  function parseNumbers(text) {
    const parts = String(text).trim().split(/[\s,;]+/);
    if (!parts[0]) return [];
    return parts.map(x=>{const value=Number(x); finite(value,'Entry'); return value;});
  }
  function csvCell(value) {
    let s = value == null ? '' : String(value);
    // Formula neutralisation for user-provided text; numbers remain numerical.
    if (typeof value === 'string' && /^[=+\-@\t\r]/.test(s)) s = "'" + s;
    return /[",\n\r]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s;
  }
  const api = {finite,priceOrder,revenue,statistics,optimize,verifyLPResult,parseNumbers,csvCell};
  root.ZephyrEngine = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : window);
