/* shopify_admin 整体架构 PPT（pptxgenjs，紧凑版） */
const pptxgen = require("pptxgenjs");
const C = { dark:"002E25", primary:"008060", primaryDk:"004C3C", accent:"96BF48", bg:"F6F8F7",
  card:"FFFFFF", ink:"202223", sub:"5C5F62", line:"E1E7E4", pale:"E6F2ED", code:"0B7A5C", onDark:"E4EFEA", onDarkSub:"9DB8AE" };
const F = "Microsoft YaHei", M = "Consolas";
const sh = () => ({ type:"outer", color:"1A2E28", blur:7, offset:2, angle:90, opacity:0.14 });
const p = new pptxgen();
p.layout = "LAYOUT_16x9";
p.author = "zane";
p.title = "shopify-admin 整体架构";
const TOTAL = 10;

function page(s, eyebrow, title, n) {
  s.background = { color: C.bg };
  s.addText(eyebrow, { x:0.55, y:0.3, w:8, h:0.26, fontSize:11, fontFace:M, color:C.primary, bold:true, charSpacing:3, margin:0 });
  s.addText(title, { x:0.55, y:0.55, w:8.9, h:0.55, fontSize:26, fontFace:F, color:C.ink, bold:true, margin:0 });
  s.addText("shopify-admin · 2026-11", { x:0.55, y:5.33, w:3, h:0.24, fontSize:9, fontFace:F, color:C.sub, margin:0 });
  s.addText(`${n}/${TOTAL}`, { x:9.0, y:5.33, w:0.45, h:0.24, fontSize:9, fontFace:M, color:C.sub, align:"right", margin:0 });
}
function card(s, x, y, w, h, fill) {
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill:{color:fill||C.card}, rectRadius:0.055, line:{color:C.line,width:1}, shadow:sh() });
}
function bar(s, x, y, h, c) { s.addShape(p.shapes.RECTANGLE, { x, y, w:0.055, h, fill:{color:c||C.primary} }); }
function kv(s, x, y, w, rows, fs1, fs2) {
  const items = rows.map(([t,d],i)=>([{ text:t+"  ", options:{fontSize:fs1||11.5, bold:true, color:C.primaryDk, fontFace:F} },
    { text:d, options:{fontSize:fs2||10.5, color:C.sub, fontFace:F, breakLine:i<rows.length-1} }])).flat();
  s.addText(items, { x, y, w, h:3, margin:0, paraSpaceAfter:7 });
}

/* 1 封面 */
{ const s = p.addSlide();
  s.background = { color: C.dark };
  s.addShape(p.shapes.OVAL, { x:7.5, y:-1.6, w:4.4, h:4.4, fill:{color:C.dark}, line:{color:C.primaryDk,width:1.2} });
  s.addShape(p.shapes.OVAL, { x:8.4, y:-0.8, w:2.8, h:2.8, fill:{color:C.dark}, line:{color:C.primary,width:1.2} });
  s.addShape(p.shapes.OVAL, { x:-1.0, y:4.4, w:2.6, h:2.6, fill:{color:C.dark}, line:{color:C.primaryDk,width:1.2} });
  s.addText("ARCHITECTURE OVERVIEW", { x:0.75, y:1.3, w:6, h:0.3, fontSize:12, fontFace:M, color:C.accent, charSpacing:4, bold:true, margin:0 });
  s.addText("Shopify 多店铺管理中台", { x:0.72, y:1.64, w:8.5, h:0.85, fontSize:40, fontFace:F, color:"FFFFFF", bold:true, margin:0 });
  s.addText("shopify-admin · 全功能接口化 · REST API + MCP 双入口共享服务层", { x:0.75, y:2.55, w:8, h:0.35, fontSize:15, fontFace:F, color:C.onDarkSub, margin:0 });
  let cx = 0.75;
  [["REST · FastAPI",1.55],["MCP · 42 个 AI 工具",1.95],["7× 定时任务",1.4],["4 库数据层",1.3]].forEach(([t,w])=>{
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x:cx, y:3.3, w, h:0.42, fill:{color:C.primaryDk}, rectRadius:0.05, line:{color:C.primary,width:0.75} });
    s.addText(t, { x:cx, y:3.29, w, h:0.42, fontSize:11.5, fontFace:F, color:C.onDark, align:"center", valign:"middle", margin:0 });
    cx += w + 0.18; });
  s.addText("2026-11 · Estry / Bomibattery 电商运营体系", { x:0.75, y:4.92, w:6, h:0.3, fontSize:11, fontFace:F, color:C.onDarkSub, margin:0 });
}

