'use strict';
// Predictions, imported measurements and image evidence are shown separately.
let skyMapPoints=[];
async function loadSkyMap(){const data=await post('/sky-map',site());const canvas=$('local-map'),ctx=canvas.getContext('2d');
 ctx.fillStyle='#090f1b';ctx.fillRect(0,0,700,700);ctx.strokeStyle='#34465e';ctx.fillStyle='#ccd9eb';ctx.font='14px system-ui';
 for(const r of [100,200,300]){ctx.beginPath();ctx.arc(350,350,r,0,Math.PI*2);ctx.stroke();}
 for(const [label,x,y] of [['N',345,30],['E',20,355],['S',345,685],['W',675,355]])ctx.fillText(label,x,y);
 skyMapPoints=[];for(const star of data.stars){const radius=(90-star.altitude_deg)/90*300,az=star.azimuth_deg*Math.PI/180;
 const x=350-radius*Math.sin(az),y=350-radius*Math.cos(az);skyMapPoints.push({...star,x,y});ctx.fillStyle='#bceee6';ctx.beginPath();ctx.arc(x,y,Math.max(1,3.8-star.magnitude*.5),0,Math.PI*2);ctx.fill();
 if(star.proper_name&&star.magnitude<2){ctx.fillStyle='#e1e9f7';ctx.fillText(star.name,x+6,y-5);}}
 $('map-caption').textContent=`${data.stars.length} catalog stars above the horizon · UTC ${data.utc}. ${data.message}`;}
$('refresh-map').onclick=run(loadSkyMap);
$('local-map').onclick=e=>{const c=$('local-map'),r=c.getBoundingClientRect(),x=(e.clientX-r.left)*700/r.width,y=(e.clientY-r.top)*700/r.height;
 let best=null,distance=12;for(const star of skyMapPoints){const d=Math.hypot(x-star.x,y-star.y);if(d<distance){distance=d;best=star;}}
 if(best)$('map-selection').textContent=`${best.name} (${best.id}) · altitude ${best.altitude_deg.toFixed(1)}° · azimuth ${best.azimuth_deg.toFixed(1)}° · magnitude ${best.magnitude}. Predicted position only.`;};

function renderEnrichment(item,panel){const box=document.createElement('div'),text=document.createElement('p'),button=document.createElement('button');box.className='enrichment';button.className='button secondary';button.textContent='Update details from SIMBAD (internet)';text.textContent='Checking saved object details…';box.append(text,button);panel.append(box);
 const url='/solves/'+encodeURIComponent(state.job.id)+'/object-details?object_id='+encodeURIComponent(item.id);
 const render=data=>{if(!box.isConnected)return;const saved=data.enrichment;if(saved){const r=saved.record;text.textContent=`${r.main_id??item.name} · type ${r.otype??'unknown'} · spectrum ${r.sp_type??'unavailable'} · SIMBAD, saved ${saved.retrieved_at}. ${data.online_error??''}`;}
 else text.textContent=data.online_error??'Local catalog details available above. No saved SIMBAD enrichment yet.';};
 run(async()=>render(await api(url)))();button.onclick=run(async()=>{button.disabled=true;try{render(await post(url,{}));}finally{button.disabled=false;}});}

function plotLightcurve(record){const c=$('lightcurve-plot'),ctx=c.getContext('2d');ctx.fillStyle='#090f1b';ctx.fillRect(0,0,900,320);
 const points=record.points,xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);let xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
 if(ymax===ymin){ymin-=.01;ymax+=.01;}const pad=(ymax-ymin)*.1;ymin-=pad;ymax+=pad;
 ctx.strokeStyle='#70839b';ctx.beginPath();ctx.moveTo(60,20);ctx.lineTo(60,270);ctx.lineTo(880,270);ctx.stroke();ctx.fillStyle='#c4d6ea';ctx.font='13px system-ui';ctx.fillText('Normalized flux',65,16);ctx.fillText('Time (input units)',690,305);ctx.fillText(ymax.toFixed(4),2,40);ctx.fillText(ymin.toFixed(4),2,265);ctx.fillText(xmin.toFixed(3),60,290);ctx.fillText(xmax.toFixed(3),800,290);
 ctx.fillStyle='#85e4d5';for(const [t,f] of points){const x=60+(t-xmin)/Math.max(xmax-xmin,1e-10)*820,y=270-(f-ymin)/(ymax-ymin)*235;ctx.beginPath();ctx.arc(x,y,2,0,Math.PI*2);ctx.fill();}
 $('lightcurve-caption').textContent=`${record.count} measurements · median input flux ${record.median_flux}. ${record.warning}`;}
async function importCurve(file){if(!file)return;plotLightcurve(await api('/lightcurves',{method:'POST',headers:{'Content-Type':'text/csv'},body:file}));}
$('curve-file').onchange=run(async()=>{await importCurve($('curve-file').files[0]);$('curve-file').value='';});
$('curve-demo').onclick=run(async()=>{const response=await fetch('/static/demo-lightcurve.csv');await importCurve(await response.blob());});
$('curve-restore').onclick=run(async()=>{const curves=await api('/lightcurves');if(curves.length)plotLightcurve(curves[0]);else notify('No brightness data has been imported yet.');});
api('/prototype/status').then(s=>{const engines=s.solver.backends??[];for(const engine of engines){const option=$('solver-engine').querySelector(`option[value="${engine.name.toLowerCase()}"]`);if(option){option.disabled=!engine.available;option.textContent=engine.name+(engine.available?' · ready':' · needs setup');}}
 $('engines-status').textContent=engines.map(e=>`${e.name}: ${e.message}`).join(' ');}).catch(()=>{});
