'use strict';
const $=id=>document.getElementById(id);
const state={image:null,bitmap:null,job:null,solar:null,analysis:null,targets:[],position:null,busy:false,imageOffset:0,labelRects:[]};
let targetSequence=Number(sessionStorage.getItem('target-sequence')??0),imageVersion=0,observerTimer;
const clientId=sessionStorage.getItem('mount-client')??Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');sessionStorage.setItem('mount-client',clientId);
function notify(text){$('notice').textContent=text;$('notice').hidden=!text;}
async function api(path,options={}){const r=await fetch('/api/v1'+path,options);if(!r.ok){let body={};try{body=await r.json();}catch{}throw new Error(typeof body.detail==='string'?body.detail:`Request failed (${r.status}).`);}return r.json();}
function post(path,data){return api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
function run(fn){return async(...args)=>{try{await fn(...args);}catch(e){notify(e.message);}};}
function number(id){if($(id).value.trim()==='')throw new Error('Complete the numeric settings.');const n=Number($(id).value);if(!Number.isFinite(n))throw new Error('Use a valid number.');return n;}
function site(){return {target_id:$('target').value,latitude:number('latitude'),longitude:number('longitude'),elevation_m:number('elevation'),utc:new Date().toISOString()};}
function photoObservation(){if(!$('photo-time').value)return null;const time=new Date($('photo-time').value);if(!Number.isFinite(time.getTime()))throw new Error('Choose a valid image capture time.');return {...site(),utc:time.toISOString()};}
function showPosition(p){state.position=p;$('position').hidden=false;$('altitude').textContent=p.altitude_deg.toFixed(2)+'°';$('azimuth').textContent=p.azimuth_deg.toFixed(2)+'°';$('target-ra').textContent=p.ra_deg.toFixed(3)+'°';$('target-dec').textContent=p.dec_deg.toFixed(3)+'°';$('visibility').textContent=(p.visible?'Above':'Below')+' the horizon · '+new Date(p.utc).toLocaleTimeString();}
function mountText(m){$('mount-status').dataset.state=m.state;$('stop').disabled=m.state==='stopped';$('reset').disabled=m.state!=='stopped';$('mount-status').textContent=m.state==='moving'?'Moving':m.state==='stopped'?'Stopped':'Ready';$('mount-target').textContent=m.target?'Target: '+m.target.name:'Select a catalog target';$('mount-alt').textContent=m.pointing?m.pointing.altitude_deg.toFixed(2)+'°':'—';$('mount-az').textContent=m.pointing?m.pointing.azimuth_deg.toFixed(2)+'°':'—';}
async function selectTarget(){const sequence=++targetSequence;sessionStorage.setItem('target-sequence',sequence);const item=state.targets.find(t=>t.id===$('target').value);if(!item)return;
 $('target-type').textContent=item.category;$('education').textContent=item.description;$('magnitude').textContent=item.magnitude??'Varies';$('distance').textContent=item.distance;$('target-message').textContent='Calculating position…';const settings=site();
 try{const result=await post('/mount/goto',{...settings,client_id:clientId,sequence});if(sequence!==targetSequence)return;showPosition(result.position);mountText(result.mount);$('target-message').textContent='Position sent to simulator.';}
 catch(e){if(sequence!==targetSequence)return;$('target-message').textContent=e.message;try{const p=await post('/astronomy/position',settings);if(sequence===targetSequence)showPosition(p);}catch{}}}
function showPage(name) {
  const titles = {home: 'Your universe awaits', explore: 'Explore', workspace: 'Observation studio', learning: 'Sky & learning', library: 'Sessions & images', profile: 'Profile'};
  document.querySelectorAll('.page').forEach(page => { page.hidden = page.id !== name; });
  document.querySelectorAll('.nav').forEach(button => {
    const active = button.dataset.page === name;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  $('page-title').textContent = titles[name];
  $('page-title').focus();
  window.scrollTo(0, 0);
}
function setBusy(value){state.busy=value;$('analyze').disabled=value||!state.image;$('replace-image').disabled=value;$('choose-image').disabled=value;$('library-upload').disabled=value;}
function resetImageSettings(image){$('solver-engine').value='auto';$('fov').value=image.calibration?.fov_deg??0;$('ra-hint').value=image.calibration?.ra_deg??'';$('dec-hint').value=image.calibration?.dec_deg??'';$('radius').value=image.calibration?5:180;$('photo-time').value='';}
async function selectImage(image,fresh=false){notify('');if(state.busy)throw new Error('Wait for the current image analysis to finish.');const version=++imageVersion;state.image=image;state.savedResult=false;state.job=null;state.solar=null;state.analysis=null;resetImageSettings(image);image.analysis=await api(`/images/${image.id}/sources`);if(version!==imageVersion)return;for (const id of ['show-sources', 'show-labels', 'show-expected']) $(id).disabled = false;$('source-summary').textContent=`${image.analysis.count} bright candidates${image.analysis.truncated?' (strongest shown)':''} · names need a solved field`;$('object-detail').hidden=true;$('empty-image').hidden=true;
 const bitmap=new Image();await new Promise((resolve,reject)=>{bitmap.onload=resolve;bitmap.onerror=()=>reject(new Error('Image could not be displayed.'));bitmap.src=image.preview_url;});if(version!==imageVersion)return;state.bitmap=bitmap;$('sky').hidden=false;$('image-detail').textContent=`${image.analysis.width} × ${image.analysis.height} pixels`;draw();renderResults();
 if(fresh){await analyze(false);return;}const previous=await api(`/images/${image.id}/latest-analysis`);if(version!==imageVersion)return;if(previous&&previous.analysis_version!==3&&!['queued','running'].includes(previous.status)){await analyze(false);return;}if(previous){state.analysis=previous;if(previous.observation){const t=new Date(previous.observation.utc);t.setMinutes(t.getMinutes()-t.getTimezoneOffset());$('photo-time').value=t.toISOString().slice(0,19);}if(['queued','running'].includes(previous.status)){setBusy(true);pollAnalysis(previous.id,version);}else{state.savedResult=true;applyAnalysis(previous);}}else await analyze(false);}
async function upload(file){if(!file)return;if(state.busy)throw new Error('Wait for the current analysis to finish.');if(file.size>20*1024*1024)throw new Error('Choose an image smaller than 20 MB.');notify('');const image=await api('/images',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file});await selectImage(image,true);await loadImages(true);}
async function analyze(reuse=false){if(!state.image)return;const version=imageVersion;const options={backend:$('solver-engine').value,fov_deg:number('fov'),radius_deg:number('radius')};if($('ra-hint').value||$('dec-hint').value){options.ra_deg=number('ra-hint');options.dec_deg=number('dec-hint');}
 const observation=photoObservation();state.savedResult=false;setBusy(true);state.job=null;state.solar=null;state.analysis=null;renderResults();$('analysis-state').textContent='Analyzing…';$('analysis-message').textContent='Choosing the right analysis for this image…';
 try{const job=await post(`/images/${state.image.id}/analyze`,{options,observation,reuse_solution:reuse});sessionStorage.setItem('active-analysis',job.id);pollAnalysis(job.id,version);}catch(e){setBusy(false);throw e;}}
async function pollAnalysis(id,version){try{const result=await api('/analyses/'+id);if(version!==imageVersion)return;state.analysis=result;$('analysis-message').textContent=result.message;if(['queued','running'].includes(result.status)){setTimeout(()=>pollAnalysis(id,version),750);return;}applyAnalysis(result);}catch(e){if(version!==imageVersion)return;setBusy(false);$('analysis-state').textContent='Unavailable';notify(e.message);}}
function applyAnalysis(result){state.analysis=result;state.job=result.plate??null;state.solar=result.solar??null;setBusy(false);sessionStorage.removeItem('active-analysis');$('analysis-details').textContent=JSON.stringify(result,null,2);renderResults();draw();}
function objects(){const identified=state.job?.identification;return [...(identified?.status==='ready'?[...identified.matched_stars,...identified.expected_objects,...identified.expected_stars]:[]),...(state.solar?.objects??[])];}
function renderResults(){const panel=$('result-list');panel.replaceChildren();$('object-detail').hidden=true;const plate=state.job?.status==='solved'?state.job.solution:null;const solar=state.solar;
 $('coordinates').hidden=!plate;if(plate){$('solved-ra').textContent=plate.ra_deg.toFixed(5)+'°';$('solved-dec').textContent=plate.dec_deg.toFixed(5)+'°';$('analysis-state').textContent=state.savedResult?'Star field solved · saved result':'Star field solved · fresh solve';const id=state.job.identification;
 const matched=id?.matched_star_count??0, catalogObjects=id?.expected_objects?.length??0;
 $('analysis-message').textContent=catalogObjects ? `${catalogObjects} deep-sky ${catalogObjects===1?'object':'objects'} in the solved field. ${matched?'Star matches are also listed.':'No individual stars matched the name catalog.'}` :
 matched ? `${matched} stars matched against the local catalog.` : 'The field position was solved. No names from the local catalog match this view.';}
 else if(solar){const fieldFailed=state.job?.status==='failed';$('analysis-state').textContent=solar.status==='suggestion'?'Visual suggestion':fieldFailed?'Star field not solved':'Object uncertain';if(state.savedResult) $('analysis-state').textContent+=' · saved result';$('analysis-message').textContent=solar.status==='suggestion'?'Appearance suggests a possible object. Its sky position has not been verified.':fieldFailed?'The stars could not be matched. '+(state.analysis?.field_error??state.job.message):solar.disk_box?'The close-up model could not distinguish this object reliably. No name has been assigned.':solar.message;}
 else{$('analysis-state').textContent=state.busy?'Analyzing…':state.analysis?.status==='failed'?'Star field not solved':state.image?'Ready':'Add an image';$('analysis-message').textContent=state.analysis?.message??'Results appear here after you add an image.';}
 $('capture-note').textContent=[state.job?.solution?.warning,state.analysis?.solar_warning].filter(Boolean).join(' ')||(solar?.mode==='field'?'Moving-object positions use capture time '+new Date(solar.observation.utc).toLocaleString()+'.':'');
 const all=objects().filter(o=>o.evidence!=='expected'||o.kind==='deep-sky object'||$('show-expected').checked);const rank=o=>o.evidence==='expected'&&o.kind==='deep-sky object'?1:o.proper_name||o.evidence==='visual suggestion'||o.evidence==='positional match'?0:o.evidence==='matched'?2:3;all.sort((a,b)=>rank(a)-rank(b));
 for(const item of all.slice(0,60)){const b=document.createElement('button');b.className='object-chip'+(item.evidence==='expected'?' expected':'');const title=document.createElement('span'),detail=document.createElement('small');title.textContent=item.name;detail.textContent=item.evidence==='matched'?'Matched star':item.evidence==='positional match'?'Position match':item.evidence==='visual suggestion'?'Appearance only':item.kind==='deep-sky object'?'Catalog object in this field':'Expected location';b.append(title,detail);b.onclick=()=>showObject(item);panel.append(b);}}
function showObject(item){const p=$('object-detail');p.replaceChildren();p.hidden=false;const h=document.createElement('h3');h.textContent=item.name;p.append(h);const info=document.createElement('p');info.textContent=item.evidence==='matched'?`${item.id} · star matched within ${item.residual_px} pixels.`:item.evidence==='visual suggestion'?'A visual suggestion, not a confirmed identification or coordinate solution.':item.evidence==='expected'?item.kind==='deep-sky object'?'This object’s catalog position falls inside the solved image.':'Predicted location; this object has not been detected.':'A positional match with the local ephemeris.';p.append(info);if(item.ra_deg!==undefined){const c=document.createElement('p');c.textContent=`RA ${item.ra_deg.toFixed(5)}° · DEC ${item.dec_deg.toFixed(5)}°`;p.append(c);}if(item.association_warning){const w=document.createElement('p');w.textContent=item.association_warning;p.append(w);}if(item.evidence==='matched'&&typeof renderEnrichment==='function')renderEnrichment(item,p);}
function draw(){if(!state.bitmap)return;const c=$('sky'),ctx=c.getContext('2d');c.width=state.bitmap.naturalWidth;c.height=state.bitmap.naturalHeight;ctx.drawImage(state.bitmap,0,0);const scale=c.width/Math.max(1,c.clientWidth);
 // Candidate markers are independent of catalog names and expected positions.
 const candidates=state.image?.analysis?.sources??[];const limit=Math.min(300,Math.max(60,Math.round(c.clientWidth*c.clientHeight/1800)));$('source-summary').textContent=`${candidates.length} bright candidates${$('show-sources').checked?' · showing '+Math.min(limit,candidates.length)+' strongest':''} · names need a solved field`;if($('show-sources').checked){ctx.save();ctx.strokeStyle='#61d7be';ctx.lineWidth=1.25*scale;for(const source of candidates.slice(0,limit)){if(!Number.isFinite(source.x)||!Number.isFinite(source.y))continue;ctx.beginPath();ctx.arc(source.x,source.y,3.5*scale,0,2*Math.PI);ctx.stroke();}ctx.restore();}
 if(!$('show-labels').checked)return;ctx.font=`600 ${Math.max(12,12*scale)}px system-ui`;const selected=objects().filter(o=>o.evidence==='expected'?$('show-expected').checked:o.proper_name||o.evidence!=='matched').slice(0,35);if(!selected.length)selected.push(...objects().filter(o=>o.evidence==='matched').slice(0,10));
 const boxes=[];for(const o of selected){if(!Number.isFinite(o.x)||!Number.isFinite(o.y))continue;const color=o.evidence==='visual suggestion'?'#dfb6ff':o.evidence==='expected'?'#ffce8a':'#8affd3';ctx.strokeStyle=color;ctx.lineWidth=1.5*scale;ctx.beginPath();ctx.arc(o.x,o.y,5*scale,0,2*Math.PI);ctx.stroke();const text=o.name+(o.evidence==='expected'?' (expected)':'');const width=ctx.measureText(text).width+8*scale,height=22*scale;
 const box=[[o.x+8*scale,o.y-height/2],[o.x-width-8*scale,o.y-height/2],[o.x-width/2,o.y-height-8*scale]].map(([x,y])=>({x,y,width,height})).find(b=>b.x>=0&&b.y>=0&&b.x+b.width<c.width&&b.y+b.height<c.height&&!boxes.some(a=>b.x<a.x+a.width&&b.x+b.width>a.x&&b.y<a.y+a.height&&b.y+b.height>a.y));if(box){boxes.push(box);ctx.fillStyle='#08131deb';ctx.fillRect(box.x,box.y,box.width,box.height);ctx.fillStyle=color;ctx.fillText(text,box.x+4*scale,box.y+16*scale);}}}
async function loadImages(reset=false){if(reset){state.imageOffset=0;$('image-library').replaceChildren();}const images=await api('/images?limit=20&offset='+state.imageOffset);state.imageOffset+=images.length;for(const image of images){const b=document.createElement('button');b.className='image-card';const img=document.createElement('img');img.src=image.preview_url;img.alt='Previously added image';const label=document.createElement('span');label.textContent=`${image.analysis.width} × ${image.analysis.height}`;b.append(img,label);b.onclick=run(async()=>{showPage('workspace');await selectImage(image);});$('image-library').append(b);}$('more-images').hidden=images.length<20;$('library-empty').hidden=state.imageOffset>0;}
async function init(){state.targets=await api('/catalog');for(const t of state.targets){const o=document.createElement('option');o.value=t.id;o.textContent=t.name;$('target').append(o);}const status=await api('/prototype/status');mountText(status.mount);$('target').disabled=false;$('api-badge').textContent='Local processing';await selectTarget();await loadImages(true);const active=sessionStorage.getItem('active-analysis');if(active){try{const a=await api('/analyses/'+active);await selectImage(await api('/images/'+a.image_id));}catch{sessionStorage.removeItem('active-analysis');}}}
$('file').onchange = run(async () => {
  const file = $('file').files[0];
  $('file').value = '';
  if (!file) return;
  if ($('workspace').hidden) showPage('workspace');
  await upload(file);
});
for (const id of ['choose-image', 'library-upload']) $(id).onclick = () => $('file').click();
$('choose-curve').onclick = () => $('curve-file').click();$('replace-image').onclick=()=>$('file').click();$('analyze').onclick=run(()=>analyze(false));
for(const e of ['dragenter','dragover'])$('dropzone').addEventListener(e,event=>{event.preventDefault();$('dropzone').classList.add('drag');});$('dropzone').addEventListener('dragleave',()=>$('dropzone').classList.remove('drag'));$('dropzone').addEventListener('drop',run(async event=>{event.preventDefault();$('dropzone').classList.remove('drag');await upload(event.dataTransfer.files[0]);}));
$('target').onchange=run(selectTarget);for(const id of ['latitude','longitude','elevation'])$(id).oninput=()=>{clearTimeout(observerTimer);observerTimer=setTimeout(()=>run(selectTarget)(),500);};
$('stop').onclick=run(async()=>mountText(await post('/mount/stop',{})));$('reset').onclick=run(async()=>{await post('/mount/reset',{});await selectTarget();});$('show-sources').onchange=draw;$('show-labels').onchange=draw;$('show-expected').onchange=()=>{renderResults();draw();};$('more-images').onclick=run(()=>loadImages());
document.querySelectorAll('.nav').forEach(button => {
  button.onclick = () => showPage(button.dataset.page);
});
function setNightMode(enabled) {
  document.body.classList.toggle('night', enabled);
  $('night').setAttribute('aria-pressed', String(enabled));
}
setNightMode(localStorage.getItem('astrolearn-night') === '1');
$('night').onclick = () => {
  const enabled = !document.body.classList.contains('night');
  setNightMode(enabled);
  localStorage.setItem('astrolearn-night', enabled ? '1' : '0');
};
const stream=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/api/v1/telemetry');stream.onmessage=e=>{try{mountText(JSON.parse(e.data).mount);}catch{}};stream.onclose=()=>{$('api-badge').textContent='Local processing · reconnect to update mount';};
init().catch(error => { $('api-badge').textContent = 'Service unavailable'; notify(error.message); });

// Keep marker radius consistent in screen pixels when the page is resized.
new ResizeObserver(()=>draw()).observe($('dropzone'));


