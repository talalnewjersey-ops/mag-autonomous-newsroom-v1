#!/usr/bin/env python3
"""
NEXUS-14: patch_images.py - Image Patcher v1
Adds 4 images to all draft posts that have no featured image.
Provider 1: Nano Banana (Gemini-2.0-flash)
Provider 2: OpenAI gpt-image-1 (fallback)
"""
import sys, os, json, time, requests, re, base64
from base64 import b64encode
from datetime import datetime
try:
    import openai as _c
except ImportError:
    os.system("pip install openai -q")
import openai

START = time.time()
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
NANO_KEY   = os.environ.get("NANO_BANANA_API_KEY", "")
WP_URL     = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
WP_USER    = os.environ.get("WORDPRESS_USERNAME", "")
WP_PASS    = os.environ.get("WORDPRESS_PASSWORD", "")
creds      = b64encode((WP_USER+":"+WP_PASS).encode()).decode() if WP_USER else ""
WP_HDR     = {"Authorization":"Basic "+creds,"Content-Type":"application/json","Accept":"application/json","User-Agent":"NEXUS14-Patcher/1.0"}

print("="*60)
print("NEXUS-14 IMAGE PATCHER v1")
print("="*60)
print("WP URL  :", WP_URL)
print("OpenAI  :", "SET" if OPENAI_KEY else "MISSING")
print("NanoBan :", "SET" if NANO_KEY   else "MISSING")
print()

def wp_get(path, params=None):
    return requests.get(WP_URL+path, headers=WP_HDR, params=params, timeout=30)

def wp_patch(path, body):
    for a in range(1,4):
        try:
            r = requests.post(WP_URL+path, headers=WP_HDR, json=body, timeout=90)
            print(f"  WP {path[-20:]} -> {r.status_code} (a{a})")
            if r.status_code in (200,201): return r
            if r.status_code==403: time.sleep(2**a); continue
            return r
        except Exception as e:
            print(f"  WP err: {e}"); time.sleep(2**a)
    return None

def upload_media(img_bytes, fname):
    hdr = {"Authorization":"Basic "+creds,"Content-Disposition":"attachment; filename="+fname,"Content-Type":"image/jpeg","User-Agent":"NEXUS14-Patcher/1.0"}
    for a in range(1,4):
        try:
            r = requests.post(WP_URL+"/wp-json/wp/v2/media", headers=hdr, data=img_bytes, timeout=60)
            print(f"  Media -> {r.status_code} (a{a})")
            if r.status_code in (200,201):
                return r.json().get("id"), r.json().get("source_url","")
            if r.status_code==403: time.sleep(2**a); continue
            print(f"  Media err: {r.text[:120]}"); return None,None
        except Exception as e:
            print(f"  Media exc: {e}"); time.sleep(2**a)
    return None,None

def prompts_for(title):
    t=title[:80]
    return [
        f"Professional financial infographic for '{t}'. Blue-green palette, white background, data charts, banking icons. Clean flat design, no text overlay, no people.",
        f"Modern world map showing international money flows. Related to '{t}'. Blue-green corporate palette, flat design.",
        f"Clean fee comparison bar chart for financial services. Context: '{t}'. Green bars, white background, professional.",
        f"Financial mobile app banner with currency symbols and savings UI. Context: '{t}'. Blue-green gradient, modern flat design.",
    ]

NB_EPS = ["https://api.nano-banana.com/v1/images/generations","https://app.nano-banana.com/api/v1/images/generations"]

def nano_banana(prompt, idx):
    if not NANO_KEY: return None,None
    hdr={"Authorization":"Bearer "+NANO_KEY,"Content-Type":"application/json"}
    body={"model":"gemini-2.0-flash-preview-image-generation","prompt":prompt,"n":1,"size":"1024x1024","response_format":"b64_json"}
    for ep in NB_EPS:
        try:
            r=requests.post(ep,headers=hdr,json=body,timeout=60)
            print(f"  [NanoBanana/Gemini] img{idx}: {ep.split('/')[2]} -> {r.status_code}")
            if r.status_code==200:
                d=r.json()
                if d.get("data"):
                    item=d["data"][0]
                    b64=item.get("b64_json") or item.get("b64") or item.get("image")
                    if b64: return base64.b64decode(b64),"nano_banana_gemini"
                    u=item.get("url")
                    if u:
                        rb=requests.get(u,timeout=30)
                        if rb.status_code==200: return rb.content,"nano_banana_gemini"
                print(f"  [NB] no data: {str(d)[:100]}")
        except Exception as e:
            print(f"  [NB] {ep.split('/')[2]}: {str(e)[:80]}")
    return None,None