/* 2 系统定位 */
{ const s = p.addSlide();
  page(s, "01 · POSITIONING", "系统定位：一套中台，管住「卖货」全链路", 2);
  s.addText("订单、产品、库存、履约、财务、定价、营销全部接口化：系统集成（REST）与 AI 助手（MCP）共用同一服务层；数据落全新 shopify_new 库，与老系统并行解耦。", { x:0.55, y:1.22, w:5.35, h:0.85, fontSize:13, fontFace:F, color:C.ink, margin:0, lineSpacingMultiple:1.25 });
  [["42","MCP 工具（shopify_*）","AI 直调，三级权限 READ/GENERAL/ADMIN"],
   ["10","业务服务域","REST 与 MCP 共享同一层"],
   ["4","MySQL 数据库","1 主库可写 + 3 只读镜像"]].forEach(([n,l,d],i)=>{
    const y = 2.28 + i*0.98;
    card(s, 0.55, y, 5.35, 0.84); bar(s, 0.55, y, 0.84);
    s.addText(n, { x:0.78, y:y+0.05, w:1.0, h:0.74, fontSize:38, fontFace:M, color:C.primary, bold:true, valign:"middle", margin:0 });
    s.addText([{ text:l, options:{fontSize:13.5, bold:true, color:C.ink, breakLine:true} },
      { text:d, options:{fontSize:10.5, color:C.sub} }],
      { x:1.85, y:y+0.1, w:3.9, h:0.64, fontFace:F, valign:"middle", margin:0 });
  });
  card(s, 6.15, 1.22, 3.3, 3.98);
  s.addText("三条核心设计原则", { x:6.4, y:1.42, w:2.9, h:0.3, fontSize:14, fontFace:F, bold:true, color:C.ink, margin:0 });
  [["全功能接口化","任何能力先做 API；系统集成与 AI 共用"],
   ["平台 × 渠道正交","卖货平台（Shopify）与履约渠道（CS/FastRite）互不耦合"],
   ["新旧库隔离","全新 shopify_new 库（Alembic 管理），老库只读迁移"]].forEach(([t,d],i)=>{
    const y = 1.9 + i*1.06;
    s.addShape(p.shapes.OVAL, { x:6.4, y:y+0.02, w:0.3, h:0.3, fill:{color:C.pale}, line:{color:C.primary,width:0.75} });
    s.addText(String(i+1), { x:6.4, y:y+0.01, w:0.3, h:0.3, fontSize:12, fontFace:M, bold:true, color:C.primary, align:"center", valign:"middle", margin:0 });
    s.addText([{ text:t, options:{fontSize:12.5, bold:true, color:C.primaryDk, breakLine:true} },
      { text:d, options:{fontSize:9.5, color:C.sub} }],
      { x:6.85, y:y-0.04, w:2.42, h:1.0, fontFace:F, margin:0, lineSpacingMultiple:1.12 });
  });
}

