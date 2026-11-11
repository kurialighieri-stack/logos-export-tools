/* Ejecutar desde tu propia sesión iniciada en https://app.logos.com/.
 * Recupera el pasaje configurado de la lista explícita de recursos. No pide ni exporta credenciales.
 * La lista puede ampliarse con otros ResourceId de TU biblioteca.
 * El servicio interno puede cambiar; este cliente se comprobó el 10-11-2026.
 */
(async () => {
  if (location.origin !== 'https://app.logos.com') throw new Error('Abre app.logos.com e inicia sesión antes de ejecutar este archivo.');
  const reference = __REFERENCE_JSON__; // Referencia configurada al generar el archivo.
  const resources = __RESOURCES_JSON__;
  const enc = new TextEncoder();
  const entries = [];
  const report = [];
  const crcTable = Uint32Array.from({length:256}, (_,n) => {
    let c=n; for(let i=0;i<8;i++) c=(c&1)?0xedb88320^(c>>>1):c>>>1; return c>>>0;
  });
  function crc32(bytes) { let c=0xffffffff; for(const b of bytes)c=crcTable[(c^b)&255]^(c>>>8);return (c^0xffffffff)>>>0; }
  function header(size) {const bytes=new Uint8Array(size);return {bytes,view:new DataView(bytes.buffer)};}
  function zip(files) {
    const chunks=[], central=[];let offset=0;
    for(const f of files) {
      const name=enc.encode(f.name),data=enc.encode(f.text),crc=crc32(data);
      const local=header(30),v=local.view;
      v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);
      v.setUint32(14,crc,true);v.setUint32(18,data.length,true);v.setUint32(22,data.length,true);v.setUint16(26,name.length,true);
      chunks.push(local.bytes,name,data);
      const dir=header(46),d=dir.view;
      d.setUint32(0,0x02014b50,true);d.setUint16(4,20,true);d.setUint16(6,20,true);d.setUint16(8,0x800,true);
      d.setUint32(16,crc,true);d.setUint32(20,data.length,true);d.setUint32(24,data.length,true);d.setUint16(28,name.length,true);d.setUint32(42,offset,true);
      central.push(dir.bytes,name);offset+=30+name.length+data.length;
    }
    const centralLength=central.reduce((n,a)=>n+a.length,0),end=header(22),e=end.view;
    e.setUint32(0,0x06054b50,true);e.setUint16(8,files.length,true);e.setUint16(10,files.length,true);e.setUint32(12,centralLength,true);e.setUint32(16,offset,true);
    return new Blob([...chunks,...central,end.bytes],{type:'application/zip'});
  }
  for(const resource of resources) {
    const url=new URL('/api/app/preview',location.origin);
    url.searchParams.set('resourceId',resource.ResourceId);url.searchParams.set('reference',reference);
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),90000);
    let stop=false;
    try {
      const response=await fetch(url,{credentials:'same-origin',signal:controller.signal});
      if(!response.ok) {
        stop=[401,403,429].includes(response.status);
        throw new Error('HTTP '+response.status+(stop?' — se detiene el lote; revisa sesión/permisos o espera antes de repetir.':''));
      }
      const data=await response.json();
      if(!data.richText) {report.push({resourceId:resource.ResourceId,title:resource.Title,status:'sin contenido'}); await new Promise(resolve=>setTimeout(resolve,1000)); continue;}
      const xml=new DOMParser().parseFromString('<Root>'+data.richText+'</Root>','application/xml');
      if(xml.querySelector('parsererror'))throw new Error('XML de respuesta inválido.');
      const paragraphs=[...xml.querySelectorAll('Paragraph')].filter(p=>!p.parentElement?.closest('Paragraph'));
      const plain=p=>[p,...p.querySelectorAll('[Text]')].map(n=>n.getAttribute('Text')||'').join('');
      const text=paragraphs.map(plain).join('\n\n');
      if(!text.trim())throw new Error('La respuesta no contiene párrafos de texto.');
      const stem=resource.ResourceId.replace(/[^a-zA-Z0-9._-]/g,'_');
      entries.push({name:'json/'+stem+'.json',text:JSON.stringify({resource,...data})});
      entries.push({name:'txt/'+stem+'.txt',text});
      report.push({resourceId:resource.ResourceId,title:resource.Title,status:'ok',paragraphs:paragraphs.length,characters:text.length});
      console.info('Recuperado:',resource.Title,'('+text.length+' caracteres)');
    } catch(error) {
      report.push({resourceId:resource.ResourceId,title:resource.Title,status:'error',error:String(error.message||error)});
      console.error(resource.Title,error);
      if(error.name==='AbortError')stop=true;
    } finally {clearTimeout(timer);}
    if(stop)break;
    await new Promise(resolve=>setTimeout(resolve,1000));
  }
  entries.push({name:'manifest.json',text:JSON.stringify({reference,created:new Date().toISOString(),requested:resources.length,results:report},null,2)});
  const blob=zip(entries),downloadUrl=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=downloadUrl;link.download='Logos - extraccion.zip';link.textContent='Descargar extracción de Logos';
  link.style.cssText='position:fixed;bottom:20px;right:20px;padding:12px;background:white;color:black;border:2px solid black;z-index:2147483647';
  document.body.appendChild(link);link.click();setTimeout(()=>{URL.revokeObjectURL(downloadUrl);link.remove();},600000);
  console.table(report);
  return report;
})();
