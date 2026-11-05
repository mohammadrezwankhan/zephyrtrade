/* ZephyrTrade numerical browser engine. Pure functions; no network or DOM. */
/**
 * @typedef {{capacity:number, da:number, up:number, down:number, hours?:number,
 *   scenarios:number[], probabilities?:number[]|null}} OfferingInput
 * @typedef {{offer:number, revenue:number}} CurvePoint
 * @typedef {{offer:number, quantile:number, expected:number, probabilities:number[],
 *   mean:number, meanOfferRevenue:number, curve:CurvePoint[], scenarioRevenues:number[]}} OfferingResult
 * @typedef {{rows:number, total:number, oracle:number, capture:number|null, regret:number,
 *   rmse:number, mae:number, r2:number|null, imbalance:number, meanOffer:number,
 *   meanActual:number, signed:number, values:number[]}} Statistics
 * @typedef {{finite:(value:unknown,name:string)=>number,
 *   priceOrder:(da:number,up:number,down:number)=>void,
 *   revenue:(offer:number,actual:number,da:number,up:number,down:number,hours?:number)=>number,
 *   statistics:(actual:number[],offers:number[],da:number[],up:number[],down:number[],hours?:number)=>Statistics,
 *   optimize:(input:OfferingInput)=>OfferingResult,
 *   verifyLPResult:(result:unknown,expected:number,capacity:number)=>boolean,
 *   parseNumbers:(text:unknown)=>number[], csvCell:(value:unknown)=>string}} BrowserEngine
 */
(function (/** @type {typeof globalThis & {ZephyrEngine?:BrowserEngine}} */ root) {
  'use strict';
  /** @param {unknown} x @param {string} name */
  const finite = (x, name) => {
    if (typeof x !== 'number' || !Number.isFinite(x)) throw new Error(`${name} must be finite.`);
    return x;
  };
  /** @param {number} da @param {number} up @param {number} down */
  function priceOrder(da, up, down) {
    [da, up, down].forEach(x => finite(x, 'Price'));
    if (!(down <= da && da <= up && down < up))
      throw new Error('Use down-regulation ≤ day-ahead ≤ up-regulation, with a positive spread.');
  }
  /**
   * @param {number} offer @param {number} actual @param {number} da
   * @param {number} up @param {number} down @param {number} [hours]
   */
  function revenue(offer, actual, da, up, down, hours = 1) {
    [offer, actual, da, up, down, hours].forEach(x => finite(x, 'Value'));
    if (hours <= 0 || offer < 0 || actual < 0) throw new Error('Use nonnegative MW and a positive duration.');
    return hours * (da * offer + down * Math.max(actual - offer, 0) - up * Math.max(offer - actual, 0));
  }
  /**
   * @param {number[]} actual @param {number[]} offers @param {number[]} da
   * @param {number[]} up @param {number[]} down @param {number} [hours]
   */
  function statistics(actual, offers, da, up, down, hours = 1) {
    if (!actual.length || ![offers, da, up, down].every(a => a.length === actual.length))
      throw new Error('Statistics require nonempty aligned vectors.');
    const n = actual.length, mean = actual.reduce((a,b) => a+b,0) / n;
    let total = 0, oracle = 0, sq = 0, absolute = 0, variance = 0, offerSum = 0, signed = 0;
    const values = actual.map((a, i) => {
      const offer = finite(offers[i], 'Value'), dayAhead = finite(da[i], 'Value');
      const upPrice = finite(up[i], 'Value'), downPrice = finite(down[i], 'Value');
      const r = revenue(offer, a, dayAhead, upPrice, downPrice, hours);
      total += r; oracle += hours * a * dayAhead; sq += (a - offer) ** 2;
      absolute += Math.abs(a - offer); signed += a - offer;
      variance += (a - mean) ** 2; offerSum += offer; return r;
    });
    return {rows:n, total, oracle, capture: oracle > 0 ? total / oracle * 100 : null,
      regret:oracle-total, rmse:Math.sqrt(sq/n), mae:absolute/n,
      r2:n < 2 ? null : variance === 0 ? (sq === 0 ? 1 : 0) : 1-sq/variance,
      imbalance:absolute*hours, meanOffer:offerSum/n, meanActual:mean, signed:signed/n, values};
  }
  /** @param {OfferingInput} input */
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
    const probabilities = probs.map(p => p/sum);
    const quantile = (da-down)/(up-down);
    /** @param {number} q */
    const expected = q => scenarios.reduce((s,x,i) => s+finite(probabilities[i], 'Probability')*revenue(q,x,da,up,down,hours),0);
    const candidates = [...new Set([0, capacity, ...scenarios])].sort((a,b)=>a-b);
    const curve = candidates.map(x=>({offer:x, revenue:expected(x)}));
    // Compare every piecewise-linear breakpoint; do not move a CDF boundary by a fixed epsilon.
    const first = curve[0];
    if (!first) throw new Error('Optimization requires at least one candidate.');
    const optimum = curve.reduce((best, point) => point.revenue > best.revenue ? point : best, first);
    const offer = optimum.offer;
    return {offer, quantile, expected:optimum.revenue, probabilities,
      mean:scenarios.reduce((s,x,i)=>s+x*finite(probabilities[i], 'Probability'),0),
      meanOfferRevenue:expected(scenarios.reduce((s,x,i)=>s+x*finite(probabilities[i], 'Probability'),0)), curve,
      scenarioRevenues:scenarios.map(x=>revenue(offer,x,da,up,down,hours))};
  }
  /** @param {unknown} result @param {number} expected @param {number} capacity */
  function verifyLPResult(result, expected, capacity) {
    if (!result || typeof result !== 'object' || !('offer_mw' in result) || !('expected_revenue_dkk' in result)
        || typeof result.offer_mw !== 'number' || typeof result.expected_revenue_dkk !== 'number'
        || !Number.isFinite(result.offer_mw) || !Number.isFinite(result.expected_revenue_dkk))
      throw new Error('The local solver returned an invalid result. Your inputs are retained.');
    finite(expected, 'Expected objective'); finite(capacity, 'Capacity');
    if (result.offer_mw < -1e-8 || result.offer_mw > capacity + 1e-8 || Math.abs(result.expected_revenue_dkk - expected) > 1e-6)
      throw new Error('The Python and browser objectives disagree. Do not rely on this result.');
    return true;
  }
  /** @param {unknown} text */
  function parseNumbers(text) {
    const raw = String(text).trim();
    if (!raw) return [];
    const fields = raw.split(/[;,]/);
    if (fields.some(field => !field.trim()))
      throw new Error('Remove empty values before, between, or after commas and semicolons.');
    return fields.flatMap(field => field.trim().split(/\s+/)).map(token => {
      const value = Number(token); finite(value, 'Entry'); return value;
    });
  }
  /** @param {unknown} value */
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
