import { useState, useEffect, useCallback, useRef } from "react";
import {
  ComposedChart, LineChart, BarChart, AreaChart, RadarChart,
  Line, Bar, Area, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine, Cell, PieChart, Pie, ScatterChart, Scatter
} from "recharts";

// ─── DESIGN TOKENS ────────────────────────────────────────────────────────────
const T = {
  bg:       "#05080d",
  surface:  "#0a0f18",
  s2:       "#111827",
  s3:       "#1a2332",
  s4:       "#1f2d42",
  border:   "rgba(99,179,237,0.1)",
  borderHi: "rgba(99,179,237,0.3)",
  accent:   "#63b3ed",
  accent2:  "#a78bfa",
  accent3:  "#34d399",
  warning:  "#fbbf24",
  danger:   "#f87171",
  muted:    "#4b5563",
  dim:      "#6b7280",
  text:     "#e2e8f0",
};

const REGIME_COLORS = {
  trending:      "rgba(52,211,153,0.15)",
  volatile:      "rgba(248,113,113,0.15)",
  mean_reverting:"rgba(99,179,237,0.15)",
};
const REGIME_STROKE = {
  trending:      "#34d399",
  volatile:      "#f87171",
  mean_reverting:"#63b3ed",
};

// ─── STYLES ───────────────────────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;500;600;700;800&display=swap');
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:${T.bg};color:${T.text};font-family:'Outfit',sans-serif;overflow-x:hidden}
  ::-webkit-scrollbar{width:4px;height:4px}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:${T.s4};border-radius:2px}
  .mono{font-family:'DM Mono',monospace}
  @keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
  @keyframes pulse2{0%,100%{opacity:1}50%{opacity:0.3}}
  @keyframes shimmer{0%{background-position:-200%}100%{background-position:200%}}
  .fade-up{animation:fadeUp 0.5s ease forwards}
  .tab-btn{transition:all 0.2s}
  .chip-hover:hover{border-color:${T.borderHi}!important;color:${T.accent}!important;transform:translateY(-1px)}
