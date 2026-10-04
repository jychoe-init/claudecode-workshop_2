#!/usr/bin/env python3
"""Build a private instructor v15 from the supplied original. Never overwrite it."""
import argparse, hashlib, html, json, re
from pathlib import Path
from bs4 import BeautifulSoup

LABS=[
 ('lab1','반복작업 — 우리 팀 양식 스킬','20분 초안','기존 회의록·주간보고 스킬을 우리 팀 양식으로 바꾸거나, 새 반복업무 스킬을 만듭니다.',
 [('목표','누가 어떤 결과를 읽는지, 반복해서 사용할 업무를 정합니다.'),('결정','길 A(기존 변형) 또는 길 B(신규), 필수 항목·근거·미정 값 처리 기준을 워크시트에 적습니다.'),('제작','자기 말로 Claude에게 요청합니다. 양식과 지시문을 분리하고 중요한 규칙의 위치를 확인합니다.'),('예측·실행','입력에서 미정인 항목의 예상 결과를 적고 자신이 만든 스킬을 호출합니다.'),('확인·수정','다른 입력 또는 바꾼 양식으로 재실행하고 원문과 결과를 비교합니다.')],
 ['팀 기준을 반영한 스킬·양식과 실제 호출 출처를 확인했습니다.','두 실행 결과를 비교하고 수정 또는 재사용 결과를 설명할 수 있습니다.']),
 ('lab2','연결 — API 업무 자동화','20분 초안','휴가 조회·조건 판단·질문·상신·처리 상태 확인을 하나의 스킬로 구성합니다.',
 [('목표','조회 결과 요약을 넘어 실습 시스템에 신청을 등록하고 상태를 다시 확인합니다.'),('결정','신청 전 조회할 정보, 질문·내용 확인 조건, 중복·일수 부족·응답 끊김에서의 행동을 정합니다.'),('제작','API 명세와 HTTP 클라이언트를 이용해 업무 절차를 스킬로 만듭니다. 클라이언트에 완성 업무 흐름을 숨기지 않습니다.'),('예측·실행','예상 신청 일수·상태를 적고, 제출 내용을 확인한 뒤 상신합니다. 생성된 ID로 재조회합니다.'),('확인·수정','실패 또는 중복 사례를 실행하고 실제 기록과 잔여 일수로 결과를 확인합니다.')],
 ['자신이 만든 스킬로 상신했고 실제 신청 상태를 재조회했습니다.','실패 또는 중복 사례의 결과와 추가 신청 여부를 확인했습니다.']),
 ('lab3','프롬프트 점검·공유','18분 초안','prompt-coach로 요청을 개선하고 결과·사용량을 비교한 뒤 저장 지시문과 공유 준비를 점검합니다.',
 [('목표','원본보다 좋은 결과의 기준을 먼저 정하고 변경 효과를 실제 실행으로 살펴봅니다.'),('결정','좋은 결과의 조건, 유지할 의도, 고칠 저장 지시문 결함을 선택합니다.'),('점검·비교','제공 prompt-coach로 개선문을 만든 뒤 원본과 개선본을 같은 입력·모델의 새 세션에서 실행합니다.'),('확인·수정','실제 출력·입출력·캐시 토큰·CLI 추정 비용을 비교합니다. doctor prompt-audit으로 저장 지시문을 점검하고 선택한 결함을 고칩니다.'),('공유','용도·입력·주의사항 세 줄을 정하고 README를 완성합니다. gitignore·diff를 확인한 뒤 선택한 파일을 커밋합니다.')],
 ['실제 결과·사용량 비교와 저장 지시문 수정 근거를 남겼습니다.','개인 입력·측정·토큰을 제외한 사용 안내와 커밋을 준비했습니다.'])]

def frag(text):return BeautifulSoup(text,'html.parser')
def block(text,label,key,kind='prompt'):
 return f'<div class="code-wrap {kind}" data-code-kind="{kind}"><div class="code-head"><span class="code-label">{html.escape(label)}</span><button class="ws-copy" type="button" data-copy-code="{key}">복사</button></div><pre id="{key}"><code>{html.escape(text)}</code></pre></div>'
