export function createCompare(originalUrl, outputUrl){
  const wrap=document.createElement('div'); wrap.className='compare';
  wrap.innerHTML=`<img class="before" src="${originalUrl}" alt="Original"><img class="after" src="${outputUrl}" alt="Cleaned"><input type="range" min="0" max="100" value="50" aria-label="Compare original and cleaned">`;
  const range=wrap.querySelector('input'); range.addEventListener('input',()=>wrap.querySelector('.after').style.clipPath=`inset(0 0 0 ${range.value}%)`); return wrap;
}
