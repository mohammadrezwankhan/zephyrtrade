/* ZephyrTrade Champion UI. All observations originate in the packaged snapshot. */
(function () {
  'use strict';
  const D = window.ZEPHYR_DATA, E = window.ZephyrEngine;
  const $ = id => document.getElementById(id);
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icons = {
    overview:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    lab:'<path d="M9 3h6M10 3v6l-6 10a1.3 1.3 0 0 0 1 2h14a1.3 1.3 0 0 0 1-2L14 9V3M7 15h10"/>',
    models:'<path d="M5 20V11M12 20V4M19 20V8M3 20h18"/>',
    data:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 4 16 4 16 0V5M4 12v7c0 4 16 4 16 0v-7"/>',
    method:'<path d="M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h6"/>',
    wind:'<path d="M3 8h11c5 0 5-6 1-6M3 12h16c4 0 4 6 0 6M3 16h8c4 0 4 5 0 5"/>',
    download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    help:'<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5M12 17h.01"/>',
    theme:'<path d="M20 14A8 8 0 0 1 10 4 8 8 0 1 0 20 14Z"/>',
    arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
    value:'<path d="M3 17 9 11l4 3 7-9M15 5h5v5"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 3"/>',
    check:'<path d="m5 12 4 4L19 6"/>',
  };
  const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.overview}</svg>`;
  const num = (x,d=1) => x == null || !Number.isFinite(x) ? '—' : x.toLocaleString('en-GB',{minimumFractionDigits:d,maximumFractionDigits:d});
  const compact = x => Math.abs(x)>=1e6 ? num(x/1e6,2)+'m' : Math.abs(x)>=1e3 ? num(x/1e3,1)+'k' : num(x,1);
  const dateLabel = s => new Date(s).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
  const shortDate = s => new Date(s).toLocaleDateString('en-GB',{day:'2-digit',month:'short',timeZone:'UTC'});
  let toastTimer, pythonAvailable = false, labVersion = 0, currentLab = null;
  let labDraft = null;
  let saved = [], dataPage = 0, dataSearch = '', chartMode = 'power';
  let labInput = {capacity:30,da:420,up:610,down:310,hours:1,scenarios:[2,5,9,13,18,24,28],probabilities:[]};
  const pageInfo = {
    overview:['Overview','WIND INTELLIGENCE / DK2','From wind to value.','Explore the forecast. Understand the offer. See the trade-off.'],
    lab:['Strategy lab','SCENARIOS / STOCHASTIC OFFERING','Test the trade-off.','Change your assumptions. Find the optimal offer. No real trades.'],
    models:['Model arena','BENCHMARK / NINE STRATEGIES','Let the evidence lead.','Compare realised value and offer error on the same retained hours.'],
    data:['Data explorer','OBSERVATIONS / HOURLY RECORDS','Every number, traceable.','Inspect the source observations behind the selected backtest.'],
    method:['Method & evidence','TRANSPARENCY / RESEARCH CONTRACT','Know what you are seeing.','The assumptions, provenance and limits behind every result.'],
  };
  const state = {page:'overview',model:'direct_regression',period:'all',from:'',to:''};
  function notify(message) { $('toast').textContent=message; $('toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').hidden=true,5500); }
  function renderIcons(root=document) { root.querySelectorAll('[data-icon]').forEach(el=>{el.innerHTML=icon(el.dataset.icon);}); }
  function persistView() { try { localStorage.setItem('zephyr-view-v1',JSON.stringify({model:state.model,period:state.period,from:state.from,to:state.to})); } catch (_) { /* Preferences are optional, unlike scenario saves. */ } }
  function indices() {
    let from=-Infinity,to=Infinity;
    if (state.period==='custom') { from=Date.parse(state.from+'T00:00:00Z');to=Date.parse(state.to+'T23:59:59Z'); }
    else if (state.period!=='all') {to=Date.parse(D.timestamps.at(-1));from=to-Number(state.period)*86400000+3600000;}
    return D.timestamps.flatMap((t,i)=>Date.parse(t)>=from&&Date.parse(t)<=to?[i]:[]);
  }
  const selectedModel = () => D.models.find(m=>m.id===state.model) || D.models[0];
  const subset = (arr,ids) => ids.map(i=>arr[i]);
  function metrics(model,ids) { return E.statistics(subset(D.actual,ids),subset(model.offers,ids),subset(D.day_ahead,ids),subset(D.up,ids),subset(D.down,ids)); }
  function rankings(ids) { return D.models.map(model=>({model,score:metrics(model,ids)})).sort((a,b)=>b.score.total-a.score.total); }
  function kpi(label,value,unit,sub,name='value',primary=false) {return `<article class="kpi${primary?' primary':''}"><div class="kpi-label">${label}<span data-icon="${name}"></span></div><div class="kpi-value">${value}${unit?`<small>${unit}</small>`:''}</div><div class="kpi-sub">${sub}</div></article>`;}
  function lineChart(lines,labels,{ylabel='',height=238,min=null,max=null,title='Chart',gaps=[]}={}) {
    const w=800,h=height,p={l:50,r:15,t:19,b:35},pw=w-p.l-p.r,ph=h-p.t-p.b;
    const flat=lines.flatMap(s=>s.values).filter(Number.isFinite);
    let lo=min ?? Math.min(0,...flat), hi=max ?? Math.max(...flat);
    if (!Number.isFinite(hi)||hi<=lo) hi=lo+1;
    const x=i=>p.l+(labels.length<2?pw/2:i/(labels.length-1)*pw), y=v=>p.t+ph-(v-lo)/(hi-lo)*ph;
    let svg=`<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>`;
    for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4,py=y(v);svg+=`<line class="grid-line" x1="${p.l}" x2="${w-p.r}" y1="${py}" y2="${py}"/><text x="${p.l-10}" y="${py+3}" text-anchor="end">${esc(Math.abs(v)>=1000?compact(v):num(v,Number.isInteger(hi)?0:1))}</text>`;}
    const ticks = [...new Set([0,Math.floor((labels.length-1)/3),Math.floor((labels.length-1)*2/3),labels.length-1])];
    ticks.forEach(i=>{if(i>=0)svg+=`<text x="${x(i)}" y="${h-10}" text-anchor="${i===0?'start':i===labels.length-1?'end':'middle'}">${esc(labels[i])}</text>`;});
    svg+=`<text x="${p.l}" y="10">${esc(ylabel)}</text>`;
    const classes=['line-a','line-b','line-c'];
    lines.forEach((s,j)=>{let path='',last=false;s.values.forEach((v,i)=>{if(!Number.isFinite(v)){last=false;return;}path+=(last&&!gaps[i]?'L':'M')+x(i).toFixed(2)+','+y(v).toFixed(2)+' ';last=true;});svg+=`<path class="${classes[j%3]}" d="${path}"/>`;if(s.values.length===1)svg+=`<circle cx="${x(0)}" cy="${y(s.values[0])}" r="3" fill="var(--accent)"/>`;});
    return svg+'</svg>';
  }
  function groupTime(ids,arrays,cumulative=false) {
    const daily=ids.length>180;
    const groups=[];let lastKey='';
    ids.forEach((id,i)=>{const key=daily?D.timestamps[id].slice(0,10):D.timestamps[id];if(key!==lastKey){groups.push({key,ids:[],points:arrays.map(()=>[])});lastKey=key;}const g=groups.at(-1);g.ids.push(id);arrays.forEach((a,j)=>g.points[j].push(a[i]));});
    return {daily,labels:groups.map(g=>daily?shortDate(g.key):D.timestamps[g.ids[0]].slice(5,16).replace('T',' ')),
      values:arrays.map((_,j)=>groups.map(g=>cumulative?g.points[j].at(-1):g.points[j].reduce((a,b)=>a+b,0)/g.points[j].length)),
      gaps:groups.map((g,i)=>i>0 && Date.parse(g.key)-Date.parse(groups[i-1].key)>(daily?86400000:3600000))};
  }
  function powerPlot(model,ids) {
    const actual=subset(D.actual,ids),offers=subset(model.offers,ids);
    let series, labels, opts, note;
    if(chartMode==='revenue') {
      let running=0,oracle=0;
      const values=ids.map(i=>running+=E.revenue(model.offers[i],D.actual[i],D.day_ahead[i],D.up[i],D.down[i]));
      const ideal=ids.map(i=>oracle+=D.actual[i]*D.day_ahead[i]);
      const g=groupTime(ids,[ideal,values],true);series=[{values:g.values[0]},{values:g.values[1]}];labels=g.labels;
      opts={ylabel:'DKK · cumulative',title:'Cumulative synthetic revenue, selected offer and perfect-foresight benchmark',gaps:g.gaps};
      note=g.daily?'End-of-day cumulative values; only retained hourly records contribute.':'Cumulative value of retained hourly records; gaps are not zero-filled.';
    } else if(chartMode==='prices') {
      const g=groupTime(ids,[subset(D.day_ahead,ids),subset(D.down,ids),subset(D.up,ids)]);series=g.values.map(values=>({values}));labels=g.labels;
      opts={ylabel:'DKK / MWh',title:'Synthetic day-ahead and balancing settlement prices',gaps:g.gaps};note=g.daily?'Daily means of retained prices. Excluded hours are not zero-filled.':'Hourly prices. Excluded hours are left as gaps.';
    } else {
      const g=groupTime(ids,[actual,offers]);series=g.values.map(values=>({values}));labels=g.labels;
      opts={ylabel:'MW',max:D.capacity_mw,title:'Actual synthetic wind output and selected strategy offer',gaps:g.gaps};note=g.daily?'Daily means of retained hours. Metrics use every hourly record.':'Hourly output and offers. Excluded hours are left as gaps.';
    }
    const legend=chartMode==='revenue'?'<span><i class="actual"></i>Perfect foresight</span><span><i class="offer"></i>Selected strategy</span>':chartMode==='prices'?'<span><i class="actual"></i>Day-ahead</span><span><i class="offer"></i>Down-regulation</span><span><i class="gold"></i>Up-regulation</span>':'<span><i class="actual"></i>Actual output</span><span><i class="offer"></i>Selected offer</span>';
    return `<div class="legend">${legend}</div>${lineChart(series,labels,opts)}<div class="chart-note"><span>${note}</span><span>UTC · ${num(ids.length,0)} records</span></div>`;
  }
  function turbineGlyph() {return `<svg class="wind-glyph" viewBox="0 0 240 105" role="img" aria-label="Wind turbine diagram"><defs><linearGradient id="tg" x2="0" y2="1"><stop stop-color="currentColor" stop-opacity=".2"/><stop offset="1" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs><path d="M7 94H235M20 98h195" stroke="currentColor" stroke-opacity=".2"/><g fill="none" stroke="currentColor" stroke-width="1.2"><path d="M107 38 103 92h11l-4-54M174 47l-3 45h7l-3-45M57 58l-2 34h5l-2-34"/><path d="M109 38 105 3c8 3 9 17 4 35ZM109 38l31 16c-1 6-22-2-31-16ZM109 38 87 62c-6-3 7-20 22-24Z"/><circle cx="109" cy="38" r="3"/><path d="m174 47 0-25c5 2 5 15 0 25ZM174 47l22 13c-2 4-16-2-22-13ZM174 47l-16 18c-5-4 7-16 16-18Z"/><circle cx="174" cy="47" r="2"/><path d="M57 58V39c4 1 4 12 0 19Zm0 0 17 10c-2 3-12-1-17-10Zm0 0L45 72c-4-3 5-12 12-14Z"/><circle cx="57" cy="58" r="1.5"/></g><path d="M30 20h36M15 30h53M186 10h36M198 19h25" stroke="currentColor" stroke-opacity=".25" stroke-linecap="round"/></svg>`;}
  function overview(ids) {
    const model=selectedModel(),s=metrics(model,ids),ranked=rankings(ids);
    const baseline=ranked.find(x=>x.model.id==='persistence_24h').score;
    const delta=s.total-baseline.total;
    const gapHours=Math.round((Date.parse(D.timestamps[ids.at(-1)])-Date.parse(D.timestamps[ids[0]]))/3600000)+1-ids.length;
    return `<div class="kpi-grid">${kpi('Realised revenue',compact(s.total),'DKK',`<span class="accent">${delta>=0?'+':''}${compact(delta)}</span> vs persistence`,'value',true)}${kpi('Perfect-foresight capture',num(s.capture,2),'%', 'Revenue ÷ benchmark revenue','target')}${kpi('Absolute imbalance',compact(s.imbalance),'MWh',num(s.mae,2)+' MW mean absolute offer error','wind')}${kpi('Retained test intervals',num(ids.length,0),'hours',num(gapHours,0)+' excluded hours between endpoints','clock')}</div>
    <div class="dashboard-grid"><section class="panel"><div class="panel-header"><div><h2>Production meets strategy</h2><p>${esc(model.name)} · held-out synthetic observations</p></div><div class="chart-toolbar" role="group" aria-label="Chart measure">${['power','revenue','prices'].map(x=>`<button data-chart="${x}" type="button" aria-pressed="${chartMode===x}">${{power:'Output',revenue:'Revenue',prices:'Prices'}[x]}</button>`).join('')}</div></div><div id="overview-plot">${powerPlot(model,ids)}</div><p class="chart-summary">${num(s.meanActual,2)} MW mean output · ${num(s.meanOffer,2)} MW mean offer · ${compact(s.regret)} DKK regret to perfect foresight</p></section>
    <aside class="panel insight-panel"><div class="eyebrow">EXPLORE THE DECISION</div><h2 class="insight-title">The best forecast<br>is not the whole story.</h2><p>A shortfall costs the up-regulation price. A surplus earns the down-regulation price. Explore how that changes your offer.</p>${turbineGlyph()}<button class="button secondary small" data-go="lab" type="button">Open strategy lab <span data-icon="arrow"></span></button></aside></div>
    <div class="split-grid"><section class="panel"><div class="panel-header"><div><h2>Leading strategies</h2><p>Ranked by revenue within the selected window</p></div><button class="text-link" data-go="models" type="button">Compare all <span data-icon="arrow"></span></button></div>${ranked.slice(0,3).map((x,i)=>`<div class="mini-row"><span class="rank">0${i+1}</span><div><strong>${esc(x.model.name)}</strong><small>${esc(x.model.family)}</small></div><div class="number">${compact(x.score.total)}<small>DKK · ${num(x.score.capture,2)}% capture</small></div></div>`).join('')}</section>
    <section class="panel"><div class="panel-header"><div><h2>The research context</h2><p>Keep the assumptions in view</p></div><span class="badge">OFFLINE</span></div><div class="context-row"><span>Evaluated farm</span><strong>Ronne Coastal Proxy</strong></div><div class="context-row"><span>Price regime</span><strong>Down ≤ day-ahead ≤ up</strong></div><div class="context-row"><span>Interval / settlement</span><strong>1 hour / DKK</strong></div><div class="context-note">Not a complete calendar backtest: negative-price hours were removed upstream. These results are not evidence of live profitability.</div></section></div>`;
  }
  function modelsPage(ids) {
    const rows=rankings(ids), max=Math.max(...rows.map(x=>x.score.total)), benchmark=rows[0].score.oracle;
    return `<div class="notice"><strong>Same hours. Different decisions.</strong> This table compares offer error, not forecast-only error. Rankings change with your date filter. Perfect foresight is shown as a non-deployable reference, not as a competing learned model.</div>
    <section class="panel"><div class="panel-header"><div><h2>Value leaderboard</h2><p>${num(ids.length,0)} retained hourly records · ${compact(benchmark)} DKK perfect-foresight reference</p></div><button class="button secondary small" id="export-models" type="button"><span data-icon="download"></span>Export comparison</button></div><div class="model-bars">${rows.map(x=>`<div class="model-bar-row"><span>${esc(x.model.name)}</span><div class="bar-track"><div class="bar-fill" style="--width:${Math.max(0,x.score.total/max*100)}%;background:var(--${x.model.family==='Direct learning'?'accent':x.model.family==='Baseline'?'gold':'cyan'})"></div></div><strong>${compact(x.score.total)} DKK</strong></div>`).join('')}</div><p class="readout-caption">Bars start at zero. Colours distinguish direct learning, forecast-then-optimise and persistence.</p><div class="table-wrap"><table><caption class="sr-only">Strategy performance in the selected time window</caption><thead><tr><th>Rank</th><th>Strategy</th><th class="number">Revenue (DKK)</th><th class="number">Capture (%)</th><th class="number">Regret (DKK)</th><th class="number">Offer RMSE (MW)</th><th class="number">Offer MAE (MW)</th><th>Explore</th></tr></thead><tbody>${rows.map((x,i)=>`<tr class="${state.model===x.model.id?'selected-row':''}"><td><span class="pill-number">${i+1}</span></td><td><strong>${esc(x.model.name)}</strong><small>${esc(x.model.family)}</small></td><td class="number">${num(x.score.total,0)}</td><td class="number">${num(x.score.capture,2)}</td><td class="number">${num(x.score.regret,0)}</td><td class="number">${num(x.score.rmse,3)}</td><td class="number">${num(x.score.mae,3)}</td><td><button class="text-link" data-select-model="${x.model.id}" type="button">Inspect <span data-icon="arrow"></span></button></td></tr>`).join('')}</tbody></table></div></section>
    <div class="split-grid section-space"><section class="panel prose"><h2>Forecast → optimise</h2><div class="flow"><div>Weather + lagged output</div><span>→</span><div>Power forecast</div><span>→</span><div>Residual scenarios</div><span>→</span><div>Optimal offer</div></div><p>The seven indirect strategies include the 24-hour persistence baseline. Saved offer vectors come from the supplied research run; changing the dashboard date window does not retrain them.</p></section><section class="panel prose"><h2>Direct learning</h2><div class="flow"><div>Same information set</div><span>→</span><div>Continuous / bracket learning</div><span>→</span><div>Offer</div></div><p>The two direct strategies learn offers from synthetic perfect-foresight targets. They are research outputs, not an independently validated production forecasting service.</p></section></div>`;
  }
  function dataPageHtml(ids) {
    const filtered=ids.filter(i=>!dataSearch||D.timestamps[i].toLowerCase().includes(dataSearch.toLowerCase()));
    const pageCount=Math.max(1,Math.ceil(filtered.length/25));dataPage=Math.min(dataPage,pageCount-1);
    const visible=filtered.slice(dataPage*25,dataPage*25+25),m=selectedModel();
    return `<div class="data-quality-grid">${kpi('Records in selected period',num(ids.length,0),'',dateLabel(D.timestamps[ids[0]])+' → '+dateLabel(D.timestamps[ids.at(-1)]),'data')}${kpi('Source rows checked',num(D.quality.revenue_values_checked,0),'', 'Saved revenue values reconciled with Python','check')}${kpi('Dataset coverage',num(D.quality.rows,0),'hours', 'One evaluated synthetic site · UTC','clock')}</div><section class="panel"><div class="panel-header"><div><h2>Hourly research ledger</h2><p>${esc(m.name)} · use the global filters to select a period</p></div><span class="badge good">SOURCE-BACKED</span></div><div class="table-controls"><label class="sr-only" for="data-search">Find a UTC date or hour</label><input id="data-search" type="search" placeholder="Find a UTC date or hour, e.g. 2024-12-15" value="${esc(dataSearch)}"><button class="button secondary small" id="export-filtered" type="button"><span data-icon="download"></span>Export ${num(filtered.length,0)} matching rows</button></div><div class="table-wrap"><table><caption class="sr-only">Hourly actual output, strategy offer, settlement prices and calculated revenue</caption><thead><tr><th>Time (UTC)</th><th class="number">Actual (MW)</th><th class="number">Offer (MW)</th><th class="number">Day-ahead<br>(DKK/MWh)</th><th class="number">Up price<br>(DKK/MWh)</th><th class="number">Down price<br>(DKK/MWh)</th><th class="number">Revenue (DKK)</th></tr></thead><tbody>${visible.length?visible.map(i=>`<tr><td class="mono">${D.timestamps[i].slice(0,16).replace('T',' ')}</td><td class="number">${num(D.actual[i],3)}</td><td class="number">${num(m.offers[i],3)}</td><td class="number">${num(D.day_ahead[i],2)}</td><td class="number">${num(D.up[i],2)}</td><td class="number">${num(D.down[i],2)}</td><td class="number">${num(E.revenue(m.offers[i],D.actual[i],D.day_ahead[i],D.up[i],D.down[i]),2)}</td></tr>`).join(''):'<tr><td colspan="7"><div class="empty"><strong>No matching records.</strong>Clear your date search or choose a different period. Missing hours are not fabricated.</div></td></tr>'}</tbody></table></div><div class="pagination"><span>${filtered.length?num(dataPage*25+1,0):0}–${num(Math.min((dataPage+1)*25,filtered.length),0)} of ${num(filtered.length,0)} rows · Page ${dataPage+1} / ${pageCount}</span><div><button class="button secondary small" data-paginate="-1" type="button" ${dataPage===0?'disabled':''}>Previous</button><button class="button secondary small" data-paginate="1" type="button" ${dataPage>=pageCount-1?'disabled':''}>Next</button></div></div></section><div class="notice section-space">CSV exports contain unrounded numerical values, the strategy ID and a synthetic-data label. The on-screen table rounds values for readability. ${D.quality.excluded_hours_between_endpoints} hours are absent between the full test-set endpoints; the original source removed ${D.quality.source_negative_price_rows_removed} negative-price hours across its complete generation period.</div>`;
  }
  function numericField(id,label,value,unit,min,max,step='1') {return `<div class="form-field"><label for="${id}">${label}</label><div class="input-unit"><input id="${id}" name="${id}" type="number" value="${value}" min="${min}" max="${max}" step="any" required><span>${unit}</span></div></div>`;}
  function labPage() {
    return `<div class="notice"><strong>Independent scenario sandbox.</strong> These are editable assumptions, not a forecast or live bid. The dashboard strategy and date filters do not affect this calculation. Negative prices are allowed here only when the required price ordering holds.</div><div class="lab-grid"><div><section class="panel"><div class="panel-header"><div><h2>Build your scenario</h2><p>Empirical production distribution + settlement prices</p></div><span class="badge blue">WHAT-IF</span></div><div class="preset-row" role="group" aria-label="Scenario presets"><button data-preset="balanced" type="button">Balanced spread</button><button data-preset="shortfall" type="button">Costly shortfall</button><button data-preset="surplus" type="button">Low surplus value</button></div><form id="lab-form" novalidate><div class="form-grid">${numericField('capacity','Physical capacity',labInput.capacity,'MW',.1,10000,.1)}${numericField('hours','Settlement interval',labInput.hours,'hours',.25,24,.25)}${numericField('da','Day-ahead price',labInput.da,'DKK/MWh',-10000,100000,.1)}${numericField('up','Up-regulation price',labInput.up,'DKK/MWh',-10000,100000,.1)}${numericField('down','Down-regulation price',labInput.down,'DKK/MWh',-10000,100000,.1)}<div class="form-field"><span>Decision rule</span><div class="formula">q = (DA − down)<br> / (up − down)</div></div><div class="form-field full"><label for="scenarios">Production scenarios (MW)</label><textarea id="scenarios" rows="3" aria-describedby="scenarios-hint" required>${labInput.scenarios.join(', ')}</textarea><small id="scenarios-hint">1–100 values, separated by commas. Every value must be within capacity.</small></div><div class="form-field full"><label for="probabilities">Probabilities (optional)</label><input id="probabilities" value="${labInput.probabilities.join(', ')}" placeholder="Leave blank for equal probabilities" aria-describedby="probabilities-hint"><small id="probabilities-hint">One nonnegative probability per scenario; sum must equal 1.</small></div></div><div id="lab-error" class="notice error" role="alert" hidden></div><button class="button wide" type="submit">Calculate optimal offer <span data-icon="arrow"></span></button></form></section><section class="panel section-space"><div class="panel-header"><div><h2>Saved scenarios</h2><p>Stored in this browser only</p></div><button class="text-link" id="import-scenario" type="button">Import JSON</button></div><input type="file" id="scenario-file" accept="application/json,.json" hidden><div id="saved-list">${savedHtml()}</div></section></div><div class="lab-results"><section class="panel" id="lab-output" aria-live="polite">${labOutput()}</section><section class="panel prose"><h2>Why this is the optimal offer</h2><p>For a given offer, a surplus earns the down-regulation price and a shortfall pays the up-regulation price. Under the stated ordering, expected revenue is concave and piecewise linear.</p><div class="formula">R(b, p) = Δt × [DA × b + down × max(p − b, 0)<br>                        − up × max(b − p, 0)]</div><p>The weighted empirical quantile at <strong>q = (DA − down) / (up − down)</strong> gives an optimum. Ties can produce more than one equally good offer. The line chart evaluates every scenario breakpoint and both capacity bounds.</p><button class="text-link" id="verify-python" type="button">${pythonAvailable?'Cross-check with Python / SciPy':'How to enable the Python cross-check'} <span data-icon="arrow"></span></button><div id="python-result" class="api-result" role="status" hidden></div></section></div></div>`;
  }
  function labOutput() {
    if(!currentLab) currentLab=E.optimize(labInput);
    const r=currentLab,n=labInput.scenarios.length, uplift=r.expected-r.meanOfferRevenue;
    const curve=r.curve;
    return `<div class="panel-header"><div><h2>Calculated offer</h2><p>Browser engine · weighted empirical quantile</p></div><span id="lab-result-state" class="badge good">CALCULATED LOCALLY</span></div><div id="lab-stale" class="notice" role="status" hidden>Inputs changed. The figures below are the last calculated result; recalculate before saving or exporting. Your draft is retained while navigating this workspace.</div><div class="result-hero"><div><div class="eyebrow">OPTIMAL DAY-AHEAD OFFER</div><div class="result-value" id="optimal-offer">${num(r.offer,2)} <small>MW</small></div></div><div class="result-side"><span>Expected scenario revenue</span><strong id="expected-revenue">${num(r.expected,2)} DKK</strong><span>per ${num(labInput.hours,2)}-hour interval</span></div></div><div class="metric-triple"><div><small>Decision quantile</small><strong>${num(r.quantile*100,1)}%</strong></div><div><small>Expected production</small><strong>${num(r.mean,2)} MW</strong></div><div><small>Value vs mean offer</small><strong>+${num(Math.max(0,uplift),2)} DKK</strong></div></div><div class="legend"><span><i class="offer"></i>Expected revenue by offer</span></div>${offerCurve(curve,r.offer)}<p class="chart-summary">${n} scenarios · ${num(labInput.capacity,1)} MW physical limit · prices in DKK/MWh. This is not a trade instruction.</p><div class="button-row"><button class="button secondary small" id="save-scenario" type="button">Save scenario</button><button class="button secondary small" id="export-scenario" type="button"><span data-icon="download"></span>Export JSON</button><button class="button secondary small" id="export-curve" type="button">Export curve CSV</button></div>`;
  }
  function offerCurve(curve,offer) {
    const w=720,h=210,p={l:62,r:18,t:15,b:38},xs=labInput.capacity;
    const ys=curve.map(p=>p.revenue),lo=Math.min(...ys,0),hi=Math.max(...ys,0)+1;
    const x=v=>p.l+v/xs*(w-p.l-p.r),y=v=>p.t+(hi-v)/(hi-lo)*(h-p.t-p.b);
    let svg=`<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Expected scenario revenue in DKK versus offer in MW; optimal offer ${num(offer,2)} MW"><title>Expected revenue versus offer; optimal offer ${num(offer,2)} MW</title>`;
    for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;svg+=`<line class="grid-line" x1="${p.l}" x2="${w-p.r}" y1="${y(v)}" y2="${y(v)}"/><text x="${p.l-8}" y="${y(v)+3}" text-anchor="end">${esc(compact(v))}</text><text x="${x(xs*i/4)}" y="${h-14}" text-anchor="middle">${num(xs*i/4,1)}</text>`;}
    const d=curve.map((p,i)=>(i?'L':'M')+x(p.offer).toFixed(2)+','+y(p.revenue).toFixed(2)).join(' ');
    svg+=`<path class="line-b" d="${d}"/><line x1="${x(offer)}" x2="${x(offer)}" y1="${p.t}" y2="${h-p.b}" stroke="var(--gold)" stroke-dasharray="4 5"/><text x="${p.l}" y="10">DKK</text><text x="${w-p.r}" y="${h-1}" text-anchor="end">Offer (MW)</text></svg>`;return svg;
  }
  function savedHtml() {return saved.length?saved.map((s,i)=>`<div class="saved-item"><div><strong>${esc(s.name)}</strong><small>${num(s.input.capacity,1)} MW capacity · ${s.input.scenarios.length} scenarios</small></div><div><button class="text-link" data-load-saved="${i}" type="button">Load</button> <button class="text-link" data-delete-saved="${i}" type="button" aria-label="Delete ${esc(s.name)}">×</button></div></div>`).join(''):'<div class="empty"><strong>Your experiments belong here.</strong>Calculate an offer, then save the assumptions for another comparison.</div>';}
  function methodPage() {
    return `<div class="notice"><strong>Research, not a live trading system.</strong> This release presents the supplied synthetic experiments and a local optimisation sandbox. It does not fetch current prices, retrain on filter changes, authenticate traders or submit orders. Public deployment and real-market validation remain outside the verified scope.</div><div class="method-grid"><section class="panel prose"><h2>What is connected to what?</h2><div class="flow"><div>Supplied CSV observations</div><span>→</span><div>Validated snapshot</div><span>→</span><div>Browser calculations</div></div><p>The dashboard contains ${num(D.quality.rows,0)} retained test observations for <strong>${esc(D.farm_name)}</strong>, covering ${dateLabel(D.timestamps[0])} to ${dateLabel(D.timestamps.at(-1))}. All values use UTC, one-hour intervals and DKK. Four farms exist in the synthetic source metadata; only one has evaluated model outputs in this workspace.</p><h3>Metric definitions</h3><p><strong>Realised revenue</strong> is day-ahead offer revenue plus surplus receipts minus shortfall costs. <strong>Capture</strong> divides realised revenue by the perfect-foresight benchmark. Capture is undefined when that denominator is not positive; it is never shown as an invented percentage.</p><div class="formula">Revenue = DA × offer + down × surplus − up × shortfall<br>Capture = 100 × Σ revenue / Σ (DA × actual output)<br>Offer MAE = mean(|actual output − offer|)<br>Imbalance MWh = Σ |actual output − offer| × interval hours</div><p><strong>Perfect foresight</strong> assumes actual output is known before offering. It is an analytical reference under the repository's price ordering, not a forecast achievable in operation. Offer RMSE is not the same quantity as wind-forecast RMSE.</p><h3>Temporal scope and exclusions</h3><p>The original pipeline removed ${D.quality.source_negative_price_rows_removed} negative-price hours from its full generated market table. ${D.quality.excluded_hours_between_endpoints} hours are absent between the first and last test observations. The UI does not fill those missing observations with zero. Daily charts use means of available hours; revenue charts use cumulative sums of included hourly values.</p><h3>Model and information limitations</h3><p>Models were trained in the supplied research run, with chronological train/validation/test separation. The weather fields are synthetic forecast-time proxies. Operational forecast issuance, gate-closure availability of lagged features, current market rules, transaction costs and live settlement data have not been independently validated here. No live profitability claim is warranted.</p><h3>Scenario lab</h3><p>The lab is independent of the saved backtest. Its production distribution and prices are your assumptions. The browser evaluates the weighted empirical quantile. When started through the optional Python launcher, a local SciPy linear program can cross-check the same objective. Local checks are not an external integration test.</p></section><div class="provenance-grid"><section class="panel"><div class="panel-header"><div><h2>Source provenance</h2><p>Artifacts from your uploaded repository</p></div><span class="badge good">TRACEABLE</span></div>${D.sources.map(s=>`<div class="context-row"><div><div class="source-path">${esc(s.path)}</div><small class="muted">SHA-256</small><div class="source-path">${s.sha256}</div></div></div>`).join('')}<p class="readout-caption">Source manifest says generated ${esc(D.source_generated_at)}. These are historical synthetic observations, not a current market feed.</p><button class="button secondary small" id="export-provenance" type="button">Export provenance JSON</button></section><section class="panel"><h2>Verified snapshot integrity</h2><div class="context-row"><span>Unique, ordered timestamps</span><strong>Validated</strong></div><div class="context-row"><span>Phase 2 / 3 row alignment</span><strong>Exact</strong></div><div class="context-row"><span>Revenue values recalculated</span><strong>${num(D.quality.revenue_values_checked,0)}</strong></div><div class="context-row"><span>Largest saved-value difference</span><strong>${D.quality.maximum_revenue_error_dkk.toExponential(2)} DKK</strong></div><div class="context-note">These are artifact checks, not a rerun of the original three-year model training. Test logs and limitations are included in <span class="mono">docs/champion/</span>.</div></section><section class="panel prose" id="python-setup"><h2>Run the Python cross-check</h2><p>The portable HTML runs without installation. For the optional local solver, extract the complete ZIP, install Python 3.11 or newer, then run:</p><div class="formula">python -m venv .venv-champion<br># Activate your environment, then:<br>python -m pip install -e .<br>python -m zephyrtrade.app</div><p>Windows users can run <strong>START_PYTHON_WINDOWS.bat</strong>. It creates a separate environment and installs the project. The service binds only to 127.0.0.1 and is intended for local research, not internet hosting.</p><h3>Privacy and persistence</h3><p>The offline app uses no remote fonts, analytics or CDNs. Saved scenario settings stay in this browser's local storage. Export JSON backups; clearing browser data removes local saves. No credentials or live customer data are required.</p></section></div></div>`;
  }
  function render() {
    const info=pageInfo[state.page];$('breadcrumb-title').textContent=info[0];$('page-eyebrow').textContent=info[1];$('page-title').textContent=info[2];$('page-subtitle').textContent=info[3];
    document.title=`${info[0]} · ZephyrTrade Champion`;
    document.querySelectorAll('nav a').forEach(a=>{if(a.dataset.page===state.page)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
    $('filterbar').hidden=['lab','method'].includes(state.page);$('heading-tag').hidden=state.page!=='overview';
    $('model-select').value=state.model;
    document.querySelectorAll('[data-period]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.period===state.period)));
    $('date-fields').hidden=state.period!=='custom';
    const ids=indices();
    $('period-label').textContent=ids.length?`${dateLabel(D.timestamps[ids[0]])} — ${dateLabel(D.timestamps[ids.at(-1)])} · UTC`:'No records in this period';
    if(!ids.length && !['lab','method'].includes(state.page)) $('page-content').innerHTML='<div class="empty"><strong>No records in this period.</strong>Choose All data or a date within the supplied test set.</div>';
    else $('page-content').innerHTML=state.page==='overview'?overview(ids):state.page==='models'?modelsPage(ids):state.page==='data'?dataPageHtml(ids):state.page==='lab'?labPage():methodPage();
    if(state.page==='lab'&&labDraft){for(const [key,value] of Object.entries(labDraft))$(key).value=value;markLabDirty();}
    renderIcons(); persistView();
  }
  function go(page,focus=true) {if(!pageInfo[page])page='overview';state.page=page;dataPage=0;render();if(focus){$('workspace').focus();window.scrollTo({top:0,behavior:'instant'});}}
  function download(name,content,type='text/plain;charset=utf-8') {
    const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);notify('Export prepared. Check your browser downloads.');
  }
  function csvDownload(name,header,rows){download(name,'\uFEFF'+[header,...rows].map(row=>row.map(E.csvCell).join(',')).join('\r\n'),'text/csv;charset=utf-8');}
  function exportData(filtered=false) {
    let ids=indices();if(filtered&&dataSearch)ids=ids.filter(i=>D.timestamps[i].includes(dataSearch));
    if(!ids.length){notify('No rows match this selection.');return;}
    const m=selectedModel();
    csvDownload(`ZephyrTrade-${m.id}-${D.timestamps[ids[0]].slice(0,10)}.csv`,['data_kind','strategy','farm_id','timestamp_utc','interval_hours','capacity_mw','actual_mw','offer_mw','day_ahead_dkk_mwh','up_dkk_mwh','down_dkk_mwh','revenue_dkk'],ids.map(i=>['synthetic_research',m.id,D.farm_id,D.timestamps[i],1,D.capacity_mw,D.actual[i],m.offers[i],D.day_ahead[i],D.up[i],D.down[i],E.revenue(m.offers[i],D.actual[i],D.day_ahead[i],D.up[i],D.down[i])]));
  }
  function exportModels(){const ids=indices();if(!ids.length){notify('No rows in this period.');return;}csvDownload('ZephyrTrade-model-comparison.csv',['data_kind','start_utc','end_utc','hours','strategy','revenue_dkk','capture_pct','regret_dkk','offer_rmse_mw','offer_mae_mw','absolute_imbalance_mwh'],rankings(ids).map(x=>['synthetic_research',D.timestamps[ids[0]],D.timestamps[ids.at(-1)],ids.length,x.model.id,x.score.total,x.score.capture,x.score.regret,x.score.rmse,x.score.mae,x.score.imbalance]));}
  function readLabForm() {
    const obj={};for(const key of ['capacity','da','up','down','hours']){const el=$(key);el.classList.remove('input-error');if(!el.checkValidity()){el.classList.add('input-error');el.focus();throw new Error(`Check ${el.previousElementSibling?.textContent||key}: enter a valid value within the shown limits.`);}obj[key]=Number(el.value);}
    obj.scenarios=E.parseNumbers($('scenarios').value);obj.probabilities=E.parseNumbers($('probabilities').value);return validateInput(obj);
  }
  function validateInput(obj) {
    if(!obj||typeof obj!=='object'||Array.isArray(obj))throw new Error('Scenario input must be an object.');
    const input={};for(const key of ['capacity','da','up','down','hours'])input[key]=E.finite(obj[key],key);
    if(input.capacity<.1||input.capacity>10000||input.hours<.25||input.hours>24)throw new Error('Capacity must be 0.1–10,000 MW and duration 0.25–24 hours.');
    for(const key of ['da','up','down'])if(input[key]<-10000||input[key]>100000)throw new Error('Prices must be between −10,000 and 100,000 DKK/MWh.');
    if(!Array.isArray(obj.scenarios)||!Array.isArray(obj.probabilities))throw new Error('Scenarios and probabilities must be arrays.');
    input.scenarios=obj.scenarios.slice();input.probabilities=obj.probabilities.slice();E.optimize(input);return input;
  }
  function calculateLab() {
    try {const input=readLabForm(),result=E.optimize(input);labInput=input;currentLab=result;labDraft=null;labVersion++;$('lab-error').hidden=true;$('lab-output').innerHTML=labOutput();renderIcons($('lab-output'));$('verify-python').disabled=false;if($('python-result'))$('python-result').hidden=true;notify('Optimal offer recalculated from your assumptions.');}
    catch(error){$('lab-error').textContent=error.message;$('lab-error').hidden=false;}
  }
  function markLabDirty() {
    if(!$('lab-stale'))return;
    $('lab-stale').hidden=false;$('lab-result-state').textContent='INPUTS CHANGED';
    for(const id of ['save-scenario','export-scenario','export-curve','verify-python'])$(id).disabled=true;
    if($('python-result'))$('python-result').hidden=true;
  }
  function scenarioDocument(name='Exported scenario') {return {schema_version:1,application:'ZephyrTrade Champion',data_kind:'user_assumptions_not_live',name,input:labInput,calculated:{offer_mw:currentLab.offer,expected_revenue_dkk:currentLab.expected,critical_quantile:currentLab.quantile}};}
  function requireFreshLab() {
    try {const input=readLabForm();if(JSON.stringify(input)!==JSON.stringify(labInput)){notify('Recalculate your edited inputs before saving or exporting.');return false;}return true;}catch(error){$('lab-error').textContent=error.message;$('lab-error').hidden=false;return false;}
  }
  function loadScenario(input) {labDraft=null;labInput=validateInput(input);currentLab=E.optimize(labInput);labVersion++;render();notify('Scenario loaded and recalculated.');}
  async function pythonCheck() {
    if(!pythonAvailable){location.hash='method';setTimeout(()=>$('python-setup')?.scrollIntoView({block:'start'}),50);return;}
    if(!requireFreshLab())return;
    const epoch=labVersion,input=JSON.parse(JSON.stringify(labInput)),expected=currentLab.expected;
    const output=$('python-result');output.hidden=false;output.textContent='Running the local SciPy linear program…';
    const button=$('verify-python');button.disabled=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),5000);
    try {const response=await fetch('/api/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(input),signal:controller.signal});const result=await response.json();if(!response.ok)throw new Error(result.error||'Local solver request failed.');if(epoch!==labVersion||state.page!=='lab')return;
      E.verifyLPResult(result,expected,input.capacity);
      output.textContent=`Cross-check passed: Python LP offer ${num(result.offer_mw,4)} MW; expected revenue ${num(result.expected_revenue_dkk,4)} DKK. Objective agrees within 0.000001 DKK. Equal-value ties can give different offers.`;
    }catch(error){if(epoch===labVersion&&state.page==='lab')output.textContent=error.name==='AbortError'?'The local solver timed out. Your inputs are retained; retry when it is available.':error.message;}finally{clearTimeout(timeout);if(button.isConnected)button.disabled=false;}
  }
  function toggleTheme(){const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=theme;$('theme-label').textContent=`Switch to ${theme==='dark'?'light':'dark'} theme`;try{localStorage.setItem('zephyr-theme',theme);}catch(_){} }
  function init() {
    if(!D||!E||D.schema_version!==1||!D.timestamps.length)throw new Error('The bundled dataset or calculation engine is missing. Re-extract the complete app or use the standalone HTML.');
    try {const view=JSON.parse(localStorage.getItem('zephyr-view-v1')||'null');if(view){if(D.models.some(m=>m.id===view.model))state.model=view.model;if(['all','7','30'].includes(view.period))state.period=view.period;}}
    catch(_){/* An unreadable view preference does not affect observations. */}
    try {const t=localStorage.getItem('zephyr-theme');if(['light','dark'].includes(t))document.documentElement.dataset.theme=t;}
    catch(_){}
    $('theme-label').textContent=`Switch to ${document.documentElement.dataset.theme==='dark'?'light':'dark'} theme`;
    try {const raw=JSON.parse(localStorage.getItem('zephyr-scenarios-v1')||'[]');if(!Array.isArray(raw)||raw.length>20)throw new Error('Invalid saved data');saved=raw.map(x=>({name:String(x.name).slice(0,80),input:validateInput(x.input)}));}
    catch(_){saved=[];notify('Browser scenario storage is unavailable or unreadable. Use JSON export; no stored data has been changed.');}
    document.querySelector('.site-card strong').textContent=D.farm_name;
    document.querySelector('.site-card p').textContent=`${num(D.capacity_mw,0)} MW · synthetic ${D.market_area} case`;
    document.querySelector('#heading-tag strong').innerHTML=esc(num(D.capacity_mw,0))+' <small>MW</small>';
    $('model-select').innerHTML=D.models.map(m=>`<option value="${m.id}">${esc(m.name)}</option>`).join('');
    $('from-date').value=D.timestamps[0].slice(0,10);$('to-date').value=D.timestamps.at(-1).slice(0,10);
    ['from-date','to-date'].forEach(id=>{$(id).min=D.timestamps[0].slice(0,10);$(id).max=D.timestamps.at(-1).slice(0,10);});
    currentLab=E.optimize(labInput);go(location.hash.slice(1)||'overview',false);
    window.addEventListener('hashchange',()=>go(location.hash.slice(1)));
    $('model-select').addEventListener('change',event=>{state.model=event.target.value;dataPage=0;render();});
    $('theme-toggle').addEventListener('click',toggleTheme);
    $('theme-top').addEventListener('click',toggleTheme);
    $('help-button').addEventListener('click',()=>$('guide-dialog').showModal());
    $('export-top').addEventListener('click',()=>exportData());
    document.addEventListener('click',event=>{
      const btn=event.target.closest('button');if(!btn)return;
      if(btn.dataset.closeDialog){$(btn.dataset.closeDialog).close();return;}
      if(btn.dataset.go){location.hash=btn.dataset.go;return;}
      if(btn.dataset.period){if(btn.dataset.period==='custom'){state.period='custom';state.from=$('from-date').value;state.to=$('to-date').value;}else state.period=btn.dataset.period;dataPage=0;$('filter-error').hidden=true;render();return;}
      if(btn.id==='apply-dates'){const from=$('from-date').value,to=$('to-date').value;if(!from||!to||from>to){$('filter-error').textContent='Choose a valid start date on or before the end date.';$('filter-error').hidden=false;return;}state.from=from;state.to=to;state.period='custom';dataPage=0;$('filter-error').hidden=true;render();return;}
      if(btn.dataset.chart){chartMode=btn.dataset.chart;render();return;}
      if(btn.dataset.selectModel){state.model=btn.dataset.selectModel;location.hash='overview';return;}
      if(btn.dataset.paginate){dataPage+=Number(btn.dataset.paginate);render();return;}
      if(btn.id==='export-models'){exportModels();return;}
      if(btn.id==='export-filtered'){exportData(true);return;}
      if(btn.dataset.preset){const presets={balanced:{da:450,up:600,down:300},shortfall:{da:450,up:900,down:300},surplus:{da:450,up:600,down:50}};loadScenario({...labInput,...presets[btn.dataset.preset]});return;}
      if(btn.id==='save-scenario'){if(!requireFreshLab())return;if(saved.length>=20){notify('The local notebook holds 20 scenarios. Export and remove one before saving another.');return;}$('scenario-name').value='';$('save-dialog').showModal();return;}
      if(btn.id==='export-scenario'){if(requireFreshLab())download('ZephyrTrade-scenario.json',JSON.stringify(scenarioDocument(),null,2),'application/json');return;}
      if(btn.id==='export-curve'){if(requireFreshLab())csvDownload('ZephyrTrade-revenue-curve.csv',['data_kind','offer_mw','expected_revenue_dkk','interval_hours'],currentLab.curve.map(p=>['user_assumptions',p.offer,p.revenue,labInput.hours]));return;}
      if(btn.id==='import-scenario'){$('scenario-file').click();return;}
      if(btn.dataset.loadSaved!=null){loadScenario(saved[Number(btn.dataset.loadSaved)].input);return;}
      if(btn.dataset.deleteSaved!=null){const i=Number(btn.dataset.deleteSaved);if(!window.confirm(`Delete “${saved[i].name}” from this browser? Export a JSON backup first if needed.`))return;const next=saved.filter((_,j)=>j!==i);try{localStorage.setItem('zephyr-scenarios-v1',JSON.stringify(next));saved=next;$('saved-list').innerHTML=savedHtml();notify('Scenario deleted from this browser.');}catch(_){notify('Deletion failed. Your saved scenario has been retained.');}return;}
      if(btn.id==='verify-python'){pythonCheck();return;}
      if(btn.id==='export-provenance'){download('ZephyrTrade-provenance.json',JSON.stringify({data_kind:D.data_kind,source_generated_at:D.source_generated_at,quality:D.quality,sources:D.sources},null,2),'application/json');}
    });
    document.addEventListener('submit',event=>{
      if(event.target.id==='lab-form'){event.preventDefault();calculateLab();}
      if(event.target.id==='save-form'){event.preventDefault();const name=$('scenario-name').value.trim();if(!name){$('scenario-name').setCustomValidity('Enter a scenario name.');$('scenario-name').reportValidity();return;}const next=[...saved,{name,input:JSON.parse(JSON.stringify(labInput))}];try{localStorage.setItem('zephyr-scenarios-v1',JSON.stringify(next));saved=next;$('save-dialog').close();$('saved-list').innerHTML=savedHtml();notify('Scenario saved in this browser. Export JSON for a backup.');}catch(_){notify('Could not save: browser storage is unavailable or full. Use Export JSON instead.');}}
    });
    document.addEventListener('input',event=>{if(event.target.closest('#lab-form')){labDraft={};for(const key of ['capacity','da','up','down','hours','scenarios','probabilities'])labDraft[key]=$(key).value;labVersion++;markLabDirty();}if(event.target.id==='scenario-name')event.target.setCustomValidity('');if(event.target.id==='data-search'){dataSearch=event.target.value;dataPage=0;const focus=event.target.selectionStart;render();const field=$('data-search');field.focus();if(focus!=null)field.setSelectionRange(focus,focus);}});
    document.addEventListener('change',async event=>{
      if(event.target.id!=='scenario-file')return;const file=event.target.files[0];if(!file)return;
      try{if(file.size>32768)throw new Error('Scenario JSON must be smaller than 32 KB.');const parsed=JSON.parse(await file.text());if(parsed.schema_version!==1)throw new Error('Unsupported scenario schema; expected version 1.');loadScenario(parsed.input);}
      catch(error){notify('Import failed: '+error.message);}finally{if($('scenario-file'))$('scenario-file').value='';}
    });
    if(location.protocol==='http:'&&['127.0.0.1','localhost'].includes(location.hostname)){
      const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),2000);
      fetch('/api/health',{signal:controller.signal}).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(result=>{if(result.service==='zephyrtrade-local'){pythonAvailable=true;$('engine-status').textContent='Browser + Python / SciPy · loopback only';if(state.page==='lab'){$('verify-python').innerHTML='Cross-check with Python / SciPy '+icon('arrow');}}}).catch(()=>{}).finally(()=>clearTimeout(timeout));
    }
  }
  try { init(); } catch(error) { $('fatal-error').textContent=error.message;$('fatal-error').hidden=false;console.error('ZephyrTrade startup failed:',error.message); }
  // Read-only testing and diagnostic contract; no privileged capabilities.
  window.ZephyrApp = {getState:()=>({...state}),getLab:()=>({input:JSON.parse(JSON.stringify(labInput)),result:currentLab}),getVisibleMetrics:()=>metrics(selectedModel(),indices())};
})();