def openai_img(prompt, idx):
    if not OPENAI_KEY: return None,None
    try:
        c=openai.OpenAI(api_key=OPENAI_KEY)
        try:
            ir=c.images.generate(model="gpt-image-1",prompt=prompt,size="1024x1024",n=1)
            b64=ir.data[0].b64_json if ir.data else None
            if b64:
                print(f"  [gpt-image-1] img{idx}: SUCCESS")
                return base64.b64decode(b64),"openai_gpt_image_1"
            if ir.data and ir.data[0].url:
                rb=requests.get(ir.data[0].url,timeout=30)
                return rb.content,"openai_gpt_image_1"
        except Exception as e1:
            print(f"  [gpt-image-1] img{idx}: {str(e1)[:80]}")
        try:
            p2="Professional financial infographic, blue-green palette, flat design, charts, no people."
            ir3=c.images.generate(model="dall-e-3",prompt=p2,size="1024x1024",quality="standard",n=1)
            if ir3.data and ir3.data[0].url:
                rb=requests.get(ir3.data[0].url,timeout=30)
                print(f"  [dall-e-3] img{idx}: SUCCESS")
                return rb.content,"openai_dall_e_3"
        except Exception as e2:
            print(f"  [dall-e-3] img{idx}: {str(e2)[:80]}")
    except Exception as e: print(f"  [OAI] init: {e}")
    return None,None

def gen_image(prompt, idx):
    img,prov=nano_banana(prompt,idx)
    if img: return img,prov
    print(f"  NB failed img{idx} -> OpenAI fallback")
    return openai_img(prompt,idx)

# STEP 1 - fetch drafts
print("[STEP 1] Fetching draft posts...")
posts,page=[],1
while True:
    r=wp_get("/wp-json/wp/v2/posts",{"status":"draft","per_page":50,"page":page,"_fields":"id,title,featured_media,content","orderby":"date","order":"asc"})
    if r.status_code!=200: print(f"  WP err {r.status_code}: {r.text[:150]}"); break
    d=r.json()
    if not d: break
    posts.extend(d)
    if len(d)<50: break
    page+=1
print(f"  Total drafts: {len(posts)}")
to_patch=[p for p in posts if not p.get("featured_media")]
print(f"  Need images : {len(to_patch)}")
print()
if not to_patch:
    print("All drafts already have images. Nothing to do.")
    sys.exit(0)

# STEP 2 - patch each post
results=[]
for i,post in enumerate(to_patch):
    pid=post["id"]
    t=post.get("title",{})
    title=t.get("rendered","") if isinstance(t,dict) else str(t)
    title=re.sub(r"<[^>]+>","",title).strip()
    print(f"[POST {i+1}/{len(to_patch)}] ID={pid} | {title[:55]}")
    prs=prompts_for(title)
    mids,murls,prov,feat=[],[],None,False
    for j,pr in enumerate(prs):
        print(f"  Generating img {j+1}/4...")
        img,p=gen_image(pr,j+1)
        if img:
            if not prov: prov=p
            fname=f"nexus14-patch-{pid}-img{j+1}-{int(time.time())}.jpg"
            mid,murl=upload_media(img,fname)
            if mid:
                mids.append(mid); murls.append(murl)
                if j==0:
                    rf=wp_patch(f"/wp-json/wp/v2/posts/{pid}",{"featured_media":mid})
                    if rf and rf.status_code in(200,201):
                        feat=True; print(f"  Featured set: Media ID {mid}")
        else:
            print(f"  img {j+1}/4 FAILED")
        time.sleep(1)
    # Inline images after h2 tags
    if murls:
        raw=post.get("content",{})
        content=raw.get("rendered","") if isinstance(raw,dict) else str(raw)
        nc=content
        ins=0
        for k,mu in enumerate(murls):
            if not mu: continue
            img_html=(f'\n<figure class="wp-block-image size-large aligncenter">'
                      f'<img src="{mu}" alt="{title[:50]}" class="wp-image-{mids[k]}"/>'
                      f'</figure>\n')
            start=0
            for _ in range(ins+1):
                p2=nc.find("</h2>",start)
                if p2==-1: start=-1; break
                start=p2+5
            if start!=-1 and start>0:
                nc=nc[:start]+img_html+nc[start:]; ins+=1
            else:
                nc+=img_html; ins+=1
        if nc!=content:
            ru=wp_patch(f"/wp-json/wp/v2/posts/{pid}",{"content":nc})
            if ru and ru.status_code in(200,201):
                print(f"  Content updated: {len(murls)} images inline")
    results.append({"post_id":pid,"title":title[:60],"images_added":len(mids),"featured_set":feat,"provider":prov,"media_ids":mids})
    print(f"  RESULT: {len(mids)}/4 imgs | featured={'YES' if feat else 'NO'} | {prov}")
    print()
    time.sleep(2)

# Final report
elapsed=round(time.time()-START,1)
patched=sum(1 for r in results if r["featured_set"])
print("="*60)
print("IMAGE PATCHER — FINAL REPORT")
print("="*60)
for r in results:
    print(f"  {'PATCHED' if r['featured_set'] else 'PARTIAL':8} | Post {r['post_id']} | {r['images_added']}/4 | {r['title'][:40]}")
print()
print(f"Posts patched : {patched}/{len(results)}")
print(f"Elapsed       : {elapsed}s")
print("="*60)
with open("patch_report.json","w") as f:
    json.dump({"run":"patch_images_v1","timestamp":datetime.utcnow().isoformat(),"total":len(to_patch),"patched":patched,"elapsed":elapsed,"results":results},f,indent=2)
print("Report: patch_report.json")
if patched==0 and to_patch: sys.exit(1)
