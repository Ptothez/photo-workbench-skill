'use strict';
const $=s=>document.querySelector(s);
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n};
const append=(parent,...children)=>{parent.append(...children);return parent};
let summary=null,token='',generation=0,lastEvent=null,reviewCategory='',reviewView='pending',reviewOffset=0,query='',libraryPage=1,locationFilter='',collectionFilter='',feedbackContext='';
const labels={home:'摄影概况',library:'照片库',review:'待你确认',learning:'经验与改进',maintenance:'资料与维护',projects:'在途与修图'};
const choiceLabels={keep_unknown:'暂按未知保留，以后有线索再补',not_family:'不是家人，请调整家庭归类',accept:'保留目前的整理结果',confirmed:'我能确认，补充信息',needs_change:'需要调整',provide_clue:'我有线索，请继续核查',deferred:'现在答不了，以后再说',keep_candidate:'保留在这个主题的候选里',not_this_round:'本轮不选，原图保留',adopt:'同意作为待验证的选片原则',reject:'不采用这条建议',revise:'修改后再讨论'};
const views={pending:'现在处理',waiting:'等我落实',deferred:'以后再说',done:'已完成判断'};
function toast(text){$('#toast').textContent=text;setTimeout(()=>{$('#toast').textContent=''},6000)}
async function get(path){const r=await fetch(path,{cache:'no-store'});const d=await r.json();if(!r.ok)throw Error(d.error||'读取失败');return d}
async function post(path,data){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Photo-Token':token},body:JSON.stringify(data)});const d=await r.json();if(!r.ok)throw Error(d.error||'保存失败');return d}
function button(text,fn,primary=false){const b=el('button',primary?'primary':'',text);b.type='button';b.onclick=fn;return b}
function link(text,hash,cls='button'){const a=el('a',cls,text);a.href=hash;return a}
function title(name,sub){const h=el('div');h.append(el('h1','',name));if(sub)h.append(el('p','intro',sub));return h}
function empty(name,text){return append(el('div','empty'),el('h2','',name),el('p','',text))}
function errorBox(error){$('#main').append(el('p','error',error.message+'。已有照片和意见保持不变。'))}
async function refreshSummary(){summary=await get('/api/v2/summary');token=summary.token;$('#review-count').textContent=summary.counts.pending||'';return summary}
async function locatePhoto(path){try{await post('/api/locate',{path});toast('已在资源管理器选中这张照片')}catch(e){toast(e.message)}}
async function openPath(path){try{await post('/api/open',{path});toast('已打开对应位置')}catch(e){toast(e.message)}}
function parent(path){return path.replace(/[\\/][^\\/]+$/,'')}
function folderButton(path,label='打开文件夹'){return button(label,()=>openPath(path))}
function photoCard(p){
 const card=el('article','photo-card'),name=p.description||p.name;let media;
 if(p.has_preview){media=button('',()=>{const dlg=$('#photo-dialog');$('#large-photo').src='/api/library-preview?id='+encodeURIComponent(p.id);$('#large-caption').textContent=name;dlg.showModal()});media.className='image-button';const img=el('img');img.loading='lazy';img.alt=name;img.src='/api/library-preview?id='+encodeURIComponent(p.id);img.onerror=()=>media.replaceWith(append(el('div','no-preview'),el('span','','预览暂不可用'),el('small','','请打开原文件查看')));media.append(img)}
 else media=append(el('div','no-preview'),el('span','',p.state==='known_unreadable'?'原文件损坏，保留待恢复':'预览正在补齐'),p.places?.[0]?button('定位这张原图',()=>locatePhoto(p.places[0].path)):el('small','','位置仍在核对'));
 card.append(media);const caption=el('div','caption');caption.append(el('h3','',name));if(p.places?.length){const best=p.places.find(x=>x.location==='onedrive')||p.places[0];caption.append(button('定位原文件',()=>locatePhoto(best.path)))}caption.append(button('对这张提意见',()=>{feedbackContext='照片：'+name+'；档案：'+p.id;showFeedback('taste')}));if(p.places?.length){const locations=[...new Set(p.places.map(x=>({onedrive:'本地／云盘',nas:'NAS',photo_media_trash:'回收区'}[x.location]||x.location)))];caption.append(el('p','',locations.join(' · ')));const details=el('details','details');details.append(el('summary','','查看位置'));for(const place of p.places){details.append(el('p','path',place.path),button('选中这个文件',()=>locatePhoto(place.path)))}caption.append(details)}card.append(caption);return card
}
function gridPhotos(photos){const grid=el('div','gallery');photos.forEach(p=>grid.append(photoCard(p)));return grid}
async function home(g){
 const s=await refreshSummary();if(g!==generation)return;const main=$('#main');main.replaceChildren(title('让照片有去处，也有机会成为作品','看处理进度、找回照片，需要你判断的事情集中在一处。'));
 const flow=el('div','flow');for(const r of [dict('新到照片',s.intake_files,'放好照片后，在对话通知我开始筛选。','打开新照片入口',()=>openPath(s.intake_path)),dict('在途项目',s.projects.length,'还在工作区中的照片项目，可查看和提出修图意见。','查看在途与修图',()=>{location.hash='projects'}),dict('已有档案',s.assets,'可按姓名、场景、主题或年月查找。','浏览照片库',()=>{location.hash='library'})]){
  flow.append(append(el('article','surface'),el('span','label',r.name),el('div','number',r.count.toLocaleString()),el('p','',r.description),button(r.action,r.run,r.name==='待你确认')))
 }main.append(append(el('div','surface accent'),append(el('div','section-head'),el('h2','','有 '+(s.counts.pending||0)+' 项需要你确认'),link('开始确认','#review','button primary')),el('p','muted','当前需要人工确认的事项集中在这里；保存后逐项减少。')));main.append(flow);
 const heading=append(el('div','section-head'),el('h2','','照片从进来到入库'));main.append(heading);
 const process=el('div','surface');process.append(el('h3','','新照片 → 看图与整理 → 已入库'),el('p','muted','需要后期的照片另进「待修图」，完成后再入库。精选与主题归属单独保留，不等同于是否入库。'));
 process.append(append(el('div','actions'),folderButton(s.intake_path,'放入新照片'),link('查看整理结果','#review'),button('提出修图或流程意见',()=>showFeedback('workflow'))));main.append(process);
 const cols=el('div','columns'),left=el('section'),right=el('section');left.append(append(el('div','section-head'),el('h2','','接下来由谁处理')));const rows=el('div','surface');
 for(const [name,value,detail] of [['需要你判断',s.counts.pending||0,'照片身份、拍摄信息、精选及分类。'],['等我落实',s.counts.waiting||0,'你已给出意见，我需要核实并执行。'],['以后再说',s.counts.deferred||0,'暂缺线索的事项，不挡住当前进度。']])rows.append(append(el('div','row'),append(el('div'),el('h3','',name+' · '+value),el('p','muted',detail))));left.append(rows);
 right.append(append(el('div','section-head'),el('h2','','你的意见会留下来')));right.append(append(el('div','surface'),el('p','','每条意见保留原话和落实结果。适合复用的经验经过提炼、确认和验证，再进入后续筛选与影集工作。'),link('查看意见与经验','#learning'),el('p','muted','没有新照片或新通知时，不会自行启动整理。')));cols.append(left,right);main.append(cols)
}
function dict(name,count,description,action,run){return {name,count,description,action,run}}
async function libraryView(g){
 const params=new URLSearchParams(location.hash.split('?')[1]||''),requestedSection=params.get('section')||'',album=params.get('album')||'',search=params.get('search')||'',page=Math.max(1,Number(params.get('page')||1)),all=params.get('all')==='1';
 const main=$('#main');main.replaceChildren(title('照片库','先选主题或分类，再看这一组的每张照片。照片可以在多个主题里出现，原件只按原有位置保存。'));
 const tools=el('form','tools'),input=el('input');input.type='search';input.placeholder='搜索姓名、场景、年月或设备';input.setAttribute('aria-label','搜索照片');input.value=search;const go=el('button','primary','搜索照片');tools.append(input,go);tools.onsubmit=e=>{e.preventDefault();location.hash='library?'+new URLSearchParams({search:input.value.trim(),all:'1'})};main.append(tools);
 const groups=await get('/api/v2/collections?'+new URLSearchParams({section:requestedSection,page}));if(g!==generation)return;const section=groups.active_section||requestedSection;
 const tabs=el('div','pills');for(const c of groups.sections){const b=button(c.title,()=>{location.hash='library?'+new URLSearchParams({section:c.id})});if(c.id===section&&!search&&!all)b.className='chosen';tabs.append(b)}tabs.append(button('全部照片',()=>{location.hash='library?all=1'}));main.append(tabs);
 if(!album&&!search&&!all){
  const current=groups.sections.find(x=>x.id===section);main.append(el('h2','',current?.title||'照片集'),el('p','muted',(current?.description||'')+' 共 '+groups.total+' 个照片集。'));
  const grid=el('div','album-grid');for(const c of groups.items){const a=el('a','album-card');a.href='#library?'+new URLSearchParams({section,album:c.id});const cover=el('div','album-cover');if(c.preview_ids.length){for(const h of c.preview_ids.slice(0,1)){const img=el('img');img.loading='lazy';img.src='/api/library-preview?id='+encodeURIComponent(h);img.alt=c.title+' 照片集封面';img.onerror=()=>{img.remove();cover.append(el('span','muted','封面正在补齐'))};cover.append(img)}}else cover.append(el('span','muted','预览正在补齐'));a.append(cover,append(el('div','album-caption'),el('h3','',c.title),el('p','muted',c.count+' 张照片 · 点击看图')));grid.append(a)}
  main.append(groups.items.length?grid:empty('这个分类还没有照片集','保留分类入口，新照片归入后会在这里出现。'));const nav=el('div','pager'),prev=button('上一页',()=>{location.hash='library?'+new URLSearchParams({section,page:page-1})}),next=button('下一页',()=>{location.hash='library?'+new URLSearchParams({section,page:page+1})});prev.disabled=page<=1;next.disabled=page*24>=groups.total;nav.append(prev,el('span','',page+' / '+Math.max(1,Math.ceil(groups.total/24))+' 页'),next);main.append(nav);return;
 }
 let result;if(album)result=await get('/api/v2/album?'+new URLSearchParams({id:album,page,q:search}));else result=await get('/api/library?'+new URLSearchParams({q:search,page}));if(g!==generation)return;
 const name=result.album?.title||(search?'搜索「'+search+'」':'全部照片');const heading=el('div','section-head');heading.append(el('h2','',name),link('返回分类','#library?'+new URLSearchParams({section})));main.append(heading,el('p','muted',result.total.toLocaleString()+' 张照片；点击图片放大，「定位原文件」会选中这一张，不用再在文件夹中找。'));
 main.append(result.items.length?gridPhotos(result.items):empty('没有匹配的照片','换个关键词试试，或者返回分类浏览。未标注姓名的照片仍可按场景查找。'));
 const turn=delta=>{const p=new URLSearchParams({section,page:page+delta});if(album)p.set('album',album);if(search)p.set('search',search);if(all)p.set('all','1');location.hash='library?'+p};const nav=el('div','pager'),prev=button('上一页',()=>turn(-1)),next=button('下一页',()=>turn(1));prev.disabled=page<=1;next.disabled=page*30>=result.total;nav.append(prev,el('span','',page+' / '+Math.max(1,Math.ceil(result.total/30))+' 页'),next);main.append(nav)
}
async function review(g){
 await refreshSummary();if(g!==generation)return;const main=$('#main');main.replaceChildren(title('待你确认','一次看清一件事。确认或留下意见后，它就退出当前队列。'));
 const pills=el('div','pills');for(const [value,text]of Object.entries(views)){const b=button(text+(summary.counts[value]?' · '+summary.counts[value]:''),()=>{reviewView=value;reviewOffset=0;render()});if(value===reviewView)b.className='chosen';pills.append(b)}main.append(pills);
 const tools=el('div','tools'),cat=el('select');cat.setAttribute('aria-label','确认事项类型');for(const c of ['',...Object.keys(summary.categories)]){const o=el('option','',c||'按建议顺序处理');o.value=c;cat.append(o)}cat.value=reviewCategory;cat.onchange=()=>{reviewCategory=cat.value;reviewOffset=0;render()};tools.append(cat);main.append(tools);
 const data=await get('/api/v2/queue?'+new URLSearchParams({category:reviewCategory,view:reviewView,offset:reviewOffset}));if(g!==generation)return;
 if(!data.items.length){main.append(empty(reviewView==='pending'?'这里暂时不需要你判断':'这里暂时没有事项',reviewView==='pending'?'新照片整理时有疑问，才会再出现。缺线索和等我执行的事项分别保留。':'已保存的意见和原始记录都会保留。'));return}
 const t=data.items[0],card=el('article','surface review-card');card.append(el('span','badge',t.category),el('p','question',t.question),el('h3','muted',t.title));
 if(t.photos.length)card.append(gridPhotos(t.photos));
 if(t.photo_count>t.photos.length)card.append(button('查看这一组全部 '+t.photo_count+' 张照片',()=>showGroup(t,card)));
 card.append(append(el('div','suggestion'),el('strong','','我的建议：'),el('span','',t.proposal)));
 if(t.category==='品味原则')card.append(el('p','muted','这是候选原则。你同意后仍需结合真实选片验证，才能成为长期规则。'));
 if(t.paths?.length){const opens=el('div','actions');for(const path of [...new Set(t.paths.map(p=>t.id.startsWith('folder:')?p:parent(p)))].slice(0,2))opens.append(folderButton(path,'打开对应文件夹'));card.append(opens)}
 const decision=el('div','decision-panel'),form=el('form'),draftKey='photo-v2-draft:'+t.id;let draft={};try{draft=JSON.parse(localStorage.getItem(draftKey)||'{}')}catch(e){}
 const old=t.decision||{};const name=el('input');name.value=(draft.person_names||old.person_names||[]).join('，');name.placeholder='例如：人物甲、人物乙';name.setAttribute('aria-label','确认的家人姓名');
 let selected=draft.action||'';for(const action of t.choices){const row=el('div','choice'),radio=el('input'),label=el('label');radio.type='radio';radio.name='decision';radio.value=action;radio.id='decision-'+action;radio.checked=selected===action;label.htmlFor=radio.id;label.textContent=choiceLabels[action]||action;row.append(radio,label);form.append(row);radio.onchange=()=>{selected=action;keep()}}
 if(t.category==='家庭身份')form.append(append(el('label'),el('span','','确认姓名时填写'),name));
 const note=el('textarea');note.placeholder='需要调整什么，或者你知道哪些信息？没有补充可以留空。';note.setAttribute('aria-label','本项审核意见');note.value=draft.note||'';form.append(append(el('label'),el('span','','补充意见'),note));
 const msg=el('p','error');const keep=()=>localStorage.setItem(draftKey,JSON.stringify({action:selected,note:note.value,person_names:name.value.split(/[，,、]/).map(s=>s.trim()).filter(Boolean)}));note.oninput=keep;name.oninput=keep;
 const save=el('button','primary','保存，继续下一项');save.type='submit';form.append(append(el('div','actions'),save,button('先看下一项',()=>{reviewOffset=(reviewOffset+1)%data.total;render()})),msg);
 form.onsubmit=async e=>{e.preventDefault();keep();if(!selected){msg.textContent='先选一项决定，再保存。';return}save.disabled=true;try{lastEvent={task:t,note:note.value,action:selected};const r=await post('/api/v2/decision',{revision:summary.revision,task_id:t.id,source_version:t.source_version,action:selected,note:note.value,person_names:name.value.split(/[，,、]/).map(s=>s.trim()).filter(Boolean)});lastEvent.revision=r.revision;localStorage.removeItem(draftKey);reviewOffset=0;toast(selected==='deferred'?'已放到「以后再说」，当前队列继续。':'已保存；需要调整的部分交给我落实。');await render()}catch(e){msg.textContent=e.message;save.disabled=false}};
 if(reviewView==='pending')decision.append(form);else{
  decision.append(el('h3','','你的决定：'+(choiceLabels[old.action]||old.action)),el('p','',old.note||'没有补充意见。'),button('重新判断这项',async()=>{try{await post('/api/v2/decision',{revision:summary.revision,task_id:t.id,source_version:t.source_version,action:'reopen',note:'本人从已保存事项重新打开'});reviewView='pending';reviewOffset=0;await render()}catch(e){toast(e.message)}}))
 }card.append(decision);
 const details=el('details','details');details.append(el('summary','','需要时查看：判断依据与具体位置'));details.addEventListener('toggle',async()=>{if(!details.open||details.dataset.loaded)return;try{const r=await get('/api/v2/task?id='+encodeURIComponent(t.id));details.dataset.loaded='yes';details.append(el('p','',t.why||''));for(const path of r.paths)details.append(el('p','path',path))}catch(e){details.append(el('p','error',e.message))}});card.append(details);main.append(el('p','muted','本类还有 '+data.total+' 项'+(reviewView==='pending'?'待判断':'已保存')),card);
 if(lastEvent&&reviewView==='pending')main.append(button('撤回刚才的决定',async()=>{try{await post('/api/v2/decision',{revision:summary.revision,task_id:lastEvent.task.id,source_version:lastEvent.task.source_version,action:'reopen',note:'本人撤回刚才的决定'});lastEvent=null;await render()}catch(e){toast(e.message)}}))
}
async function showGroup(task,card){
 const panel=el('div','surface');let page=0;const draw=async()=>{const r=await get('/api/v2/task?'+new URLSearchParams({id:task.id,page}));panel.replaceChildren(gridPhotos(r.photos));const row=el('div','pager'),prev=button('前一组',()=>{page--;draw()}),next=button('后一组',()=>{page++;draw()});prev.disabled=page===0;next.disabled=(page+1)*24>=r.total;row.append(prev,el('span','',(page+1)+' / '+Math.max(1,Math.ceil(r.total/24))+' 组'),next);panel.append(row)};card.append(panel);await draw()
}
function showFeedback(scope='workflow'){$('#feedback-form').elements.scope.value=scope;$('#feedback-error').textContent='';$('#feedback-dialog').showModal()}
async function learning(g){
 const data=await get('/api/v2/learning');if(g!==generation)return;const main=$('#main');main.replaceChildren(title('经验与改进','原话留下来，落实有结果，适合复用的经验再进入长期规则。'));
 main.append(append(el('div','surface'),el('h3','','意见 → 落实 → 提炼 → 验证 → 以后复用'),el('p','muted','具体照片意见用于这张照片；跨照片、跨批次成立的原则才进入经验库。候选、本人采用、验证和正式生效分别记录。'),button('再提一条意见',()=>showFeedback())));
 main.append(append(el('div','section-head'),el('h2','','你提出的意见')));
 if(!data.suggestions.length)main.append(empty('从你的下一条意见开始','审核照片时的意见也会完整留存；这里另外收纳你对流程、选片、Skill 和影集的建议。'));
 for(const s of data.suggestions.slice().reverse()){const c=el('article','surface feedback-item');c.append(el('span','badge',s.receipt?({applied:'已落实',blocked:'仍有阻塞',needs_user:'需要补充',not_adopted:'已说明处理结果'}[s.receipt.result]||'处理中'):'已记录，等我处理'),append(el('details'),el('summary','',s.text.slice(0,90)+(s.text.length>90?'… 查看完整原话':'')),el('blockquote','',s.text)));if(s.receipt)c.append(el('p','',s.receipt.summary));if(s.duplicate_of)c.append(el('p','muted','与此前意见相同，原话仍保留，合并跟进。'));main.append(c)}
 main.append(append(el('div','section-head'),el('h2','','可复用的规则')));
 if(!data.rules.length)main.append(el('p','muted','还没有从新反馈中正式提炼的规则。不会把模型猜测或单张照片的细节自动变成长久标准。'));
 for(const r of data.rules){const c=el('article','surface feedback-item');c.append(el('span','badge',r.status==='active'?'已生效':['retired','paused'].includes(r.status)?'已停用':r.adopted?'已采用，验证中':'候选，等你确认'),el('h3','',r.text),el('p','',r.boundary),el('p','muted','已记录 '+r.validations.length+' 轮验证'));
  if(r.status==='active')c.append(button('暂停使用这条规则',async()=>{try{await refreshSummary();await post('/api/v2/rule-adoption',{revision:summary.revision,rule_id:r.rule_id,adopt:false});render()}catch(e){toast(e.message)}}));if(r.status==='candidate'&&!r.adopted)c.append(button('同意作为待验证原则',async()=>{try{await refreshSummary();await post('/api/v2/rule-adoption',{revision:summary.revision,rule_id:r.rule_id,adopt:true});render()}catch(e){toast(e.message)}}));main.append(c)
 }
}
async function maintenance(g){
 const s=await refreshSummary();if(g!==generation)return;const main=$('#main');main.replaceChildren(title('资料与维护','低频资料和技术记录放在这里，日常不用阅读它们才能审核。'));
 const data=[['完整流程说明','摄影工作流_改写版.html'],['资料与预设记录','pending-review-addendum.json'],['操作与历史证据','审计/2026-10-26_接手核查/final-delivery-root-verification.json'],['当前档案核对时间','照片档案/current.json']];
 const panel=el('div','surface');for(const [text,path]of data){const row=el('div','row');row.append(el('h3','',text));const a=el('a','button','查看');a.href=path;a.target='_blank';a.rel='noopener';row.append(a);panel.append(row)}main.append(panel);
 main.append(el('p','muted','档案最近更新：'+(s.catalog_at?new Date(s.catalog_at).toLocaleString('zh-CN'):'尚未建立照片档案')+'。按通知后的批次核对，不持续扫描文件。'),el('p','muted','旧记录和回收区均保留。永久清理和更改媒体不由本页自动执行。'))
}
async function projects(g){const s=await refreshSummary();if(g!==generation)return;const m=$('#main');m.replaceChildren(title('在途与修图','这里列出仍在工作区中的项目。是否需要修图由实际选片和你的意见确定，不把所有在途照片都当作待修图。'),link('返回摄影概况','#home'));const list=el('div','surface');for(const p of s.projects){const row=el('div','row');row.append(append(el('div'),el('h3','',p.name),el('p','muted',p.photos+' 张照片')),append(el('div','actions'),folderButton(p.path),button('提出修图意见',()=>{feedbackContext='项目：'+p.name+'；位置：'+p.path;showFeedback('workflow')})));list.append(row)}if(!s.projects.length)list.append(el('p','muted','目前没有在途项目。'));m.append(list)}
async function render(){const g=++generation;const raw=location.hash.slice(1).split('?')[0];const page=Object.hasOwn(labels,raw)?raw:'home';$('#breadcrumb').textContent=labels[page];document.querySelectorAll('[data-page]').forEach(a=>a.classList.toggle('on',a.dataset.page===page));$('#main').replaceChildren(el('p','muted','正在读取…'));try{await ({home,library:libraryView,review,learning,maintenance,projects}[page])(g)}catch(e){if(g===generation)errorBox(e)}}
$('#feedback-open').onclick=()=>showFeedback();$('#feedback-cancel').onclick=()=>$('#feedback-dialog').close();$('#photo-close').onclick=()=>$('#photo-dialog').close();
$('#feedback-form').onsubmit=async e=>{e.preventDefault();const form=e.currentTarget,b=form.querySelector('[type=submit]');b.disabled=true;try{await refreshSummary();await post('/api/v2/suggestion',{revision:summary.revision,scope:form.elements.scope.value,text:form.elements.text.value,context:feedbackContext||(labels[location.hash.slice(1)]||'摄影概况')});form.elements.text.value='';feedbackContext='';$('#feedback-dialog').close();toast('意见已完整记录，可在「经验与改进」跟进落实结果。');await render()}catch(e){$('#feedback-error').textContent=e.message}finally{b.disabled=false}};
window.addEventListener('hashchange',()=>render());(async()=>{try{await refreshSummary();await render()}catch(e){errorBox(e)}})();