/* 3 总体架构 */
{ const s = p.addSlide();
  page(s, "02 · ARCHITECTURE", "总体架构：四层正交，入口共享服务", 3);
  const L = [
    { n:"入口层", e:"ENTRY", y:1.18, h:0.96, c:C.primary, items:["REST · FastAPI\n11 路由域 + /console","MCP · FastMCP\n42 工具 stdio/SSE","Scheduler\n进程内 / 独立进程"] },
    { n:"服务层", e:"SERVICES", y:2.3, h:0.88, c:C.primaryDk, chips:["stores","orders","products","inventory","fulfillment","finance","pricing","reports","marketing","shipping"] },
    { n:"适配层", e:"ADAPTER", y:3.34, h:0.8, c:C.primary, items:["platforms/shopify\nAdmin API·REST+GraphQL+bulk","channels 履约渠道抽象\n库存/运费/下单/查单/跟踪"] },
    { n:"数据层", e:"DATA", y:4.32, h:0.84, c:C.primaryDk, items:["shopify_new\n主库·可写·Alembic","shopify\n老库·只读迁移","cs_new\nCS 镜像·只读","fast_rite\n海外仓镜像·只读"] },
  ];
  for (const l of L) {
    s.addShape(p.shapes.RECTANGLE, { x:0.55, y:l.y, w:1.22, h:l.h, fill:{color:l.c} });
    s.addText([{ text:l.n, options:{fontSize:13.5, bold:true, color:"FFFFFF", breakLine:true} },
      { text:l.e, options:{fontSize:8, fontFace:M, color:"BFE3D6"} }],
      { x:0.55, y:l.y, w:1.22, h:l.h, align:"center", valign:"middle", fontFace:F, margin:0 });
    const rx = 1.95, rw = 7.5;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x:rx, y:l.y, w:rw, h:l.h, fill:{color:C.card}, rectRadius:0.05, line:{color:C.line,width:1} });
    if (l.chips) l.chips.forEach((t,i)=>{
      const cw = 1.38, g = 0.13;
      s.addShape(p.shapes.ROUNDED_RECTANGLE, { x:rx+0.14+(i%5)*(cw+g), y:l.y+0.1+Math.floor(i/5)*0.37, w:cw, h:0.3, fill:{color:C.pale}, rectRadius:0.05, line:{color:C.line,width:0.75} });
      s.addText(t, { x:rx+0.14+(i%5)*(cw+g), y:l.y+0.085+Math.floor(i/5)*0.37, w:cw, h:0.3, fontSize:9.5, fontFace:M, bold:true, color:C.primaryDk, align:"center", valign:"middle", margin:0 });
    });
    else l.items.forEach((t,i)=>{
      const n = l.items.length, g = 0.14, w = (rw-0.28-g*(n-1))/n;
      s.addText(t, { x:rx+0.14+i*(w+g), y:l.y, w, h:l.h, fontSize:9.5, fontFace:F, color:C.ink, align:"center", valign:"middle", margin:0, lineSpacingMultiple:1.08 });
    });
  }
  [2.17,3.21,4.19].forEach(y=> s.addShape(p.shapes.ISOSCELES_TRIANGLE, { x:1.03, y, w:0.26, h:0.1, fill:{color:C.accent}, rotate:180 }));
}

/* 4 双入口 */
{ const s = p.addSlide();
  page(s, "03 · DUAL ENTRY", "双入口：系统集成走 REST，AI 助手走 MCP", 4);
  const mk = (x, tag, title, rows, cmd) => {
    card(s, x, 1.2, 4.35, 3.24); bar(s, x, 1.2, 3.24);
    s.addText(tag, { x:x+0.24, y:1.36, w:2, h:0.24, fontSize:10, fontFace:M, color:C.primary, bold:true, charSpacing:2, margin:0 });
    s.addText(title, { x:x+0.24, y:1.6, w:3.9, h:0.33, fontSize:16, fontFace:F, bold:true, color:C.ink, margin:0 });
    kv(s, x+0.24, 2.05, 3.9, rows);
    s.addText(cmd, { x:x+0.24, y:4.0, w:3.9, h:0.36, fontSize:8.5, fontFace:M, color:C.code, margin:0 });
  };
  mk(0.55, "REST", "FastAPI · 系统集成入口", [["11 个业务路由域","stores/orders/.../tasks 全覆盖"],
    ["/console 测试台","自动发现接口·表单一键发送"],["X-API-Key 鉴权","配置即启用"],["OpenAPI 文档","/docs 自动生成"]],
    "uvicorn shopify_admin.api.app:create_app --factory");
  mk(5.1, "MCP", "FastMCP · AI 助手入口", [["42 个 shopify_* 工具","覆盖八业务域，AI 直调"],
    ["三级权限","READ 查询 / GENERAL 同步 / ADMIN 写操作"],["双模式","stdio 本地 · SSE 远程 token 定级"]],
    "python -m shopify_admin.mcp_server --sse");
  card(s, 0.55, 4.62, 8.9, 0.56, C.pale);
  s.addText([{ text:"共享同一服务层  ", options:{bold:true, color:C.primaryDk, fontSize:11.5} },
    { text:"能力一处实现、两处可用；任务操作经 @task_record 审计，失败 SMTP 告警", options:{color:C.sub, fontSize:10.5} }],
    { x:0.8, y:4.62, w:8.5, h:0.56, fontFace:F, valign:"middle", margin:0 });
}

