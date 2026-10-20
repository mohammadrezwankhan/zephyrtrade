#!/usr/bin/env node
'use strict';
// Offline executable regression: only the captured pure engine is evaluated.
// Usage: node tests/numerical-regression.cjs snapshot/run.html [result.json]
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const file = process.argv[2];
if (!file) throw new Error('Pass the HTML snapshot to test.');
const html = fs.readFileSync(file, 'utf8');
const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)].filter(x => !/\bsrc\s*=/.test(x[1]));
const engine = scripts.find(x => x[2].includes('ZephyrTrade numerical browser engine'))[2];
const context = vm.createContext({ module: { exports: {} } });
vm.runInContext(engine, context, { timeout: 1000 });
const E = context.module.exports;
const checks = [];
function check(name, ok, details = {}) { checks.push({ name, status: ok ? 'pass' : 'fail', ...details }); }
const badLists = [',2,5', '2,5,', ';2;5', '2;5;', '2,,5', '2;;5', '2, ;5', ',0.2,0.8'];
for (const text of badLists) {
  let rejected = false, parsed;
  try { parsed = [...E.parseNumbers(text)]; } catch (_) { rejected = true; }
  check('reject_empty_field:' + JSON.stringify(text), rejected, { issue: 'ISS-001', parsed });
}
for (const [text, expected] of [['', []], [' \n\t', []], ['2, 5; 9\n13', [2,5,9,13]], [' 2 5\t9 ', [2,5,9]], ['0.2,0.8', [0.2,0.8]]]) {
  let parsed, error;
  try { parsed = [...E.parseNumbers(text)]; } catch (e) { error = e.message; }
  check('preserve_valid_list:' + JSON.stringify(text), JSON.stringify(parsed) === JSON.stringify(expected), { parsed, error });
}
function compensated(values) {
  let sum = 0, correction = 0;
  for (const value of values) { const adjusted = value - correction, next = sum + adjusted; correction = (next - sum) - adjusted; sum = next; }
  return sum;
}
// Independent opportunity-cost formula, evaluated at all piecewise-linear
// breakpoints and capacity bounds; it never calls the implementation's revenue.
function oracle(input) {
  const weights = input.probabilities.length ? input.probabilities : input.scenarios.map(() => 1 / input.scenarios.length);
  const total = compensated(weights);
  const expected = offer => compensated(input.scenarios.map((actual, i) => {
    const penalty = offer > actual ? (input.up - input.da) * (offer - actual) : (input.da - input.down) * (actual - offer);
    return weights[i] / total * input.hours * (input.da * actual - penalty);
  }));
  const points = [...new Set([0, input.capacity, ...input.scenarios])].map(offer => ({ offer, expected: expected(offer) }));
  return { expected, maximum: Math.max(...points.map(x => x.expected)), points };
}
const extreme = { capacity:10000, hours:24, da:45000.000000055, up:100000, down:-10000, scenarios:[0,10000], probabilities:[0.5,0.5] };
const result = E.optimize(extreme), reference = oracle(extreme);
const deficit = reference.maximum - reference.expected(result.offer);
check('CDF_boundary_selects_best_objective', deficit <= 1e-6 && result.offer === 10000, { issue:'ISS-005', offer:result.offer, deficitDkk:deficit, independentMaximumDkk:reference.maximum, expectedDkk:result.expected });
const base = { capacity:30, hours:1, da:420, up:610, down:310, scenarios:[2,5,9,13,18,24,28], probabilities:[] };
const named = [base, {...base,da:310}, {...base,da:610}, {...base,scenarios:[0,30],probabilities:[0,1]}, {...base,scenarios:[17]}, {...base,scenarios:[0]}, {...base,scenarios:[30]}, {...base,scenarios:[1,10,1,30],probabilities:[.1,.4,.2,.3]}, {...base,down:-1000,da:-500,up:-100}, {...base,capacity:.1,scenarios:[0,.01,.1],hours:.25}, {...base,scenarios:Array.from({length:100},(_,i)=>30*i/99)}];
let seed=0x28c9e3b7;
const random=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return (seed>>>0)/4294967296;};
const generated=[];
for(let i=0;i<1000;i++){
  const count=1+Math.floor(random()*100),capacity=.1+random()*9999.9;
  const down=-10000+random()*50000,up=down+.01+random()*(100000-down-.01),q=i%13===0?0:i%13===1?1:random();
  const scenarios=Array.from({length:count},()=>capacity*random()),weights=scenarios.map(()=>random()>.2?random():0);
  if(!compensated(weights))weights[0]=1;
  generated.push({capacity,down,up,da:q===0?down:q===1?up:down+q*(up-down),hours:.25+random()*23.75,scenarios,probabilities:weights.map(x=>x/compensated(weights))});
}
let maximumDeficit=0, maximumAgreementError=0, bad=0;
for(const input of [...named,...generated]){
  const got=E.optimize(input),ref=oracle(input),loss=ref.maximum-ref.expected(got.offer),agreement=Math.abs(got.expected-ref.expected(got.offer));
  maximumDeficit=Math.max(maximumDeficit,loss);maximumAgreementError=Math.max(maximumAgreementError,agreement);
  if(!Number.isFinite(got.expected)||got.offer<0||got.offer>input.capacity||loss>1e-5||agreement>1e-6+1e-12*Math.abs(ref.expected(got.offer)))bad++;
}
check('independent_breakpoint_oracle',bad===0,{ cases:named.length+generated.length, failures:bad, maximumDeficitDkk:maximumDeficit, maximumAgreementErrorDkk:maximumAgreementError, deficitToleranceDkk:1e-5, agreementAbsoluteToleranceDkk:1e-6, agreementRelativeTolerance:1e-12 });
const datasetContext=vm.createContext({window:{}});
vm.runInContext(scripts.find(x=>x[2].includes('window.ZEPHYR_DATA'))[2],datasetContext,{timeout:1000});
const D=datasetContext.window.ZEPHYR_DATA;
let datasetFailures=0,maxRowError=0;
for(const model of D.models)for(let i=0;i<D.actual.length;i++){
  const actual=D.actual[i],offer=model.offers[i],penalty=offer>actual?(D.up[i]-D.day_ahead[i])*(offer-actual):(D.day_ahead[i]-D.down[i])*(actual-offer);
  const ref=D.interval_hours*(D.day_ahead[i]*actual-penalty),got=E.revenue(offer,actual,D.day_ahead[i],D.up[i],D.down[i],D.interval_hours),error=Math.abs(ref-got);
  maxRowError=Math.max(maxRowError,error);if(error>1e-8)datasetFailures++;
}
check('all_saved_model_row_revenues',datasetFailures===0,{ rows:D.actual.length*D.models.length, failures:datasetFailures, maximumErrorDkk:maxRowError, toleranceDkk:1e-8 });
const report={ file, sha256:crypto.createHash('sha256').update(html).digest('hex'), method:'Offline Node VM: pure numerical engine and bundled dataset only; no UI, browser, network or analytics execution.', checks, passed:checks.filter(x=>x.status==='pass').length, failed:checks.filter(x=>x.status==='fail').length };
if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
process.exitCode=report.failed?1:0;
