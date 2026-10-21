/** Optional, licensed, SAME-ORIGIN font URLs supplied by the integrating site.
 * No font binaries are distributed with this project. Local installed fonts work too.
 * Example after you provision your own files: inter: './public/fonts/inter.woff2'
 */
export const FONT_ASSETS = Object.freeze({ inter: null, mono: null });
export async function loadFonts() {
  const errors=[];
  for(const [key,family] of [['inter','Inter'],['mono','JetBrains Mono']]) {
    if(!FONT_ASSETS[key])continue;
    try {
      const url=new URL(FONT_ASSETS[key],document.baseURI);
      if(url.origin!==location.origin)throw new Error('Font URLs must be same-origin.');
      const face=await new FontFace(family,`url("${url.href}")`,{weight:'100 900',display:'block'}).load();
      document.fonts.add(face);
    }catch(e){errors.push(`${family}: ${e.message}`);}
  }
  await document.fonts.ready;
  const available=family=>{
    const canvas=document.createElement('canvas'),c=canvas.getContext('2d');
    const str='WQim 1234567890 .,/{}';
    c.font='72px monospace';const baseline=c.measureText(str).width;
    c.font=`72px "${family}", monospace`;return Math.abs(c.measureText(str).width-baseline)>.01;
  };
  return { inter:available('Inter'), sfPro:available('SF Pro Display'), jetbrainsMono:available('JetBrains Mono'),
    fallbackSans:'Arial / system sans-serif',fallbackMono:'Liberation Mono / system monospace',errors };
}
