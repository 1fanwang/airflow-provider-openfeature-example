"""Native Airflow UI panel for the OpenFeature provider (Airflow 3.x plugin).

Adds an "OpenFeature" tab to the Airflow navbar. The panel reads the live flag state through the
registered OpenFeature client, so it reflects whatever backend is wired (Unleash, Flipt, flagd, ...)
without knowing which one. It shows the placement policy's canary split and the A/B assignment as the
flags change, which is the effect the cluster policy applies at DAG parse.

This is demo scaffolding baked into the hosted image's plugins dir. If it proves out, the same
fastapi_apps + external_views wiring belongs on the provider's own OpenFeaturePlugin.
"""
from __future__ import annotations

import os

from airflow.plugins_manager import AirflowPlugin
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

CANARY_DAG = "platform_pool_canary"
POOL_FLAG = "airflow.task.pool"
AB_FLAG = "author.model_ab"

app = FastAPI()


def _provider_name() -> str:
    from openfeature import api

    try:
        return api.get_provider_metadata().name
    except Exception:
        try:
            return api.get_client().get_metadata().name
        except Exception:
            return "unknown"


@app.get("/state")
def state() -> JSONResponse:
    from openfeature import api
    from openfeature.evaluation_context import EvaluationContext

    client = api.get_client()
    tasks = [f"{CANARY_DAG}:task_{i}" for i in range(10)]
    canary = [
        t.split(":")[1]
        for t in tasks
        if client.get_string_value(POOL_FLAG, "default_pool", EvaluationContext(targeting_key=t)) == "canary_pool"
    ]
    treatment = sum(
        1
        for i in range(100)
        if client.get_string_value(AB_FLAG, "control", EvaluationContext(targeting_key=f"run_{i}")) == "treatment"
    )
    return JSONResponse(
        {
            "provider": _provider_name(),
            "pool_flag": POOL_FLAG,
            "ab_flag": AB_FLAG,
            "canary_tasks": canary,
            "canary_count": len(canary),
            "total": len(tasks),
            "ab_treatment_pct": treatment,
        }
    )


PANEL = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>OpenFeature</title>
<style>
 body{margin:0;background:#0d1117;color:#e6edf3;font:14px -apple-system,Segoe UI,Roboto,sans-serif}
 .w{max-width:820px;margin:0 auto;padding:22px 18px}
 h1{font-size:20px;margin:0 0 4px}.sub{color:#8b949e;margin:0 0 20px}
 .card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin-bottom:14px}
 .card h2{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#8b949e;margin:0 0 12px}
 code{background:#0d1117;border:1px solid #30363d;border-radius:5px;padding:1px 6px}
 .big{font-size:34px;font-weight:700;line-height:1}.big small{font-size:14px;color:#8b949e;font-weight:400}
 .dots{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0 6px}
 .dot{width:30px;height:30px;border-radius:7px;background:#30363d;border:1px solid #30363d;
      display:flex;align-items:center;justify-content:center;font-size:11px;color:#8b949e}
 .dot.on{background:#2ea043;color:#fff;border-color:transparent}
 .bar{height:10px;border-radius:5px;background:#30363d;overflow:hidden;margin:12px 0 4px}
 .bar>span{display:block;height:100%;background:#58a6ff;transition:width .4s}
 .row{display:flex;justify-content:space-between;color:#8b949e;font-size:12px}
 .pill{display:inline-block;background:#1f6feb22;color:#58a6ff;border:1px solid #1f6feb55;
       border-radius:999px;padding:2px 10px;font-size:12px}
 .live{display:inline-block;width:8px;height:8px;border-radius:50%;background:#2ea043;margin-right:6px;
       animation:p 1.6s infinite}@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
</style></head><body><div class=w>
 <h1><span class=live></span>OpenFeature &times; Airflow</h1>
 <p class=sub>Live flag state read through the OpenFeature client. Backend: <span class=pill id=prov>-</span></p>
 <div class=card>
   <h2>Canary &mdash; <code>airflow.task.pool</code></h2>
   <div class=dots id=dots></div>
   <div class=row><span id=split>-</span><span>green = routed to canary_pool by the policy</span></div>
 </div>
 <div class=card>
   <h2>A/B assignment &mdash; <code>author.model_ab</code></h2>
   <div class=big id=abp>-<small>% treatment</small></div>
   <div class=bar><span id=abb style=width:0%></span></div>
   <div class=row><span>treatment</span><span>control</span></div>
 </div>
</div><script>
async function tick(){try{const r=await fetch('state',{cache:'no-store'});if(!r.ok)return;const s=await r.json();
 document.getElementById('prov').textContent=s.provider;
 const d=document.getElementById('dots');d.innerHTML='';const c=new Set(s.canary_tasks||[]);
 for(let i=0;i<(s.total||10);i++){const e=document.createElement('div');e.className='dot'+(c.has('task_'+i)?' on':'');e.textContent=i;d.appendChild(e);}
 document.getElementById('split').textContent=(s.canary_count??'-')+' / '+(s.total??'-')+' tasks on canary_pool';
 if(s.ab_treatment_pct!=null){document.getElementById('abp').innerHTML=s.ab_treatment_pct+'<small>% treatment</small>';document.getElementById('abb').style.width=s.ab_treatment_pct+'%';}
}catch(e){}}
tick();setInterval(tick,2000);
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def panel() -> HTMLResponse:
    return HTMLResponse(PANEL)


class OpenFeatureUIPlugin(AirflowPlugin):
    name = "openfeature_ui"
    # Opt-in supplement: off unless OPENFEATURE_UI_ENABLED is truthy. It never replaces a backend's
    # own admin UI (where you flip flags); it only shows the effect inside Airflow.
    _on = os.getenv("OPENFEATURE_UI_ENABLED", "false").lower() in ("1", "true", "yes")
    fastapi_apps = [{"name": "OpenFeature", "app": app, "url_prefix": "/openfeature"}] if _on else []
    external_views = (
        [
            {
                "name": "OpenFeature",
                "href": "/openfeature/",
                "destination": "nav",
                "icon": "fa-flag",
            }
        ]
        if _on
        else []
    )
