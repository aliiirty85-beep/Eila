from __future__ import annotations
import json,time,urllib.parse
from pathlib import Path

class WebBrain:
    def __init__(self,db_factory,ai,base:Path,cfg:dict):
        self.db_factory=db_factory;self.ai=ai;self.base=base;self.cfg=cfg;self.last_run=0.0;self.last_error="";self.running=False
    def _sources(self):
        p=self.base/"research_sources.json"
        if not p.exists():return {"pubmed_queries":[],"arxiv_queries":[],"feeds":[]}
        try:return json.loads(p.read_text(encoding="utf-8"))
        except Exception:return {"pubmed_queries":[],"arxiv_queries":[],"feeds":[]}
    async def _get_text(self,url):
        import httpx
        async with httpx.AsyncClient(timeout=20,follow_redirects=True,headers={"User-Agent":"EilaStudyOS/2.0"}) as client:
            r=await client.get(url);r.raise_for_status();return r.text
    async def _pubmed(self,query,limit=5):
        import xml.etree.ElementTree as ET
        q=urllib.parse.quote(query);xml=await self._get_text(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmax={limit}&sort=date&term={q}")
        root=ET.fromstring(xml);ids=[x.text for x in root.findall('.//Id') if x.text]
        if not ids:return []
        summ=await self._get_text("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id="+','.join(ids));root=ET.fromstring(summ);out=[]
        for doc in root.findall('.//DocSum'):
            pmid=(doc.findtext('Id') or '').strip();fields={}
            for it in doc.findall('Item'):fields[it.attrib.get('Name','')]=(it.text or '').strip()
            title=fields.get('Title','');date=fields.get('PubDate','')
            if title:out.append({"source":"PubMed","title":title,"url":"https://pubmed.ncbi.nlm.nih.gov/"+pmid+"/","published_at":date})
        return out
    async def _arxiv(self,query,limit=5):
        import xml.etree.ElementTree as ET
        q=urllib.parse.quote(query);xml=await self._get_text(f"https://export.arxiv.org/api/query?search_query=all:{q}&start=0&max_results={limit}&sortBy=submittedDate&sortOrder=descending")
        root=ET.fromstring(xml);ns={'a':'http://www.w3.org/2005/Atom'};out=[]
        for e in root.findall('a:entry',ns):
            title=' '.join((e.findtext('a:title','',ns) or '').split());link=e.findtext('a:id','',ns);pub=e.findtext('a:published','',ns);summary=' '.join((e.findtext('a:summary','',ns) or '').split())
            if title:out.append({"source":"arXiv","title":title,"url":link,"published_at":pub,"abstract":summary[:1800]})
        return out
    async def _feeds(self,urls,limit=10):
        import feedparser
        out=[]
        for url in urls[:10]:
            try:
                raw=await self._get_text(url);f=feedparser.parse(raw)
                for e in f.entries[:limit]:out.append({"source":f.feed.get('title','RSS'),"title":e.get('title',''),"url":e.get('link',''),"published_at":e.get('published',''),"abstract":e.get('summary','')[:1800]})
            except Exception:continue
        return out
    async def run_once(self,force=False):
        if self.running:return {"ok":False,"reason":"already-running"}
        interval=float(self.cfg.get("web_brain_interval_hours",20))*3600
        if not force and time.time()-self.last_run<interval:return {"ok":True,"skipped":True}
        self.running=True
        try:
            src=self._sources();items=[]
            for q in src.get("pubmed_queries",[])[:4]:
                try:items.extend(await self._pubmed(q,4))
                except Exception as e:self.last_error=f"pubmed:{e}"
            for q in src.get("arxiv_queries",[])[:4]:
                try:items.extend(await self._arxiv(q,4))
                except Exception as e:self.last_error=f"arxiv:{e}"
            items.extend(await self._feeds(src.get("feeds",[]),5));items=items[:int(self.cfg.get("web_brain_max_items",12))];saved=0
            for it in items:
                context=f"Title: {it.get('title')}\nSource: {it.get('source')}\nDate: {it.get('published_at')}\nAbstract: {it.get('abstract','')}"
                prompt="این ورودی پژوهشی برای مربی مطالعه ایلاست. فقط اگر نکته تصمیم‌ساز و قابل‌آزمایش برای کیفیت مطالعه/طراحی ایلا دارد، خلاصه 1 تا 3 جمله‌ای بده. ادعای قطعی فراتر از متن نکن. اگر کم‌ربط است فقط SKIP بنویس.\n"+context
                summary=await self.ai.ask("research",[{"role":"user","content":prompt}],temperature=.1,max_tokens=260)
                if summary.startswith("__AI_ERROR__"):summary=""
                relevance=0.0 if summary.strip().upper()=="SKIP" or not summary else .6
                c=self.db_factory()
                try:
                    c.execute("""insert or ignore into research_items(created_at,source,title,url,published_at,summary,relevance,adopted)
                      values(?,?,?,?,?,?,?,0)""",(int(time.time()),it.get("source",""),it.get("title",""),it.get("url",""),it.get("published_at",""),summary,float(relevance)))
                    saved+=c.total_changes;c.commit()
                finally:c.close()
            self.last_run=time.time();return {"ok":True,"found":len(items),"saved":saved,"last_error":self.last_error}
        finally:self.running=False
    def latest(self,limit=10):
        c=self.db_factory();rows=c.execute("select * from research_items order by id desc limit ?",(int(limit),)).fetchall();c.close();return [dict(r) for r in rows]
