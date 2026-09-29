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
 close(E.optimize({...base,da:200}).offer,2);
});
test('zero-probability scenarios are not quantile support',()=>{
 close(E.optimize({...base,da:200,probabilities:[0,1,0]}).offer,8);
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
test('statistics reject mismatched and nonfinite inputs',()=>{
 assert.throws(()=>E.statistics([],[],[],[],[]));assert.throws(()=>E.statistics([1],[NaN],[1],[2],[0]));
});

test('malformed or mismatched Python results cannot produce a passed cross-check',()=>{
 for(const bad of [null,{}, {offer_mw:8}, {offer_mw:NaN,expected_revenue_dkk:3200},
  {offer_mw:31,expected_revenue_dkk:3200}, {offer_mw:8,expected_revenue_dkk:0}])
  assert.throws(()=>E.verifyLPResult(bad,3200,30));
 assert.equal(E.verifyLPResult({offer_mw:8,expected_revenue_dkk:3200},3200,30),true);
});
