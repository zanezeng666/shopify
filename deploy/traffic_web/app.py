# -*- coding: utf-8 -*-
"""流量质量看板：GA4 当日访客来源/国家/落地页/停留时间明细 + 自动质量标签（浅色主题）。
访问：https://api.bornmieo.com/traffic/?k=<TRAFFIC_KEY>（key 在 /home/jason/shopify-admin/.env）
GA4=313397200（Estry，property 时区 Asia/Shanghai）。数据缓存 5 分钟。"""
import datetime as dt
import os
import time

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse

load_dotenv("/home/jason/shopify-admin/.env")

GA4 = "313397200"
KEY = os.environ.get("TRAFFIC_KEY", "")
CACHE_TTL = 300  # 5 分钟
_req_cache: dict = {}          # {cache_key: (ts, payload)}
_token = {"at": None, "exp": 0}
_tz = {"name": None}

app = FastAPI(title="Traffic Quality Dashboard")

# ---------------------------------------------------------------- GA4 认证


def _access_token() -> str:
    if _token["at"] and time.time() < _token["exp"] - 60:
        return _token["at"]
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    j = r.json()
    _token["at"] = j["access_token"]
    _token["exp"] = time.time() + int(j.get("expires_in", 3600))
    return _token["at"]


def _property_tz() -> str:
    """GA4 媒体资源时区（一次查询缓存进程级复用）。"""
    if _tz["name"]:
        return _tz["name"]
    try:
        r = httpx.get(
            f"https://analyticsadmin.googleapis.com/v1beta/properties/{GA4}",
            headers={"Authorization": f"Bearer {_access_token()}"},
            timeout=30)
        if r.status_code == 200:
            _tz["name"] = r.json().get("timeZone", "")
    except Exception:
        pass
    return _tz["name"] or "Asia/Shanghai"


def runreport(body: dict) -> list:
    """runReport → rows 列表；异常抛 RuntimeError（带简情）。"""
    r = httpx.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}"
        ":runReport",
        headers={"Authorization": f"Bearer {_access_token()}",
                 "Content-Type": "application/json"},
        json=body, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"GA4 {r.status_code}: {r.text[:160]}")
    j = r.json()
    return j.get("rows", [])


# ---------------------------------------------------------------- 质量打分


def quality(sessions: int, dur_per: float, eng_rate: float,
            pages_per: float, ke: int) -> str:
    """流量质量标签：good/norm/low/bot（依据既有流量审计指纹）。"""
    if sessions >= 4 and dur_per < 8 and eng_rate < 0.06 and pages_per < 1.4:
        return "bot"      # 1 页/秒退/零参与 —— bot Direct 会话指纹
    if ke > 0 or (dur_per >= 40 and eng_rate >= 0.3):
        return "good"
    if eng_rate >= 0.2 and dur_per >= 25:
        return "good"
    if eng_rate < 0.08 or dur_per < 15:
        return "low"
    return "norm"


def _row_vals(row: dict) -> tuple:
    mv = [m["value"] for m in row["metricValues"]]
    f = lambda i: float(mv[i])
    sess = int(f(0))
    engaged, dur, views, ke = f(1), f(2), f(3), f(4)
    dur_per = dur / sess if sess else 0.0
    eng_rate = engaged / sess if sess else 0.0
    pages_per = views / sess if sess else 0.0
    return sess, engaged, dur, views, int(ke), dur_per, eng_rate, pages_per


EVENTS = ("add_to_cart", "begin_checkout", "purchase", "generate_lead",
          "search", "form_submit", "view_item")