/* 5 十域服务 */
{ const s = p.addSlide();
  page(s, "04 · SERVICES", "业务服务层：十域覆盖", 5);
  [["stores","多店铺管理·凭据状态"],["orders","拉单/履约/转化回传"],["products","产品/变体·CS 周同步"],["inventory","库存镜像·diff 推送"],["fulfillment","分仓路由·渠道下单"],
   ["finance","Payout/交易/成本"],["pricing","净利率定价引擎"],["reports","店铺日报汇总"],["marketing","Google Ads·GMC"],["shipping","运费回调·Carrier"]].forEach(([n,d],i)=>{
    const w=1.66, h=1.6, x=0.55+(i%5)*(w+0.155), y=1.3+Math.floor(i/5)*(h+0.22);
    card(s, x, y, w, h); bar(s, x, y, h, i<5?C.primary:C.primaryDk);
    s.addText(n, { x:x+0.15, y:y+0.13, w:w-0.28, h:0.3, fontSize:13, fontFace:M, bold:true, color:C.primaryDk, margin:0 });
    s.addText(d, { x:x+0.15, y:y+0.47, w:w-0.28, h:1.0, fontSize:9.5, fontFace:F, color:C.sub, margin:0, lineSpacingMultiple:1.15 });
  });
}

/* 6 平台×渠道 */
{ const s = p.addSlide();
  page(s, "05 · PLATFORM × CHANNEL", "适配层：卖货平台与履约渠道正交解耦", 6);
  card(s, 0.55, 1.22, 4.35, 3.0); bar(s, 0.55, 1.22, 3.0);
  s.addText("platforms / shopify", { x:0.8, y:1.38, w:3.9, h:0.3, fontSize:15, fontFace:M, bold:true, color:C.ink, margin:0 });
  s.addText("Shopify Admin API 自建客户端（httpx）", { x:0.8, y:1.7, w:3.9, h:0.26, fontSize:10.5, fontFace:F, color:C.sub, margin:0 });
  kv(s, 0.8, 2.12, 3.85, [["REST + GraphQL + bulk","批量操作走 bulk"],["代理支持","国内经 Clash 访问 myshopify"],["限流 + 重试","429 退避，调用方无感"]], 11.5, 9.5);
  card(s, 5.1, 1.22, 4.35, 3.0); bar(s, 5.1, 1.22, 3.0, C.primaryDk);
  s.addText("channels / 履约渠道抽象", { x:5.35, y:1.38, w:3.9, h:0.3, fontSize:15, fontFace:F, bold:true, color:C.ink, margin:0 });
  s.addText("FulfillmentChannel ABC · 五能力：库存 / 运费 / 下单 / 查单 / 跟踪", { x:5.35, y:1.68, w:3.9, h:0.46, fontSize:10, fontFace:F, color:C.sub, margin:0, lineSpacingMultiple:1.1 });
  [["cs.py · CS 代发","复用 BMAI（path 依赖懒加载）；下单去重共用 cs_new.order_records"],
   ["fastrite.py · FastRite 海外仓","xlwms OpenAPI；库存/运费/出库全链路"]].forEach(([t,d],i)=>{
    const y = 2.24 + i*0.98;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x:5.35, y, w:3.85, h:0.86, fill:{color:C.pale}, rectRadius:0.05, line:{color:C.line,width:0.75} });
    s.addText([{ text:t, options:{fontSize:11.5, bold:true, color:C.primaryDk, breakLine:true} },
      { text:d, options:{fontSize:9, color:C.sub} }],
      { x:5.5, y:y+0.07, w:3.55, h:0.74, fontFace:F, margin:0, lineSpacingMultiple:1.1 });
  });
  card(s, 0.55, 4.42, 8.9, 0.7);
  s.addText([{ text:"为什么正交？  ", options:{bold:true, fontSize:12, color:C.primaryDk} },
    { text:"「在哪个店卖」与「谁帮你发货」是独立维度——换仓不动店铺、加店不动渠道，新增渠道只需实现 5 个接口。", options:{fontSize:10.5, color:C.sub} }],
    { x:0.8, y:4.42, w:8.45, h:0.7, fontFace:F, valign:"middle", margin:0 });
}