def build(source):
 soup=BeautifulSoup(source,'html.parser')
 protected=['settings-overview','t0','a1','a2','a3','a4','a5','part-a-recap']
 before={key:str(soup.find(id=key)) for key in protected}
 manifest=str(soup.find(id='section-view-manifest'))
 style=soup.new_tag('style',id='v15-lab-layout')
 style.string="""
 #lab1 table,#lab2 table,#lab3 table,#wrapup table{width:100%;border-collapse:collapse;margin:20px 0}
 #lab1 th,#lab1 td,#lab2 th,#lab2 td,#lab3 th,#lab3 td,#wrapup th,#wrapup td{padding:11px 14px;text-align:left;vertical-align:top;border-bottom:1px solid rgba(113,139,165,.3);line-height:1.65}
 #lab1 th,#lab2 th,#lab3 th,#wrapup th{background:rgba(113,139,165,.1);font-weight:700}
 #lab1 th:first-child,#lab2 th:first-child,#lab3 th:first-child,#wrapup th:first-child{width:130px}
 #lab1 .cp-title,#lab2 .cp-title,#lab3 .cp-title{color:inherit;font-weight:700}
 """
 soup.head.append(style)
 pb=soup.find(id='pb');wrap=soup.find(id='wrapup')
 if not pb or not wrap:raise ValueError('Original must contain pb and wrapup sections')
 for sec in list(soup.find_all('section')):
  if re.fullmatch(r'(m[1-7]|b[1-4]|lab[1-3])',sec.get('id','')):sec.decompose()
 pb.clear();pb.append(frag('<div class="task-head"><span class="task-num">PART B / SUPER LAB</span><h2>직접 만드는 세 가지 업무 실습</h2><span class="time-badge">본문 58분 초안 · 준비·마무리 별도</span></div><p class="task-goal">반복작업 스킬 제작 → API 업무 자동화 → 프롬프트 점검·공유. 세 랩은 각각 새 작업 공간에서 시작합니다. 시간은 리허설로 조정합니다.</p><div class="callout tip"><span class="co-title">진행 방식</span>목표 → 내 결정 → 제작 요청 → 예측·실행 → 확인·수정. 코치는 요청받은 현재 범위의 파일을 작성하고 실행할 수 있습니다. 기준과 결과 판단은 참가자가 합니다.</div>'))
 pb.append(frag(block('git clone --branch ch4-three-labs-api https://github.com/jychoe-init/claudecode-workshop_2.git\ncd claudecode-workshop_2\nbash setup.sh','터미널 · 검토용 3랩 브랜치 준비','v15-setup','terminal')))
 pb.append(frag('<p>Claude Code 2.1.283 이상을 확인하세요. 사용 실행기가 cca라면 run 명령에 --command cca를 추가합니다. API 주소·토큰 준비는 Lab 2에만 필요하며 토큰은 Claude에 입력하지 않습니다.</p>'))
 for lab,title,duration,goal,steps,dod in LABS:
  body=f'<section class="task mission" id="{lab}"><div class="task-head"><span class="task-num">{lab.upper()}</span><h2>{title}</h2><span class="time-badge">{duration}</span></div><p class="task-goal">{goal}</p>'
  if lab=='lab2':
   body+='<div class="callout tip"><span class="co-title">API 준비</span>공용 API가 제공되면 키트 README의 주소·토큰 등록 절차를 따릅니다. 로컬 대체는 아래 순서로 먼저 준비합니다. 데이터는 모두 가상이며 pending은 상신 상태입니다.</div>'
   body+=block('.venv/bin/python workshop.py serve --state .local/api','터미널 1 · 로컬 API 서버','v15-api-server','terminal')
   body+=block('.venv/bin/python workshop.py init lab2 --root workspaces/lab2\n.venv/bin/python workshop.py configure --workspace workspaces/lab2 --local-demo','터미널 2 · 새 작업 공간과 로컬 연결','v15-api-config','terminal')
   body+=block('.venv/bin/python workshop.py run --workspace workspaces/lab2','터미널 2 · 준비 후 Claude 시작','v15-lab2-start','terminal')
  else:
   body+=block(f'.venv/bin/python workshop.py init {lab} --root workspaces/{lab}\n.venv/bin/python workshop.py run --workspace workspaces/{lab}','터미널 · 새 작업 공간',f'v15-{lab}-start','terminal')
  body+=block(f'/workshop:workshop-coach {lab}','Claude 입력창 · 가이드 시작',f'v15-{lab}-coach')
  body+='<table><thead><tr><th>과정</th><th>참가자가 할 일</th></tr></thead><tbody>'+''.join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a,b in steps)+'</tbody></table>'
  if lab=='lab1':body+='<table><thead><tr><th>길</th><th>출발점</th><th>내가 바꿀 것</th></tr></thead><tbody><tr><td>A · 변형</td><td>회의록·주간보고 시작본</td><td>우리 팀 양식과 판단 기준</td></tr><tr><td>B · 신규</td><td>새 반복업무</td><td>목적·입력·출력·금지사항을 갖춘 스킬</td></tr></tbody></table>'
  if lab=='lab3':
   body+=block('/workshop:prompt-coach inputs/original-prompt.txt','Claude 입력창 · 제공 코치 활용','v15-prompt-coach')
   body+=block('python3 tools/compare.py --original inputs/original-prompt.txt --improved artifacts/improved-prompt.txt','Lab 3 작업 공간 터미널 · 개선문 준비 후 실행','v15-compare','terminal')
   body+=block('/doctor prompt-audit inspection-target','Claude 입력창 · 저장 지시문 점검','v15-audit')
   body+='<div class="callout warn"><span class="co-title">비교 해석</span>실제 CLI 사용량을 읽습니다. 응답 글자 수를 토큰·비용으로 대체하지 않습니다. 캐시 차이와 모델 일치를 함께 확인하며 코치 비용을 분리 측정하지 않았으면 미측정으로 남깁니다. 단일 비교 결과를 모든 업무에 일반화하지 않습니다.</div>'
  body+='<p>막히면 “힌트”, 현재 결과는 “확인해줘”, 위치는 “어디야”, 다음 행동은 “다음”으로 요청하세요. 완성 예시는 명시적으로 요청한 경우에만 사용하고 워크시트에 기록합니다.</p>'
  body+='<div class="checkpoint dod"><div class="cp-title">완료 기준</div>'+''.join(f'<label class="cp-item"><input type="checkbox" data-cp="{lab}-{i}"><span>{text}</span></label>' for i,text in enumerate(dod,1))+'</div></section>'
  wrap.insert_before(frag(body))
 wrap.clear();wrap.append(frag('<div class="task-head"><span class="task-num">WRAP UP</span><h2>내 업무에 가져갈 것</h2></div><table><thead><tr><th>축</th><th>확인할 결과</th></tr></thead><tbody><tr><td>Repeat</td><td>우리 팀 양식과 기준을 담은 스킬</td></tr><tr><td>Connect</td><td>API로 업무를 처리하고 상태까지 확인하는 스킬</td></tr><tr><td>Prompt</td><td>원본·개선본의 실제 결과와 사용량 비교</td></tr><tr><td>Inspect · Share</td><td>고친 지시문과 README·gitignore·커밋</td></tr></tbody></table><h3>NEXT CHAPTER</h3><p>오늘 검증한 작업을 /goal·헤드리스 실행으로 확장합니다. plugin eval은 반복 평가를 위한 심화 주제로 다룹니다.</p>'))
 flow=soup.find(id='flow')
 if flow:
  goal=flow.find(class_='task-goal')
  if goal:goal.string='Part A의 설정·권한·Hook·MCP 학습을 바탕으로, Part B에서는 서로 다른 세 업무 사례를 직접 만들고 실행합니다.'
  for old in list(flow.select('.workshop-flow-original')):old.decompose()
  ol=flow.select_one('.workshop-flow-guide ol')
  if ol:
   for a in list(ol.select('a[href]')):
    if re.fullmatch(r'#(m[1-7]|b[1-4]|lab[1-3])',a.get('href','')):a.find_parent('li').decompose()
   for lab,title,_,goal,_,_ in LABS:ol.append(frag(f'<li><a class="flow-step" href="#{lab}"><span class="flow-step-number">{lab.upper()}</span><span class="flow-step-content"><strong>{title}</strong><span class="flow-step-summary">{goal}</span></span></a></li>'))
  for svg in list(flow.find_all('svg')):svg.decompose()
  svg='<svg role="img" aria-label="세 랩 흐름" viewBox="0 0 1100 180" style="width:100%;height:auto">'
  for i,(lab,title,_,_,_,_) in enumerate(LABS):
   x=15+i*365
   svg+=f'<rect x="{x}" y="20" width="340" height="125" rx="14" fill="#10283f" stroke="#4e86ad"/><text x="{x+20}" y="56" fill="#82d3ff" font-size="15">{lab.upper()}</text><text x="{x+20}" y="90" fill="#ffffff" font-size="18">{html.escape(title)}</text><text x="{x+20}" y="121" fill="#c5d8e5" font-size="13">결정 → 제작 → 예측·실행 → 확인</text>'
  flow.append(frag(svg+'</svg>'))
 for parent in list(soup.select('.sidenav, #reading-toc-list')):
  for a in list(parent.select('a[href]')):
   if re.fullmatch(r'#(m[1-7]|b[1-4]|lab[1-3])',a.get('href','')):
    victim=a.find_parent('li') if parent.name in ['ol','ul'] else a
    if victim:victim.decompose()
  for lab,title,_,_,_,_ in LABS:
   parent.append(frag(f'<li data-toc-entry><a data-reading-jump="{lab}" href="#{lab}"><span class="toc-title">{title}</span></a></li>' if parent.name in ['ol','ul'] else f'<a data-nav="{lab}" href="#{lab}">{title}</a>'))
 segments=soup.find(id='segments')
 if segments:
  for item in list(segments.select('[data-task]')):
   if re.fullmatch(r'(m[1-7]|b[1-4]|lab[1-3])',item.get('data-task','')):item.decompose()
  for lab,title,duration,_,_,_ in LABS:segments.append(frag(f'<button class="seg" data-task="{lab}" style="flex:{20 if lab!="lab3" else 18}" title="{title}"><span class="fill"></span><span class="seg-txt">{lab.upper()}</span></button>'))
 for script in soup.find_all('script'):
  text=script.string or script.get_text()
  if 'var taskGroups = {' in text:
   match=re.search(r'var taskGroups = \{([\s\S]*?)\n  \};',text)
   if not match:raise ValueError('taskGroups format changed; inspect before editing')
   old=match.group(1);lines=[line for line in old.splitlines() if not re.match(r'\s*(m[1-7]|b[1-4]|lab[1-3])\s*:',line)]
   kept='\n'.join(lines).rstrip().rstrip(',')
   replacement='var taskGroups = {'+kept+',\n'+',\n'.join(f'    {lab}: ["{lab}-1", "{lab}-2"]' for lab,*_ in LABS)+'\n  };'
   text=text[:match.start()]+replacement+text[match.end():]
   text=re.sub(r'doneCount \+ "/\d+"','doneCount + "/" + Object.keys(taskGroups).length',text)
   script.string=text
 hero=soup.find('h1').find_parent('header') if soup.find('h1') else None
 if hero:
  for n in list(hero.find_all(string=True)):
   t=str(n).replace('S1–S7','3개 업무 랩').replace('7 Module','3 Lab').replace('4 Mission','3 Lab').replace('모듈별 진행','Part B 본문 58분 초안').replace('2026.09','2026.10')
   if t!=str(n):n.replace_with(t)
  count=hero.find(id='progress-count')
  if count:count.string='0/9'
 count=soup.find(id='progress-count')
 if count:count.string='0/9'
 for label in soup.select('.timeline-label'):
  if label.find(id='progress-count') is None and 'min' in label.get_text():label.string='Part B 58 min 초안'
 persistence=soup.new_tag('script',id='v15-lab-progress')
 persistence.string="""(function(){
 const key='ccw.ch4.v15.lab-checks';
 const boxes=Array.from(document.querySelectorAll('input[data-cp^="lab"]'));
 let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch(_){}
 boxes.forEach(box=>{box.checked=saved[box.dataset.cp]===true});
 document.addEventListener('change',event=>{
  if(!boxes.includes(event.target))return;
  try{localStorage.setItem(key,JSON.stringify(Object.fromEntries(boxes.map(box=>[box.dataset.cp,box.checked]))))}catch(_){}
 });
 if(boxes.length)boxes[0].dispatchEvent(new Event('change',{bubbles:true}));
})();"""
 soup.body.append(persistence)
 rendered=str(soup).replace('PART B / S1–S7 슈퍼랩','PART B / 업무 실습 3랩')
 after=BeautifulSoup(rendered,'html.parser')
 for key,original in before.items():assert str(after.find(id=key))==original,('Part A changed',key)
 assert str(after.find(id='section-view-manifest'))==manifest,'Presentation manifest changed'
 ids=[n['id'] for n in after.select('[id]')];assert len(ids)==len(set(ids)),'Duplicate IDs'
 for lab,*_ in LABS:assert after.find(id=lab)
 return rendered,{'protected_sections_unchanged':protected,'presentation_manifest_unchanged':True,'labs':[x[0] for x in LABS]}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--out',required=True);p.add_argument('--report',required=True);a=p.parse_args()
 source=Path(a.source);out=Path(a.out)
 if source.resolve()==out.resolve():raise ValueError('Use a new version file')
 raw=source.read_text();result,report=build(raw);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(result)
 report.update(source_sha256=hashlib.sha256(raw.encode()).hexdigest(),output_sha256=hashlib.sha256(result.encode()).hexdigest())
 Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'output':str(out),'checks':report},ensure_ascii=False))
if __name__=='__main__':main()
