(() => {
  'use strict';
  function init() {
    const root = document.querySelector('.ganc-dashboard');
    if (!root || root.dataset.followupReady) return;
    root.dataset.followupReady = 'true';
    const appliedCaption = filterCaption();
    root.querySelectorAll('.followup-toggle').forEach(button => {
      const details = document.getElementById(button.dataset.details);
      if (!details) return;
      button.addEventListener('click', () => {
        details.open = !details.open;
        if (details.open) details.scrollIntoView({block:'nearest',behavior:'smooth'});
      });
      details.addEventListener('toggle', () => {
        button.setAttribute('aria-expanded', String(details.open));
        button.querySelector('span').textContent = details.open ? 'Hide women ↑' : 'View women ↓';
      });
    });
    root.querySelectorAll('.women-search').forEach(input => {
      const details = input.closest('details');
      const rows = [...details.querySelectorAll('[data-woman-row]')];
      const update = () => {
        const q = input.value.trim().toLocaleLowerCase();
        let count = 0;
        rows.forEach(row => { row.hidden = !row.textContent.toLocaleLowerCase().includes(q); if (!row.hidden) count++; });
        details.querySelector('.women-match-count').textContent = `${count} of ${rows.length} women`;
        details.querySelector('.women-no-match').hidden = count !== 0;
      };
      input.addEventListener('input',update); update();
    });
    root.querySelectorAll('.ganc-chart-wrap svg').forEach(svg => {
      const title = svg.closest('.ganc-section')?.querySelector('h2')?.textContent.trim() || svg.getAttribute('aria-label') || 'Dashboard chart';
      const toolbar = document.createElement('div'); toolbar.className = 'chart-toolbar';
      const message = document.createElement('span'); message.className='chart-export-message'; message.setAttribute('role','status');
      ['PNG','SVG'].forEach(format => {
        const button=document.createElement('button'); button.type='button'; button.className='chart-save';
        button.textContent=`Save ${format}`; button.setAttribute('aria-label',`Save ${title} as ${format}`);
        button.addEventListener('click',async () => {
          button.disabled=true; message.textContent='Preparing chart…';
          try { await exportChart(svg,title,format,appliedCaption); message.textContent=`${format} download ready`; }
          catch(error) { message.textContent=error.message || 'Unable to save this chart. Try again.'; }
          finally { button.disabled=false; }
        }); toolbar.appendChild(button);
      });
      toolbar.appendChild(message); svg.parentNode.insertBefore(toolbar,svg);
    });
  }
  function filterCaption() {
    return [...document.querySelectorAll('.ganc-filter-panel select')].map(select => {
      const label=document.querySelector(`label[for="${select.id}"]`)?.textContent.trim() || select.name;
      const values=[...select.selectedOptions].filter(o=>o.value).map(o=>o.textContent.trim());
      return values.length ? `${label}: ${values.join(', ')}` : '';
    }).filter(Boolean).join(' · ') || 'All available cohorts and locations';
  }
  function wrapText(text, max) {
    const lines=[]; let line='';
    for (const word of text.split(/\s+/)) {
      if ((line+' '+word).length>max && line) {lines.push(line);line='';}
      line += (line?' ':'')+word;
    }
    if(line) lines.push(line); return lines;
  }
  function svgExport(svg,title,caption) {
    if (!svg.querySelector('rect,path,line,circle,text,polyline,polygon')) throw new Error('Chart is not ready yet. Wait for it to load and try again.');
    const box=svg.getBoundingClientRect();
    const vb=svg.viewBox.baseVal;
    const sourceW=vb.width || box.width, sourceH=vb.height || box.height;
    if (!sourceW || !sourceH) throw new Error('Chart has no visible size. Reload the dashboard and try again.');
    const clone=svg.cloneNode(true);
    const originals=[svg,...svg.querySelectorAll('*')], copies=[clone,...clone.querySelectorAll('*')];
    const properties=['fill','stroke','stroke-width','stroke-dasharray','opacity','fill-opacity','stroke-opacity','font-family','font-size','font-weight','text-anchor','dominant-baseline','visibility'];
    originals.forEach((node,i) => {
      const computed=getComputedStyle(node);
      properties.forEach(p=>copies[i].style.setProperty(p,computed.getPropertyValue(p)));
    });
    const ns='http://www.w3.org/2000/svg', width=1400, margin=40;
    const titleLines=wrapText(title,85), captionLines=wrapText(caption,130);
    const header=42+titleLines.length*32+captionLines.length*22+35;
    const chartH=(width-2*margin)*sourceH/sourceW, height=Math.ceil(header+chartH+50);
    const outer=document.createElementNS(ns,'svg'); outer.setAttribute('width',width);outer.setAttribute('height',height);outer.setAttribute('viewBox',`0 0 ${width} ${height}`);
    const bg=document.createElementNS(ns,'rect');bg.setAttribute('width','100%');bg.setAttribute('height','100%');bg.setAttribute('fill','#ffffff');outer.appendChild(bg);
    const addText=(text,y,size,color) => { const n=document.createElementNS(ns,'text');n.setAttribute('x',margin);n.setAttribute('y',y);n.setAttribute('font-family','Arial, sans-serif');n.setAttribute('font-size',size);n.setAttribute('fill',color);n.textContent=text;outer.appendChild(n); };
    let y=40;titleLines.forEach(l=>{addText(l,y,27,'#173b3b');y+=32;});
    captionLines.forEach(l=>{addText(l,y,15,'#52666a');y+=22;});
    addText(`GANC/PNC Dashboard · Exported ${new Date().toLocaleDateString()}`,y+4,14,'#52666a');
    clone.setAttribute('viewBox',svg.getAttribute('viewBox') || `0 0 ${sourceW} ${sourceH}`);
    clone.setAttribute('x',margin);clone.setAttribute('y',header);clone.setAttribute('width',width-2*margin);clone.setAttribute('height',chartH);
    clone.style.removeProperty('width');clone.style.removeProperty('height');clone.removeAttribute('id');outer.appendChild(clone);
    return {text:new XMLSerializer().serializeToString(outer),width,height};
  }
  function download(blob,name) {
    const url=URL.createObjectURL(blob), a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
  }
  async function exportChart(svg,title,format,caption) {
    const data=svgExport(svg,title,caption), blob=new Blob([data.text],{type:'image/svg+xml;charset=utf-8'});
    const slug=(title.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'') || 'chart');
    const name=`ganc-pnc-${slug}-${new Date().toISOString().slice(0,10)}`;
    if(format==='SVG') {download(blob,name+'.svg');return;}
    const url=URL.createObjectURL(blob);
    try {
      const img=new Image();await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(new Error('Unable to render PNG. Please use Save SVG.'));img.src=url;});
      const canvas=document.createElement('canvas');canvas.width=data.width*2;canvas.height=data.height*2;
      const ctx=canvas.getContext('2d');ctx.scale(2,2);ctx.drawImage(img,0,0,data.width,data.height);
      const png=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
      if(!png)throw new Error('PNG export failed. Please use Save SVG.');download(png,name+'.png');
    } finally {URL.revokeObjectURL(url);}
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