`;

// ─── MOCK DATA (mirrors backend API responses) ─────────────────────────────────
function genGBM(n, s0=450, mu=0.0003, sigma=0.015) {
  const prices = [s0];
  for(let i=1;i<n;i++){
    const ret = Math.exp((mu-0.5*sigma*sigma)+sigma*( (Math.random()+Math.random()+Math.random()-1.5)*0.5773));
    prices.push(+(prices[i-1]*ret).toFixed(2));
  }
  return prices;
}
function genTimestamps(n, intervalMin=60) {
  const base = new Date("2024-01-02T09:30:00");
  return Array.from({length:n},(_,i)=>{
    const d = new Date(base.getTime() + i*intervalMin*60000);
    return d.toISOString().slice(0,16).replace("T"," ");
  });
}

const DATA = (() => {
  const n=120; const closes=genGBM(n); const ts=genTimestamps(n);
  // Market + sentiment
  let sentBase=0;
  const market = closes.map((c,i)=>{
    sentBase += (Math.random()-0.5)*0.08;
    sentBase = Math.max(-1,Math.min(1,sentBase));
    const spr = c*0.008;
    return {
      ts: ts[i], close:c,
      open: i>0?closes[i-1]:c*0.999,
      high: +(c+Math.abs((Math.random()-0.5)*spr*2)).toFixed(2),
      low:  +(c-Math.abs((Math.random()-0.5)*spr*2)).toFixed(2),
      vol:  Math.round(800000+Math.random()*3200000),
      sentiment: +sentBase.toFixed(3),
      articles:  Math.round(2+Math.random()*16),
    };
  });

  // Events
  const HEADLINES=[
    {h:"Fed signals rate pause",s:0.72},
    {h:"Earnings beat by 12%",s:0.85},
    {h:"CEO departure announced",s:-0.68},
    {h:"Product recall issued",s:-0.55},
    {h:"Major AI acquisition",s:0.61},
    {h:"SEC probe initiated",s:-0.74},
    {h:"Record quarterly revenue",s:0.88},
    {h:"Missed guidance by 8%",s:-0.71},
  ];
  const evtIdxs=[9,22,35,44,60,73,88,105];
  const events = evtIdxs.map((idx,i)=>({
    id:`e${i}`, idx, ts:ts[idx],
    headline: HEADLINES[i%HEADLINES.length].h,
    sentiment: HEADLINES[i%HEADLINES.length].s,
    priceBefore: closes[Math.max(0,idx-1)],
    priceAfter:  closes[Math.min(n-1,idx+3)],
    abnReturn:  +((closes[Math.min(n-1,idx+3)]-closes[Math.max(0,idx-1)])/closes[Math.max(0,idx-1)]*100).toFixed(2),
  }));

  // Portfolio equity curve
  const portfolio252 = genGBM(252, 100000, 0.0004, 0.012);
  const benchmark252 = genGBM(252, 100000, 0.00035, 0.010);
  let peak=portfolio252[0];
  const equity = portfolio252.map((v,i)=>{
    peak=Math.max(peak,v);
    return {
      date:`2024-${String(Math.floor(i/21)+1).padStart(2,"0")}-${String((i%21)+1).padStart(2,"0")}`,
      portfolio:+v.toFixed(0), benchmark:+benchmark252[i].toFixed(0),
      drawdown: +((v-peak)/peak*100).toFixed(2),
    };
  });

  // Correlation matrix
  const assets=["AAPL","MSFT","NVDA","JPM","SPY","BND","AMZN","GLD"];
  const corrMatrix=[
    [1.00,0.82,0.71,0.41,0.78,-0.18,0.65,-0.12],
    [0.82,1.00,0.68,0.38,0.75,-0.21,0.70,-0.09],
    [0.71,0.68,1.00,0.29,0.62,-0.14,0.58,-0.05],
    [0.41,0.38,0.29,1.00,0.55, 0.12,0.36, 0.08],
    [0.78,0.75,0.62,0.55,1.00, 0.05,0.72,-0.02],
    [-0.18,-0.21,-0.14,0.12,0.05,1.00,-0.15,0.42],
    [0.65,0.70,0.58,0.36,0.72,-0.15,1.00,-0.08],
    [-0.12,-0.09,-0.05,0.08,-0.02,0.42,-0.08,1.00],
  ];

  // Regime
  const regimeSched=[
    {start:0,end:30,r:"trending",conf:0.91,color:REGIME_COLORS.trending,stroke:REGIME_STROKE.trending},
    {start:30,end:55,r:"volatile",conf:0.88,color:REGIME_COLORS.volatile,stroke:REGIME_STROKE.volatile},
    {start:55,end:80,r:"mean_reverting",conf:0.76,color:REGIME_COLORS.mean_reverting,stroke:REGIME_STROKE.mean_reverting},
    {start:80,end:95,r:"trending",conf:0.83,color:REGIME_COLORS.trending,stroke:REGIME_STROKE.trending},
    {start:95,end:120,r:"volatile",conf:0.79,color:REGIME_COLORS.volatile,stroke:REGIME_STROKE.volatile},
  ];
  const regimeData = closes.map((c,i)=>{
    const seg = regimeSched.find(s=>i>=s.start&&i<s.end)||regimeSched[0];
    const pt = seg.conf; const other=(1-pt)/2;
    return {
      ts:ts[i], close:c,
      p_trending:    seg.r==="trending"    ? +pt.toFixed(2) : +other.toFixed(2),
      p_volatile:    seg.r==="volatile"    ? +pt.toFixed(2) : +other.toFixed(2),
      p_mean_revert: seg.r==="mean_reverting"?+pt.toFixed(2):+other.toFixed(2),
      regime: seg.r,
    };
  });

  // Trades
  const tCloses = genGBM(80, 580, 0.0002, 0.018);
  const tTs = genTimestamps(80, 30);
  const tradeData = tCloses.map((c,i)=>({ts:tTs[i],close:c}));
  const tradePts=[
    {idx:8,act:"BUY",qty:10,ai:"Momentum breakout",mistake:false},
    {idx:22,act:"SELL",qty:10,ai:"Risk-off signal",mistake:false},
    {idx:35,act:"BUY",qty:10,ai:"Mean reversion entry",mistake:false},
    {idx:50,act:"SELL",qty:10,ai:"Weak signal",mistake:true,reason:"Sold too early — missed 8% continuation"},
    {idx:65,act:"BUY",qty:10,ai:"Regime shift detected",mistake:false},
  ];
  const trades = tradePts.map((t,i)=>({
    ...t, price:tCloses[t.idx], ts:tTs[t.idx],
    pnl: t.act==="SELL"?+((tCloses[t.idx]-tCloses[tradePts[i-1]?.idx||t.idx])*10).toFixed(0):null,
  }));
  let cumPnl=0;
  const pnlTimeline = tCloses.map((c,i)=>{
    const tr = trades.find(t=>t.idx===i&&t.pnl!=null);
    if(tr) cumPnl+=tr.pnl;
    return {ts:tTs[i],cumPnl, tradePnl:tr?.pnl??null};
  });

  return { market, events, equity, corrMatrix, assets, regimeData, regimeSched, tradeData, trades, pnlTimeline };
})();

// ─── SHARED COMPONENTS ────────────────────────────────────────────────────────
const Panel = ({title, subtitle, children, className=""}) => (
  <div style={{background:T.s2,border:`1px solid ${T.border}`,borderRadius:12,overflow:"hidden"}} className={className}>
    {(title||subtitle) && (
      <div style={{padding:"14px 18px",borderBottom:`1px solid ${T.border}`,display:"flex",alignItems:"baseline",gap:10}}>
        {title && <span style={{fontFamily:"Outfit",fontWeight:700,fontSize:14,color:T.text}}>{title}</span>}
        {subtitle && <span style={{fontFamily:"DM Mono",fontSize:10,color:T.muted,letterSpacing:"1.5px",textTransform:"uppercase"}}>{subtitle}</span>}
      </div>
    )}
    <div style={{padding:18}}>{children}</div>
  </div>
);

const Metric = ({label,value,sub,color=T.text,glow=false}) => (
  <div style={{background:T.s3,border:`1px solid ${T.border}`,borderRadius:8,padding:"12px 14px",
    boxShadow:glow?`0 0 16px ${color}22`:undefined}}>
    <div style={{fontSize:10,fontFamily:"DM Mono",color:T.muted,letterSpacing:"1.5px",textTransform:"uppercase",marginBottom:4}}>{label}</div>
    <div style={{fontFamily:"Outfit",fontWeight:700,fontSize:22,color}}>{value}</div>
    {sub && <div style={{fontSize:10,fontFamily:"DM Mono",color:T.dim,marginTop:3}}>{sub}</div>}
  </div>
);

const Badge = ({label,color=T.accent}) => (
  <span style={{background:`${color}18`,border:`1px solid ${color}44`,color,borderRadius:20,
    padding:"2px 10px",fontSize:10,fontFamily:"DM Mono",letterSpacing:"1px"}}>
    {label}
  </span>
);

const Loading = () => (
  <div style={{display:"flex",alignItems:"center",justifyContent:"center",height:200}}>
    <div style={{display:"flex",gap:8}}>
      {[0,1,2].map(i=>(
        <div key={i} style={{width:8,height:8,borderRadius:"50%",background:T.accent,
          animation:`pulse2 1.2s ${i*0.2}s infinite`}}/>
      ))}
    </div>
  </div>
);

// Custom tooltip base
const TooltipBox = ({children}) => (
  <div style={{background:T.s3,border:`1px solid ${T.borderHi}`,borderRadius:8,
    padding:"10px 14px",boxShadow:"0 8px 32px rgba(0,0,0,0.5)",maxWidth:280}}>
    {children}
  </div>
);

// ─── 1. MARKET-NEWS DASHBOARD ─────────────────────────────────────────────────
const MarketNewsDashboard = () => {
  const [selected, setSelected] = useState(null);
  const [hovering, setHovering] = useState(null);

  const evtMap = {};
  DATA.events.forEach(e=>{ evtMap[e.ts]=e; });

  const chartData = DATA.market.map((d,i)=>({
    ...d,
    label: d.ts.slice(5,16),
    event: evtMap[d.ts]||null,
    sentBar: d.sentiment,
  }));

  const CustomDot = (props) => {
    const {cx,cy,payload} = props;
    if(!payload.event) return null;
    const s = payload.event.sentiment;
    const color = s>0?T.accent3:T.danger;
    return (
      <g onClick={()=>setSelected(payload.event)} style={{cursor:"pointer"}}>
        <circle cx={cx} cy={cy} r={6} fill={color} stroke={T.bg} strokeWidth={2}
          opacity={selected?.id===payload.event.id?1:0.8}/>
        <circle cx={cx} cy={cy} r={10} fill={color} opacity={0.2}/>
      </g>
    );
  };

  const CustomTooltip = ({active,payload}) => {
    if(!active||!payload?.length) return null;
    const d = payload[0]?.payload;
    return (
      <TooltipBox>
        <div className="mono" style={{fontSize:10,color:T.muted,marginBottom:6}}>{d.ts}</div>
        <div style={{fontSize:13,fontWeight:600,marginBottom:4}}>Close: <span style={{color:T.accent}}>${d.close}</span></div>
        <div style={{fontSize:12,color:T.dim}}>Sentiment: <span style={{color:d.sentiment>0?T.accent3:T.danger}}>{d.sentiment?.toFixed(3)}</span></div>
        <div style={{fontSize:11,color:T.dim}}>Articles: {d.articles}</div>
        {d.event && (
          <div style={{marginTop:8,paddingTop:8,borderTop:`1px solid ${T.border}`}}>
            <div style={{fontSize:11,fontWeight:600,color:T.warning}}>📰 News Event</div>
            <div style={{fontSize:11,marginTop:4,color:T.text,lineHeight:1.4}}>{d.event.headline}</div>
            <div style={{fontSize:10,color:T.dim,marginTop:2}}>Abnormal Return: <span style={{color:d.event.abnReturn>0?T.accent3:T.danger}}>{d.event.abnReturn>0?"+":""}{d.event.abnReturn}%</span></div>
          </div>
        )}
      </TooltipBox>
    );
  };

  return (
    <div style={{display:"flex",flexDirection:"column",gap:16}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
        <Metric label="Events Detected" value={DATA.events.length} color={T.accent}/>
        <Metric label="Avg Abnormal Ret" value="+1.24%" color={T.accent3} glow/>
        <Metric label="Positive Events" value={DATA.events.filter(e=>e.sentiment>0).length} color={T.accent3}/>
        <Metric label="Negative Events" value={DATA.events.filter(e=>e.sentiment<0).length} color={T.danger}/>
      </div>

      <Panel title="Price + Sentiment Timeline" subtitle="click event markers">
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={chartData.filter((_,i)=>i%2===0)}>
            <CartesianGrid stroke={T.border} strokeDasharray="2 4"/>
            <XAxis dataKey="label" tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} interval={14} tickLine={false}/>
            <YAxis yAxisId="price" domain={["auto","auto"]} tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} tickLine={false} width={55}
              tickFormatter={v=>`$${v.toFixed(0)}`}/>
            <YAxis yAxisId="sent" orientation="right" domain={[-1,1]} tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} tickLine={false} width={40}/>
            <Tooltip content={<CustomTooltip/>}/>
            <Bar yAxisId="sent" dataKey="sentBar" opacity={0.5} radius={[2,2,0,0]}>
              {chartData.filter((_,i)=>i%2===0).map((d,i)=>(
                <Cell key={i} fill={d.sentiment>0?T.accent3:T.danger}/>
              ))}
            </Bar>
            <Line yAxisId="price" type="monotone" dataKey="close" stroke={T.accent}
              strokeWidth={2} dot={<CustomDot/>} activeDot={{r:4,fill:T.accent}}/>
          </ComposedChart>
        </ResponsiveContainer>
      </Panel>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
        <Panel title="News Events Log" subtitle={`${DATA.events.length} events`}>
          <div style={{display:"flex",flexDirection:"column",gap:6,maxHeight:240,overflowY:"auto"}}>
            {DATA.events.map(e=>(
              <div key={e.id} onClick={()=>setSelected(selected?.id===e.id?null:e)}
                style={{background:selected?.id===e.id?T.s4:T.s3,border:`1px solid ${selected?.id===e.id?T.borderHi:T.border}`,
                  borderRadius:6,padding:"8px 12px",cursor:"pointer",transition:"all 0.2s",
                  borderLeft:`3px solid ${e.sentiment>0?T.accent3:T.danger}`}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:3}}>
                  <span style={{fontSize:10,fontFamily:"DM Mono",color:T.muted}}>{e.ts.slice(5,16)}</span>
                  <Badge label={`${e.abnReturn>0?"+":""}${e.abnReturn}%`} color={e.abnReturn>0?T.accent3:T.danger}/>
                </div>
                <div style={{fontSize:12,color:T.text,lineHeight:1.3}}>{e.headline}</div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Abnormal Returns" subtitle="event window analysis">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={DATA.events.map(e=>({name:e.headline.slice(0,18)+"…",ret:e.abnReturn,fill:e.abnReturn>0?T.accent3:T.danger}))}>
              <CartesianGrid stroke={T.border} strokeDasharray="2 4"/>
              <XAxis dataKey="name" tick={{fill:T.muted,fontSize:8,fontFamily:"DM Mono"}} interval={0} angle={-20} textAnchor="end" height={50}/>
              <YAxis tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} tickLine={false} tickFormatter={v=>`${v}%`}/>
              <ReferenceLine y={0} stroke={T.border} strokeWidth={1}/>
              <Tooltip formatter={(v)=>[`${v}%`,"Abnormal Return"]} contentStyle={{background:T.s3,border:`1px solid ${T.borderHi}`,borderRadius:8}}/>
              <Bar dataKey="ret" radius={[3,3,0,0]}>
                {DATA.events.map((e,i)=><Cell key={i} fill={e.abnReturn>0?T.accent3:T.danger}/>)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>
    </div>
  );
};

// ─── 2. PORTFOLIO RISK DASHBOARD ──────────────────────────────────────────────
const radarData = [
  {metric:"Volatility",  value:62, full:100},
  {metric:"Beta",        value:87, full:100},
  {metric:"Drawdown",    value:45, full:100},
  {metric:"Diversif.",   value:73, full:100},
  {metric:"Sharpe",      value:71, full:100},
  {metric:"VaR",         value:55, full:100},
];
const alloc = [
  {name:"AAPL",value:22,color:"#63b3ed"},{name:"MSFT",value:18.5,color:"#a78bfa"},
  {name:"NVDA",value:15,color:"#34d399"},{name:"JPM",value:10,color:"#fbbf24"},
  {name:"SPY",value:12,color:"#f87171"},{name:"BND",value:8,color:"#6ee7b7"},
  {name:"AMZN",value:9.5,color:"#c084fc"},{name:"CASH",value:5,color:"#94a3b8"},
];

const PortfolioRiskDashboard = () => {
  const [activeRange, setActiveRange] = useState("1Y");
  const slices = {
    "1M": DATA.equity.slice(-21), "3M": DATA.equity.slice(-63),
    "6M": DATA.equity.slice(-126), "1Y": DATA.equity,
  };
  const equitySlice = slices[activeRange];

  const CustomTooltip = ({active,payload,label}) => {
    if(!active||!payload?.length) return null;
    return (
      <TooltipBox>
        <div className="mono" style={{fontSize:10,color:T.muted,marginBottom:6}}>{label}</div>
        {payload.map((p,i)=>(
          <div key={i} style={{fontSize:12,marginBottom:2}}>
            <span style={{color:p.stroke||p.fill}}>{p.name}: </span>
            <span style={{fontWeight:600}}>${p.value?.toLocaleString()}</span>
          </div>
        ))}
      </TooltipBox>
    );
  };

  const DdTooltip = ({active,payload,label}) => {
    if(!active||!payload?.length) return null;
    return (
      <TooltipBox>
        <div className="mono" style={{fontSize:10,color:T.muted,marginBottom:4}}>{label}</div>
        <div style={{fontSize:12,color:T.danger,fontWeight:600}}>{payload[0]?.value?.toFixed(2)}%</div>
      </TooltipBox>
    );
  };

  return (
    <div style={{display:"flex",flexDirection:"column",gap:16}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
        <Metric label="Ann. Volatility" value="18.4%" color={T.warning}/>
        <Metric label="Sharpe Ratio" value="1.42" color={T.accent3} glow/>
        <Metric label="Max Drawdown" value="-12.3%" color={T.danger}/>
        <Metric label="Portfolio Beta" value="0.87" color={T.accent}/>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
        <Panel title="Risk Radar" subtitle="normalized 0–100">
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={radarData} outerRadius={90}>
              <PolarGrid stroke={T.border}/>
              <PolarAngleAxis dataKey="metric" tick={{fill:T.dim,fontSize:11,fontFamily:"DM Mono"}}/>
              <PolarRadiusAxis angle={90} domain={[0,100]} tick={false} axisLine={false}/>
              <Radar name="Portfolio" dataKey="value" stroke={T.accent} fill={T.accent} fillOpacity={0.2} strokeWidth={2}/>
            </RadarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Allocation" subtitle="by weight">
          <div style={{display:"flex",gap:16,alignItems:"center"}}>
            <div style={{flex:"0 0 180px"}}>
              <ResponsiveContainer width={180} height={180}>
                <PieChart>
                  <Pie data={alloc} dataKey="value" cx="50%" cy="50%" outerRadius={75}
                    innerRadius={40} strokeWidth={0}>
                    {alloc.map((a,i)=><Cell key={i} fill={a.color}/>)}
                  </Pie>
                  <Tooltip formatter={(v,n)=>[`${v}%`,n]} contentStyle={{background:T.s3,border:`1px solid ${T.borderHi}`,borderRadius:8}}/>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{flex:1,display:"grid",gridTemplateColumns:"1fr 1fr",gap:4}}>
              {alloc.map(a=>(
                <div key={a.name} style={{display:"flex",alignItems:"center",gap:6,padding:"4px 0"}}>
                  <div style={{width:8,height:8,borderRadius:"50%",background:a.color,flexShrink:0}}/>
                  <span style={{fontSize:11,fontFamily:"DM Mono",color:T.text}}>{a.name}</span>
                  <span style={{fontSize:11,fontFamily:"DM Mono",color:T.muted,marginLeft:"auto"}}>{a.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Equity Curve" subtitle="vs benchmark">
        <div style={{display:"flex",gap:8,marginBottom:12}}>
          {["1M","3M","6M","1Y"].map(r=>(
            <button key={r} onClick={()=>setActiveRange(r)} className="tab-btn"
              style={{background:activeRange===r?T.accent+"22":T.s3,
                border:`1px solid ${activeRange===r?T.accent:T.border}`,
                color:activeRange===r?T.accent:T.dim,borderRadius:6,
                padding:"4px 14px",fontSize:11,fontFamily:"DM Mono",cursor:"pointer"}}>
              {r}
            </button>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={equitySlice}>
            <CartesianGrid stroke={T.border} strokeDasharray="2 4"/>
            <XAxis dataKey="date" tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} interval={Math.floor(equitySlice.length/6)} tickLine={false}/>
            <YAxis tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} tickLine={false} tickFormatter={v=>`$${(v/1000).toFixed(0)}k`} width={50}/>
            <Tooltip content={<CustomTooltip/>}/>
            <Line type="monotone" dataKey="portfolio" name="Portfolio" stroke={T.accent} strokeWidth={2} dot={false}/>
            <Line type="monotone" dataKey="benchmark" name="Benchmark" stroke={T.muted} strokeWidth={1.5} dot={false} strokeDasharray="4 2"/>
          </ComposedChart>
        </ResponsiveContainer>
      </Panel>

      <Panel title="Drawdown Chart" subtitle="peak-to-trough">
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={equitySlice}>
            <CartesianGrid stroke={T.border} strokeDasharray="2 4"/>
            <XAxis dataKey="date" tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} interval={Math.floor(equitySlice.length/6)} tickLine={false}/>
            <YAxis tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} tickLine={false} tickFormatter={v=>`${v}%`} width={45}/>
            <Tooltip content={<DdTooltip/>}/>
            <ReferenceLine y={0} stroke={T.border}/>
            <Area type="monotone" dataKey="drawdown" stroke={T.danger} fill={T.danger} fillOpacity={0.2} strokeWidth={1.5}/>
          </AreaChart>
        </ResponsiveContainer>
      </Panel>
    </div>
  );
};

// ─── 3. REGIME TIMELINE ───────────────────────────────────────────────────────
const RegimeDashboard = () => {
  const [hoverRegime, setHoverRegime] = useState(null);

  const regimeLabels = {trending:"Trending",volatile:"Volatile",mean_reverting:"Mean Rev."};
  const regimeBadgeColors = {trending:T.accent3,volatile:T.danger,mean_reverting:T.accent};

  // Build reference areas for background coloring
  const transitions = [];
  let curRegime = DATA.regimeData[0]?.regime;
  let curStart = DATA.regimeData[0]?.ts;
  DATA.regimeData.forEach((d,i)=>{
    if(d.regime!==curRegime||i===DATA.regimeData.length-1){
      transitions.push({start:curStart,end:d.ts,regime:curRegime,
        color:REGIME_COLORS[curRegime]});
      curRegime=d.regime; curStart=d.ts;
    }
  });

  const PriceTooltip = ({active,payload}) => {
    if(!active||!payload?.length) return null;
    const d=payload[0]?.payload;
    return (
      <TooltipBox>
        <div className="mono" style={{fontSize:10,color:T.muted,marginBottom:6}}>{d.ts}</div>
        <div style={{fontSize:13,fontWeight:600}}>Close: <span style={{color:T.accent}}>${d.close}</span></div>
        <div style={{marginTop:6,display:"flex",gap:6,flexWrap:"wrap"}}>
          <Badge label={`Trend ${(d.p_trending*100).toFixed(0)}%`} color={T.accent3}/>
          <Badge label={`Vol ${(d.p_volatile*100).toFixed(0)}%`} color={T.danger}/>
          <Badge label={`MR ${(d.p_mean_revert*100).toFixed(0)}%`} color={T.accent}/>
        </div>
      </TooltipBox>
    );
  };

  const step = 4;
  const regimeSlice = DATA.regimeData.filter((_,i)=>i%step===0);

  return (
    <div style={{display:"flex",flexDirection:"column",gap:16}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12}}>
        {Object.entries({trending:[T.accent3,"Trending Bars",DATA.regimeSched.filter(s=>s.r==="trending").length],
                         volatile:[T.danger,"Volatile Bars",DATA.regimeSched.filter(s=>s.r==="volatile").length],
                         mean_reverting:[T.accent,"Mean Rev Bars",DATA.regimeSched.filter(s=>s.r==="mean_reverting").length]})
          .map(([r,[c,l,v]])=>(
          <div key={r} style={{background:T.s3,border:`1px solid ${c}33`,borderRadius:8,
            padding:"12px 16px",boxShadow:`0 0 16px ${c}11`}}>
            <div style={{fontSize:10,fontFamily:"DM Mono",color:T.muted,letterSpacing:"1.5px",textTransform:"uppercase",marginBottom:4}}>{l}</div>
            <div style={{fontSize:22,fontWeight:700,color:c}}>{v}</div>
            <div style={{height:3,background:T.s4,borderRadius:2,marginTop:8}}>
              <div style={{height:"100%",width:`${v/5*100}%`,background:c,borderRadius:2}}/>
            </div>
          </div>
        ))}
      </div>

      <Panel title="Price with Regime Zones" subtitle="colored background by detected regime">
        <div style={{marginBottom:8,display:"flex",gap:12,flexWrap:"wrap"}}>
          {Object.entries({trending:[T.accent3,"Trending"],volatile:[T.danger,"Volatile"],mean_reverting:[T.accent,"Mean Rev."]}).map(([k,[c,l]])=>(
            <div key={k} style={{display:"flex",alignItems:"center",gap:5}}>
              <div style={{width:12,height:12,borderRadius:2,background:c,opacity:0.7}}/>
              <span style={{fontSize:11,fontFamily:"DM Mono",color:T.dim}}>{l}</span>
            </div>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart data={regimeSlice}>
            <CartesianGrid stroke={T.border} strokeDasharray="2 4"/>
            <XAxis dataKey="ts" tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} interval={8}
              tickFormatter={v=>v.slice(5,13)} tickLine={false}/>
            <YAxis domain={["auto","auto"]} tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} tickLine={false}
              tickFormatter={v=>`$${v.toFixed(0)}`} width={55}/>
            <Tooltip content={<PriceTooltip/>}/>
            {/* Colored area by regime */}
            <Area type="monotone" dataKey={d=>
              d.regime==="trending"?d.close:null
            } fill={T.accent3} fillOpacity={0.06} stroke="none"/>
            {/* Regime-colored line segments */}
            <Line type="monotone" dataKey="close" strokeWidth={2.5} dot={false}
              stroke={T.accent} activeDot={{r:4,fill:T.accent}}/>
          </ComposedChart>
        </ResponsiveContainer>
      </Panel>

      <Panel title="Regime Probability Stack" subtitle="HMM state probabilities over time">
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={regimeSlice}>
            <CartesianGrid stroke={T.border} strokeDasharray="2 4"/>
            <XAxis dataKey="ts" tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} interval={8}
              tickFormatter={v=>v.slice(5,13)} tickLine={false}/>
            <YAxis domain={[0,1]} tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} tickLine={false}
              tickFormatter={v=>`${(v*100).toFixed(0)}%`} width={40}/>
            <Tooltip contentStyle={{background:T.s3,border:`1px solid ${T.borderHi}`,borderRadius:8}}/>
            <Legend wrapperStyle={{fontSize:10,fontFamily:"DM Mono"}}/>
            <Area type="monotone" dataKey="p_trending" name="Trending" stackId="1" stroke={T.accent3} fill={T.accent3} fillOpacity={0.6}/>
            <Area type="monotone" dataKey="p_volatile" name="Volatile" stackId="1" stroke={T.danger} fill={T.danger} fillOpacity={0.6}/>
            <Area type="monotone" dataKey="p_mean_revert" name="Mean Rev." stackId="1" stroke={T.accent} fill={T.accent} fillOpacity={0.6}/>
          </AreaChart>
        </ResponsiveContainer>
      </Panel>
    </div>
  );
};

// ─── 4. CORRELATION HEATMAP ───────────────────────────────────────────────────
const CorrelationHeatmap = () => {
  const [hovCell, setHovCell] = useState(null);
  const [selectedPair, setSelectedPair] = useState(null);
  const assets = DATA.assets;
  const matrix = DATA.corrMatrix;

  const corrColor = (v) => {
    if(v>=0.7) return "#1d4ed8";
    if(v>=0.5) return "#3b82f6";
    if(v>=0.3) return "#60a5fa";
    if(v>=0.1) return "#93c5fd";
    if(v>=-0.1) return "#475569";
    if(v>=-0.3) return "#f97316";
    if(v>=-0.5) return "#ea580c";
    return "#dc2626";
  };

  const cellSize = 56;
  const n = assets.length;

  return (
    <div style={{display:"flex",flexDirection:"column",gap:16}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
        <Metric label="Assets" value={n} color={T.accent}/>
        <Metric label="Avg Tech Corr" value="0.74" color={T.accent} sub="AAPL/MSFT/NVDA"/>
        <Metric label="Bond Hedge" value="-0.18" color={T.accent3} sub="BND vs tech" glow/>
        <Metric label="Gold Diversif." value="-0.07" color={T.accent2} sub="GLD avg"/>
      </div>

      <Panel title="Correlation Heatmap" subtitle="90-day rolling pearson · hover to inspect">
        <div style={{display:"flex",gap:24,flexWrap:"wrap"}}>
          <div style={{overflowX:"auto"}}>
            <div style={{display:"inline-block"}}>
              {/* Column headers */}
              <div style={{display:"flex",marginLeft:cellSize+4}}>
                {assets.map(a=>(
                  <div key={a} style={{width:cellSize,textAlign:"center",fontSize:9,
                    fontFamily:"DM Mono",color:T.muted,paddingBottom:4}}>{a}</div>
                ))}
              </div>
              {/* Rows */}
              {matrix.map((row,i)=>(
                <div key={i} style={{display:"flex",marginBottom:2,alignItems:"center"}}>
                  <div style={{width:cellSize,fontSize:9,fontFamily:"DM Mono",
                    color:T.muted,textAlign:"right",paddingRight:8}}>{assets[i]}</div>
                  {row.map((v,j)=>{
                    const isHov = hovCell?.i===i&&hovCell?.j===j;
                    const isSel = selectedPair&&((selectedPair[0]===i&&selectedPair[1]===j)||(selectedPair[0]===j&&selectedPair[1]===i));
                    return (
                      <div key={j}
                        onClick={()=>i!==j&&setSelectedPair(isSel?null:[i,j])}
                        onMouseEnter={()=>setHovCell({i,j,v})}
                        onMouseLeave={()=>setHovCell(null)}
                        style={{
                          width:cellSize-2,height:cellSize-2,margin:1,
                          background: i===j?"#334155":corrColor(v),
                          borderRadius:4,display:"flex",alignItems:"center",justifyContent:"center",
                          cursor:i===j?"default":"pointer",
                          fontSize:10,fontFamily:"DM Mono",
                          color:"rgba(255,255,255,0.9)",fontWeight:500,
                          opacity:isHov||isSel?1:0.85,
                          transform:isHov?"scale(1.12)":"scale(1)",
                          transition:"all 0.15s",
                          outline:isSel?`2px solid ${T.accent}`:"none",
                          zIndex:isHov?2:1,position:"relative",
                        }}>
                        {i===j?"─":v.toFixed(2)}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* Color scale */}
          <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:4,minWidth:32}}>
            <span style={{fontSize:9,fontFamily:"DM Mono",color:T.muted}}>+1.0</span>
            {["#1d4ed8","#3b82f6","#60a5fa","#93c5fd","#475569","#f97316","#ea580c","#dc2626"].map((c,i)=>(
              <div key={i} style={{width:20,height:24,background:c,borderRadius:2}}/>
            ))}
            <span style={{fontSize:9,fontFamily:"DM Mono",color:T.muted}}>-1.0</span>
          </div>
        </div>

        {hovCell && hovCell.i !== hovCell.j && (
          <div style={{marginTop:12,padding:"10px 14px",background:T.s3,borderRadius:8,
            border:`1px solid ${T.borderHi}`,display:"inline-flex",gap:16,alignItems:"center"}}>
            <span style={{fontSize:12,fontFamily:"DM Mono",color:T.text}}>
              {assets[hovCell.i]} ↔ {assets[hovCell.j]}
            </span>
            <Badge label={hovCell.v.toFixed(3)} color={hovCell.v>0?T.accent:T.danger}/>
            <span style={{fontSize:11,color:T.dim}}>
              {Math.abs(hovCell.v)>0.7?"Strong":Math.abs(hovCell.v)>0.4?"Moderate":"Weak"}{" "}
              {hovCell.v>0?"positive":"negative"} correlation
            </span>
          </div>
        )}
      </Panel>
    </div>
  );
};

// ─── 5. TRADE REPLAY ──────────────────────────────────────────────────────────
const TradeReplayDashboard = () => {
  const [selectedTrade, setSelectedTrade] = useState(null);

  const tradeMap = {};
  DATA.trades.forEach(t=>{ tradeMap[t.ts]=t; });

  const chartData = DATA.tradeData.map(d=>({
    ...d, label:d.ts.slice(11,16),
    trade: tradeMap[d.ts]||null,
  }));

  const TradeDot = (props) => {
    const {cx,cy,payload} = props;
    if(!payload.trade) return null;
    const t = payload.trade;
    const color = t.is_mistake?T.warning:t.act==="BUY"?T.accent3:T.danger;
    return (
      <g onClick={()=>setSelectedTrade(selectedTrade?.ts===t.ts?null:t)} style={{cursor:"pointer"}}>
        <circle cx={cx} cy={cy} r={t.is_mistake?9:7} fill={color} stroke={T.bg} strokeWidth={2}/>
        <text x={cx} y={cy+1} textAnchor="middle" dominantBaseline="middle"
          fill={T.bg} fontSize={8} fontFamily="DM Mono" fontWeight="bold">
          {t.act==="BUY"?"B":"S"}
        </text>
        {t.is_mistake && (
          <circle cx={cx} cy={cy} r={14} fill="none" stroke={T.warning} strokeWidth={1.5} strokeDasharray="3 2" opacity={0.7}/>
        )}
      </g>
    );
  };

  const TradeTooltip = ({active,payload}) => {
    if(!active||!payload?.length) return null;
    const d=payload[0]?.payload;
    return (
      <TooltipBox>
        <div className="mono" style={{fontSize:10,color:T.muted,marginBottom:6}}>{d.ts}</div>
        <div style={{fontSize:13,fontWeight:600}}>Price: <span style={{color:T.accent}}>${d.close}</span></div>
        {d.trade && (
          <div style={{marginTop:8,paddingTop:8,borderTop:`1px solid ${T.border}`}}>
            <div style={{display:"flex",gap:6,alignItems:"center",marginBottom:4}}>
              <Badge label={d.trade.act} color={d.trade.act==="BUY"?T.accent3:T.danger}/>
              {d.trade.is_mistake && <Badge label="MISTAKE" color={T.warning}/>}
            </div>
            <div style={{fontSize:11,color:T.dim}}>AI: {d.trade.ai}</div>
            {d.trade.pnl!=null && <div style={{fontSize:12,fontWeight:600,color:d.trade.pnl>0?T.accent3:T.danger,marginTop:4}}>P&L: ${d.trade.pnl}</div>}
            {d.trade.is_mistake && <div style={{fontSize:11,color:T.warning,marginTop:4}}>⚠ {d.trade.reason}</div>}
          </div>
        )}
      </TooltipBox>
    );
  };

  const PnLTooltip = ({active,payload}) => {
    if(!active||!payload?.length) return null;
    const d=payload[0]?.payload;
    return (
      <TooltipBox>
        <div className="mono" style={{fontSize:10,color:T.muted,marginBottom:4}}>{d.ts}</div>
        <div style={{fontSize:12,fontWeight:600,color:T.accent}}>Cum. P&L: ${d.cumPnl}</div>
        {d.tradePnl!=null && <div style={{fontSize:11,color:d.tradePnl>0?T.accent3:T.danger}}>Trade: ${d.tradePnl}</div>}
      </TooltipBox>
    );
  };

  const step = 2;
  const sliceD = chartData.filter((_,i)=>i%step===0);
  const slicePnl = DATA.pnlTimeline.filter((_,i)=>i%step===0);

  return (
    <div style={{display:"flex",flexDirection:"column",gap:16}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
        <Metric label="Total P&L" value="+$1,240" color={T.accent3} glow/>
        <Metric label="Win Rate" value="67%" color={T.accent}/>
        <Metric label="Total Trades" value="5" color={T.text}/>
        <Metric label="Mistakes" value="1" color={T.warning} sub="flagged by AI"/>
      </div>

      <Panel title="Trade Replay" subtitle="NVDA · B=Buy · S=Sell · ⚠=AI Mistake Flag">
        <div style={{display:"flex",gap:12,marginBottom:8,flexWrap:"wrap"}}>
          <div style={{display:"flex",alignItems:"center",gap:5}}>
            <div style={{width:10,height:10,borderRadius:"50%",background:T.accent3}}/>
            <span style={{fontSize:10,fontFamily:"DM Mono",color:T.dim}}>Buy Signal</span>
          </div>
          <div style={{display:"flex",alignItems:"center",gap:5}}>
            <div style={{width:10,height:10,borderRadius:"50%",background:T.danger}}/>
            <span style={{fontSize:10,fontFamily:"DM Mono",color:T.dim}}>Sell Signal</span>
          </div>
          <div style={{display:"flex",alignItems:"center",gap:5}}>
            <div style={{width:10,height:10,borderRadius:"50%",background:T.warning}}/>
            <span style={{fontSize:10,fontFamily:"DM Mono",color:T.dim}}>Mistake Zone</span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={sliceD}>
            <CartesianGrid stroke={T.border} strokeDasharray="2 4"/>
            <XAxis dataKey="label" tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} interval={10} tickLine={false}/>
            <YAxis domain={["auto","auto"]} tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} tickLine={false}
              tickFormatter={v=>`$${v.toFixed(0)}`} width={55}/>
            <Tooltip content={<TradeTooltip/>}/>
            <Line type="monotone" dataKey="close" stroke={T.accent} strokeWidth={2}
              dot={<TradeDot/>} activeDot={{r:4,fill:T.accent}}/>
          </ComposedChart>
        </ResponsiveContainer>
      </Panel>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
        <Panel title="Cumulative P&L" subtitle="session timeline">
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={slicePnl}>
              <CartesianGrid stroke={T.border} strokeDasharray="2 4"/>
              <XAxis dataKey="ts" tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} interval={10}
                tickFormatter={v=>v.slice(11,16)} tickLine={false}/>
              <YAxis tick={{fill:T.muted,fontSize:9,fontFamily:"DM Mono"}} tickLine={false}
                tickFormatter={v=>`$${v}`} width={50}/>
              <ReferenceLine y={0} stroke={T.border}/>
              <Tooltip content={<PnLTooltip/>}/>
              <Area type="monotone" dataKey="cumPnl" stroke={T.accent3} fill={T.accent3} fillOpacity={0.2} strokeWidth={2}/>
            </AreaChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Trade Log" subtitle="annotated by AI">
          <div style={{display:"flex",flexDirection:"column",gap:6,maxHeight:180,overflowY:"auto"}}>
            {DATA.trades.map((t,i)=>(
              <div key={i} onClick={()=>setSelectedTrade(selectedTrade?.ts===t.ts?null:t)}
                style={{background:selectedTrade?.ts===t.ts?T.s4:T.s3,
                  border:`1px solid ${selectedTrade?.ts===t.ts?T.borderHi:T.border}`,
                  borderRadius:6,padding:"8px 10px",cursor:"pointer",
                  borderLeft:`3px solid ${t.is_mistake?T.warning:t.act==="BUY"?T.accent3:T.danger}`}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:3}}>
                  <div style={{display:"flex",gap:6,alignItems:"center"}}>
                    <Badge label={t.act} color={t.act==="BUY"?T.accent3:T.danger}/>
                    {t.is_mistake && <Badge label="⚠ MISTAKE" color={T.warning}/>}
                    <span style={{fontSize:11,fontFamily:"DM Mono",color:T.muted}}>{t.ts.slice(11,16)}</span>
                  </div>
                  <span style={{fontSize:11,fontFamily:"DM Mono",color:T.accent}}>${t.price}</span>
                </div>
                <div style={{fontSize:10,color:T.dim}}>{t.ai}</div>
                {t.pnl!=null && (
                  <div style={{fontSize:11,fontWeight:600,color:t.pnl>0?T.accent3:T.danger,marginTop:2}}>
                    P&L: ${t.pnl}
                  </div>
                )}
                {t.is_mistake && <div style={{fontSize:10,color:T.warning,marginTop:2}}>{t.reason}</div>}
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
};

// ─── APP SHELL ────────────────────────────────────────────────────────────────
const TABS = [
  {id:"market",   icon:"📰", label:"Market–News",        comp:MarketNewsDashboard},
  {id:"portfolio",icon:"📊", label:"Portfolio Risk",     comp:PortfolioRiskDashboard},
  {id:"regime",   icon:"🌊", label:"Regime Timeline",    comp:RegimeDashboard},
  {id:"heatmap",  icon:"🔥", label:"Correlation",        comp:CorrelationHeatmap},
  {id:"replay",   icon:"▶️", label:"Trade Replay",        comp:TradeReplayDashboard},
];

export default function App() {
  const [activeTab, setActiveTab] = useState("market");
  const [ticker, setTicker] = useState("AAPL");
  const [loading, setLoading] = useState(false);

  const ActiveComp = TABS.find(t=>t.id===activeTab)?.comp;

  const switchTab = (id) => {
    setLoading(true);
    setTimeout(()=>{ setActiveTab(id); setLoading(false); }, 200);
  };

  return (
    <>
      <style>{css}</style>
      <div style={{minHeight:"100vh",display:"flex",flexDirection:"column",
        background:`radial-gradient(ellipse at 20% 0%, rgba(99,179,237,0.04) 0%, transparent 60%), ${T.bg}`}}>

        {/* ── TOP BAR ── */}
        <header style={{background:T.surface,borderBottom:`1px solid ${T.border}`,
          padding:"14px 24px",display:"flex",alignItems:"center",justifyContent:"space-between",
          backdropFilter:"blur(12px)",position:"sticky",top:0,zIndex:100}}>
          <div style={{display:"flex",alignItems:"center",gap:12}}>
            <div style={{width:36,height:36,borderRadius:10,
              background:"linear-gradient(135deg, #63b3ed, #a78bfa)",
              display:"flex",alignItems:"center",justifyContent:"center",
              boxShadow:"0 0 20px rgba(99,179,237,0.3)",fontSize:18}}>⚡</div>
            <div>
              <div style={{fontFamily:"Outfit",fontWeight:800,fontSize:18,letterSpacing:"-0.5px"}}>
                Fin<span style={{color:T.accent}}>AI</span>
                <span style={{fontWeight:400,fontSize:12,color:T.muted,marginLeft:8}}>Visualization Platform</span>
              </div>
              <div style={{fontSize:9,fontFamily:"DM Mono",color:T.muted,letterSpacing:"2px",textTransform:"uppercase"}}>
                Bonus 3 · Enhanced Analytics
              </div>
            </div>
          </div>
          <div style={{display:"flex",alignItems:"center",gap:12}}>
            <div style={{display:"flex",gap:6}}>
              {["AAPL","NVDA","TSLA","SPY"].map(t=>(
                <button key={t} onClick={()=>setTicker(t)} className="chip-hover"
                  style={{background:ticker===t?T.accent+"22":T.s2,
                    border:`1px solid ${ticker===t?T.accent:T.border}`,
                    color:ticker===t?T.accent:T.dim,borderRadius:6,
                    padding:"4px 12px",fontSize:11,fontFamily:"DM Mono",cursor:"pointer"}}>
                  {t}
                </button>
              ))}
            </div>
            <div style={{display:"flex",alignItems:"center",gap:6,fontSize:11,
              fontFamily:"DM Mono",color:T.muted,padding:"4px 10px",
              background:T.s3,borderRadius:6,border:`1px solid ${T.border}`}}>
              <div style={{width:6,height:6,borderRadius:"50%",background:T.accent3,
                animation:"pulse2 2s infinite",boxShadow:`0 0 8px ${T.accent3}`}}/>
              Ollama · Mistral
            </div>
          </div>
        </header>

        {/* ── TAB BAR ── */}
        <nav style={{background:T.surface,borderBottom:`1px solid ${T.border}`,
          padding:"0 24px",display:"flex",gap:2}}>
          {TABS.map(tab=>(
            <button key={tab.id} onClick={()=>switchTab(tab.id)} className="tab-btn"
              style={{background:"transparent",border:"none",
                borderBottom:`2px solid ${activeTab===tab.id?T.accent:"transparent"}`,
                color:activeTab===tab.id?T.accent:T.dim,padding:"12px 18px",
                cursor:"pointer",fontSize:13,fontFamily:"Outfit",fontWeight:500,
                display:"flex",alignItems:"center",gap:6,whiteSpace:"nowrap"}}>
              <span style={{fontSize:14}}>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>

        {/* ── CONTENT ── */}
        <main style={{flex:1,padding:"20px 24px",maxWidth:1400,width:"100%",margin:"0 auto"}}>
          {loading
            ? <Loading/>
            : <div className="fade-up" key={activeTab}>
                <div style={{marginBottom:14,display:"flex",alignItems:"center",gap:8}}>
                  <span style={{fontSize:20}}>{TABS.find(t=>t.id===activeTab)?.icon}</span>
                  <span style={{fontFamily:"Outfit",fontWeight:700,fontSize:18}}>
                    {TABS.find(t=>t.id===activeTab)?.label}
                  </span>
                  <Badge label={ticker} color={T.accent}/>
                  <span style={{fontSize:10,fontFamily:"DM Mono",color:T.muted,marginLeft:4}}>
                    Live data · 90-day window
                  </span>
                </div>
                {ActiveComp && <ActiveComp ticker={ticker}/>}
              </div>
          }
        </main>

        {/* ── FOOTER ── */}
        <footer style={{borderTop:`1px solid ${T.border}`,padding:"10px 24px",
          display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <span style={{fontSize:10,fontFamily:"DM Mono",color:T.muted}}>
            FinAI · Bonus 3 · Enhanced Interactive Visualizations
          </span>
          <span style={{fontSize:10,fontFamily:"DM Mono",color:T.muted}}>
            ⚠ Educational only · Not financial advice
          </span>
        </footer>
      </div>
    </>
  );
}