def fetch_day(date_str: str) -> dict:
    """拉齐一个日期的全套数据（GA4 today=媒体资源时区）。"""
    dr = [{"startDate": date_str, "endDate": date_str}]
    metrics = [{"name": n} for n in
               ("sessions", "engagedSessions", "userEngagementDuration",
                "screenPageViews", "keyEvents")]

    def dims_report(dims: list, limit: int, extra: dict | None = None,
                    dimension_fallback: list | None = None) -> list:
        body = {"dateRanges": dr, "dimensions": [{"name": d} for d in dims],
                "metrics": metrics,
                "orderBys": [{"metric": {"metricName": "sessions"},
                              "desc": True}], "limit": limit}
        if extra:
            body.update(extra)
        try:
            return runreport(body)
        except RuntimeError:
            if dimension_fallback:
                for alt in dimension_fallback:
                    body["dimensions"] = [{"name": d} for d in
                                          [alt if d.startswith("landing")
                                           else d for d in dims]]
                    try:
                        return runreport(body)
                    except RuntimeError:
                        continue
            raise

    # A 来源
    src_rows = dims_report(
        ["sessionDefaultChannelGroup", "sessionSourceMedium"], 100)
    # B 明细（landing 维度名跨版本兼容）
    det_rows = dims_report(
        ["sessionSourceMedium", "country", "city", "deviceCategory",
         "landingPagePlusQueryString"], 500,
        dimension_fallback=["landingPagePlusCombinedUrl", "landingPage"])
    # C 页面停留
    page_rows = runreport({
        "dateRanges": dr,
        "dimensions": [{"name": "pagePath"}],
        "metrics": [{"name": "screenPageViews"},
                    {"name": "userEngagementDuration"}],
        "orderBys": [{"metric": {"metricName": "screenPageViews"},
                      "desc": True}], "limit": 100})
    # D 事件×来源
    ev_rows = runreport({
        "dateRanges": dr,
        "dimensions": [{"name": "eventName"}, {"name": "sessionSourceMedium"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {"filter": {
            "fieldName": "eventName",
            "inListFilter": {"values": list(EVENTS)}}},
        "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
        "limit": 200})

    # ---- 汇总
    sources, tot = [], {"sessions": 0, "engaged": 0.0, "dur": 0.0,
                        "views": 0.0, "ke": 0}
    for r in src_rows:
        d = [x["value"] for x in r["dimensionValues"]]
        s, en, du, vw, ke, dp, er, pp = _row_vals(r)
        tot["sessions"] += s; tot["engaged"] += en; tot["dur"] += du
        tot["views"] += vw; tot["ke"] += ke
        sources.append({"channel": d[0], "srcmed": d[1], "sessions": s,
                        "durPer": round(dp, 1), "engRate": round(er, 3),
                        "pagesPer": round(pp, 2), "ke": ke,
                        "tag": quality(s, dp, er, pp, ke)})

    def short_landing(u: str) -> str:
        if not u or u == "(not set)":
            return u
        u = u.split("?", 1)
        q = ("?" + u[1][:40]) if len(u) > 1 else ""
        path = u[0].replace("https://estrybattery.com", "")[:60]
        return path + q

    def full_landing(u: str) -> str:
        """完整可点 URL：http(s) 开头原样，其余拼站点域名；(not set) 留空。"""
        if not u or u == "(not set)":
            return ""
        if u.startswith(("http://", "https://")):
            return u
        return "https://estrybattery.com" + (u if u.startswith("/") else "/" + u)

    detail = []
    for r in det_rows:
        d = [x["value"] for x in r["dimensionValues"]]
        s, en, du, vw, ke, dp, er, pp = _row_vals(r)
        detail.append({"srcmed": d[0], "country": d[1], "city": d[2],
                       "device": d[3], "landing": short_landing(d[4]),
                       "landingUrl": full_landing(d[4]),
                       "sessions": s, "durPer": round(dp, 1),
                       "engRate": round(er, 3), "views": int(vw),
                       "pagesPer": round(pp, 2), "ke": ke,
                       "tag": quality(s, dp, er, pp, ke)})
    tag_rank = {"good": 0, "norm": 1, "low": 2, "bot": 3}
    detail.sort(key=lambda x: (tag_rank[x["tag"]], -x["sessions"]))

    pages = []
    for r in page_rows:
        d = [x["value"] for x in r["dimensionValues"]]
        views = int(float(r["metricValues"][0]["value"]))
        dur = float(r["metricValues"][1]["value"])
        pages.append({"path": d[0][:80], "url": full_landing(d[0]),
                      "views": views,
                      "durTotal": round(dur, 0),
                      "durPerView": round(dur / views, 1) if views else 0})

    events = {}
    ev_detail = []
    for r in ev_rows:
        name, srcmed = (x["value"] for x in r["dimensionValues"])
        cnt = int(float(r["metricValues"][0]["value"]))
        events[name] = events.get(name, 0) + cnt
        ev_detail.append({"event": name, "srcmed": srcmed, "count": cnt})

    ts = tot["sessions"]
    return {
        "date": date_str, "tz": _property_tz(),
        "generatedAt": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totals": {
            "sessions": ts,
            "engRate": round(tot["engaged"] / ts, 3) if ts else 0,
            "avgDur": round(tot["dur"] / ts, 1) if ts else 0,
            "totalDur": round(tot["dur"], 0),
            "views": int(tot["views"]), "ke": tot["ke"],
            "events": {k: v for k, v in events.items()}},
        "sources": sources, "detail": detail, "pages": pages,
        "eventDetail": ev_detail}


def _check_key(k: str | None):
    if not KEY or k != KEY:
        raise HTTPException(401, "invalid key")


# ---------------------------------------------------------------- API/页面


@app.get("/api/day")
def api_day(date: str = "today", k: str = ""):
    _check_key(k)
    d = date.strip()
    if d not in ("today", "yesterday"):
        try:
            dt.date.fromisoformat(d)
        except ValueError:
            raise HTTPException(422, "date must be today/yesterday/YYYY-MM-DD")
    ck = (d, )
    hit = _req_cache.get(ck)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    payload = fetch_day(d)
    _req_cache[ck] = (time.time(), payload)
    return payload


@app.get("/", response_class=HTMLResponse)
def index(k: str = ""):
    _check_key(k)
    return PAGE


PAGE = r"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>流量质量看板 · Estry</title>
<style>
:root{--bg:#f6f8fa;--card:#ffffff;--bd:#d0d7de;--fg:#1f2328;--dim:#57606a;
--good:#1a7f37;--norm:#0969da;--low:#9a6700;--bot:#cf222e;--hover:#f3f4f6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 -apple-system,"Segoe UI",Roboto,"Noto Sans SC",sans-serif;padding:20px}
h1{font-size:18px;margin:0 0 4px;color:var(--fg)}.sub{color:var(--dim);
font-size:12px;margin-bottom:16px}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:8px;
padding:10px 14px;min-width:110px;box-shadow:0 1px 2px rgba(31,35,40,.06)}
.card .v{font-size:20px;font-weight:600}.card .l{color:var(--dim);font-size:11px}
.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
button,select,input{background:var(--card);color:var(--fg);border:1px solid var(--bd);
border-radius:6px;padding:6px 12px;font-size:13px;cursor:pointer}
button:hover,input:hover{background:var(--hover)}
input[type=date],input[type=search]{cursor:text}
.fbtn.on{border-color:var(--norm);color:var(--norm);font-weight:600}
table{width:100%;border-collapse:separate;border-spacing:0;
background:var(--card);border:1px solid var(--bd);border-radius:8px;
overflow:hidden;font-size:13px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--bd);
white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:340px}
tbody tr:last-child td{border-bottom:none}
th{color:var(--dim);font-weight:600;font-size:12px;position:sticky;top:0;
background:var(--card);box-shadow:inset 0 -1px 0 var(--bd)}
tbody tr:hover td{background:var(--hover)}
.tag{padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600}
.tag.good{background:rgba(26,127,55,.12);color:var(--good)}
.tag.norm{background:rgba(9,105,218,.12);color:var(--norm)}
.tag.low{background:rgba(154,103,0,.14);color:var(--low)}
.tag.bot{background:rgba(207,34,46,.12);color:var(--bot)}
.us{color:var(--good);font-weight:600}
h2{font-size:14px;margin:22px 0 8px;color:var(--fg)}
.num{text-align:right}td.num{font-variant-numeric:tabular-nums}
#msg{color:var(--dim);padding:20px;text-align:center}
.pill{display:inline-block;margin-left:6px;padding:1px 8px;border-radius:10px;
background:#eaeef2;color:var(--dim);font-size:11px;font-weight:500}
.note{background:rgba(154,103,0,.08);border:1px solid rgba(154,103,0,.35);
color:var(--low);border-radius:8px;padding:8px 14px;font-size:13px;
margin-bottom:14px;display:none}
a.lk{color:var(--norm);text-decoration:none;
border-bottom:1px dotted #8cacd0;cursor:pointer}
a.lk:hover{border-bottom-style:solid}
</style></head><body>
<h1>流量质量看板 <span class="pill" id="gen"></span><span class="pill" id="tz"></span></h1>
<div class="sub">按 GA4 媒体资源时区统计 · 当日数据延迟 1-3 小时 ·
优质=有事件或停留≥40s且参与≥30% · 低质=停留&lt;15s或参与&lt;8% ·
Bot?=1页秒退零参与指纹</div>
<div class="bar">
 <button data-d="today">今天</button><button data-d="yesterday">昨天</button>
 <input type="date" id="pick"><button id="go">查看</button>
 <span style="flex:1"></span>
 <button class="fbtn on" data-f="all">全部</button>
 <button class="fbtn" data-f="good">优质</button>
 <button class="fbtn" data-f="norm">普通</button>
 <button class="fbtn" data-f="low">低质</button>
 <button class="fbtn" data-f="bot">疑似Bot</button>
</div>
<div class="note" id="note"></div>
<div class="cards" id="cards"></div>
<h2>访客明细（来源 × 国家 × 城市 × 设备 × 落地页）</h2>
<div class="bar"><input type="search" id="q" placeholder="搜索来源/国家/页面…"
 style="min-width:260px"></div>
<div style="overflow:auto;max-height:460px"><table id="detail">
<thead><tr><th>质量</th><th>来源/媒介</th><th>国家</th><th>城市</th>
<th>设备</th><th>落地页</th><th class="num">会话</th><th class="num">停留/会话</th>
<th class="num">参与率</th><th class="num">页/会话</th><th class="num">事件</th>
</tr></thead><tbody></tbody></table></div>
<h2>来源汇总（渠道组 × 来源/媒介）</h2>
<div style="overflow:auto;max-height:340px"><table id="sources">
<thead><tr><th>质量</th><th>渠道组</th><th>来源/媒介</th><th class="num">会话</th>
<th class="num">停留/会话</th><th class="num">参与率</th><th class="num">页/会话</th>
<th class="num">关键事件</th></tr></thead><tbody></tbody></table></div>
<h2>页面停留（全站浏览与停留时长）</h2>
<div style="overflow:auto;max-height:340px"><table id="pages">
<thead><tr><th>页面</th><th class="num">浏览量</th><th class="num">总停留</th>
<th class="num">停留/浏览</th></tr></thead><tbody></tbody></table></div>
<h2>动作事件（谁在产生行为）</h2>
<div style="overflow:auto;max-height:280px"><table id="events">
<thead><tr><th>事件</th><th>来源/媒介</th><th class="num">次数</th>
</tr></thead><tbody></tbody></table></div>
<div id="msg">加载中…</div>
<script>
const K=new URLSearchParams(location.search).get('k')||localStorage.getItem('tk')||'';
if(K)localStorage.setItem('tk',K);
let cur='today',filter='all';
const $=s=>document.querySelector(s);
const fm=s=>s>=60?Math.floor(s/60)+'m'+Math.round(s%60)+'s':Math.round(s)+'s';
const pc=x=>(x*100).toFixed(0)+'%';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;',
'>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const lk=(url,text)=>url?('<a class="lk" href="'+esc(url)+
 '" target="_blank" rel="noopener">'+esc(text)+'</a>'):esc(text);
const tagTxt={good:'优质',norm:'普通',low:'低质',bot:'Bot?'};
document.querySelectorAll('[data-d]').forEach(b=>b.onclick=()=>load(b.dataset.d));
document.querySelectorAll('.fbtn').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('.fbtn').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');filter=b.dataset.f;render(dCache)});
$('#go').onclick=()=>load($('#pick').value||'today');
$('#q').oninput=()=>render(dCache);
function load(d){cur=d;$('#msg').textContent='加载 '+d+' …';
 /* 相对路径：站点挂在 /traffic/ 子路径时也能正确请求本服务 */
 fetch('api/day?date='+encodeURIComponent(d)+'&k='+encodeURIComponent(K))
 .then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json()})
 .then(j=>{dCache=j;render(j);$('#msg').textContent=''})
 .catch(e=>{$('#msg').innerHTML='加载失败：'+e.message+
  '（key 失效请用带 <b>?k=</b> 的完整链接重开）'}) }
