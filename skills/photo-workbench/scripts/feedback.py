"""Append-only user feedback, execution receipts and reusable rule lifecycle.

No media operations; UI writes user decisions only. Agent receipts require
existing evidence with full hashes. Skill context is generated from this ledger.
"""
import argparse, datetime as dt, hashlib, json, re, sqlite3, uuid
from pathlib import Path
import os

def write_json_atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.pending')
    with temp.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)

PROJECT=Path.cwd().resolve()
BASE=PROJECT/'data'
def stamp():return dt.datetime.now().astimezone().isoformat()
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def connect(base=None):
    base=BASE if base is None else Path(base);folder=base/'经验库';folder.mkdir(exist_ok=True)
    con=sqlite3.connect(folder/'反馈账本.sqlite',timeout=20);con.row_factory=sqlite3.Row
    con.executescript('''CREATE TABLE IF NOT EXISTS event(seq INTEGER PRIMARY KEY,id TEXT UNIQUE,at TEXT,kind TEXT,actor TEXT,payload TEXT,previous_sha TEXT,sha256 TEXT UNIQUE);
CREATE TRIGGER IF NOT EXISTS preserve_event_update BEFORE UPDATE ON event BEGIN SELECT RAISE(ABORT,'append-only feedback');END;
CREATE TRIGGER IF NOT EXISTS preserve_event_delete BEFORE DELETE ON event BEGIN SELECT RAISE(ABORT,'append-only feedback');END;''')
    return con
def events(base=None):
    con=connect(base)
    try:rows=[dict(r) for r in con.execute('SELECT * FROM event ORDER BY seq')]
    finally:con.close()
    previous=''
    for row in rows:
        row['payload']=json.loads(row['payload']);claimed=row.pop('sha256')
        assert row['previous_sha']==previous and digest(row)==claimed,'反馈账本校验失败，停止写入'
        row['sha256']=claimed;previous=claimed
    return rows
def append(kind,payload,*,actor='User',revision=None,base=None):
    # A single SQLite transaction checks revision and appends; no projection can
    # lose a committed decision after a crash.
    con=connect(base)
    try:
        con.execute('BEGIN IMMEDIATE');last=con.execute('SELECT seq,sha256 FROM event ORDER BY seq DESC LIMIT 1').fetchone();seq=last['seq'] if last else 0
        if revision is not None and (type(revision) is not int or revision!=seq):raise RuntimeError('另一页面已保存，请刷新后继续；你的草稿保留')
        row=dict(seq=seq+1,id='FB-'+uuid.uuid4().hex,at=stamp(),kind=kind,actor=actor,payload=payload,previous_sha=last['sha256'] if last else '')
        h=digest(row);con.execute('INSERT INTO event VALUES(?,?,?,?,?,?,?,?)',(row['seq'],row['id'],row['at'],row['kind'],row['actor'],json.dumps(payload,ensure_ascii=False),row['previous_sha'],h));con.commit();row['sha256']=h;return row
    finally:con.close()
def projection(base=None):
    rows=events(base);decisions={};suggestions=[];receipts={};rules={}
    for e in rows:
        p=e['payload']
        if e['kind']=='decision':decisions[p['task_id']]=dict(p,event_id=e['id'],event_sha=e['sha256'],at=e['at'])
        elif e['kind']=='suggestion':suggestions.append(dict(p,event_id=e['id'],event_sha=e['sha256'],at=e['at']))
        elif e['kind']=='execution':
            for ident in p['feedback_ids']:receipts[ident]=dict(p,event_id=e['id'],at=e['at'])
        elif e['kind']=='rule_proposal':rules[p['rule_id']]=dict(p,status='candidate',validations=[],adopted=False,activation=None)
        elif e['kind']=='rule_adoption' and p['rule_id'] in rules:
            rules[p['rule_id']]['adopted']=p['adopt']
            if not p['adopt'] and rules[p['rule_id']]['status']=='active':rules[p['rule_id']]['status']='paused'
        elif e['kind']=='rule_validation' and p['rule_id'] in rules:rules[p['rule_id']]['validations'].append(p)
        elif e['kind']=='rule_activation' and p['rule_id'] in rules:rules[p['rule_id']].update(status='active',activation=dict(p,event_id=e['id']))
        elif e['kind']=='rule_retirement' and p['rule_id'] in rules:rules[p['rule_id']]['status']='retired'
    return dict(revision=rows[-1]['seq'] if rows else 0,decisions=decisions,suggestions=suggestions,receipts=receipts,rules=rules)
