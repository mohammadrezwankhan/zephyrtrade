/** Optional, licensed, SAME-ORIGIN font URLs supplied by the integrating site.
 * No font binaries are distributed with this project. Local installed fonts work too.
 * Example after you provision your own files: inter: './public/fonts/inter.woff2'
 */
/** @type {Readonly<Record<'inter'|'mono',string|null>>} */
export const FONT_ASSETS = Object.freeze({ inter: null, mono: null });
export async function loadFonts() {
  const errors=[];
  /** @type {['inter'|'mono',string][]} */
  const families=[['inter','Inter'],['mono','JetBrains Mono']];
  for(const [key,family] of families) {
    const source=FONT_ASSETS[key];
    if(!source)continue;
    try {
      const url=new URL(source,document.baseURI);
      if(url.origin!==location.origin)throw new Error('Font URLs must be same-origin.');
      const face=await new FontFace(family,`url("${url.href}")`,{weight:'100 900',display:'block'}).load();
      document.fonts.add(face);
    }catch(e){errors.push(`${family}: ${e instanceof Error ? e.message : String(e)}`);}
  }
  await document.fonts.ready;
  const available=(/** @type {string} */ family)=>{
    const canvas=document.createElement('canvas'),c=canvas.getContext('2d');
    if(!c) return false;
    const str='WQim 1234567890 .,/{}';
    c.font='72px monospace';const baseline=c.measureText(str).width;
    c.font=`72px "${family}", monospace`;return Math.abs(c.measureText(str).width-baseline)>.01;
  };
  return { inter:available('Inter'), sfPro:available('SF Pro Display'), jetbrainsMono:available('JetBrains Mono'),
    fallbackSans:'Arial / system sans-serif',fallbackMono:'Liberation Mono / system monospace',errors };
}
