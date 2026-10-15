"""UI regression on copied SQLite DB and isolated Edge profile.
Real CDP mouse input; playback adapter is a test double, not a YouTube benchmark.
"""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
import websockets

ROOT = Path(__file__).resolve().parents[1]
SCR = Path(os.environ['LOCALAPPDATA']) / 'hermes/cache/scratch'
VENV = Path(os.environ['LOCALAPPDATA']) / 'hermes/hermes-agent/venv/Scripts/python.exe'
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
RUN = Path(tempfile.mkdtemp(prefix='player-check-', dir=SCR))
REPORT = {'test_scope': 'Real DOM/CDP input; isolated database; mock playback API', 'checks': []}

def check(name, condition, details=None):
    REPORT['checks'].append({'name': name, 'pass': bool(condition), 'details': details})
    print(('PASS ' if condition else 'FAIL ') + name, details or '', flush=True)
    if not condition:
        raise AssertionError(name)

async def test(ws, port):
    async with websockets.connect(ws, max_size=None) as sock:
        mid = 0
        errors = []
        async def send(method, **params):
            nonlocal mid
            mid += 1
            await sock.send(json.dumps({'id': mid, 'method': method, 'params': params}))
            while True:
                msg = json.loads(await asyncio.wait_for(sock.recv(), 30))
                if msg.get('method') == 'Runtime.exceptionThrown':
                    errors.append(msg['params']['exceptionDetails'])
                if msg.get('id') == mid:
                    if 'error' in msg:
                        raise RuntimeError(msg['error'])
                    return msg.get('result', {})
        async def ev(code):
            r = await send('Runtime.evaluate', expression=code, awaitPromise=True, returnByValue=True)
            if 'exceptionDetails' in r:
                raise RuntimeError(r['exceptionDetails'])
            return r.get('result', {}).get('value')
        async def mouse(kind, x, y, **args):
            return await send('Input.dispatchMouseEvent', type=kind, x=x, y=y, **args)
        async def click(x, y):
            await mouse('mouseMoved', x, y)
            await mouse('mousePressed', x, y, button='left', buttons=1, clickCount=1)
            await mouse('mouseReleased', x, y, button='left', buttons=0, clickCount=1)
        async def size(w, h=950):
            await send('Emulation.setDeviceMetricsOverride', width=w, height=h, deviceScaleFactor=1, mobile=False)
            await asyncio.sleep(.4)
        await send('Runtime.enable')
        await send('Page.enable')
        await size(1500)
        await send('Page.navigate', url=f'http://127.0.0.1:{port}/')
        for _ in range(150):
            if await ev("typeof allVideos!=='undefined' && allVideos.length >= 5"):
                break
            await asyncio.sleep(.2)
        check('Real dashboard loaded', await ev('allVideos.length >= 5'))
        # This fixture exercises actual navigation/layout/handlers without playing personal videos.
        await ev('''window.__rateCalls=[];
          window.__fixturePlayer={getPlaybackRate:()=>LB.rate||1,
            setPlaybackRate:r=>window.__rateCalls.push(r), getDuration:()=>600,
            getCurrentTime:()=>0, getPlayerState:()=>2, seekTo:()=>{}};
          currentPlayer=()=>window.__fixturePlayer;
          createYTPlayer=()=>{document.getElementById('lb-frame').innerHTML='<div style="height:100%;display:grid;place-items:center;color:white">UI TEST — playback adapter</div>';};
          markSeen=()=>{};
          LB.queue=allVideos.slice(0,7).map(v=>v.video_id); LB.idx=3; LB.context='channel';
          showLightbox();''')
        await asyncio.sleep(.8)
        check('Controls belong to central card', await ev("document.querySelector('.lb-main').contains(document.querySelector('.lb-bottom')) && document.querySelector('.lb-main').contains(document.getElementById('lb-progress'))"))
        check('Exactly one copy of controls', await ev("document.querySelectorAll('#lb-speed-btn').length===1 && document.querySelectorAll('#lb-progress').length===1"))
        data = await ev('''(()=>{const s=document.querySelector('.lb-stage'), m=document.querySelector('.lb-main'),d=document.querySelector('.lb-dialog');return {grid:getComputedStyle(s).display,bg:getComputedStyle(d).backgroundColor,border:getComputedStyle(d).borderWidth,mainWidth:m.getBoundingClientRect().width,sideWidth:document.getElementById('lb-side-prev').getBoundingClientRect().width,farWidth:document.getElementById('lb-side-prev2').getBoundingClientRect().width};})()''')
        check('Transparent shell and staircase sizes', data['grid']=='grid' and data['bg']=='rgba(0, 0, 0, 0)' and data['border']=='0px' and data['mainWidth']>data['sideWidth']>data['farWidth'], data)
        for suffix, offset in [('prev2',-2),('prev',-1),('next',1),('next2',2)]:
            check('Correct queue preview '+suffix, await ev(f"document.getElementById('lb-side-{suffix}').dataset.videoId === LB.queue[LB.idx+({offset})]"))
        for w,h in [(1500,950),(1366,768),(1200,800),(1000,700),(860,700),(700,800),(480,800)]:
            await size(w,h)
            rects = await ev('''(()=>{const m=document.querySelector('.lb-main').getBoundingClientRect(); const cs=[...document.querySelectorAll('.lb-bottom button, .lb-progress-wrap')].filter(e=>e.getBoundingClientRect().width>0).map(e=>({id:e.id||e.className,r:e.getBoundingClientRect().right,l:e.getBoundingClientRect().left,b:e.getBoundingClientRect().bottom}));const sides=[...document.querySelectorAll('.lb-side:not(.lb-side-far)')].filter(e=>getComputedStyle(e).display!=='none').map(e=>({l:e.getBoundingClientRect().left,r:e.getBoundingClientRect().right}));return {w:innerWidth,main:{l:m.left,r:m.right,b:m.bottom,t:m.top},controls:cs,sides,overflow:document.querySelector('.lb-bottom').scrollWidth>document.querySelector('.lb-bottom').clientWidth+1};})()''')
            valid = all(c['l'] >= rects['main']['l']-1 and c['r'] <= rects['main']['r']+1 and c['b'] <= rects['main']['b']+1 for c in rects['controls'])
            valid = valid and all(c['l']>=0 and c['r']<=w for c in rects['sides']) and not rects['overflow']
            check(f'Contained controls/previews {w}x{h}',valid,rects)
        await size(1500)
        await mouse('mouseMoved', 1, 1)
        await ev("document.querySelector('.lb-speed-btn').click()")
        await asyncio.sleep(.3)
        track = await ev("(()=>{let r=document.getElementById('lb-speed-range').getBoundingClientRect();return {x:r.x+r.width/2,top:r.top,bottom:r.bottom,height:r.height}})()")
        # Drag min -> max -> min, through every discrete step; use actual pointer capture.
        await mouse('mouseMoved', track['x'], track['bottom'])
        await mouse('mousePressed',track['x'],track['bottom'],button='left',buttons=1,clickCount=1)
        measured=[]
        for step in list(range(8)) + list(range(6,-1,-1)):
            y=track['bottom']-track['height']*step/7
            await mouse('mouseMoved',track['x'],y,button='left',buttons=1)
            d=await ev("(()=>{let r=document.getElementById('lb-speed-thumb').getBoundingClientRect();return {rate:LB.rate,y:r.y+r.height/2,api:window.__rateCalls.at(-1),aria:document.getElementById('lb-speed-range').getAttribute('aria-valuenow')}})()")
            expected=.25+step*.25
            check('Drag step '+str(expected), d['rate']==expected and d['api']==expected and abs(d['y']-y)<2,d)
            measured.append(d)
        await mouse('mouseReleased',track['x'],track['bottom'],button='left',buttons=0,clickCount=1)
        REPORT['drag_samples']=measured
        for rate in [.25,.5,.75,1,1.25,1.5,1.75,2]:
            p=await ev(f"(()=>{{const e=document.querySelector('.lb-speed-tick[data-rate=\"{rate}\"]');const r=e.getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
            await click(p['x'],p['y'])
            d=await ev("(()=>{const r=document.getElementById('lb-speed-thumb').getBoundingClientRect();return {rate:LB.rate,y:r.y+r.height/2}})()")
            check('Badge/knob agreement '+str(rate),d['rate']==rate and abs(d['y']-p['y'])<2,d)
        await ev("document.getElementById('lb-speed-range').focus()")
        await send('Input.dispatchKeyEvent',type='keyDown',key='Home',code='Home',windowsVirtualKeyCode=36)
        await send('Input.dispatchKeyEvent',type='keyUp',key='Home',code='Home',windowsVirtualKeyCode=36)
        check('Keyboard Home minimum',await ev('LB.rate===0.25'))
        await ev('toggleSpeedMenu()')
        # Visible slivers must accept hover, and rise above central card.
        for suffix in ['prev','next']:
            point=await ev(f'''(()=>{{const e=document.getElementById('lb-side-{suffix}'),r=e.getBoundingClientRect();for(let x=r.left+2;x<r.right-2;x+=2){{let t=document.elementFromPoint(x,r.y+r.height/2);if(t&&e.contains(t))return {{x,y:r.y+r.height/2}}}}return null}})()''')
            check('Preview reachable '+suffix,point is not None,point)
            await mouse('mouseMoved',point['x'],point['y']); await asyncio.sleep(.3)
            check('Hover lifts '+suffix,await ev(f"getComputedStyle(document.getElementById('lb-side-{suffix}')).zIndex==='11' && getComputedStyle(document.getElementById('lb-side-{suffix}')).opacity==='1'"))
            await mouse('mouseMoved',1,1); await asyncio.sleep(.3)
        # Far previews are opaque passive scenery; near previews alone are interactive.
        for theme in ['light','dark']:
            await ev(f"document.documentElement.dataset.theme='{theme}'")
            d=await ev("""(()=>{let a=[...document.querySelectorAll('.lb-side')];return a.map(e=>({far:e.classList.contains('lb-side-far'),opacity:getComputedStyle(e).opacity,shade:getComputedStyle(e,'::after').backgroundColor,bg:getComputedStyle(e).backgroundColor,shadow:getComputedStyle(e).boxShadow}));})()""")
            check('Opaque shaded cards '+theme,all(x['opacity']=='1' and x['shade']==('rgba(0, 0, 0, 0.4)' if x['far'] else 'rgba(0, 0, 0, 0.2)') and x['shadow']!='none' and x['bg']!='rgba(0, 0, 0, 0)' for x in d),d)
        await ev("document.documentElement.dataset.theme='light'")
        for suffix in ['prev2','next2']:
            d=await ev(f"""(()=>{{let e=document.getElementById('lb-side-{suffix}'),r=e.getBoundingClientRect(),s=getComputedStyle(e);return {{l:r.left,r:r.right,w:innerWidth,y:r.y+r.height/2,tf:s.transform,z:s.zIndex,idx:LB.idx}}}})()""")
            check('Far at screen edge '+suffix,(d['l']<1 and d['r']>0) if suffix=='prev2' else (d['r']>d['w']-1 and d['l']<d['w']),d)
            x=4 if suffix=='prev2' else d['w']-4
            await mouse('mouseMoved',x,d['y']); await asyncio.sleep(.3)
            await click(x,d['y']);await asyncio.sleep(.3)
            check('Far hover/click inert '+suffix,await ev(f"""(()=>{{let e=document.getElementById('lb-side-{suffix}'),s=getComputedStyle(e);return LB.idx==={d['idx']} && document.getElementById('lb').style.display!=='none' && s.zIndex==='1' && s.transform==={json.dumps(d['tf'])} && e.tabIndex===-1 && !e.onclick}})()"""))
            await mouse('mouseMoved',1,1);await asyncio.sleep(.3)
        # Exercise an actual near-card click in its exposed area.
        point=await ev("""(()=>{let e=document.getElementById('lb-side-next'),r=e.getBoundingClientRect();for(let x=r.left+2;x<r.right-2;x+=2){let t=document.elementFromPoint(x,r.y+r.height/2);if(t&&e.contains(t))return {x,y:r.y+r.height/2}}return null})()""")
        await mouse('mouseMoved',point['x'],point['y']);await asyncio.sleep(.3)
        await click(point['x'],point['y']);await asyncio.sleep(.6)
        check('Near click advances to central',await ev('LB.idx===4'))
        await ev('LB.idx=3;showLightbox()');await asyncio.sleep(.6)
        await mouse('mouseMoved',1,1)
        d=await ev("""(()=>{const e=document.querySelector('#lb .lb-close'),r=e.getBoundingClientRect(),m=document.querySelector('.lb-main').getBoundingClientRect();return {parent:e.parentElement.id,dx:r.right-m.right,dy:r.top-m.top,shadow:getComputedStyle(e).boxShadow,filter:getComputedStyle(e).filter}})()""")
        check('Close at central corner no glow',d['parent']=='lb-main' and abs(d['dx'])<15 and abs(d['dy'])<15 and d['shadow']=='none' and d['filter']=='none',d)
        await ev('toggleNotes()')
        for _ in range(30):
            # Request a compositor frame before hit-testing a headless transition.
            await send('Page.captureScreenshot',format='png')
            if await ev("getComputedStyle(document.getElementById('lb-notes-panel')).transform === 'matrix(1, 0, 0, 1, 0, 0)'"): break
            await asyncio.sleep(.1)
        nd=await ev("(()=>{let e=document.getElementById('lb-notes-panel'),r=e.getBoundingClientRect(),t=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {ok:e.contains(t),classes:e.className,rect:{x:r.x,y:r.y,w:r.width,h:r.height},hit:t?.outerHTML.slice(0,180),display:document.getElementById('lb').style.display}})()")
        check('Notes above player by hit-test',nd['ok'],nd)
        await ev("LB.queue=['__notInLib__'];LB.idx=0;LB.context='search';showLightbox()")
        await asyncio.sleep(.6)
        dd=json.loads(await ev("""JSON.stringify({fwd5:!!document.getElementById('lb-fwd5'),back5:!!document.getElementById('lb-back5'),
          order:[...document.querySelectorAll('.lb-bottom-center .lb-ctrl')].map(b=>b.id),
          addShown:document.getElementById('lb-add').style.display,
          dismissShown:document.getElementById('lb-dismiss').style.display})"""))
        check('±5s steps exist',dd['fwd5'] and dd['back5'],dd)
        check('Order prev,back20,back5,play,fwd5,fwd20,next',
          dd['order']==['lb-prev','lb-back','lb-back5','lb-play','lb-fwd5','lb-fwd','lb-next'],dd['order'])
        check('Search keeps ADD, removes red X',dd['addShown']=='flex' and dd['dismissShown']=='none',dd)
        await ev("LB.context='feed';showLightbox()");await asyncio.sleep(.5)
        check('Feed keeps red X',await ev("document.getElementById('lb-dismiss').style.display==='flex'"))
        await ev("""window.__seeks=[];window.__fixturePlayer.seekTo=s=>window.__seeks.push(Math.round(s));
          window.__fixturePlayer.getCurrentTime=()=>100;window.__fixturePlayer.getDuration=()=>600;""")
        await ev("playerSkip(SKIP_SMALL);playerSkip(-SKIP_SMALL)")
        check('±5s seeks +5 then -5',await ev("JSON.stringify(window.__seeks)")=='[105,95]',await ev("JSON.stringify(window.__seeks)"))
        check('SKIP_SMALL=5, SKIP_SEC=20',await ev("SKIP_SMALL===5 && SKIP_SEC===20"))
        await ev("toggleCaptions()")
        check('captions persisted as boolean',await ev("""(async()=>{const d=await (await fetch('/api/dashboard')).json();return typeof d.captions==='boolean';})()"""))
        # HOVER ΣΤΑ ΑΚΡΑ: σηκώνει την κάρτα
        await ev("LB.queue=allVideos.slice(0,7).map(v=>v.video_id);LB.idx=3;showLightbox()");await asyncio.sleep(.5)
        await ev("bindEdgePreview();previewHover(1)")
        check('Edge hover lifts NEXT card',await ev("document.getElementById('lb-side-next').classList.contains('hover-preview') && getComputedStyle(document.getElementById('lb-side-next')).zIndex==='11'"))
        await ev("previewHoverEnd(1)")
        check('Pointer leave lowers it instantly',await ev("!document.getElementById('lb-side-next').classList.contains('hover-preview')"))
        await ev("previewHover(-1)")
        check('Edge hover lifts PREV card',await ev("document.getElementById('lb-side-prev').classList.contains('hover-preview')"))
        await ev("previewHoverEnd(-1)")
        check('Hover preview only on 2 edge buttons',await ev("document.getElementById('lb-prev').dataset.previewBound==='1' && document.getElementById('lb-next').dataset.previewBound==='1' && !document.getElementById('lb-back').dataset.previewBound && !document.getElementById('lb-fwd').dataset.previewBound"))
        await ev("LB.queue=allVideos.slice(0,7).map(v=>v.video_id);LB.context='channel';LB.idx=3;showLightbox()")
        await asyncio.sleep(.6)
        await ev('toggleNotes();stepLightbox(1)'); await asyncio.sleep(.6)
        check('Next central retains controls',await ev("LB.idx===4 && document.querySelector('.lb-main').contains(document.querySelector('.lb-bottom'))"))
        await ev('LB.idx=0;updateCarousel()');await asyncio.sleep(.4)
        check('Queue start hides both previous previews', await ev("document.getElementById('lb-side-prev').classList.contains('hidden') && document.getElementById('lb-side-prev2').classList.contains('hidden')"))
        await ev('LB.idx=LB.queue.length-1;updateCarousel()');await asyncio.sleep(.4)
        check('Queue end hides both next previews', await ev("document.getElementById('lb-side-next').classList.contains('hidden') && document.getElementById('lb-side-next2').classList.contains('hidden')"))
        # Sample real animation presentation, not merely a CSS class.
        await ev('stopCarouselMotion();LB.idx=3;showLightbox();stepLightbox(1);for(const a of carouselMotion.values()){a.pause();a.currentTime=0;}')
        motion=await ev("""(()=>{const a=[...carouselMotion.entries()];a.forEach(([e,m])=>{m.pause();m.currentTime=0});return a.map(([e,m])=>({id:e.id||e.className,x:parseFloat(getComputedStyle(e).translate),z:getComputedStyle(e).zIndex,opacity:getComputedStyle(e).opacity,click:!!e.onclick,tab:e.tabIndex}));})()""")
        check('Five synchronized springs on navigation',len(motion)==5,motion)
        far=[m for m in motion if m['id'] in ['lb-side-prev2','lb-side-next2']]
        check('Far bounce remains subtle and decorative',len(far)==2 and all(0<m['x']<=7 and m['z']=='1' and m['opacity']=='1' and not m['click'] and m['tab']==-1 for m in far),far)
        d=await ev("""(()=>{for(const a of carouselMotion.values())a.currentTime=a.effect.getTiming().duration*.62;return [...carouselMotion.keys()].map(e=>({id:e.id,x:parseFloat(getComputedStyle(e).translate)}))})()""")
        check('Actual spring overshoots then settles',all(v['x']<0 for v in d),d)
        check('Refresh does not restart bounce',await ev("(()=>{const a=carouselMotion.get(document.getElementById('lb-main'));updateCarousel();return carouselMotion.get(document.getElementById('lb-main'))===a})()"))
        check('Rapid reversal keeps current visual position',await ev("(()=>{const e=document.getElementById('lb-main'),before=getComputedStyle(e).translate;stepLightbox(-1);const a=carouselMotion.get(e);a.pause();a.currentTime=0;return LB.idx===3 && getComputedStyle(e).translate===before})()"))
        await ev('stopCarouselMotion();animateCarouselHandoff(-1)')
        check('Reverse direction mirrored',await ev("(()=>{const e=document.getElementById('lb-main'),a=carouselMotion.get(e);a.pause();a.currentTime=0;return parseFloat(getComputedStyle(e).translate)<0})()"))
        await send('Emulation.setEmulatedMedia',features=[{'name':'prefers-reduced-motion','value':'reduce'}])
        await ev('stepLightbox(1)')
        check('Reduced motion disables spring',await ev('carouselMotion.size===0'))
        await send('Emulation.setEmulatedMedia',features=[{'name':'prefers-reduced-motion','value':'no-preference'}])
        await ev('stopCarouselMotion();LB.idx=3;showLightbox();toggleSpeedMenu()')
        await asyncio.sleep(.4)
        image=await send('Page.captureScreenshot',format='png')
        import base64
        (RUN/'player.png').write_bytes(base64.b64decode(image['data']))
        REPORT['screenshot']=str(RUN/'player.png')
        point=await ev("(()=>{const r=document.querySelector('#lb .lb-close').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        await click(point['x'],point['y'])
        check('Close button works',await ev("document.getElementById('lb').style.display==='none'"))
        check('No unhandled JS exceptions',not errors,errors)

if __name__=='__main__':
    source=sqlite3.connect('file:C:/Users/andys/AppData/Local/PrivacyYouTuber/privacy_yt.db?mode=ro',uri=True)
    dest=sqlite3.connect(RUN/'test.db');source.backup(dest);dest.close();source.close()
    log=(RUN/'server.log').open('w',encoding='utf-8')
    code=f"import sys;sys.path.insert(0,{str(ROOT)!r});from server import db,app;db.DB_PATH={str(RUN/'test.db')!r};db.init();s,p=app._bind_server(app.HOST,20150);print('PORT',p,flush=True);s.serve_forever()"
    srv=subprocess.Popen([str(VENV),'-c',code],stdout=log,stderr=log)
    browser=None
    try:
        port=None
        for _ in range(100):
            text=(RUN/'server.log').read_text(encoding='utf-8')
            if 'PORT ' in text:
                port=int(text.split('PORT ',1)[1].split()[0]);break
            if srv.poll() is not None:raise RuntimeError(text)
            time.sleep(.1)
        if not port:raise RuntimeError('No test server')
        browser=subprocess.Popen([EDGE,'--headless=new','--remote-debugging-port=20670',f'--user-data-dir={RUN / "edge"}','--no-first-run','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        ws=None
        for _ in range(100):
            try:
                tabs=json.loads(urllib.request.urlopen('http://127.0.0.1:20670/json',timeout=1).read())
                ws=next(t['webSocketDebuggerUrl'] for t in tabs if t['type']=='page');break
            except Exception:time.sleep(.1)
        if not ws:raise RuntimeError('No CDP endpoint')
        asyncio.run(test(ws,port))
    finally:
        if browser:browser.terminate()
        srv.terminate();log.close()
        (RUN/'report.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
        print('REPORT',RUN/'report.json')