def pins(paths,base=None):
    root=PROJECT if base is None else Path(base).parent
    result=[]
    for name in paths:
        f=(root/name).resolve()
        if not f.is_relative_to(root.resolve()) or not f.is_file() or f.is_symlink():raise ValueError('证据须为项目内实际文件')
        result.append(dict(path=str(f.relative_to(root)),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    if not result:raise ValueError('缺少真实证据')
    return result
def check_pins(records,base=None):
    if not records:raise ValueError('缺少证据')
    actual=pins([r['path'] for r in records],base)
    if actual!=records:raise ValueError('证据已变化，不能作为当前执行或规则证明')
def save_suggestion(data,base=None):
    text=data.get('text');scope=data.get('scope')
    if not isinstance(text,str) or not text.strip() or len(text)>20000:raise ValueError('请填写具体意见')
    if scope not in {'workflow','taste','skill','album','other'}:raise ValueError('意见范围无效')
    state=projection(base);fingerprint=digest(dict(text=re.sub(r'\s+',' ',text.strip()),scope=scope));same=next((e for e in state['suggestions'] if e['fingerprint']==fingerprint),None)
    return append('suggestion',dict(text=text,scope=scope,context=data.get('context','')[:1000],fingerprint=fingerprint,duplicate_of=same['event_id'] if same else None),revision=data.get('revision'),base=base)
def record_execution(data,base=None):
    state=projection(base);raw={e['id']:e for e in events(base)};ids=data.get('feedback_ids',[])
    if not ids or any(x not in raw or raw[x]['kind'] not in {'suggestion','decision'} for x in ids):raise ValueError('落实回执必须对应原始反馈')
    if data.get('result') not in {'applied','needs_user','blocked','not_adopted'} or not data.get('summary'):raise ValueError('须有明确落实结果')
    evidence=pins(data.get('evidence',[]),base)
    return append('execution',dict(feedback_ids=ids,source_shas={x:raw[x]['sha256'] for x in ids},summary=data['summary'],result=data['result'],evidence=evidence),actor='Agent',base=base)
def propose_rule(data,base=None):
    rows={e['id']:e for e in events(base)};ids=data.get('source_feedback_ids',[])
    if not ids or any(x not in rows or rows[x]['kind'] not in {'suggestion','decision'} for x in ids):raise ValueError('规则需要可追溯的本人原始反馈')
    if any(not isinstance(data.get(k),str) or not data[k].strip() for k in ['text','scope','boundary','rationale','generalization','counterexample']):raise ValueError('规则须说明可复用主张、范围、边界、理由、跨场景适用方式和反例')
    if data['scope'] not in {'workflow','taste','skill','album'}:raise ValueError('规则适用领域无效')
    state=projection(base);fingerprint=digest(dict(text=re.sub(r'\s+',' ',data['text'].strip()),scope=data['scope']))
    same=next((r for r in state['rules'].values() if r['fingerprint']==fingerprint),None)
    if same:return dict(duplicate_of=same['rule_id'],rule_id=same['rule_id'])
    ident='GR-'+uuid.uuid4().hex[:12]
    return append('rule_proposal',dict(rule_id=ident,text=data['text'],scope=data['scope'],boundary=data['boundary'],rationale=data['rationale'],generalization=data['generalization'],counterexample=data['counterexample'],source_feedback_ids=ids,source_shas={x:rows[x]['sha256'] for x in ids},fingerprint=fingerprint,conflicts_with=data.get('conflicts_with',[])),actor='Agent',base=base)
def validate_rule(data,base=None):
    state=projection(base);rule=state['rules'].get(data.get('rule_id'))
    if not rule:raise ValueError('规则不存在')
    if not data.get('case_id') or not data.get('context_key') or not data.get('summary') or data.get('passed') is not True:raise ValueError('验证须有独立样本、场景标识、结果和说明')
    evidence=pins(data.get('evidence',[]),base)
    if any(v['case_id']==data['case_id'] or v['evidence']==evidence for v in rule['validations']):raise ValueError('同一轮或同一证据不能重复计作多轮')
    return append('rule_validation',dict(rule_id=data['rule_id'],case_id=data['case_id'],context_key=data['context_key'],summary=data['summary'],passed=True,evidence=evidence),actor='Agent',base=base)
def activate_rule(ident,base=None):
    state=projection(base);rule=state['rules'].get(ident)
    if not rule or not rule['adopted'] or len(rule['validations'])<2 or len({v['context_key'] for v in rule['validations']})<2:raise ValueError('规则需本人采用，并在至少两个场景完成有证据的验证')
    if rule['conflicts_with']:raise ValueError('规则仍有冲突，先解决并另立有来源的新提议')
    for result in rule['validations']:check_pins(result['evidence'],base)
    return append('rule_activation',dict(rule_id=ident,rule_sha=digest(rule),source_feedback_ids=rule['source_feedback_ids']),actor='Agent',base=base)
def context(base=None):
    base=BASE if base is None else Path(base);state=projection(base)
    active=[]
    for r in state['rules'].values():
        if r['status']!='active':continue
        if not r['adopted'] or r['conflicts_with']:continue
        for v in r['validations']:check_pins(v['evidence'],base)
        active.append(r)
    pending=[e for e in events(base) if e['kind'] in {'suggestion','decision'} and (e['id'] not in state['receipts'] or state['receipts'][e['id']]['result']!='applied')]
    result=dict(at=stamp(),ledger_revision=state['revision'],active_rules=active,pending_feedback=pending,context_sha=digest(dict(active_rules=active,pending_feedback=pending)),instruction='先完整阅读原反馈与生效规则；具体执行后按原事件留落实回执。候选不能当生效标准。')
    folder=base/'执行记录/Skill上下文';folder.mkdir(parents=True,exist_ok=True);target=folder/(dt.datetime.now().strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:6]+'.json');result['context_file']=str(target.relative_to(base));write_json_atomic(target,result)
    write_json_atomic(base/'经验库/有效规则.json',dict(revision=state['revision'],rules=active))
    lines=['# 当前生效规则','', '由有来源的采用、验证和生效事件派生；完整原话在反馈账本中。','']
    for r in active:lines.extend(['## '+r['text'],'',r['boundary'],'','来源：'+', '.join(r['source_feedback_ids']),''])
    if not active:lines.append('目前没有通过本账本完成采用及多轮验证的新增规则。既有用户明确要求仍以项目真源和 Skill 正文为准。')
    (base/'经验库/Golden_Rules.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');return result
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['context','execution','propose','validate','activate']);parser.add_argument('--file');parser.add_argument('--rule-id');parser.add_argument('--root',required=True);args=parser.parse_args();PROJECT=Path(args.root).resolve();BASE=PROJECT/'data'
    data=json.loads(Path(args.file).read_bytes()) if args.file else {}
    value=context() if args.action=='context' else record_execution(data) if args.action=='execution' else propose_rule(data) if args.action=='propose' else validate_rule(data) if args.action=='validate' else activate_rule(args.rule_id)
    print(json.dumps(value,ensure_ascii=False))
