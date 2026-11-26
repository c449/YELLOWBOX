import sys, json, math, asyncio, base64
from playwright.async_api import async_playwright
OUT=sys.argv[1]; MODE=sys.argv[2]  # probe | film
URL='https://deusaderit.com/chapel/'
INIT="""
window.__rafQ=[];const __o=window.requestAnimationFrame.bind(window);
window.requestAnimationFrame=cb=>{if(window.__film){window.__rafQ.push(cb);return 0;}return __o(cb);};
"""
def interp(K,t):
  j=max(k for k in range(len(K)-1) if K[k][0]<=t)
  n_=len(K)
  def tan(k,n):
    # monotone tangent (per second) at key k; zero at ends, holds and turning points
    if k<=0 or k>=n_-1: return 0.0
    dl=(K[k][n]-K[k-1][n])/(K[k][0]-K[k-1][0]); dr=(K[k+1][n]-K[k][n])/(K[k+1][0]-K[k][0])
    if dl*dr<=0: return 0.0
    m=(dl+dr)/2
    lim=3*min(abs(dl),abs(dr))
    return max(-lim,min(lim,m))
  p1,p2=K[j],K[j+1]; h=p2[0]-p1[0]; u=(t-p1[0])/h
  u2,u3=u*u,u*u*u
  out=[]
  for n in range(1,6):
    m1=tan(j,n)*h; m2=tan(j+1,n)*h
    out.append((2*u3-3*u2+1)*p1[n]+(u3-2*u2+u)*m1+(-2*u3+3*u2)*p2[n]+(u3-u2)*m2)
  return out
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(channel='chrome',headless=True,args=['--use-angle=metal','--enable-gpu','--ignore-gpu-blocklist'])
    pg=await b.new_page(viewport={'width':int(__import__('os').environ.get('W','1280')),'height':int(__import__('os').environ.get('H','720'))})
    await pg.add_init_script(INIT)
    async def fix(route):
      r=await route.fetch(); s=await r.text()
      s=s.replace("const cam=Object.assign({y:1.6},STATIONS.outside);","const cam=Object.assign({y:1.6},STATIONS.outside);window.__cam=cam;window.__G=G;window.__car=()=>CARBOX;",1)
      s=s.replace("scene.add(new THREE.Mesh(new THREE.SphereGeometry(150","scene.add(window.__sky=new THREE.Mesh(new THREE.SphereGeometry(150",1)
      s=s.replace("renderer.render(scene,camera);requestAnimationFrame(frame);","if(window.__sky)window.__sky.position.copy(camera.position);renderer.render(scene,camera);requestAnimationFrame(frame);",1)
      s=s.replace("cam.y+=(ty-cam.y)*Math.min(1,dt*8);","cam.y+=((window.__ty||ty)-cam.y)*Math.min(1,dt*8);",1)
      s=s.replace("</head>","<style>#play,.pad,#player{display:none!important}</style></head>",1)
      await route.fulfill(response=r,body=s)
    await pg.route(URL,fix)
    await pg.goto(URL); 
    await pg.wait_for_function("window.__car&&window.__car()",timeout=90000)
    await pg.wait_for_timeout(3000)
    print('CAR',await pg.evaluate("window.__car()"))
    await pg.add_style_tag(content="#play,.pad,#player{display:none!important}")
    await pg.evaluate("window.__film=true")
    await pg.wait_for_timeout(300)
    keys=[k+[1.6]*(6-len(k)) for k in json.load(open(sys.argv[3]))]
    fps=30; N=int(keys[-1][0]*fps)
    STILLS=json.loads(__import__('os').environ.get('STILLS','[]'))
    frames=range(N) if MODE=='film' else ([int(k[0]*fps) for k in keys[:-1]] if MODE=='probe' else [])
    for si,st in enumerate(STILLS):
      v=interp(keys,st)
      for w in range(25):
        url=await pg.evaluate("""([x,z,yaw,pitch,ty,ms])=>{const c=window.__cam;window.__ty=ty;c.x=x;c.z=z;c.yaw=yaw;c.pitch=pitch;
          const q=window.__rafQ;window.__rafQ=[];q.forEach(cb=>cb(ms));return w_last?null:null;}""".replace('return w_last?null:null;',''),[v[0],v[1],v[2],v[3],v[4],100000+st*1000-(25-w)*33])
      url=await pg.evaluate("""([x,z,yaw,pitch,ty,ms])=>{const c=window.__cam;window.__ty=ty;c.x=x;c.z=z;c.yaw=yaw;c.pitch=pitch;
        const q=window.__rafQ;window.__rafQ=[];q.forEach(cb=>cb(ms));return document.querySelector('canvas').toDataURL('image/png');}""",[v[0],v[1],v[2],v[3],v[4],100000+st*1000])
      open(f'{OUT}/still-{si+1:02d}.png','wb').write(base64.b64decode(url.split(',',1)[1]))
    SIGS=[float(v)*fps for v in __import__('os').environ.get('SMOOTH','0,0,0,0,0').split(',')]
    RAW=[interp(keys,i/fps) for i in range(N)]
    def smooth(i):
      out=[]
      for n in range(5):
        SG=SIGS[n]
        if SG<=0: out.append(RAW[i][n]);continue
        R=int(SG*3);a=0;ws=0
        for d in range(-R,R+1):
          j=min(max(i+d,0),N-1);w=math.exp(-d*d/(2*SG*SG));ws+=w;a+=RAW[j][n]*w
        out.append(a/ws)
      return out
    for i in frames:
      t=i/fps
      v=smooth(i)
      url=await pg.evaluate("""([x,z,yaw,pitch,ty,ms])=>{const c=window.__cam;window.__ty=ty;c.x=x;c.z=z;c.yaw=yaw;c.pitch=pitch;
        const q=window.__rafQ;window.__rafQ=[];q.forEach(cb=>cb(ms));return document.querySelector('#stage canvas, canvas').toDataURL('image/jpeg',0.93);}""",[v[0],v[1],v[2],v[3],v[4],100000+t*1000])
      open(f'{OUT}/f{i:04d}.jpg','wb').write(base64.b64decode(url.split(',',1)[1]))
    await b.close()
asyncio.run(main())
