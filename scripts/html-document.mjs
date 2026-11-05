import {parse} from 'parse5';

/** @typedef {import('parse5').DefaultTreeAdapterTypes.Node} HtmlNode */
/** @typedef {import('parse5').DefaultTreeAdapterTypes.Element} HtmlElement */
const htmlNamespace='http://www.w3.org/1999/xhtml';
const svgNamespace='http://www.w3.org/2000/svg';
const xlinkNamespace='http://www.w3.org/1999/xlink';

/** @param {HtmlNode} node @returns {HtmlNode[]} */
function children(node){return 'childNodes' in node?node.childNodes:[];}

/** @param {HtmlNode} root @param {string} tag @param {string|null} [namespace] @returns {HtmlElement[]} */
function elements(root,tag,namespace=htmlNamespace){
  /** @type {HtmlElement[]} */
  const found=[];
  const pending=[root];
  while(pending.length){
    const node=pending.pop();
    if(!node)continue;
    if('tagName' in node&&(namespace===null||node.namespaceURI===namespace)&&node.tagName===tag)found.push(node);
    const descendants=children(node);
    for(let index=descendants.length-1;index>=0;index--){
      const child=descendants[index];
      if(child)pending.push(child);
    }
  }
  return found;
}

/** @param {HtmlElement} node @param {string} name */
function attribute(node,name){return node.attrs.find(item=>item.name===name&&!item.namespace)?.value;}

/** Modern SVG href takes precedence over its legacy namespaced alternative.
 * @param {HtmlElement} node @returns {string|undefined}
 */
function anchorHref(node){
  const href=attribute(node,'href');
  if(href!==undefined)return href;
  return node.namespaceURI===svgNamespace?node.attrs.find(item=>item.name==='href'&&item.namespace===xlinkNamespace)?.value:undefined;
}

/** @param {HtmlNode} node @returns {string} */
function textContent(node){return 'value' in node?node.value:children(node).map(textContent).join('');}

const textBreaks=new Set(['h1','h2','h3','h4','h5','h6','p','li','summary','figcaption','div','section','article']);

/** Render visible document content into plain text, never executable HTML.
 * @param {HtmlNode} node @returns {string}
 */
function visibleText(node){
  if('value' in node)return node.value;
  if(!('tagName' in node))return children(node).map(visibleText).join('');
  if(['script','style','template','noscript'].includes(node.tagName))return '';
  if(node.tagName==='br')return '\n';
  const body=children(node).map(visibleText).join('');
  const href=node.tagName==='a'?anchorHref(node):undefined;
  if(href!==undefined)return `${body} (${href}) `;
  return body+(textBreaks.has(node.tagName)?'\n':'');
}

/** Extract the one HTML document title and one visible main into the text guide.
 * @param {string} html @param {string} source @returns {string}
 */
export function extractStaticPageText(html,source){
  const document=parse(html);
  const head=elements(document,'head')[0];
  const titles=head?elements(head,'title'):[];
  if(titles.length!==1||!titles[0])throw Error('Expected one HTML document title');
  const title=textContent(titles[0]).trim();
  if(!title)throw Error('Expected a nonempty HTML document title');
  const mains=elements(document,'main').filter(node=>attribute(node,'id')==='main');
  if(mains.length!==1||!mains[0])throw Error('Expected one main content element');
  const visible=visibleText(mains[0]).replace(/[ \t\r\f\v]+/g,' ').replace(/ *\n */g,'\n').replace(/\n{3,}/g,'\n\n').trim();
  return `### ${title}\nSource: ${source}\n\n${visible}`;
}

/** Match actual document anchors by normalized origin and complete directory boundary.
 * @param {string} html @param {string} directoryUrl @param {string} baseUrl
 * @returns {boolean}
 */
export function hasAnchorUnder(html,directoryUrl,baseUrl){
  const directory=new URL(directoryUrl);
  if(!directory.pathname.endsWith('/'))throw new TypeError('Link directory must end with a slash');
  return elements(parse(html),'a',null).some(anchor=>{
    if(anchor.namespaceURI!==htmlNamespace&&anchor.namespaceURI!==svgNamespace)return false;
    const href=anchorHref(anchor);
    if(href===undefined)return false;
    try{
      const destination=new URL(href,baseUrl);
      return destination.origin===directory.origin&&destination.pathname.startsWith(directory.pathname);
    }catch{return false;}
  });
}
