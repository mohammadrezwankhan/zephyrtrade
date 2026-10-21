const test = require('node:test');
const assert = require('node:assert/strict');
const E = require('../../src/zephyrtrade/web/engine.js');
const base = {capacity:30,da:400,up:600,down:200,hours:1,scenarios:[2,8,20],probabilities:[.2,.5,.3]};
const close = (a,b) => assert.ok(Math.abs(a-b)<1e-7,`${a} != ${b}`);

test('surplus, shortfall and interval settlement are explicit',()=>{
 close(E.revenue(8,2,400,600,200),-400);
 close(E.revenue(8,20,400,600,200,.5),2800);
});
test('weighted quantile agrees with every piecewise breakpoint',()=>{
 const r=E.optimize(base);close(r.offer,8);r.curve.forEach(p=>assert.ok(p.revenue<=r.expected+1e-7));
 close(r.expected,.2*(-400)+.5*3200+.3*5600);
});
test('duration scales objective, not offer',()=>{
 const a=E.optimize(base),b=E.optimize({...base,hours:.25});close(a.offer,b.offer);close(a.expected*.25,b.expected);
});
test('quantile endpoints and floating-point rows do not wrap',()=>{
 close(E.optimize({...base,da:600,probabilities:[.2,.3,.49999999]}).offer,20);
 // At the lower price boundary every offer below the first supported scenario ties.
 close(E.optimize({...base,da:200}).offer,0);
});
test('zero weights do not change the objective and exact ties choose the lowest breakpoint',()=>{
 const r=E.optimize({...base,da:200,probabilities:[0,1,0]});
 close(r.offer,0);close(r.expected,E.revenue(8,8,200,600,200));
});
test('negative prices are supported under ordered assumptions',()=>{
 const r=E.optimize({...base,da:-100,up:0,down:-200});r.curve.forEach(p=>assert.ok(p.revenue<=r.expected+1e-7));
});
test('invalid prices, capacities and probabilities are rejected',()=>{
 for(const patch of [{capacity:NaN},{hours:0},{up:10},{scenarios:[-1]},{scenarios:[31]},
 {probabilities:[1.2,-.5,.3]},{probabilities:[0,0,0]},{scenarios:[]},{probabilities:[1]},
 {scenarios:Array(101).fill(1)}])assert.throws(()=>E.optimize({...base,...patch}));
});
test('zero-oracle capture and one-observation R2 are undefined',()=>{
 const r=E.statistics([0],[0],[400],[600],[200]);assert.equal(r.capture,null);assert.equal(r.r2,null);close(r.total,0);
});
test('revenue statistics respect units and mean absolute error',()=>{
 const r=E.statistics([2,8],[3,6],[400,400],[600,600],[200,200],.5);
 close(r.mae,1.5);close(r.imbalance,1.5);close(r.rmse,Math.sqrt(2.5));close(r.oracle,2000);
});
test('CSV quotes and formula-neutralises text, not negative numbers',()=>{
 assert.equal(E.csvCell('=SUM(A1)'),"'=SUM(A1)");assert.equal(E.csvCell(-20),'-20');
 assert.equal(E.csvCell('a,"b"'),'"a,""b"""');
});
test('scenario parser accepts documented separators and rejects bad input',()=>{
 assert.deepEqual(E.parseNumbers('1, 2;3\n4'),[1,2,3,4]);assert.deepEqual(E.parseNumbers(''),[]);
 assert.throws(()=>E.parseNumbers('1,NaN'));assert.throws(()=>E.parseNumbers('1,word'));
});

test('empty comma and semicolon fields are rejected instead of becoming zero or equal weights',()=>{
 for(const text of [',2,5','2,5,',';2;5','2;5;','2,,5','2;;5','2, ;5',',0.2,0.8'])
  assert.throws(()=>E.parseNumbers(text),/empty values/);
 assert.deepEqual(E.parseNumbers(' \t\n '),[]);
 assert.deepEqual(E.parseNumbers('0.2 0.8'),[.2,.8]);
});

test('near a CDF boundary the actual best objective wins',()=>{
 const input={capacity:10000,hours:24,da:45000.000000055,up:100000,down:-10000,scenarios:[0,10000],probabilities:[.5,.5]};
 const r=E.optimize(input);
 assert.equal(r.offer,10000);
 assert.ok(r.expected > r.curve.find(p=>p.offer===0).revenue);
});
test('statistics reject mismatched and nonfinite inputs',()=>{
 assert.throws(()=>E.statistics([],[],[],[],[]));assert.throws(()=>E.statistics([1],[NaN],[1],[2],[0]));
});

test('malformed or mismatched Python results cannot produce a passed cross-check',()=>{
 for(const bad of [null,{}, {offer_mw:8}, {offer_mw:NaN,expected_revenue_dkk:3200},
  {offer_mw:31,expected_revenue_dkk:3200}, {offer_mw:8,expected_revenue_dkk:0}])
  assert.throws(()=>E.verifyLPResult(bad,3200,30));
 assert.equal(E.verifyLPResult({offer_mw:8,expected_revenue_dkk:3200},3200,30),true);
});
