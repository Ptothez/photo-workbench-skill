"""Create a new personalized workbench only after its profile is confirmed."""
import argparse,json,shutil
from pathlib import Path
def create(profile_path,destination):
    profile=json.loads(Path(profile_path).read_text(encoding='utf-8'));required=['purpose','source_roots','stages','review_kinds','update_trigger','collections']
    if profile.get('confirmed_by_user') is not True or any(not profile.get(k) for k in required):raise ValueError('先与使用者确认目标、来源、流程、分类、审核方式与触发条件，再创建工作台')
    if profile['update_trigger']!='manual_message':raise ValueError('此起点只实现会话通知后按批执行；其他触发需单独设计和授权')
    for c in profile['collections']:
        if not all(c.get(k) for k in ['id','title','description']):raise ValueError('每个分类需要 id、名称和用途')
    dest=Path(destination).resolve();dest.mkdir(parents=True,exist_ok=False);skill=Path(__file__).resolve().parents[1];(dest/'data').mkdir();(dest/'assets').mkdir()
    for name in ['feedback.py','start.py']:
        shutil.copyfile(skill/'scripts'/name,dest/name)
    for f in (skill/'assets').iterdir():
        if f.is_file() and f.name!='index.html':shutil.copyfile(f,dest/'assets'/f.name)
    shutil.copyfile(skill/'assets/index.html',dest/'index.html')
    (dest/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,value in [('catalog.json',[]),('review_tasks.json',[]),('collections.json',[]),('projects.json',[]),('legacy_feedback.json',{})]:
        (dest/'data'/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    (dest/'README.md').write_text('用户确认的目标、流程与分类见 profile.json。\n手动启动：python start.py --port 8932\n每次处理照片前：python feedback.py context --root .\n需要 Agent 在真实盘点、看图与核验后更新 data/，空工作台不表示已完成筛选。\n',encoding='utf-8');return dest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--destination',required=True);a=p.parse_args();print(create(a.profile,a.destination))