/* 7 数据层 */
{ const s = p.addSlide();
  page(s, "06 · DATA", "数据层：一主三只读，Alembic 全程管理", 7);
  [["shopify_new","主库 · 可写","业务表全量·Alembic 管理",true],
   ["shopify","老库 · 只读","迁移源 from_legacy",false],
   ["cs_new","CS 镜像 · 只读","BMAI 侧自管",false],
   ["fast_rite","海外仓镜像 · 只读","xlwms 侧自管",false]].forEach(([n,t,d,main],i)=>{
    const w=2.12, x=0.55+i*(w+0.14), y=1.25, h=1.42;
    card(s, x, y, w, h, main?C.pale:C.card); bar(s, x, y, h, main?C.primary:C.sub);
    s.addText(n, { x:x+0.14, y:y+0.12, w:w-0.26, h:0.28, fontSize:12.5, fontFace:M, bold:true, color:C.ink, margin:0 });
    s.addText(t, { x:x+0.14, y:y+0.44, w:w-0.26, h:0.26, fontSize:10.5, fontFace:F, bold:true, color:C.primaryDk, margin:0 });
    s.addText(d, { x:x+0.14, y:y+0.74, w:w-0.26, h:0.6, fontSize:9.5, fontFace:F, color:C.sub, margin:0 });
  });
  card(s, 0.55, 2.92, 8.9, 2.2);
  s.addText("核心数据模型（SQLAlchemy 2.0 · MySQL）", { x:0.8, y:3.08, w:8, h:0.3, fontSize:13.5, fontFace:F, bold:true, color:C.ink, margin:0 });
  const groups = [["店铺/产品","Store · Product · Variant · Collection · Metafield · GoogleProductField · GmcFeed"],
    ["订单/履约","Order · OrderItem（gclid 转化回传）· FulfillmentOrder"],
    ["库存","InventoryLocation · InventoryLevel · SyncLog · SyncPolicy"],
    ["财务/审计","Payout · Transaction · OrderCost · TaskResult"]];
  groups.forEach(([g, ds], i)=>{
    const y = 3.46 + i*0.4;
    s.addText([{ text:g+"  ", options:{fontSize:10.5, bold:true, color:C.primaryDk} },
      { text:ds, options:{fontSize:9.5, fontFace:M, color:C.sub} }],
      { x:0.8, y, w:8.4, h:0.34, fontFace:F, margin:0, valign:"middle" });
  });
}

/* 8 自动化 + 运营 */
{ const s = p.addSlide();
  page(s, "07 · AUTOMATION & OPS", "自动化与运营：调度常驻，运营脚本就位", 8);
  card(s, 0.55, 1.22, 4.35, 3.9); bar(s, 0.55, 1.22, 3.9);
  s.addText("定时任务（APScheduler）", { x:0.8, y:1.36, w:3.9, h:0.3, fontSize:14, fontFace:F, bold:true, color:C.ink, margin:0 });
  [["pull_orders","*/10min","增量拉单·游标续传"],["auto_fulfill","*/15min","分仓路由·可自动下单"],
   ["poll_channels","*/30min","渠道轮询·跟踪号回传"],["sync_inventory","每小时","镜像 diff 推送 Shopify"],
   ["daily_report","08:10","每店铺昨日销量"],["周同步/重定价","周一/每日","产品周同步·重定价"]].forEach(([j,c,d],i)=>{
    const y = 1.76 + i*0.52;
    s.addText([{ text:j+"  ", options:{fontFace:M, fontSize:10.5, bold:true, color:C.primaryDk} },
      { text:c, options:{fontFace:M, fontSize:9.5, color:C.accent, breakLine:true} }],
      { x:0.8, y, w:1.85, h:0.5, fontFace:F, margin:0 });
    s.addText(d, { x:2.7, y:y+0.03, w:2.05, h:0.48, fontSize:9.5, fontFace:F, color:C.sub, margin:0 });
  });
  card(s, 5.1, 1.22, 4.35, 3.9); bar(s, 5.1, 1.22, 3.9, C.primaryDk);
  s.addText("运营体系（deploy/ · 服务器运行）", { x:5.35, y:1.36, w:3.9, h:0.3, fontSize:14, fontFace:F, bold:true, color:C.ink, margin:0 });
  [["Google Ads 投放","300+ 脚本：建系列/修价/PMax/断崖诊断"],
   ["GA4 分析","流量审计·结账漏斗·转化归因"],
   ["B2B 主题交付","Battery Finder/规格书/证书页 + 回滚 SOP"],
   ["部署","systemd + nginx（HK 服务器）"]].forEach(([t,d],i)=>{
    const y = 1.78 + i*0.8;
    s.addShape(p.shapes.OVAL, { x:5.35, y:y+0.04, w:0.12, h:0.12, fill:{color:C.accent} });
    s.addText([{ text:t, options:{fontSize:11.5, bold:true, color:C.primaryDk, breakLine:true} },
      { text:d, options:{fontSize:9.5, color:C.sub} }],
      { x:5.6, y:y-0.05, w:3.6, h:0.78, fontFace:F, margin:0, lineSpacingMultiple:1.12 });
  });
}