let dCache=null;
function cards(t){const ev=t.events||{};
 $('#cards').innerHTML=[
 ['会话',t.sessions],['参与率',pc(t.engRate)],['平均停留',fm(t.avgDur)],
 ['总浏览',t.views],['关键事件',t.ke],
 ['加购',ev.add_to_cart||0],['开始结账',ev.begin_checkout||0],
 ['购买',ev.purchase||0]].map(x=>
 '<div class="card"><div class="v">'+x[1]+'</div><div class="l">'+x[0]+
 '</div></div>').join('')}
function tr(cls,cells){return '<tr class="'+cls+'">'+cells.map((c,i)=>
 '<td'+((typeof c==='object')?'':' class="'+(i>=6?'num':'')+'"')+'>'+
 (typeof c==='object'?c.v:c)+'</td>').join('')+'</tr>'}
function render(j){cards(j.totals);
 $('#gen').textContent=j.date+' · 更新 '+j.generatedAt;
 $('#tz').textContent='GA4 时区 '+(j.tz||'');
 const nb=$('#note');
 if(j.totals.sessions===0){nb.style.display='block';
  nb.textContent='该日暂无会话数据——当日数据有 1-3 小时延迟，凌晨时段少属正常，可切“昨天”查看。'}
 else nb.style.display='none';
 const kw=($('#q').value||'').toLowerCase();
 const rows=j.detail.filter(r=>(filter==='all'||r.tag===filter)&&
  (!kw||(r.srcmed+r.country+r.city+r.landing+r.device).toLowerCase().includes(kw)));
 $('#detail tbody').innerHTML=rows.map(r=>tr('',
  [{v:'<span class="tag '+r.tag+'">'+tagTxt[r.tag]+'</span>'},r.srcmed,
   {v:r.country==='United States'?'<span class="us">US</span>':r.country},
   r.city,r.device,{v:lk(r.landingUrl,r.landing)},r.sessions,fm(r.durPer),
   pc(r.engRate),r.pagesPer,r.ke])).join('')||'<tr><td colspan="11">无匹配行</td></tr>';
 $('#sources tbody').innerHTML=j.sources.map(r=>tr('',
  [{v:'<span class="tag '+r.tag+'">'+tagTxt[r.tag]+'</span>'},r.channel,
   r.srcmed,r.sessions,fm(r.durPer),pc(r.engRate),r.pagesPer,r.ke])).join('');
 $('#pages tbody').innerHTML=j.pages.map(p=>tr('',
  [{v:lk(p.url,p.path)},p.views,fm(p.durTotal),fm(p.durPerView)])).join('');
 $('#events tbody').innerHTML=j.eventDetail.map(e=>tr('',[e.event,e.srcmed,
  e.count])).join('')||'<tr><td colspan="3">当日无关键事件</td></tr>'}
load('today');
setInterval(()=>load(cur),300000);
</script></body></html>
"""
