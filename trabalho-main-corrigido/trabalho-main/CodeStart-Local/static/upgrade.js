'use strict';
const StudyHub = {
    tab: 'all', page: 1, size: 15, timer: null, remaining: 1500, deadline: 0, pendingImport: null,
    $: id => document.getElementById(id),
    today(date = new Date()) { return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`; },
    clean(value) { return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); },
    data() {
        const s = Gamification.state;
        s.studyHub ||= {tasks: [], activity: {}, drafts: {}, focusSessions: 0};
        s.studyHub.tasks ||= []; s.studyHub.activity ||= {}; s.studyHub.drafts ||= {};
        return s.studyHub;
    },
    save() { return Storage.save(Gamification.state); },
    download(name, data, type='application/json') {
        const url = URL.createObjectURL(new Blob([data], {type}));
        const a = document.createElement('a'); a.href=url; a.download=name; a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    init() {
        this.data();
        const originalSave = Storage.save.bind(Storage);
        const originalReset = Storage.reset.bind(Storage);
        Storage.reset=()=>{this.resetting=true;originalReset();};
        Storage.save = state => { try { originalSave(state); return true; } catch { showToast('Não foi possível salvar neste navegador. Exporte um backup antes de sair.', 'error'); return false; } };
        this.rows = COURSES.flatMap(c => c.lessons.map((l,i) => ({key:`${c.id}-${i}`,course:c.id,name:c.name,title:l.title,module:l.module,index:i,search:this.clean(`${c.name} ${l.title} ${l.module} ${l.body}`)})));
        this.recalculate();
        const main = document.querySelector('main');
        main.insertAdjacentHTML('afterbegin', `<div class="hub-toolbar"><span class="hub-caption"><span class="hub-dot"></span>Seu espaço de programação</span><button class="hub-button primary" id="hub-open">⌕ Minha central <span aria-hidden="true">↗</span></button><button class="hub-button" id="hub-search-shortcut">Buscar aulas <kbd> / </kbd></button><button class="hub-button" id="hub-backup">↓ Backup</button></div>`);
        main.insertAdjacentHTML('beforeend', `<section id="view-central" class="view-section hidden">
          <div class="hub-heading"><div><p class="hub-eyebrow">ORGANIZE SEU APRENDIZADO</p><h1 class="hub-title">Minha central de estudos</h1><p class="hub-muted">Encontre uma aula, retome suas notas e planeje o próximo passo.</p></div><button class="hub-button" id="hub-import">↑ Importar progresso</button></div>
          <div class="hub-layout"><div class="hub-stack"><div class="hub-panel">
            <div class="hub-fields"><label class="hub-field">Buscar em todas as aulas<input id="hub-query" type="search" placeholder="Ex.: listas, JOIN, Flask…" autocomplete="off"></label><label class="hub-field" style="max-width:220px">Curso<select id="hub-course"><option value="all">Todos os cursos</option>${COURSES.map(c=>`<option value="${escapeHTML(c.id)}">${escapeHTML(c.name)}</option>`).join('')}</select></label></div>
            <div class="hub-tabs" role="group" aria-label="Filtrar aulas"><button class="hub-button" data-hub-tab="all" aria-pressed="true">Todas</button><button class="hub-button" data-hub-tab="favorites" aria-pressed="false">★ Favoritos</button><button class="hub-button" data-hub-tab="notes" aria-pressed="false">✎ Anotações</button><button class="hub-button" data-hub-tab="pending" aria-pressed="false">Pendentes</button><button class="hub-button" data-hub-tab="done" aria-pressed="false">Concluídas</button></div>
            <p id="hub-count" class="hub-count" role="status"></p><div id="hub-results" class="hub-results"></div><div class="hub-actions"><button class="hub-button" id="hub-prev">← Anterior</button><span id="hub-page" class="hub-count"></span><button class="hub-button" id="hub-next">Próxima →</button></div>
          </div><div class="hub-panel"><h3>Seu plano da semana</h3><p class="hub-muted">Transforme o objetivo em tarefas pequenas e possíveis.</p><form id="hub-task-form" class="hub-actions"><label class="hub-field"><span>Nova tarefa</span><input id="hub-task-input" maxlength="180" placeholder="Ex.: praticar JOIN por 20 minutos" required></label><button class="hub-button primary" type="submit" style="align-self:end">Adicionar</button></form><div id="hub-tasks"></div></div></div>
          <aside class="hub-stack"><div class="hub-panel"><p class="hub-eyebrow">UM PASSO DE CADA VEZ</p><h3>Seu ritmo hoje</h3><p id="hub-goal" class="hub-muted"></p><div class="hub-progress"><div id="hub-goal-bar"></div></div><div id="hub-week" class="hub-week"></div><p class="hub-count">Aulas concluídas nos últimos 7 dias. O histórico diário começa nesta versão.</p></div>
          <div class="hub-panel"><h3>Tempo de foco</h3><label class="hub-field">Duração<select id="hub-duration"><option value="25">25 minutos</option><option value="15">15 minutos</option><option value="50">50 minutos</option><option value="5">Pausa de 5 minutos</option></select></label><div id="hub-timer" class="hub-timer" role="timer">25:00</div><div id="hub-timer-status" class="hub-timer-status" role="status">Pronto para começar</div><div class="hub-actions"><button id="hub-timer-toggle" class="hub-button primary">Iniciar</button><button id="hub-timer-reset" class="hub-button">Reiniciar</button></div><p id="hub-focus-count" class="hub-count"></p></div>
          <div class="hub-panel"><h3>Seus dados, com você</h3><p class="hub-muted">Progresso, notas e rascunhos ficam neste navegador. Faça um backup para trocar de dispositivo.</p><div class="hub-actions"><button id="hub-export-all" class="hub-button">↓ Exportar backup</button><button id="hub-export-notes" class="hub-button">↓ Baixar notas</button></div></div></aside></div></section>`);
        document.body.insertAdjacentHTML('beforeend', `<input id="hub-file" type="file" accept=".json,application/json" hidden><dialog id="hub-dialog" aria-labelledby="hub-dialog-title"><h2 id="hub-dialog-title">Restaurar seu progresso</h2><p class="hub-muted">Confira o arquivo antes de substituir os dados deste navegador.</p><div id="hub-import-preview"></div><p class="hub-count">Exporte o progresso atual antes de continuar, se quiser guardá-lo.</p><div class="hub-actions"><button id="hub-confirm-import" class="hub-button primary">Restaurar estes dados</button><button id="hub-cancel-import" class="hub-button">Cancelar</button></div></dialog>`);
        this.$('view-home').insertAdjacentHTML('afterbegin', `<div class="hub-banner"><div><p class="hub-eyebrow">SEU CAMINHO, NO SEU RITMO</p><h2 id="hub-welcome">Vamos continuar?</h2><p id="hub-home-summary"></p></div><button id="hub-resume" class="hub-button primary">Continuar estudando →</button></div>`);
        this.$('hub-open').onclick=()=>Router.go('central');
        this.$('hub-search-shortcut').onclick=()=>{Router.go('central');this.$('hub-query').focus();};
        this.$('hub-resume').onclick=()=>this.resume();
        ['hub-backup','hub-export-all'].forEach(id=>this.$(id).onclick=()=>this.export());
        this.$('hub-export-notes').onclick=()=>this.exportNotes();
        this.$('hub-import').onclick=()=>this.$('hub-file').click();
        this.$('hub-file').onchange=e=>this.import(e.target.files[0]);
        this.$('hub-cancel-import').onclick=()=>{this.pendingImport=null;this.$('hub-dialog').close();};
        this.$('hub-confirm-import').onclick=()=>this.restore();
        this.$('hub-query').oninput=()=>{this.page=1;this.renderResults();};
        this.$('hub-course').onchange=()=>{this.page=1;this.renderResults();};
        document.querySelectorAll('[data-hub-tab]').forEach(b=>b.onclick=()=>{this.tab=b.dataset.hubTab;this.page=1;this.renderResults();});
        this.$('hub-prev').onclick=()=>{this.page--;this.renderResults();};this.$('hub-next').onclick=()=>{this.page++;this.renderResults();};
        this.$('hub-task-form').onsubmit=e=>{e.preventDefault();const input=this.$('hub-task-input');const text=input.value.trim();if(!text)return;if(this.data().tasks.length>=100){showToast('Conclua ou remova tarefas antes de adicionar mais.','info');return;}this.data().tasks.push({id:crypto.randomUUID(),text,done:false});input.value='';this.save();this.renderTasks();};
        this.$('hub-timer-toggle').onclick=()=>this.toggleTimer();this.$('hub-timer-reset').onclick=()=>this.resetTimer();this.$('hub-duration').onchange=()=>this.resetTimer();
        this.hookLessons();this.hookEditor();this.hookRouter();this.hookTutor();
        document.addEventListener('keydown',e=>{if(e.key==='/'&&!/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)&&!e.target.isContentEditable&&!e.ctrlKey&&!e.metaKey){e.preventDefault();this.$('hub-search-shortcut').click();}});
        this.$('menu-toggle').setAttribute('aria-controls','mobile-menu');this.$('menu-toggle').setAttribute('aria-expanded','false');
        new MutationObserver(()=>this.$('menu-toggle').setAttribute('aria-expanded',String(!this.$('mobile-menu').classList.contains('hidden')))).observe(this.$('mobile-menu'),{attributes:true,attributeFilter:['class']});
        this.$('toast-notification').setAttribute('role','status');
        this.render();Router.go(location.hash.slice(1)||'home');
    },
    recalculate() {
        const s=Gamification.state;
        COURSES.forEach(c=>s.courseProgress[c.id]=c.lessons.filter((_,i)=>s.completedLessons.includes(`${c.id}-${i}`)).length/c.lessons.length);
        s.completedCourses=COURSES.filter(c=>s.courseProgress[c.id]===1).map(c=>c.id);
        this.save();
    },
    hookRouter() {
        const go=Router.go.bind(Router);
        Router.go=view=>{if(!this.$(`view-${view}`))view='home';go(view);if(location.hash!==`#${view}`)history.pushState(null,'',`#${view}`);document.querySelectorAll('[data-route]').forEach(b=>{if(b.dataset.route===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});this.render();};
        window.addEventListener('popstate',()=>Router.go(location.hash.slice(1)||'home'));
    },
    hookLessons() {
        const load=LessonsPage.load.bind(LessonsPage);
        LessonsPage.load=idx=>{load(idx);if(LessonsPage.course?.lessons[idx]){this.data().lastLesson={course:LessonsPage.course.id,index:idx};this.save();}};
        const complete=LessonsPage.complete.bind(LessonsPage);
        LessonsPage.complete=()=>{const key=LessonExtras.key();if(key&&!Gamification.state.completedLessons.includes(key)){const activity=this.data().activity;const today=this.today();activity[today]=Math.min(639,(activity[today]||0)+1);}complete();this.save();this.render();};
        const note=this.$('lesson-note');let noteTimer;
        note.addEventListener('input',()=>{const key=LessonExtras.key(),value=note.value;Gamification.state.notes[key]=value;clearTimeout(noteTimer);noteTimer=setTimeout(()=>this.save(),350);});
        window.addEventListener('pagehide',()=>{if(!this.resetting)this.save();});
        this.$('lesson-save-note').insertAdjacentHTML('afterend',' <button id="hub-reading" class="hub-button" aria-pressed="false">Leitura ampliada</button><span class="hub-count"> Notas com salvamento automático</span>');
        this.$('hub-reading').onclick=()=>{const on=document.body.classList.toggle('hub-reading');this.$('hub-reading').setAttribute('aria-pressed',String(on));};
    },
    hookEditor() {
        const ta=this.$('editor-textarea'),sel=this.$('editor-lang-select');
        const load=EditorPage.loadPreset.bind(EditorPage);
        EditorPage.loadPreset=lang=>{load(lang);if(typeof this.data().drafts[lang]==='string'){ta.value=this.data().drafts[lang];EditorPage.updateLineNumbers();}};
        EditorPage.loadPreset(sel.value);
        ta.addEventListener('input',()=>{this.data().drafts[sel.value]=ta.value;this.save();});
        ta.addEventListener('keydown',e=>{if(e.key==='Tab'){e.preventDefault();ta.setRangeText('    ',ta.selectionStart,ta.selectionEnd,'end');ta.dispatchEvent(new Event('input'));}if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();EditorPage.run();}});
        this.$('editor-reset').addEventListener('click',()=>{if(!confirm('Substituir o rascunho desta linguagem pelo exemplo original?'))return;delete this.data().drafts[sel.value];this.save();load(sel.value);});
        this.$('editor-clear').addEventListener('click',()=>{this.data().drafts[sel.value]='';this.save();});
        this.$('editor-copy').insertAdjacentHTML('afterend','<button id="hub-code-download" class="hub-button">↓ Baixar código</button>');
        this.$('hub-code-download').onclick=()=>this.download(EditorPage.PRESETS[sel.value].filename,ta.value,'text/plain');
        const run=EditorPage.run.bind(EditorPage);
        EditorPage.run=async()=>{
            if(sel.value!=='js')return run();
            if(this.worker){showToast('Aguarde a execução atual.','info');return;}
            this.$('editor-status-tag').textContent='Executando…';
            const code=ta.value;
            const source=`self.fetch=undefined;self.XMLHttpRequest=undefined;self.WebSocket=undefined;self.importScripts=undefined;self.onmessage=async e=>{const lines=[];const fmt=x=>{try{return typeof x==='object'?JSON.stringify(x):String(x)}catch{return String(x)}};const console={log:(...a)=>{if(lines.length<1000)lines.push(a.map(fmt).join(' ').slice(0,10000))},warn:(...a)=>console.log(...a),error:(...a)=>console.log(...a)};try{await new Function('console',e.data)(console);self.postMessage({text:lines.join('\\n')||'Executado sem saída.'})}catch(e){self.postMessage({error:e.message})}}`;
            const url=URL.createObjectURL(new Blob([source],{type:'text/javascript'}));
            let timer;
            const finish=(message,error=false)=>{clearTimeout(timer);this.worker?.terminate();this.worker=null;URL.revokeObjectURL(url);EditorPage.output(`<span class="${error?'text-rose-400':'text-emerald-400'}">${escapeHTML(message)}</span>`);this.$('editor-status-tag').textContent=error?'Erro':'Pronto';if(!error)Gamification.addXP(5,'Execução no editor');};
            try{this.worker=new Worker(url);timer=setTimeout(()=>finish('Execução interrompida após 3 segundos. Verifique loops sem fim.',true),3000);this.worker.onmessage=e=>finish(e.data.error||e.data.text,!!e.data.error);this.worker.onerror=e=>finish(e.message,true);this.worker.postMessage(code);}catch(e){finish(e.message,true);}
        };
    },
    hookTutor() {
        TutorPage.ask=async()=>{
            if(this.tutorBusy)return;
            const input=this.$('tutor-user-input'),q=input.value.trim();if(!q)return;
            if(q.length>2000){showToast('Use no máximo 2.000 caracteres.','error');return;}
            this.tutorBusy=true;input.value='';input.disabled=true;
            const send=this.$('tutor-send'),oldLabel=send.innerHTML;send.disabled=true;send.textContent='Respondendo…';
            const box=this.$('tutor-chat-box');box.setAttribute('aria-busy','true');
            try {
                const response=await fetch('/api/tutor',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pergunta:q,historico:(Gamification.state.tutorHistory||[]).filter(h=>typeof h.text==='string').slice(-4).map(h=>({q:h.q,text:h.text}))}),signal:AbortSignal.timeout(190000)});
                const result=await response.json();if(!response.ok||!result.success)throw Error(result.error||'Tutor indisponível');
                const answer=`<p class="text-teal-300"><strong>${escapeHTML(result.title||'Busca no material')}</strong> · ${escapeHTML(result.course||'CodeStart')}</p><p style="white-space:pre-wrap">${escapeHTML(result.answer)}</p>${result.code?`<pre class="overflow-x-auto bg-slate-950 p-3 rounded-xl mt-3"><code>${escapeHTML(result.code)}</code></pre>`:''}<p class="text-xs text-slate-400 mt-3">${result.mode==='ai'?'Resposta gerada por IA. Confira os exemplos antes de usar.':'Busca no material didático (sem geração por IA).'}</p>`;
                Gamification.state.tutorHistory.push({q,a:answer,text:result.answer});Gamification.state.tutorHistory=Gamification.state.tutorHistory.slice(-50);this.save();TutorPage.welcome();TutorPage.restoreHistory();
            } catch(e) {input.value=q;showToast(e.name==='TimeoutError'?'O tutor demorou para responder. Tente novamente.':e.message||'Falha ao consultar o tutor.','error');}
            finally {this.tutorBusy=false;input.disabled=false;send.disabled=false;send.innerHTML=oldLabel;box.removeAttribute('aria-busy');input.focus();}
        };
    },
    resume() { const last=this.data().lastLesson;const row=last&&this.rows.find(r=>r.course===last.course&&r.index===last.index)||this.rows.find(r=>!Gamification.state.completedLessons.includes(r.key));if(row)this.open(row);else Router.go('dashboard'); },
    open(row) {Router.go('cursos');LessonsPage.open(row.course,row.index);},
    render() {
        if(!this.$('hub-results'))return;
        this.renderResults();this.renderTasks();
        const s=Gamification.state,goal=Math.max(1,Number(s.dailyGoal)||2),count=this.data().activity[this.today()]||0;
        this.$('hub-goal').textContent=`${count} de ${goal} aulas concluídas hoje${count>=goal?' · Meta alcançada!':''}`;
        this.$('hub-goal-bar').style.width=`${Math.min(100,count/goal*100)}%`;
        this.$('hub-week').innerHTML=Array.from({length:7},(_,i)=>{const d=new Date();d.setDate(d.getDate()-6+i);const n=this.data().activity[this.today(d)]||0;return `<div class="hub-day ${n?'active':''}" title="${d.toLocaleDateString('pt-BR')}: ${n} aulas">${d.toLocaleDateString('pt-BR',{weekday:'short'}).replace('.','')}<strong>${n}</strong></div>`;}).join('');
        this.$('hub-focus-count').textContent=`${this.data().focusSessions||0} sessões de foco concluídas`;
        this.$('hub-welcome').textContent=s.studentName==='Aluno(a) CodeStart'?'Vamos dar o próximo passo?':`${s.studentName}, vamos continuar?`;
        this.$('hub-home-summary').textContent=`${s.completedLessons.length} aulas concluídas · ${s.favorites.length} favoritas · ${this.data().tasks.filter(t=>!t.done).length} tarefas no seu plano`;
    },
    renderResults() {
        const s=Gamification.state,q=this.clean(this.$('hub-query').value.trim()),course=this.$('hub-course').value;
        const filtered=this.rows.filter(r=>(course==='all'||r.course===course)&&(!q||r.search.includes(q)||this.clean(s.notes[r.key]).includes(q))&&(this.tab==='all'||this.tab==='favorites'&&s.favorites.includes(r.key)||this.tab==='notes'&&String(s.notes[r.key]||'').trim()||this.tab==='pending'&&!s.completedLessons.includes(r.key)||this.tab==='done'&&s.completedLessons.includes(r.key)));
        const pages=Math.max(1,Math.ceil(filtered.length/this.size));this.page=Math.max(1,Math.min(pages,this.page));
        this.$('hub-count').textContent=`${filtered.length} aula${filtered.length===1?'':'s'} encontrada${filtered.length===1?'':'s'}`;
        this.$('hub-page').textContent=`${this.page} / ${pages}`;this.$('hub-prev').disabled=this.page===1;this.$('hub-next').disabled=this.page===pages;
        document.querySelectorAll('[data-hub-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.hubTab===this.tab)));
        const rows=filtered.slice((this.page-1)*this.size,this.page*this.size);
        this.$('hub-results').innerHTML=rows.length?rows.map((r,i)=>`<article class="hub-result"><div><small>${escapeHTML(r.name)} · Aula ${r.index+1} ${s.completedLessons.includes(r.key)?'· ✓ Concluída':''}</small><h4>${escapeHTML(r.title)}</h4><p>${escapeHTML(this.tab==='notes'?s.notes[r.key]:r.module)}</p></div><button class="hub-button" data-open="${i}" aria-label="Abrir ${escapeHTML(r.title)}">Abrir →</button></article>`).join(''):'<div class="hub-empty">Nenhuma aula por aqui ainda.<br>Experimente outro filtro ou salve uma aula nos favoritos.</div>';
        this.$('hub-results').querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>this.open(rows[Number(b.dataset.open)]));
    },
    renderTasks() {
        const tasks=this.data().tasks;
        this.$('hub-tasks').innerHTML=tasks.length?tasks.map((t,i)=>`<div class="hub-task"><label><input type="checkbox" data-task="${i}" ${t.done?'checked':''}> <span>${escapeHTML(t.text)}</span></label><button data-remove="${i}" aria-label="Excluir tarefa ${escapeHTML(t.text)}">×</button></div>`).join(''):'<p class="hub-count">Sem tarefas. Que tal reservar alguns minutos para praticar?</p>';
        this.$('hub-tasks').querySelectorAll('[data-task]').forEach(b=>b.onchange=()=>{tasks[Number(b.dataset.task)].done=b.checked;this.save();this.render();});
        this.$('hub-tasks').querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{tasks.splice(Number(b.dataset.remove),1);this.save();this.render();});
    },
    updateTimer() {this.$('hub-timer').textContent=`${String(Math.floor(this.remaining/60)).padStart(2,'0')}:${String(this.remaining%60).padStart(2,'0')}`;},
    toggleTimer() {
        if(this.timer){this.remaining=Math.max(0,Math.ceil((this.deadline-Date.now())/1000));clearInterval(this.timer);this.timer=null;this.$('hub-timer-toggle').textContent='Continuar';this.$('hub-timer-status').textContent='Pausado';return;}
        if(this.remaining<=0)this.remaining=Number(this.$('hub-duration').value)*60;
        this.deadline=Date.now()+this.remaining*1000;this.$('hub-timer-toggle').textContent='Pausar';this.$('hub-timer-status').textContent='Concentre-se em uma tarefa';this.$('hub-duration').disabled=true;
        this.timer=setInterval(()=>{this.remaining=Math.max(0,Math.ceil((this.deadline-Date.now())/1000));this.updateTimer();if(this.remaining===0){clearInterval(this.timer);this.timer=null;this.$('hub-duration').disabled=false;this.$('hub-timer-toggle').textContent='Iniciar';this.$('hub-timer-status').textContent='Sessão concluída!';if(this.$('hub-duration').value!=='5')this.data().focusSessions=(this.data().focusSessions||0)+1;this.save();this.render();showToast('Tempo concluído! Faça uma pausa e respire.','success');}},250);
    },
    resetTimer(){clearInterval(this.timer);this.timer=null;this.remaining=Number(this.$('hub-duration').value)*60;this.updateTimer();this.$('hub-timer-toggle').textContent='Iniciar';this.$('hub-timer-status').textContent='Pronto para começar';this.$('hub-duration').disabled=false;},
    export(){this.download(`codestart-backup-${this.today()}.json`,JSON.stringify({app:'CodeStart',version:8,exportedAt:new Date().toISOString(),state:Gamification.state},null,2));},
    exportNotes(){const notes=this.rows.filter(r=>String(Gamification.state.notes[r.key]||'').trim()).map(r=>`## ${r.name} — ${r.title}\n\n${Gamification.state.notes[r.key]}`);this.download('minhas-anotacoes.md','# Minhas anotações CodeStart\n\n'+(notes.join('\n\n')||'Ainda não há anotações.'),'text/markdown');},
    validateBackup(raw) {
        if(!raw||raw.app!=='CodeStart'||raw.version!==8||!raw.state||typeof raw.state!=='object'||Array.isArray(raw.state))throw Error('Este arquivo não é um backup CodeStart V8 válido.');
        const source=raw.state,out=JSON.parse(JSON.stringify(DEFAULT_STATE));
        const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
        const safeKeys=o=>Object.keys(o).every(k=>!['__proto__','prototype','constructor'].includes(k));
        for(const [key,def] of Object.entries(out)){
            const v=source[key];if(v===undefined)continue;
            if(Array.isArray(def)){if(!Array.isArray(v)||v.length>10000)throw Error('Lista inválida no backup.');if(key==='tutorHistory'){out[key]=v.filter(h=>obj(h)&&typeof h.q==='string'&&typeof h.a==='string').map(h=>({q:h.q,a:escapeHTML(h.a)}));}else{if(v.some(x=>typeof x!=='string'))throw Error('Lista inválida no backup.');out[key]=[...new Set(v)];}}
            else if(typeof def==='number'){if(!Number.isFinite(v)||v<0||v>1e9)throw Error('Número inválido no backup.');out[key]=v;}
            else if(typeof def==='string'){if(typeof v!=='string'||v.length>10000)throw Error('Texto inválido no backup.');out[key]=v;}
            else if(obj(def)){if(!obj(v)||!safeKeys(v))throw Error('Dados inválidos no backup.');out[key]={};for(const [k,value] of Object.entries(v)){if(key==='notes'?typeof value!=='string':!Number.isFinite(value))throw Error('Dados inválidos no backup.');out[key][k]=value;}}
            else if(key==='lastStudyDate'){if(v!==null&&(typeof v!=='string'||Number.isNaN(Date.parse(v))))throw Error('Data inválida.');out[key]=v;}
        }
        const known=new Set(this.rows.map(r=>r.key));out.completedLessons=out.completedLessons.filter(k=>known.has(k));const courses=new Set(COURSES.map(c=>c.id));out.startedCourses=out.startedCourses.filter(k=>courses.has(k));out.trailCourseIds=out.trailCourseIds.filter(k=>courses.has(k));out.favorites=out.favorites.filter(k=>known.has(k));out.lives=Math.min(5,Math.floor(out.lives));out.dailyGoal=Math.max(1,Math.min(10,Math.floor(out.dailyGoal)));out.studentName=out.studentName.slice(0,100);
        out.gamesHighScore={...DEFAULT_STATE.gamesHighScore,...out.gamesHighScore};out.studyHub={tasks:[],activity:{},drafts:{},focusSessions:0};
        const h=source.studyHub;
        if(h!==undefined){if(!obj(h))throw Error('Central de estudos inválida.');if(h.tasks!==undefined){if(!Array.isArray(h.tasks)||h.tasks.length>100)throw Error('Tarefas inválidas.');out.studyHub.tasks=h.tasks.map(t=>{if(!obj(t)||typeof t.text!=='string')throw Error('Tarefa inválida.');return{id:crypto.randomUUID(),text:t.text.slice(0,180),done:t.done===true};});}
            if(h.activity!==undefined){if(!obj(h.activity))throw Error('Histórico inválido.');for(const [k,v] of Object.entries(h.activity)){if(!/^\d{4}-\d{2}-\d{2}$/.test(k)||!Number.isInteger(v)||v<0||v>639)throw Error('Histórico inválido.');out.studyHub.activity[k]=v;}}
            if(h.drafts!==undefined){if(!obj(h.drafts))throw Error('Rascunhos inválidos.');for(const [k,v] of Object.entries(h.drafts)){if(!Object.hasOwn(EditorPage.PRESETS,k)||typeof v!=='string'||v.length>500000)throw Error('Rascunho inválido.');out.studyHub.drafts[k]=v;}}
            if(h.focusSessions!==undefined){if(!Number.isInteger(h.focusSessions)||h.focusSessions<0)throw Error('Sessões inválidas.');out.studyHub.focusSessions=h.focusSessions;}
            if(h.lastLesson&&this.rows.some(r=>r.course===h.lastLesson.course&&r.index===h.lastLesson.index))out.studyHub.lastLesson={course:h.lastLesson.course,index:h.lastLesson.index};
        }
        return out;
    },
    async import(file) {this.$('hub-file').value='';if(!file)return;try{if(file.size>6000000)throw Error('O backup deve ter no máximo 6 MB.');this.pendingImport=this.validateBackup(JSON.parse(await file.text()));const s=this.pendingImport;this.$('hub-import-preview').textContent=`Estudante: ${s.studentName}\nAulas concluídas: ${s.completedLessons.length}\nFavoritos: ${s.favorites.length}\nAnotações: ${Object.values(s.notes).filter(v=>v.trim()).length}\nXP: ${s.xp}`;this.$('hub-dialog').showModal();}catch(e){this.pendingImport=null;showToast(e.message||'Não foi possível ler o backup.','error');}},
    restore(){if(!this.pendingImport)return;if(!Storage.save(this.pendingImport))return;Gamification.state=this.pendingImport;this.pendingImport=null;location.reload();}
};