/* 9 店铺前端 */
{ const s = p.addSlide();
  page(s, "08 · STOREFRONT", "店铺前端：B2B 能力直接长在主题上", 9);
  const pics = [["../estry-model-page.png","Battery Finder 型号页","8,752 型号五维分面搜索，索引 9,114 条"],
    ["../wholesale.png","批发询盘 / B2B Hub","阶梯价·询盘表单·规格书·UN38.3 证书页"]];
  pics.forEach(([f, t, d], i)=>{
    const x = 0.55 + i*4.55;
    card(s, x, 1.22, 4.35, 3.42);
    s.addImage({ path: f, x: x+0.13, y: 1.35, w: 4.09, h: 2.3, sizing: { type: "cover", w: 4.09, h: 2.3 } });
    s.addText(t, { x:x+0.13, y:3.72, w:4.09, h:0.28, fontSize:12.5, fontFace:F, bold:true, color:C.ink, margin:0 });
    s.addText(d, { x:x+0.13, y:4.0, w:4.09, h:0.55, fontSize:9.5, fontFace:F, color:C.sub, margin:0, lineSpacingMultiple:1.12 });
  });
  card(s, 0.55, 4.78, 8.9, 0.44, C.pale);
  s.addText("交付链路：CS 镜像库 → build_spec_index.py 分片 JSON 索引 → theme assets（liquid section）· 政策页/弃购监控已上线", { x:0.8, y:4.78, w:8.5, h:0.44, fontSize:10, fontFace:F, color:C.primaryDk, valign:"middle", margin:0 });
}

/* 10 尾页 */
{ const s = p.addSlide();
  s.background = { color: C.dark };
  s.addShape(p.shapes.OVAL, { x:7.9, y:3.6, w:3.6, h:3.6, fill:{color:C.dark}, line:{color:C.primaryDk,width:1.2} });
  s.addText("STACK & DEPLOY", { x:0.75, y:0.55, w:6, h:0.3, fontSize:11, fontFace:M, color:C.accent, charSpacing:4, bold:true, margin:0 });
  s.addText("技术栈与部署拓扑", { x:0.72, y:0.85, w:8, h:0.6, fontSize:30, fontFace:F, color:"FFFFFF", bold:true, margin:0 });
  const stack = ["Python 3.11","FastAPI","FastMCP","SQLAlchemy 2.0","Alembic","APScheduler","httpx","MySQL","uv","pytest×34"];
  let sx = 0.75, sy = 1.75;
  stack.forEach(t=>{
    const w = 0.35 + t.length*0.095;
    if (sx + w > 9.4) { sx = 0.75; sy += 0.52; }
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x:sx, y:sy, w, h:0.38, fill:{color:C.primaryDk}, rectRadius:0.05, line:{color:C.primary,width:0.75} });
    s.addText(t, { x:sx, y:sy-0.01, w, h:0.38, fontSize:10.5, fontFace:M, color:C.onDark, align:"center", valign:"middle", margin:0 });
    sx += w + 0.15;
  });
  const flow = [["Windows 开发",1.5],["GitHub",1.1],["HK 服务器部署",1.9],["Shopify / CS / FastRite",2.35]];
  let fx = 0.75;
  flow.forEach(([t,w],i)=>{
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x:fx, y:3.85, w, h:0.5, fill:{color:"013B2F"}, rectRadius:0.05, line:{color:C.primary,width:1} });
    s.addText(t, { x:fx, y:3.84, w, h:0.5, fontSize:10.5, fontFace:F, color:C.onDark, align:"center", valign:"middle", margin:0 });
    fx += w;
    if (i < flow.length-1) {
      s.addText("→", { x:fx-0.02, y:3.84, w:0.35, h:0.5, fontSize:14, color:C.accent, align:"center", valign:"middle", margin:0 });
      fx += 0.32;
    }
  });
  s.addText("shopify-admin · 2026-11 · zane", { x:0.75, y:5.0, w:5, h:0.3, fontSize:10.5, fontFace:F, color:C.onDarkSub, margin:0 });
}

p.writeFile({ fileName: "shopify_admin_architecture.pptx" }).then(() => console.log("OK shopify_admin_architecture.pptx"));
