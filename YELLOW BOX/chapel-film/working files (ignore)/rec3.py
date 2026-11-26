import sys, base64, asyncio
from playwright.async_api import async_playwright
OUT=sys.argv[1]; SECS=float(sys.argv[2])
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(channel='chrome',headless=False,args=['--autoplay-policy=no-user-gesture-required','--window-position=0,0','--window-size=500,400'])
    pg=await b.new_page()
    await pg.goto('https://deusaderit.com/chapel/')
    await pg.wait_for_timeout(5000)
    f=[f for f in pg.frames if 'youtube' in f.url][0]
    await f.wait_for_selector('video',state='attached',timeout=20000)
    await pg.evaluate("document.querySelector('#play').click()")
    await pg.wait_for_timeout(2500)
    r=await f.evaluate("""async(secs)=>{const v=document.querySelector('video');
      const ctx=new AudioContext();await ctx.resume();const src=ctx.createMediaElementSource(v);const dst=ctx.createMediaStreamDestination();src.connect(dst);src.connect(ctx.destination);const a=dst.stream;const s=a;
      const rec=new MediaRecorder(a,{mimeType:'audio/webm;codecs=opus',audioBitsPerSecond:256000});const ch=[];rec.ondataavailable=e=>ch.push(e.data);
            v.currentTime=154;await Promise.race([new Promise(r=>v.addEventListener('seeked',r,{once:true})),new Promise(r=>setTimeout(r,6000))]);await new Promise(r=>setTimeout(r,400));const t0=[v.currentTime,v.paused,s.getAudioTracks().length];rec.start();
      await new Promise(r=>setTimeout(r,secs*1000));const done=new Promise(r=>rec.onstop=r);rec.stop();await Promise.race([done,new Promise(r=>setTimeout(r,3000))]);
      const u=new Uint8Array(await new Blob(ch).arrayBuffer());let s2='';for(let i=0;i<u.length;i+=32768)s2+=String.fromCharCode.apply(null,u.subarray(i,i+32768));
      return {t0,b64:btoa(s2),n:a.getTracks().length};}""",SECS)
    print('start',r['t0'],'tracks',r['n'])
    open(OUT,'wb').write(base64.b64decode(r['b64']))
    await b.close()
asyncio.run(main())
