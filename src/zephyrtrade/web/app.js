/* ZephyrTrade Champion UI. All observations originate in the packaged snapshot. */
(function () {
  'use strict';
/** @typedef {import('./browser-contracts.js').ZephyrModel} ZephyrModel */
/** @typedef {import('./browser-contracts.js').LabInput} LabInput */
/** @typedef {import('./engine.js').OfferingResult} OfferingResult */
/** @typedef {{name:string,input:LabInput}} SavedScenario */
/** @typedef {{id:string}|{attribute:string,value:string|null}} FocusKey */
/** @template T @param {T|null|undefined} value @param {string} label @returns {T} */
function required(value, label) {
  if (value === null || value === undefined) throw new Error(`Missing ${label}`);
  return value;
}
/** @template T @param {readonly T[]} values @param {number} index @returns {T} */
function at(values, index) { return required(values[index], `entry ${index}`); }
/** @template T @param {readonly T[]} values @returns {T} */
function last(values) { return required(values.at(-1), 'last entry'); }
/** @param {unknown} value @returns {value is Record<string,unknown>} */
function isRecord(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
/** @param {unknown} error @returns {string} */
function errorMessage(error) { return error instanceof Error ? error.message : String(error); }

/**
 * Construct the application's small HTML/SVG view vocabulary without HTML sinks.
 * Callers still escape interpolated text. This is deliberately not a general HTML
 * parser: executable elements, event attributes and resource-loading CSS fail
 * closed, before the existing view is replaced.
 */
const viewHTMLTags = new Set('a article aside b br button canvas caption code col colgroup dd details dialog div dl dt em fieldset figcaption figure footer form h1 h2 h3 h4 h5 header hr i input kbd label legend li main nav ol optgroup option output p pre progress section select small span strong summary sup table tbody td textarea th thead time tr ul'.split(' '));
const viewSVGTags = new Set('svg circle clipPath defs desc ellipse g line linearGradient marker mask path pattern polygon polyline radialGradient rect stop text title tspan'.toLowerCase().split(' '));
const viewVoidTags = new Set(['br', 'col', 'hr', 'input']);
const viewSVGResourceAttributes = new Set(['clip-path', 'color-profile', 'cursor', 'fill', 'filter', 'marker', 'marker-start', 'marker-mid', 'marker-end', 'mask', 'stroke']);
/** @type {Record<string,string>} */
const svgNames = { clippath: 'clipPath', lineargradient: 'linearGradient', radialgradient: 'radialGradient' };
/** @type {Record<string,string>} */
const viewEntities = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: '\u00a0', ndash: '\u2013', mdash: '\u2014', times: '\u00d7', minus: '\u2212', hellip: '\u2026', middot: '\u00b7', copy: '\u00a9', deg: '\u00b0' };
/** @param {string} text */
function viewText(text) {
    return text.replace(/&(#x[\da-f]+|#\d+|[a-z]+);/gi, (entity, code) => {
        if (code[0] !== '#')
            return viewEntities[code] ?? entity;
        const value = code[1]?.toLowerCase() === 'x' ? Number.parseInt(code.slice(2), 16) : Number.parseInt(code.slice(1), 10);
        return value > 0 && value <= 0x10ffff && !(value >= 0xd800 && value <= 0xdfff) ? String.fromCodePoint(value) : '\ufffd';
    });
}
/** @param {HTMLElement|SVGElement} element @param {string} name @param {string} value */
function setViewAttribute(element, name, value) {
    const key = name.toLowerCase();
    if (/^on/i.test(key) || ['srcdoc', 'is', 'src', 'srcset', 'action', 'formaction', 'ping', 'background', 'xmlns:xlink', 'xlink:href'].includes(key)) {
        throw new Error(`Unsupported view attribute: ${name}`);
    }
    if (key === 'style') {
        // CSSOM assignments are compatible with style-src-attr 'none'. None of our
        // numeric chart/animation styles need URL, escaped or executable CSS.
        if (/url\s*\(|image-set\s*\(|expression\s*\(|@import|behavior\s*:|-moz-binding|\\|\/\*/i.test(value))
            throw new Error('Unsupported view style');
        const style = element.style;
        for (const declaration of value.split(';')) {
            if (!declaration.trim())
                continue;
            const separator = declaration.indexOf(':');
            if (separator < 1)
                throw new Error('Invalid view style');
            const property = declaration.slice(0, separator).trim();
            if (!/^(?:--[\w-]+|[a-z][a-z-]*)$/i.test(property))
                throw new Error('Invalid view style property');
            const raw = declaration.slice(separator + 1).trim();
            const important = /\s*!important$/i.test(raw);
            style.setProperty(property, raw.replace(/\s*!important$/i, ''), important ? 'important' : '');
        }
        return;
    }
    if (key === 'href') {
        if (element.namespaceURI === 'http://www.w3.org/2000/svg') {
            if (!/^#[A-Za-z][\w:.-]*$/.test(value))
                throw new Error('Unsupported SVG reference');
        }
        else {
            const url = new URL(value, element.ownerDocument.baseURI);
            if (!['http:', 'https:', 'mailto:', 'file:'].includes(url.protocol) || Array.from(value).some(character => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127))
                throw new Error('Unsupported view link');
        }
    }
    // SVG presentation attributes are CSS too. Reject escapes and comments before
    // looking for URLs so CSS token normalization cannot hide a resource load.
    // Labels/data attributes keep their literal values; only resource attributes
    // need this CSS restriction. Canonical local fragments remain supported.
    if (element.namespaceURI === 'http://www.w3.org/2000/svg' && viewSVGResourceAttributes.has(key)
        && /\\|\/\*|\*\/|image-set\s*\(|expression\s*\(|@import/i.test(value))
        throw new Error('Unsupported view resource');
    if (/url\s*\(/i.test(value) && !/^url\(#[A-Za-z][\w:.-]*\)$/.test(value))
        throw new Error('Unsupported view resource');
    element.setAttribute(name, value);
}
/** @param {string} markup @param {Document} [doc] */
function viewFragment(markup, doc = document) {
    const fragment = doc.createDocumentFragment();
    /** @type {(DocumentFragment|HTMLElement|SVGElement)[]} */
    const stack = [fragment];
    /** @type {string[]} */
    const names = [];
    /** @param {string} text */
    const appendText = (text) => { last(stack).appendChild(doc.createTextNode(viewText(text))); };
    let offset = 0;
    while (offset < markup.length) {
        if (markup[offset] !== '<') {
            const next = markup.indexOf('<', offset);
            const end = next < 0 ? markup.length : next;
            appendText(markup.slice(offset, end));
            offset = end;
            continue;
        }
        if (markup.startsWith('<!--', offset)) {
            const end = markup.indexOf('-->', offset + 4);
            if (end < 0)
                throw new Error('Unclosed view comment');
            offset = end + 3;
            continue;
        }
        const closing = /^<\/\s*([A-Za-z][\w-]*)\s*>/.exec(markup.slice(offset));
        if (closing) {
            const tag = required(closing[1], 'closing tag').toLowerCase();
            if (names[names.length - 1] !== tag)
                throw new Error(`Unbalanced view element: ${tag}`);
            names.pop();
            stack.pop();
            offset += closing[0].length;
            continue;
        }
        const opening = /^<([A-Za-z][\w-]*)/.exec(markup.slice(offset));
        if (!opening) {
            appendText('<');
            offset++;
            continue;
        }
        const tag = required(opening[1], 'opening tag').toLowerCase();
        const parent = last(stack);
        const svg = tag === 'svg' || ('namespaceURI' in parent && parent.namespaceURI === 'http://www.w3.org/2000/svg');
        if (!(svg ? viewSVGTags : viewHTMLTags).has(tag))
            throw new Error(`Unsupported view element: ${tag}`);
        const element = svg ? doc.createElementNS('http://www.w3.org/2000/svg', svgNames[tag] ?? tag) : doc.createElement(tag);
        offset += opening[0].length;
        let selfClosing = false;
        while (offset < markup.length) {
            const whitespace = /^\s+/.exec(markup.slice(offset));
            if (whitespace)
                offset += whitespace[0].length;
            if (markup.startsWith('/>', offset)) {
                offset += 2;
                selfClosing = true;
                break;
            }
            if (markup[offset] === '>') {
                offset++;
                break;
            }
            const attribute = /^([^\s=<>/"'`]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s<>`]+)))?/.exec(markup.slice(offset));
            if (!attribute)
                throw new Error('Invalid view attribute');
            setViewAttribute(element, required(attribute[1], 'attribute name'), viewText(attribute[2] ?? attribute[3] ?? attribute[4] ?? ''));
            offset += attribute[0].length;
        }
        if (offset >= markup.length && !markup.endsWith('>'))
            throw new Error('Unclosed view element');
        parent.appendChild(element);
        if (!selfClosing && !viewVoidTags.has(tag)) {
            stack.push(element);
            names.push(tag);
        }
    }
    if (names.length)
        throw new Error(`Unclosed view element: ${names[names.length - 1]}`);
    return fragment;
}
/** @param {Element|null} target @param {string} markup */
function renderView(target, markup) {
    if (target)
        target.replaceChildren(viewFragment(markup, target.ownerDocument));
}

  const D = window.ZEPHYR_DATA, E = window.ZephyrEngine;
  /** @param {string} id */
  const findElement = id => document.getElementById(id);
  /** @param {string} id */
  const $ = id => required(findElement(id), `element #${id}`);
  /** @param {string} id */
  const inputElement = id => {
    const element = $(id);
    if (!(element instanceof HTMLInputElement)) throw new Error(`Expected input #${id}`);
    return element;
  };
  /** @param {string} id */
  const controlElement = id => {
    const element = $(id);
    if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element instanceof HTMLSelectElement))
      throw new Error(`Expected form control #${id}`);
    return element;
  };
  /** @param {string} id */
  const buttonElement = id => {
    const element = $(id);
    if (!(element instanceof HTMLButtonElement)) throw new Error(`Expected button #${id}`);
    return element;
  };
  /** @param {string} id */
  const dialogElement = id => {
    const element = $(id);
    if (!(element instanceof HTMLDialogElement)) throw new Error(`Expected dialog #${id}`);
    return element;
  };
  /** @param {unknown} value */
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c] ?? c));
  /** @type {Record<string,string> & {overview:string}} */
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
  /** @param {string|null|undefined} name */
  const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name ?? 'overview'] || icons.overview}</svg>`;
  /** @param {number|null|undefined} x @param {number} [d] */
  const num = (x,d=1) => x == null || !Number.isFinite(x) ? '—' : x.toLocaleString('en-GB',{minimumFractionDigits:d,maximumFractionDigits:d});
  /** @param {number} x */
  const compact = x => Math.abs(x)>=1e6 ? num(x/1e6,2)+'m' : Math.abs(x)>=1e3 ? num(x/1e3,1)+'k' : num(x,1);
  /** @param {string} s */
  const dateLabel = s => new Date(s).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
  /** @param {string} s */
  const shortDate = s => new Date(s).toLocaleDateString('en-GB',{day:'2-digit',month:'short',timeZone:'UTC'});
  /** @type {ReturnType<typeof setTimeout>|undefined} */
  let toastTimer;
  let pythonAvailable = false, labVersion = 0;
  /** @type {OfferingResult|null} */
  let currentLab = null;
  /** @type {Record<string,string>|null} */
  let labDraft = null;
  /** @type {SavedScenario[]} */
  let saved = [];
  let dataPage = 0, dataSearch = '', chartMode = 'power';
  /** @type {LabInput} */
  let labInput = {capacity:30,da:420,up:610,down:310,hours:1,scenarios:[2,5,9,13,18,24,28],probabilities:[]};
  /** @type {Record<string,[string,string,string,string]>} */
  const pageInfo = {
    overview:['Overview','WIND INTELLIGENCE / DK2','From wind to value.','Explore the forecast. Understand the offer. See the trade-off.'],
    lab:['Strategy lab','SCENARIOS / STOCHASTIC OFFERING','Test the trade-off.','Change your assumptions. Find the optimal offer. No real trades.'],
    models:['Model arena','BENCHMARK / NINE STRATEGIES','Let the evidence lead.','Compare realised value and offer error on the same retained hours.'],
    data:['Data explorer','OBSERVATIONS / HOURLY RECORDS','Every number, traceable.','Inspect the source observations behind the selected backtest.'],
    method:['Method & evidence','TRANSPARENCY / RESEARCH CONTRACT','Know what you are seeing.','The assumptions, provenance and limits behind every result.'],
  };
  const state = {page:'overview',model:'direct_regression',period:'all',from:'',to:''};
  /** @param {string} message */
  function notify(message) { $('toast').textContent=message; $('toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').hidden=true,5500); }
  /** @param {ParentNode} [root] */
  function renderIcons(root=document) { root.querySelectorAll('[data-icon]').forEach(el=>{renderView(el, icon(el.getAttribute('data-icon')));}); }
  function persistView() { try { localStorage.setItem('zephyr-view-v1',JSON.stringify({model:state.model,period:state.period,from:state.from,to:state.to})); } catch { /* Preferences are optional, unlike scenario saves. */ } }
  /** @param {string} from @param {string} to */
  function validCustomRange(from,to) {
    /** @param {unknown} value */
    const validDate=value=>typeof value==='string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value+'T00:00:00Z')) && new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
    return validDate(from) && validDate(to) && from<=to && from>=at(D.timestamps,0).slice(0,10) && to<=last(D.timestamps).slice(0,10);
  }
  /** @param {unknown} view */
  function restoreView(view) {
    if(!isRecord(view))return;
    if(typeof view.model==='string' && D.models.some(m=>m.id===view.model))state.model=view.model;
    if(typeof view.period==='string' && ['all','7','30'].includes(view.period))state.period=view.period;
    if(typeof view.from==='string' && typeof view.to==='string' && validCustomRange(view.from,view.to)){
      state.from=view.from;state.to=view.to;
      if(view.period==='custom')state.period='custom';
    }
  }
  function indices() {
    let from=-Infinity,to=Infinity;
    if (state.period==='custom') { from=Date.parse(state.from+'T00:00:00Z');to=Date.parse(state.to+'T23:59:59Z'); }
    else if (state.period!=='all') {to=Date.parse(last(D.timestamps));from=to-Number(state.period)*86400000+3600000;}
    return D.timestamps.flatMap((t,i)=>Date.parse(t)>=from&&Date.parse(t)<=to?[i]:[]);
  }
  const selectedModel = () => D.models.find(m=>m.id===state.model) || D.models[0];
  /** @template T @param {T[]} arr @param {number[]} ids */
  const subset = (arr,ids) => ids.map(i=>at(arr,i));
  /** @param {ZephyrModel} model @param {number[]} ids */
  function metrics(model,ids) { return E.statistics(subset(D.actual,ids),subset(model.offers,ids),subset(D.day_ahead,ids),subset(D.up,ids),subset(D.down,ids)); }
  /** @param {number[]} ids */
  function rankings(ids) { return D.models.map(model=>({model,score:metrics(model,ids)})).sort((a,b)=>b.score.total-a.score.total); }
  /** @param {string} label @param {string} value @param {string} unit @param {string} sub @param {string} [name] @param {boolean} [primary] */
  function kpi(label,value,unit,sub,name='value',primary=false) {return `<article class="kpi${primary?' primary':''}"><div class="kpi-label">${label}<span data-icon="${name}"></span></div><div class="kpi-value">${value}${unit?`<small>${unit}</small>`:''}</div><div class="kpi-sub">${sub}</div></article>`;}
  /** @param {number} value @param {boolean} compactLayout */
  function chartValue(value,compactLayout) {return compactLayout && Math.abs(value)>=1e9?num(value/1e9,1)+'b':compact(value);}
  /** @param {{values:number[]}[]} lines @param {string[]} labels @param {{ylabel?:string,height?:number,min?:number|null,max?:number|null,title?:string,gaps?:boolean[],width?:number}} [options] */
  function lineChart(lines,labels,{ylabel='',height=238,min=null,max=null,title='Chart',gaps=[],width=800}={}) {
    const compactLayout=Number.isFinite(width) && width<600;
    const w=compactLayout?Math.max(160,width):800,h=height,p=compactLayout?{l:70,r:18,t:24,b:40}:{l:50,r:15,t:19,b:35},pw=w-p.l-p.r,ph=h-p.t-p.b;
    const flat=lines.flatMap(s=>s.values).filter(Number.isFinite);
    let lo=min ?? Math.min(0,...flat), hi=max ?? Math.max(...flat);
    if (!Number.isFinite(hi)||hi<=lo) hi=lo+1;
    const x=(/** @type {number} */ i)=>p.l+(labels.length<2?pw/2:i/(labels.length-1)*pw), y=(/** @type {number} */ v)=>p.t+ph-(v-lo)/(hi-lo)*ph;
    let svg=`<svg class="chart${compactLayout?' chart-compact':''}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>`;
    for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4,py=y(v);svg+=`<line class="grid-line" x1="${p.l}" x2="${w-p.r}" y1="${py}" y2="${py}"/><text x="${p.l-10}" y="${py+3}" text-anchor="end">${esc(Math.abs(v)>=1000?chartValue(v,compactLayout):num(v,Number.isInteger(hi)?0:1))}</text>`;}
    const ticks = [...new Set(compactLayout?[0,labels.length-1]:[0,Math.floor((labels.length-1)/3),Math.floor((labels.length-1)*2/3),labels.length-1])];
    ticks.forEach(i=>{if(i>=0)svg+=`<text x="${x(i)}" y="${h-10}" text-anchor="${i===0?'start':i===labels.length-1?'end':'middle'}">${esc(labels[i])}</text>`;});
    svg+=`<text x="${p.l}" y="${compactLayout?12:10}">${esc(ylabel)}</text>`;
    const classes=['line-a','line-b','line-c'];
    lines.forEach((s,j)=>{let path='',last=false;s.values.forEach((v,i)=>{if(!Number.isFinite(v)){last=false;return;}path+=(last&&!gaps[i]?'L':'M')+x(i).toFixed(2)+','+y(v).toFixed(2)+' ';last=true;});svg+=`<path class="${classes[j%3]}" d="${path}"/>`;if(s.values.length===1)svg+=`<circle cx="${x(0)}" cy="${y(at(s.values,0))}" r="3" fill="var(--accent)"/>`;});
    return svg+'</svg>';
  }
  /** @param {number[]} ids @param {number[][]} arrays @param {boolean} [cumulative] */
  function groupTime(ids,arrays,cumulative=false) {
    const daily=ids.length>180;
    /** @type {{key:string,ids:number[],points:number[][]}[]} */
    const groups=[];let lastKey='';
    ids.forEach((id,i)=>{const key=daily?at(D.timestamps,id).slice(0,10):at(D.timestamps,id);if(key!==lastKey){groups.push({key,ids:[],points:arrays.map(()=>[])});lastKey=key;}const g=last(groups);g.ids.push(id);arrays.forEach((a,j)=>at(g.points,j).push(at(a,i)));});
    return {daily,labels:groups.map(g=>daily?shortDate(g.key):at(D.timestamps,at(g.ids,0)).slice(5,16).replace('T',' ')),
      values:arrays.map((_,j)=>groups.map(g=>cumulative?last(at(g.points,j)):at(g.points,j).reduce((a,b)=>a+b,0)/at(g.points,j).length)),
      gaps:groups.map((g,i)=>i>0 && Date.parse(g.key)-Date.parse(at(groups,i-1).key)>(daily?86400000:3600000))};
  }
  /** @param {ZephyrModel} model @param {number[]} ids @param {number} [width] */
  function powerPlot(model,ids,width=800) {
    const actual=subset(D.actual,ids),offers=subset(model.offers,ids);
    let series, labels, opts, note;
    if(chartMode==='revenue') {
      let running=0,oracle=0;
      const values=ids.map(i=>running+=E.revenue(at(model.offers,i),at(D.actual,i),at(D.day_ahead,i),at(D.up,i),at(D.down,i)));
      const ideal=ids.map(i=>oracle+=at(D.actual,i)*at(D.day_ahead,i));
      const g=groupTime(ids,[ideal,values],true);series=[{values:at(g.values,0)},{values:at(g.values,1)}];labels=g.labels;
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
    const headings=chartMode==='revenue'?['Perfect foresight (DKK)','Selected strategy (DKK)']:chartMode==='prices'?['Day-ahead (DKK/MWh)','Down-regulation (DKK/MWh)','Up-regulation (DKK/MWh)']:['Actual output (MW)','Selected offer (MW)'];
    const rows=labels.map((label,i)=>`<tr><th scope="row">${esc(label)}</th>${series.map(s=>`<td class="number">${num(at(s.values,i),2)}</td>`).join('')}</tr>`).join('');
    return `<div class="legend">${legend}</div>${lineChart(series,labels,{...opts,width})}<div class="chart-note"><span>${note}</span><span>UTC · ${num(ids.length,0)} records</span></div><details><summary>View chart data table</summary><div class="table-wrap" tabindex="0" role="region" aria-labelledby="overview-chart-data-caption"><table><caption id="overview-chart-data-caption" class="sr-only">${esc(opts.title)} (rounded values)</caption><thead><tr><th scope="col">UTC interval</th>${headings.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div></details>`;
  }
  function turbineGlyph() {return `<svg class="wind-glyph" viewBox="0 0 240 105" role="img" aria-label="Wind turbine diagram"><defs><linearGradient id="tg" x2="0" y2="1"><stop stop-color="currentColor" stop-opacity=".2"/><stop offset="1" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs><path d="M7 94H235M20 98h195" stroke="currentColor" stroke-opacity=".2"/><g fill="none" stroke="currentColor" stroke-width="1.2"><path d="M107 38 103 92h11l-4-54M174 47l-3 45h7l-3-45M57 58l-2 34h5l-2-34"/><path d="M109 38 105 3c8 3 9 17 4 35ZM109 38l31 16c-1 6-22-2-31-16ZM109 38 87 62c-6-3 7-20 22-24Z"/><circle cx="109" cy="38" r="3"/><path d="m174 47 0-25c5 2 5 15 0 25ZM174 47l22 13c-2 4-16-2-22-13ZM174 47l-16 18c-5-4 7-16 16-18Z"/><circle cx="174" cy="47" r="2"/><path d="M57 58V39c4 1 4 12 0 19Zm0 0 17 10c-2 3-12-1-17-10Zm0 0L45 72c-4-3 5-12 12-14Z"/><circle cx="57" cy="58" r="1.5"/></g><path d="M30 20h36M15 30h53M186 10h36M198 19h25" stroke="currentColor" stroke-opacity=".25" stroke-linecap="round"/></svg>`;}
  /** @param {number[]} ids */
  function overview(ids) {
    const model=selectedModel(),s=metrics(model,ids),ranked=rankings(ids);
    const baseline=required(ranked.find(x=>x.model.id==='persistence_24h'), 'persistence benchmark').score;
    const delta=s.total-baseline.total;
    const gapHours=Math.round((Date.parse(at(D.timestamps,last(ids)))-Date.parse(at(D.timestamps,at(ids,0))))/3600000)+1-ids.length;
    return `<div class="kpi-grid">${kpi('Realised revenue',compact(s.total),'DKK',`<span class="accent">${delta>=0?'+':''}${compact(delta)}</span> vs persistence`,'value',true)}${kpi('Perfect-foresight capture',num(s.capture,2),'%', 'Revenue ÷ benchmark revenue','target')}${kpi('Absolute imbalance',compact(s.imbalance),'MWh',num(s.mae,2)+' MW mean absolute offer error','wind')}${kpi('Retained test intervals',num(ids.length,0),'hours',num(gapHours,0)+' excluded hours between endpoints','clock')}</div>
    <div class="dashboard-grid"><section class="panel"><div class="panel-header"><div><h2>Production meets strategy</h2><p>${esc(model.name)} · held-out synthetic observations</p></div><div class="chart-toolbar" role="group" aria-label="Chart measure">${['power','revenue','prices'].map(x=>`<button data-chart="${x}" type="button" aria-pressed="${chartMode===x}">${{power:'Output',revenue:'Revenue',prices:'Prices'}[x]}</button>`).join('')}</div></div><div id="overview-plot">${powerPlot(model,ids)}</div><p class="chart-summary">${num(s.meanActual,2)} MW mean output · ${num(s.meanOffer,2)} MW mean offer · ${compact(s.regret)} DKK regret to perfect foresight</p></section>
    <aside class="panel insight-panel"><div class="eyebrow">EXPLORE THE DECISION</div><h2 class="insight-title">The best forecast<br>is not the whole story.</h2><p>A shortfall costs the up-regulation price. A surplus earns the down-regulation price. Explore how that changes your offer.</p>${turbineGlyph()}<button class="button secondary small" data-go="lab" type="button">Open strategy lab <span data-icon="arrow"></span></button></aside></div>
    <div class="split-grid"><section class="panel"><div class="panel-header"><div><h2>Leading strategies</h2><p>Ranked by revenue within the selected window</p></div><button class="text-link" data-go="models" type="button">Compare all <span data-icon="arrow"></span></button></div>${ranked.slice(0,3).map((x,i)=>`<div class="mini-row"><span class="rank">0${i+1}</span><div><strong>${esc(x.model.name)}</strong><small>${esc(x.model.family)}</small></div><div class="number">${compact(x.score.total)}<small>DKK · ${num(x.score.capture,2)}% capture</small></div></div>`).join('')}</section>
    <section class="panel"><div class="panel-header"><div><h2>The research context</h2><p>Keep the assumptions in view</p></div><span class="badge">OFFLINE</span></div><div class="context-row"><span>Evaluated farm</span><strong>Ronne Coastal Proxy</strong></div><div class="context-row"><span>Price regime</span><strong>Down ≤ day-ahead ≤ up</strong></div><div class="context-row"><span>Interval / settlement</span><strong>1 hour / DKK</strong></div><div class="context-note">Not a complete calendar backtest: negative-price hours were removed upstream. These results are not evidence of live profitability.</div></section></div>`;
  }
  /** @param {number[]} ids */
  function modelsPage(ids) {
    const rows=rankings(ids), max=Math.max(...rows.map(x=>x.score.total)), benchmark=at(rows,0).score.oracle;
    return `<div class="notice"><strong>Same hours. Different decisions.</strong> This table compares offer error, not forecast-only error. Rankings change with your date filter. Perfect foresight is shown as a non-deployable reference, not as a competing learned model.</div>
    <section class="panel"><div class="panel-header"><div><h2>Value leaderboard</h2><p>${num(ids.length,0)} retained hourly records · ${compact(benchmark)} DKK perfect-foresight reference</p></div><button class="button secondary small" id="export-models" type="button"><span data-icon="download"></span>Export comparison</button></div><div class="model-bars">${rows.map(x=>`<div class="model-bar-row"><span>${esc(x.model.name)}</span><div class="bar-track"><div class="bar-fill" style="--width:${Math.max(0,x.score.total/max*100)}%;background:var(--${x.model.family==='Direct learning'?'accent':x.model.family==='Baseline'?'gold':'cyan'})"></div></div><strong>${compact(x.score.total)} DKK</strong></div>`).join('')}</div><p class="readout-caption">Bars start at zero. Colours distinguish direct learning, forecast-then-optimise and persistence.</p><div class="table-wrap"><table><caption class="sr-only">Strategy performance in the selected time window</caption><thead><tr><th>Rank</th><th>Strategy</th><th class="number">Revenue (DKK)</th><th class="number">Capture (%)</th><th class="number">Regret (DKK)</th><th class="number">Offer RMSE (MW)</th><th class="number">Offer MAE (MW)</th><th>Explore</th></tr></thead><tbody>${rows.map((x,i)=>`<tr class="${state.model===x.model.id?'selected-row':''}"><td><span class="pill-number">${i+1}</span></td><td><strong>${esc(x.model.name)}</strong><small>${esc(x.model.family)}</small></td><td class="number">${num(x.score.total,0)}</td><td class="number">${num(x.score.capture,2)}</td><td class="number">${num(x.score.regret,0)}</td><td class="number">${num(x.score.rmse,3)}</td><td class="number">${num(x.score.mae,3)}</td><td><button class="text-link" data-select-model="${x.model.id}" type="button">Inspect <span data-icon="arrow"></span></button></td></tr>`).join('')}</tbody></table></div></section>
    <div class="split-grid section-space"><section class="panel prose"><h2>Forecast → optimise</h2><div class="flow"><div>Weather + lagged output</div><span>→</span><div>Power forecast</div><span>→</span><div>Residual scenarios</div><span>→</span><div>Optimal offer</div></div><p>The seven indirect strategies include the 24-hour persistence baseline. Saved offer vectors come from the supplied research run; changing the dashboard date window does not retrain them.</p></section><section class="panel prose"><h2>Direct learning</h2><div class="flow"><div>Same information set</div><span>→</span><div>Continuous / bracket learning</div><span>→</span><div>Offer</div></div><p>The two direct strategies learn offers from synthetic perfect-foresight targets. They are research outputs, not an independently validated production forecasting service.</p></section></div>`;
  }
  /** @param {number[]} ids */
  function matchingIds(ids) {
    const query=String(dataSearch).toLowerCase();
    return ids.filter(i=>at(D.timestamps,i).toLowerCase().includes(query));
  }
  /** @param {number[]} ids */
  function dataPageHtml(ids) {
    const filtered=matchingIds(ids);
    const pageCount=Math.max(1,Math.ceil(filtered.length/25));dataPage=Math.min(dataPage,pageCount-1);
    const visible=filtered.slice(dataPage*25,dataPage*25+25),m=selectedModel();
    return `<div class="data-quality-grid">${kpi('Records in selected period',num(ids.length,0),'',dateLabel(at(D.timestamps,at(ids,0)))+' → '+dateLabel(at(D.timestamps,last(ids))),'data')}${kpi('Source rows checked',num(D.quality.revenue_values_checked,0),'', 'Saved revenue values reconciled with Python','check')}${kpi('Dataset coverage',num(D.quality.rows,0),'hours', 'One evaluated synthetic site · UTC','clock')}</div><section class="panel"><div class="panel-header"><div><h2>Hourly research ledger</h2><p>${esc(m.name)} · use the global filters to select a period</p></div><span class="badge good">SOURCE-BACKED</span></div><div class="table-controls"><label class="sr-only" for="data-search">Find a UTC date or hour</label><input id="data-search" aria-describedby="data-search-status" type="search" placeholder="Find a UTC date or hour, e.g. 2024-12-15" value="${esc(dataSearch)}"><button class="button secondary small" id="export-filtered" type="button"><span data-icon="download"></span>Export ${num(filtered.length,0)} matching rows</button></div><div class="table-wrap"><table><caption class="sr-only">Hourly actual output, strategy offer, settlement prices and calculated revenue</caption><thead><tr><th>Time (UTC)</th><th class="number">Actual (MW)</th><th class="number">Offer (MW)</th><th class="number">Day-ahead<br>(DKK/MWh)</th><th class="number">Up price<br>(DKK/MWh)</th><th class="number">Down price<br>(DKK/MWh)</th><th class="number">Revenue (DKK)</th></tr></thead><tbody>${visible.length?visible.map(i=>`<tr><td class="mono">${at(D.timestamps,i).slice(0,16).replace('T',' ')}</td><td class="number">${num(at(D.actual,i),3)}</td><td class="number">${num(at(m.offers,i),3)}</td><td class="number">${num(at(D.day_ahead,i),2)}</td><td class="number">${num(at(D.up,i),2)}</td><td class="number">${num(at(D.down,i),2)}</td><td class="number">${num(E.revenue(at(m.offers,i),at(D.actual,i),at(D.day_ahead,i),at(D.up,i),at(D.down,i)),2)}</td></tr>`).join(''):'<tr><td colspan="7"><div class="empty"><strong>No matching records.</strong>Clear your date search or choose a different period. Missing hours are not fabricated.</div></td></tr>'}</tbody></table></div><div class="pagination"><span>${filtered.length?num(dataPage*25+1,0):0}–${num(Math.min((dataPage+1)*25,filtered.length),0)} of ${num(filtered.length,0)} rows · Page ${dataPage+1} / ${pageCount}</span><div><button class="button secondary small" data-paginate="-1" type="button" ${dataPage===0?'disabled':''}>Previous</button><button class="button secondary small" data-paginate="1" type="button" ${dataPage>=pageCount-1?'disabled':''}>Next</button></div></div></section><div class="notice section-space">CSV exports contain unrounded numerical values, the strategy ID and a synthetic-data label. The on-screen table rounds values for readability. ${D.quality.excluded_hours_between_endpoints} hours are absent between the full test-set endpoints; the original source removed ${D.quality.source_negative_price_rows_removed} negative-price hours across its complete generation period.</div>`;
  }
  /** @param {string} id @param {string} label @param {number} value @param {string} unit @param {number} min @param {number} max */
  function numericField(id,label,value,unit,min,max) {return `<div class="form-field"><label for="${id}">${label}</label><div class="input-unit"><input id="${id}" name="${id}" type="number" value="${value}" min="${min}" max="${max}" step="any" required><span>${unit}</span></div></div>`;}
  function labPage() {
    return `<div class="notice"><strong>Independent scenario sandbox.</strong> These are editable assumptions, not a forecast or live bid. The dashboard strategy and date filters do not affect this calculation. Negative prices are allowed here only when the required price ordering holds.</div><div class="lab-grid"><div><section class="panel"><div class="panel-header"><div><h2>Build your scenario</h2><p>Empirical production distribution + settlement prices</p></div><span class="badge blue">WHAT-IF</span></div><div class="preset-row" role="group" aria-label="Scenario presets"><button data-preset="balanced" type="button">Balanced spread</button><button data-preset="shortfall" type="button">Costly shortfall</button><button data-preset="surplus" type="button">Low surplus value</button></div><form id="lab-form" novalidate><div class="form-grid">${numericField('capacity','Physical capacity',labInput.capacity,'MW',.1,10000)}${numericField('hours','Settlement interval',labInput.hours,'hours',.25,24)}${numericField('da','Day-ahead price',labInput.da,'DKK/MWh',-10000,100000)}${numericField('up','Up-regulation price',labInput.up,'DKK/MWh',-10000,100000)}${numericField('down','Down-regulation price',labInput.down,'DKK/MWh',-10000,100000)}<div class="form-field"><span>Decision rule</span><div class="formula">q = (DA − down)<br> / (up − down)</div></div><div class="form-field full"><label for="scenarios">Production scenarios (MW)</label><textarea id="scenarios" rows="3" aria-describedby="scenarios-hint" required>${labInput.scenarios.join(', ')}</textarea><small id="scenarios-hint">1–100 values, separated by commas. Every value must be within capacity.</small></div><div class="form-field full"><label for="probabilities">Probabilities (optional)</label><input id="probabilities" value="${labInput.probabilities.join(', ')}" placeholder="Leave blank for equal probabilities" aria-describedby="probabilities-hint"><small id="probabilities-hint">One nonnegative probability per scenario; sum must equal 1.</small></div></div><div id="lab-error" class="notice error" role="alert" hidden></div><button class="button wide" type="submit">Calculate optimal offer <span data-icon="arrow"></span></button></form></section><section class="panel section-space"><div class="panel-header"><div><h2>Saved scenarios</h2><p>Stored in this browser only</p></div><button class="text-link" id="import-scenario" type="button">Import JSON</button></div><input type="file" id="scenario-file" accept="application/json,.json" hidden><div id="saved-list">${savedHtml()}</div></section></div><div class="lab-results"><section class="panel" id="lab-output" aria-live="polite">${labOutput()}</section><section class="panel prose"><h2>Why this is the optimal offer</h2><p>For a given offer, a surplus earns the down-regulation price and a shortfall pays the up-regulation price. Under the stated ordering, expected revenue is concave and piecewise linear.</p><div class="formula">R(b, p) = Δt × [DA × b + down × max(p − b, 0)<br>                        − up × max(b − p, 0)]</div><p>The weighted empirical quantile at <strong>q = (DA − down) / (up − down)</strong> gives an optimum. Ties can produce more than one equally good offer. The line chart evaluates every scenario breakpoint and both capacity bounds.</p><button class="text-link" id="verify-python" type="button">${pythonAvailable?'Cross-check with Python / SciPy':'How to enable the Python cross-check'} <span data-icon="arrow"></span></button><div id="python-result" class="api-result" role="status" hidden></div></section></div></div>`;
  }
  function labOutput() {
    if(!currentLab) currentLab=E.optimize(labInput);
    const r=currentLab,n=labInput.scenarios.length, uplift=r.expected-r.meanOfferRevenue;
    const curve=r.curve;
    return `<div class="panel-header"><div><h2>Calculated offer</h2><p>Browser engine · weighted empirical quantile</p></div><span id="lab-result-state" class="badge good">CALCULATED LOCALLY</span></div><div id="lab-stale" class="notice" role="status" hidden>Inputs changed. The figures below are the last calculated result; recalculate before saving or exporting. Your draft is retained while navigating this workspace.</div><div class="result-hero"><div><div class="eyebrow">OPTIMAL DAY-AHEAD OFFER</div><div class="result-value" id="optimal-offer">${num(r.offer,2)} <small>MW</small></div></div><div class="result-side"><span>Expected scenario revenue</span><strong id="expected-revenue">${num(r.expected,2)} DKK</strong><span>per ${num(labInput.hours,2)}-hour interval</span></div></div><div class="metric-triple"><div><small>Decision quantile</small><strong>${num(r.quantile*100,1)}%</strong></div><div><small>Expected production</small><strong>${num(r.mean,2)} MW</strong></div><div><small>Value vs mean offer</small><strong>+${num(Math.max(0,uplift),2)} DKK</strong></div></div><div class="table-wrap"><table id="scenario-comparison"><caption>Scenario offer comparison · expected revenue per interval</caption><thead><tr><th scope="col">Offer rule</th><th scope="col">Offer (MW)</th><th scope="col">Expected revenue (DKK)</th></tr></thead><tbody><tr><th scope="row">Optimal offer</th><td>${num(r.offer,2)}</td><td>${num(r.expected,2)}</td></tr><tr><th scope="row">Expected production offer</th><td>${num(r.mean,2)}</td><td>${num(r.meanOfferRevenue,2)}</td></tr></tbody></table></div><div class="legend"><span><i class="offer"></i>Expected revenue by offer</span></div><div id="offer-plot">${offerCurve(curve,r.offer)}</div><p class="chart-summary">${n} scenarios · ${num(labInput.capacity,1)} MW physical limit · prices in DKK/MWh. This is not a trade instruction.</p><div class="button-row"><button class="button secondary small" id="save-scenario" type="button">Save scenario</button><button class="button secondary small" id="export-scenario" type="button"><span data-icon="download"></span>Export JSON</button><button class="button secondary small" id="export-curve" type="button">Export curve CSV</button></div>`;
  }
  /** @param {import('./engine.js').CurvePoint[]} curve @param {number} offer @param {number} [width] */
  function offerCurve(curve,offer,width=720) {
    const compactLayout=Number.isFinite(width) && width<600;
    const w=compactLayout?Math.max(160,width):720,h=210,p=compactLayout?{l:70,r:18,t:24,b:40}:{l:62,r:18,t:15,b:38},xs=labInput.capacity;
    const ys=curve.map(p=>p.revenue),lo=Math.min(...ys,0),hi=Math.max(...ys,0)+1;
    const x=(/** @type {number} */ v)=>p.l+v/xs*(w-p.l-p.r),y=(/** @type {number} */ v)=>p.t+(hi-v)/(hi-lo)*(h-p.t-p.b);
    let svg=`<svg class="chart${compactLayout?' chart-compact':''}" viewBox="0 0 ${w} ${h}" role="img" aria-label="Expected scenario revenue in DKK versus offer in MW; optimal offer ${num(offer,2)} MW"><title>Expected revenue versus offer; optimal offer ${num(offer,2)} MW</title>`;
    for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;svg+=`<line class="grid-line" x1="${p.l}" x2="${w-p.r}" y1="${y(v)}" y2="${y(v)}"/><text x="${p.l-8}" y="${y(v)+3}" text-anchor="end">${esc(chartValue(v,compactLayout))}</text>`;if(!compactLayout || i===0 || i===4 || (w>=280 && i===2)){const anchor=compactLayout?(i===0?'start':i===4?'end':'middle'):'middle';svg+=`<text x="${x(xs*i/4)}" y="${h-14}" text-anchor="${anchor}">${num(xs*i/4,1)}</text>`;}}
    const d=curve.map((p,i)=>(i?'L':'M')+x(p.offer).toFixed(2)+','+y(p.revenue).toFixed(2)).join(' ');
    svg+=`<path class="line-b" d="${d}"/><line x1="${x(offer)}" x2="${x(offer)}" y1="${p.t}" y2="${h-p.b}" stroke="var(--gold)" stroke-dasharray="4 5"/><text x="${p.l}" y="${compactLayout?12:10}">DKK</text><text x="${w-p.r}" y="${h-1}" text-anchor="end">Offer (MW)</text></svg>`;return svg;
  }
  function resizeCharts() {
    /** @param {string} id @param {(width:number)=>string} draw */
    const redraw=(id,draw)=>{
      const plot=findElement(id);if(!plot || !plot.isConnected || plot.clientWidth<=0)return;
      const width=Math.max(160,Math.floor(plot.clientWidth));
      if(plot.dataset.chartWidth===String(width))return;
      const detail=plot.querySelector('details'),wasOpen=detail?.open,wasFocused=detail?.contains(document.activeElement);
      plot.dataset.chartWidth=String(width);renderView(plot, draw(width));
      const replacement=plot.querySelector('details');
      if(replacement && wasOpen)replacement.open=true;
      if(wasFocused)replacement?.querySelector('summary')?.focus({preventScroll:true});
    };
    redraw('overview-plot',width=>powerPlot(selectedModel(),indices(),width));
    const result=currentLab;
    if(result)redraw('offer-plot',width=>offerCurve(result.curve,result.offer,width));
  }
  function savedHtml() {return saved.length?saved.map((s,i)=>`<div class="saved-item"><div><strong>${esc(s.name)}</strong><small>${num(s.input.capacity,1)} MW capacity · ${s.input.scenarios.length} scenarios</small></div><div><button class="text-link" data-load-saved="${i}" type="button">Load</button> <button class="text-link" data-delete-saved="${i}" type="button" aria-label="Delete ${esc(s.name)}">×</button></div></div>`).join(''):'<div class="empty"><strong>Your experiments belong here.</strong>Calculate an offer, then save the assumptions for another comparison.</div>';}
  function methodPage() {
    return `<div class="notice"><strong>Research, not a live trading system.</strong> This release presents the supplied synthetic experiments and a local optimisation sandbox. It does not fetch current prices, retrain on filter changes, authenticate traders or submit orders. Public deployment and real-market validation remain outside the verified scope.</div><div class="method-grid"><section class="panel prose"><h2>What is connected to what?</h2><div class="flow"><div>Supplied CSV observations</div><span>→</span><div>Validated snapshot</div><span>→</span><div>Browser calculations</div></div><p>The dashboard contains ${num(D.quality.rows,0)} retained test observations for <strong>${esc(D.farm_name)}</strong>, covering ${dateLabel(at(D.timestamps,0))} to ${dateLabel(last(D.timestamps))}. All values use UTC, one-hour intervals and DKK. Four farms exist in the synthetic source metadata; only one has evaluated model outputs in this workspace.</p><h3>Metric definitions</h3><p><strong>Realised revenue</strong> is day-ahead offer revenue plus surplus receipts minus shortfall costs. <strong>Capture</strong> divides realised revenue by the perfect-foresight benchmark. Capture is undefined when that denominator is not positive; it is never shown as an invented percentage.</p><div class="formula">Revenue = DA × offer + down × surplus − up × shortfall<br>Capture = 100 × Σ revenue / Σ (DA × actual output)<br>Offer MAE = mean(|actual output − offer|)<br>Imbalance MWh = Σ |actual output − offer| × interval hours</div><p><strong>Perfect foresight</strong> assumes actual output is known before offering. It is an analytical reference under the repository's price ordering, not a forecast achievable in operation. Offer RMSE is not the same quantity as wind-forecast RMSE.</p><h3>Temporal scope and exclusions</h3><p>The original pipeline removed ${D.quality.source_negative_price_rows_removed} negative-price hours from its full generated market table. ${D.quality.excluded_hours_between_endpoints} hours are absent between the first and last test observations. The UI does not fill those missing observations with zero. Daily charts use means of available hours; revenue charts use cumulative sums of included hourly values.</p><h3>Model and information limitations</h3><p>Models were trained in the supplied research run, with chronological train/validation/test separation. The weather fields are synthetic forecast-time proxies. Operational forecast issuance, gate-closure availability of lagged features, current market rules, transaction costs and live settlement data have not been independently validated here. No live profitability claim is warranted.</p><h3>Scenario lab</h3><p>The lab is independent of the saved backtest. Its production distribution and prices are your assumptions. The browser evaluates the weighted empirical quantile. When started through the optional Python launcher, a local SciPy linear program can cross-check the same objective. Local checks are not an external integration test.</p></section><div class="provenance-grid"><section class="panel"><div class="panel-header"><div><h2>Source provenance</h2><p>Artifacts from your uploaded repository</p></div><span class="badge good">TRACEABLE</span></div>${D.sources.map(s=>`<div class="context-row"><div><div class="source-path">${esc(s.path)}</div><small class="muted">SHA-256</small><div class="source-path">${s.sha256}</div></div></div>`).join('')}<p class="readout-caption">Source manifest says generated ${esc(D.source_generated_at)}. These are historical synthetic observations, not a current market feed.</p><button class="button secondary small" id="export-provenance" type="button">Export provenance JSON</button></section><section class="panel"><h2>Verified snapshot integrity</h2><div class="context-row"><span>Unique, ordered timestamps</span><strong>Validated</strong></div><div class="context-row"><span>Phase 2 / 3 row alignment</span><strong>Exact</strong></div><div class="context-row"><span>Revenue values recalculated</span><strong>${num(D.quality.revenue_values_checked,0)}</strong></div><div class="context-row"><span>Largest saved-value difference</span><strong>${D.quality.maximum_revenue_error_dkk.toExponential(2)} DKK</strong></div><div class="context-note">These are artifact checks, not a rerun of the original three-year model training. Test logs and limitations are included in <span class="mono">docs/champion/</span>.</div></section><section class="panel prose" id="python-setup"><h2>Run the Python cross-check</h2><p>The portable HTML runs without installation. For the optional local solver, extract the complete ZIP, install Python 3.11 or newer, then run:</p><div class="formula">python -m venv .venv-champion<br># Activate your environment, then:<br>python -m pip install -e .<br>python -m zephyrtrade.app</div><p>Windows users can run <strong>START_PYTHON_WINDOWS.bat</strong>. It creates a separate environment and installs the project. The service binds only to 127.0.0.1 and is intended for local research, not internet hosting.</p><h3>Privacy and persistence</h3><p>The app calculates with the bundled dataset in your browser. Saved scenario settings stay in this browser's local storage. Export JSON backups; clearing browser data removes local saves. The hosted site is delivered through Cloudflare and advertises a network-error reporting policy. That configuration alone does not establish that a report was sent. No credentials or live customer data are required.</p></section></div></div>`;
  }
  /** @param {Element|null} element @returns {FocusKey|null} */
  function contentFocusKey(element) {
    if(!element || !$('page-content').contains(element))return null;
    if(element.id)return {id:element.id};
    for(const attribute of ['data-chart','data-paginate','data-preset','data-load-saved']){
      if(element.hasAttribute(attribute))return {attribute,value:element.getAttribute(attribute)};
    }
    return null;
  }
  /** @param {FocusKey|null} key */
  function restoreContentFocus(key) {
    if(!key)return;
    const content=$('page-content');
    const target='id' in key?findElement(key.id):Array.from(content.querySelectorAll('['+key.attribute+']')).find(el=>el.getAttribute(key.attribute)===key.value);
    if(target instanceof HTMLElement && !('disabled' in target && target.disabled)){target.focus({preventScroll:true});return;}
    if('attribute' in key && key.attribute==='data-paginate'){
      const neighbor=content.querySelector('[data-paginate]:not([disabled])');
      if(neighbor instanceof HTMLElement){neighbor.focus({preventScroll:true});return;}
    }
    $('workspace').focus({preventScroll:true});
  }
  /** @param {number[]} ids */
  function updateSearchStatus(ids) {
    const count=state.page==='data'?matchingIds(ids).length:0;
    $('data-search-status').textContent=state.page==='data'?(count?`${num(count,0)} matching record${count===1?'':'s'}.`:'No matching records.'):'';
  }
  function render() {
    const focusKey=contentFocusKey(document.activeElement);
    const info=required(pageInfo[state.page], 'page definition');$('breadcrumb-title').textContent=info[0];$('page-eyebrow').textContent=info[1];$('page-title').textContent=info[2];$('page-subtitle').textContent=info[3];
    document.title=`${info[0]} · ZephyrTrade Champion`;
    document.querySelectorAll('nav a').forEach(a=>{if(a.getAttribute('data-page')===state.page)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
    $('filterbar').hidden=['lab','method'].includes(state.page);$('heading-tag').hidden=state.page!=='overview';
    controlElement('model-select').value=state.model;
    document.querySelectorAll('[data-period]').forEach(b=>b.setAttribute('aria-pressed',String(b.getAttribute('data-period')===state.period)));
    $('date-fields').hidden=state.period!=='custom';
    const ids=indices();
    $('period-label').textContent=ids.length?`${dateLabel(at(D.timestamps,at(ids,0)))} — ${dateLabel(at(D.timestamps,last(ids)))} · UTC`:'No records in this period';
    if(!ids.length && !['lab','method'].includes(state.page)) renderView($('page-content'), '<div class="empty"><strong>No records in this period.</strong>Choose All data or a date within the supplied test set.</div>');
    else renderView($('page-content'), state.page==='overview'?overview(ids):state.page==='models'?modelsPage(ids):state.page==='data'?dataPageHtml(ids):state.page==='lab'?labPage():methodPage());
    if(state.page==='lab'&&labDraft){for(const [key,value] of Object.entries(labDraft))controlElement(key).value=value;markLabDirty();}
    renderIcons();resizeCharts();persistView();updateSearchStatus(ids);restoreContentFocus(focusKey);
  }
  /** @param {string} page @param {boolean} [focus] */
  function go(page,focus=true) {if(!pageInfo[page])page='overview';state.page=page;dataPage=0;render();if(focus){$('workspace').focus();window.scrollTo({top:0,behavior:'instant'});}}
  /** @param {string} name @param {BlobPart} content @param {string} [type] */
  function download(name,content,type='text/plain;charset=utf-8') {
    const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);notify('Export prepared. Check your browser downloads.');
  }
  /** @param {string} name @param {string[]} header @param {unknown[][]} rows */
  function csvDownload(name,header,rows){download(name,'\uFEFF'+[header,...rows].map(row=>row.map(E.csvCell).join(',')).join('\r\n'),'text/csv;charset=utf-8');}
  function exportData(filtered=false) {
    let ids=indices();if(filtered)ids=matchingIds(ids);
    if(!ids.length){notify('No rows match this selection.');return;}
    const m=selectedModel();
    csvDownload(`ZephyrTrade-${m.id}-${at(D.timestamps,at(ids,0)).slice(0,10)}.csv`,['data_kind','strategy','farm_id','timestamp_utc','interval_hours','capacity_mw','actual_mw','offer_mw','day_ahead_dkk_mwh','up_dkk_mwh','down_dkk_mwh','revenue_dkk'],ids.map(i=>['synthetic_research',m.id,D.farm_id,at(D.timestamps,i),1,D.capacity_mw,at(D.actual,i),at(m.offers,i),at(D.day_ahead,i),at(D.up,i),at(D.down,i),E.revenue(at(m.offers,i),at(D.actual,i),at(D.day_ahead,i),at(D.up,i),at(D.down,i))]));
  }
  function exportModels(){const ids=indices();if(!ids.length){notify('No rows in this period.');return;}csvDownload('ZephyrTrade-model-comparison.csv',['data_kind','start_utc','end_utc','hours','strategy','revenue_dkk','capture_pct','regret_dkk','offer_rmse_mw','offer_mae_mw','absolute_imbalance_mwh'],rankings(ids).map(x=>['synthetic_research',at(D.timestamps,at(ids,0)),at(D.timestamps,last(ids)),ids.length,x.model.id,x.score.total,x.score.capture,x.score.regret,x.score.rmse,x.score.mae,x.score.imbalance]));}
  function readLabForm() {
    /** @type {Record<string,unknown>} */
    const obj={};for(const key of ['capacity','da','up','down','hours']){const el=inputElement(key);el.classList.remove('input-error');if(!el.checkValidity()){el.classList.add('input-error');el.focus();throw new Error(`Check ${el.previousElementSibling?.textContent||key}: enter a valid value within the shown limits.`);}obj[key]=Number(el.value);}
    obj.scenarios=E.parseNumbers(controlElement('scenarios').value);obj.probabilities=E.parseNumbers(controlElement('probabilities').value);return validateInput(obj);
  }
  /** @param {unknown} obj @returns {LabInput} */
  function validateInput(obj) {
    if(!isRecord(obj))throw new Error('Scenario input must be an object.');
    /** @type {LabInput} */
    const input={capacity:E.finite(obj.capacity,'capacity'),da:E.finite(obj.da,'da'),up:E.finite(obj.up,'up'),down:E.finite(obj.down,'down'),hours:E.finite(obj.hours,'hours'),scenarios:[],probabilities:[]};
    if(input.capacity<.1||input.capacity>10000||input.hours<.25||input.hours>24)throw new Error('Capacity must be 0.1–10,000 MW and duration 0.25–24 hours.');
    for(const price of [input.da,input.up,input.down])if(price<-10000||price>100000)throw new Error('Prices must be between −10,000 and 100,000 DKK/MWh.');
    if(!Array.isArray(obj.scenarios)||!Array.isArray(obj.probabilities))throw new Error('Scenarios and probabilities must be arrays.');
    E.priceOrder(input.da,input.up,input.down);
    /** @type {unknown[]} */
    const scenarios=obj.scenarios;
    /** @type {unknown[]} */
    const probabilities=obj.probabilities;
    input.scenarios=scenarios.map(value=>E.finite(value,'Scenario'));
    input.probabilities=probabilities.map(value=>E.finite(value,'Probability'));
    E.optimize(input);return input;
  }
  /** Preserve the JSON snapshot semantics used for saves and cross-checks. @param {LabInput} input */
  function cloneLabInput(input) { return validateInput(JSON.parse(JSON.stringify(input))); }
  function calculateLab() {
    try {const input=readLabForm(),result=E.optimize(input);labInput=input;currentLab=result;labDraft=null;labVersion++;$('lab-error').hidden=true;renderView($('lab-output'), labOutput());renderIcons($('lab-output'));resizeCharts();buttonElement('verify-python').disabled=false;if(findElement('python-result'))$('python-result').hidden=true;notify('Optimal offer recalculated from your assumptions.');}
    catch(error){$('lab-error').textContent=errorMessage(error);$('lab-error').hidden=false;}
  }
  function markLabDirty() {
    if(!findElement('lab-stale'))return;
    $('lab-stale').hidden=false;$('lab-result-state').textContent='INPUTS CHANGED';
    for(const id of ['save-scenario','export-scenario','export-curve','verify-python'])buttonElement(id).disabled=true;
    if(findElement('python-result'))$('python-result').hidden=true;
  }
  function scenarioDocument(name='Exported scenario') {return {schema_version:1,application:'ZephyrTrade Champion',data_kind:'user_assumptions_not_live',name,input:labInput,calculated:{offer_mw:required(currentLab, 'calculated result').offer,expected_revenue_dkk:required(currentLab, 'calculated result').expected,critical_quantile:required(currentLab, 'calculated result').quantile}};}
  function requireFreshLab() {
    try {const input=readLabForm();if(JSON.stringify(input)!==JSON.stringify(labInput)){notify('Recalculate your edited inputs before saving or exporting.');return false;}return true;}catch(error){$('lab-error').textContent=errorMessage(error);$('lab-error').hidden=false;return false;}
  }
  /** @param {unknown} input */
  function loadScenario(input) {
    const nextInput=validateInput(input),nextResult=E.optimize(nextInput);
    // Commit only after validation and calculation succeed; rejected imports retain the draft.
    labInput=nextInput;currentLab=nextResult;labDraft=null;labVersion++;
    render();notify('Scenario loaded and recalculated.');
  }
  async function pythonCheck() {
    if(!pythonAvailable){location.hash='method';setTimeout(()=>findElement('python-setup')?.scrollIntoView({block:'start'}),50);return;}
    if(!requireFreshLab())return;
    const epoch=labVersion,input=cloneLabInput(labInput),expected=required(currentLab, 'calculated result').expected;
    const output=$('python-result');output.hidden=false;output.textContent='Running the local SciPy linear program…';
    const button=buttonElement('verify-python');button.disabled=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),5000);
    try {const response=await fetch('/api/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(input),signal:controller.signal});const result=await response.json();if(!response.ok)throw new Error(result.error||'Local solver request failed.');if(epoch!==labVersion||state.page!=='lab')return;
      E.verifyLPResult(result,expected,input.capacity);
      output.textContent=`Cross-check passed: Python LP offer ${num(result.offer_mw,4)} MW; expected revenue ${num(result.expected_revenue_dkk,4)} DKK. Objective agrees within 0.000001 DKK. Equal-value ties can give different offers.`;
    }catch(error){if(epoch===labVersion&&state.page==='lab')output.textContent=error instanceof Error && error.name==='AbortError'?'The local solver timed out. Your inputs are retained; retry when it is available.':errorMessage(error);}finally{clearTimeout(timeout);if(button.isConnected)button.disabled=false;}
  }
  function toggleTheme(){const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=theme;$('theme-label').textContent=`Switch to ${theme==='dark'?'light':'dark'} theme`;try{localStorage.setItem('zephyr-theme',theme);}catch{/* Optional theme storage can be unavailable; retain the in-memory theme. */} }
  function init() {
    if(!D||!E||D.schema_version!==1||!D.timestamps.length)throw new Error('The bundled dataset or calculation engine is missing. Re-extract the complete app or use the standalone HTML.');
    state.from=at(D.timestamps,0).slice(0,10);state.to=last(D.timestamps).slice(0,10);
    try {restoreView(JSON.parse(localStorage.getItem('zephyr-view-v1')||'null'));}
    catch{/* An unreadable view preference does not affect observations. */}
    try {const t=localStorage.getItem('zephyr-theme');if(t !== null && ['light','dark'].includes(t))document.documentElement.dataset.theme=t;}
    catch{/* Optional theme storage can be unavailable; retain the in-memory theme. */}
    $('theme-label').textContent=`Switch to ${document.documentElement.dataset.theme==='dark'?'light':'dark'} theme`;
    try {const raw=JSON.parse(localStorage.getItem('zephyr-scenarios-v1')||'[]');if(!Array.isArray(raw)||raw.length>20)throw new Error('Invalid saved data');saved=raw.map(x=>({name:String(x.name).slice(0,80),input:validateInput(x.input)}));}
    catch{saved=[];notify('Browser scenario storage is unavailable or unreadable. Use JSON export; no stored data has been changed.');}
    required(document.querySelector('.site-card strong'), 'site name').textContent=D.farm_name;
    required(document.querySelector('.site-card p'), 'site description').textContent=`${num(D.capacity_mw,0)} MW · synthetic ${D.market_area} case`;
    renderView(document.querySelector('#heading-tag strong'), esc(num(D.capacity_mw,0))+' <small>MW</small>');
    renderView(controlElement('model-select'), D.models.map(m=>`<option value="${m.id}">${esc(m.name)}</option>`).join(''));
    inputElement('from-date').value=state.from;inputElement('to-date').value=state.to;
    ['from-date','to-date'].forEach(id=>{inputElement(id).min=at(D.timestamps,0).slice(0,10);inputElement(id).max=last(D.timestamps).slice(0,10);});
    currentLab=E.optimize(labInput);go(location.hash.slice(1)||'overview',false);
    window.addEventListener('hashchange',()=>go(location.hash.slice(1)));
    required(document.querySelector('.skip-link'), 'skip link').addEventListener('click',event=>{event.preventDefault();$('workspace').focus();});
    let chartResizeFrame=0;
    const scheduleCharts=()=>{if(!chartResizeFrame)chartResizeFrame=requestAnimationFrame(()=>{chartResizeFrame=0;resizeCharts();});};
    window.addEventListener('resize',scheduleCharts);
    if(typeof ResizeObserver==='function')new ResizeObserver(scheduleCharts).observe($('page-content'));
    controlElement('model-select').addEventListener('change',()=>{state.model=controlElement('model-select').value;dataPage=0;render();});
    $('theme-toggle').addEventListener('click',toggleTheme);
    $('theme-top').addEventListener('click',toggleTheme);
    $('help-button').addEventListener('click',()=>dialogElement('guide-dialog').showModal());
    $('export-top').addEventListener('click',()=>exportData());
    document.addEventListener('click',event=>{
      if(!(event.target instanceof Element))return;
      const btn=event.target.closest('button');if(!btn)return;
      if(btn.dataset.closeDialog){dialogElement(btn.dataset.closeDialog).close();return;}
      if(btn.dataset.go){location.hash=btn.dataset.go;return;}
      if(btn.dataset.period){if(btn.dataset.period==='custom'){const from=inputElement('from-date').value,to=inputElement('to-date').value;if(!validCustomRange(from,to)){$('filter-error').textContent='Choose valid dates within the supplied test set, with the start on or before the end.';$('filter-error').hidden=false;return;}state.period='custom';state.from=from;state.to=to;}else state.period=btn.dataset.period;dataPage=0;$('filter-error').hidden=true;render();return;}
      if(btn.id==='apply-dates'){const from=inputElement('from-date').value,to=inputElement('to-date').value;if(!validCustomRange(from,to)){$('filter-error').textContent='Choose valid dates within the supplied test set, with the start on or before the end.';$('filter-error').hidden=false;return;}state.from=from;state.to=to;state.period='custom';dataPage=0;$('filter-error').hidden=true;render();return;}
      if(btn.dataset.chart){chartMode=btn.dataset.chart;render();return;}
      if(btn.dataset.selectModel){state.model=btn.dataset.selectModel;location.hash='overview';return;}
      if(btn.dataset.paginate){dataPage+=Number(btn.dataset.paginate);render();return;}
      if(btn.id==='export-models'){exportModels();return;}
      if(btn.id==='export-filtered'){exportData(true);return;}
      if(btn.dataset.preset){
        /** @type {Record<string,Pick<LabInput,'da'|'up'|'down'>>} */
        const presets={balanced:{da:450,up:600,down:300},shortfall:{da:450,up:900,down:300},surplus:{da:450,up:600,down:50}};loadScenario({...labInput,...presets[btn.dataset.preset]});return;}
      if(btn.id==='save-scenario'){if(!requireFreshLab())return;if(saved.length>=20){notify('The local notebook holds 20 scenarios. Export and remove one before saving another.');return;}inputElement('scenario-name').value='';dialogElement('save-dialog').showModal();return;}
      if(btn.id==='export-scenario'){if(requireFreshLab())download('ZephyrTrade-scenario.json',JSON.stringify(scenarioDocument(),null,2),'application/json');return;}
      if(btn.id==='export-curve'){if(requireFreshLab())csvDownload('ZephyrTrade-revenue-curve.csv',['data_kind','offer_mw','expected_revenue_dkk','interval_hours'],required(currentLab, 'calculated result').curve.map(p=>['user_assumptions',p.offer,p.revenue,labInput.hours]));return;}
      if(btn.id==='import-scenario'){inputElement('scenario-file').click();return;}
      if(btn.dataset.loadSaved!=null){loadScenario(at(saved,Number(btn.dataset.loadSaved)).input);return;}
      if(btn.dataset.deleteSaved!=null){const i=Number(btn.dataset.deleteSaved);if(!window.confirm(`Delete “${at(saved,i).name}” from this browser? Export a JSON backup first if needed.`))return;const next=saved.filter((_,j)=>j!==i);try{localStorage.setItem('zephyr-scenarios-v1',JSON.stringify(next));saved=next;renderView($('saved-list'), savedHtml());const remaining=$('saved-list').querySelectorAll('[data-delete-saved]');const focus=remaining[Math.min(i,remaining.length-1)]||buttonElement('save-scenario');if(focus instanceof HTMLElement)focus.focus();notify('Scenario deleted from this browser.');}catch{notify('Deletion failed. Your saved scenario has been retained.');}return;}
      if(btn.id==='verify-python'){pythonCheck();return;}
      if(btn.id==='export-provenance'){download('ZephyrTrade-provenance.json',JSON.stringify({data_kind:D.data_kind,source_generated_at:D.source_generated_at,quality:D.quality,sources:D.sources},null,2),'application/json');}
    });
    document.addEventListener('submit',event=>{
      if(!(event.target instanceof HTMLFormElement))return;
      if(event.target.id==='lab-form'){event.preventDefault();calculateLab();}
      if(event.target.id==='save-form'){event.preventDefault();const name=inputElement('scenario-name').value.trim();if(!name){inputElement('scenario-name').setCustomValidity('Enter a scenario name.');inputElement('scenario-name').reportValidity();return;}const next=[...saved,{name,input:cloneLabInput(labInput)}];try{localStorage.setItem('zephyr-scenarios-v1',JSON.stringify(next));saved=next;dialogElement('save-dialog').close();renderView($('saved-list'), savedHtml());notify('Scenario saved in this browser. Export JSON for a backup.');}catch{notify('Could not save: browser storage is unavailable or full. Use Export JSON instead.');}}
    });
    document.addEventListener('input',event=>{
      const target=event.target;
      if(!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement))return;
      if(target.closest('#lab-form')){labDraft={};for(const key of ['capacity','da','up','down','hours','scenarios','probabilities'])labDraft[key]=controlElement(key).value;labVersion++;markLabDirty();}
      if(target.id==='scenario-name')target.setCustomValidity('');
      if(target.id==='data-search' && target instanceof HTMLInputElement){dataSearch=target.value;dataPage=0;const focus=target.selectionStart;render();const field=inputElement('data-search');field.focus();if(focus!=null)field.setSelectionRange(focus,focus);}
    });
    document.addEventListener('change',async event=>{
      const target=event.target;
      if(!(target instanceof HTMLInputElement) || target.id!=='scenario-file')return;
      const file=target.files?.[0];if(!file)return;
      try{
        if(file.size>32768)throw new Error('Scenario JSON must be smaller than 32 KB.');
        /** @type {unknown} */
        const parsed=JSON.parse(await file.text());
        if(!isRecord(parsed) || parsed.schema_version!==1)throw new Error('Unsupported scenario schema; expected version 1.');
        loadScenario(parsed.input);
      }catch(error){notify('Import failed: '+errorMessage(error));}finally{if(findElement('scenario-file'))inputElement('scenario-file').value='';}
    });
    if(location.protocol==='http:'&&['127.0.0.1','localhost'].includes(location.hostname)){
      const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),2000);
      fetch('/api/health',{signal:controller.signal}).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(result=>{if(result.service==='zephyrtrade-local'){pythonAvailable=true;$('engine-status').textContent='Browser + Python / SciPy · loopback only';if(state.page==='lab'){renderView(buttonElement('verify-python'), 'Cross-check with Python / SciPy '+icon('arrow'));}}}).catch(()=>{}).finally(()=>clearTimeout(timeout));
    }
  }
  try { init(); } catch(error) { $('fatal-error').textContent=errorMessage(error);$('fatal-error').hidden=false;console.error('ZephyrTrade startup failed:',errorMessage(error)); }
  // Read-only testing and diagnostic contract; no privileged capabilities.
  window.ZephyrApp = {getState:()=>({...state}),getLab:()=>({input:cloneLabInput(labInput),result:currentLab}),getVisibleMetrics:()=>metrics(selectedModel(),indices())};
})();
