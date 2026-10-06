"""Three explicit customer variants; no browser or mandatory Node dependency."""

import base64
import hashlib
import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

from liquent.research_pilot.execution import validate_configuration
from liquent_platform.application.customer_research import customer_input_binding
from liquent_platform.transport.http import research_customer_ui as ui


EXAMPLES = Path(__file__).resolve().parents[1] / "examples/research_pilot"
ORDER_FIELDS = "reference title instrument price_unit data_origin assumptions".split()
VARIANT_FIELDS = "id strategy seed hypothesis".split()
STRATEGY_FIELDS = (
    "lookback_bars stop_distance_pct min_strength allow_short "
    "breakout_threshold_pct cooldown_bars max_signals_per_day"
).split()
RISK_FIELDS = (
    "initial_equity sizing_mode max_position_size max_total_exposure risk_per_trade "
    "max_daily_drawdown risk_per_trade_pct max_position_notional max_daily_loss max_losing_streak"
).split()
FIELDS = VARIANT_FIELDS + ["strategy_parameters." + key for key in STRATEGY_FIELDS]
FIELDS += ["risk." + key for key in RISK_FIELDS]
FIELDS += ["costs." + key for key in ("fee_rate", "spread", "slippage")]


class Markup(HTMLParser):
    """Keep containment and labels, without requiring third-party HTML parsers."""

    def __init__(self, source):
        super().__init__()
        self.root = {"tag": "root", "attrs": {}, "children": [], "text": ""}
        self.stack = [self.root]
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "children": [], "text": ""}
        self.stack[-1]["children"].append(node)
        if tag not in {"input", "br", "hr", "meta", "link", "img"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1]["text"] += data


def descendants(node):
    for child in node["children"]:
        yield child
        yield from descendants(child)


def by_id(root, identifier):
    matches = [node for node in descendants(root) if node["attrs"].get("id") == identifier]
    assert len(matches) == 1, f"Expected exactly one #{identifier}"
    return matches[0]


def all_text(node):
    return node["text"] + " ".join(all_text(child) for child in node["children"])


@pytest.fixture
def example():
    return json.loads((EXAMPLES / "order.json").read_text())


@pytest.fixture
def markup():
    return Markup(ui.CUSTOMER_CONTROLS).root


@pytest.fixture(scope="module")
def node_runtime():
    node = shutil.which("node")
    if node is None:
        # Read-only discovery of the desktop bundle; never install a runtime.
        bundle = Path("/Applications/Codex.app/Contents/Resources")
        node = next((str(path) for path in bundle.glob("**/node") if path.is_file()), None)
    if node is None:
        pytest.skip("Node unavailable on PATH and in the Codex bundle; serializer VM tests skipped")
    return node


def test_exactly_three_blank_labeled_fieldsets_and_explicit_modes(markup):
    form = by_id(markup, "variant-form")
    variants = [n for n in descendants(form) if n["tag"] == "fieldset" and "data-variant" in n["attrs"]]
    assert [n["attrs"]["data-variant"] for n in variants] == ["0", "1", "2"]
    ids = [n["attrs"]["id"] for n in descendants(markup) if "id" in n["attrs"]]
    assert len(ids) == len(set(ids))
    labels = [n for n in descendants(markup) if n["tag"] == "label"]
    for key in ORDER_FIELDS:
        by_id(form, "order-" + key)
    for index, variant in enumerate(variants):
        assert any(n["tag"] == "legend" and all_text(n).strip() for n in descendants(variant))
        for field in FIELDS:
            identifier = f"variant-{index}-{field.replace('.', '-')}"
            control = by_id(variant, identifier)
            assert control["attrs"].get("data-field") == field
            assert any(
                all_text(label).strip() and (
                    label["attrs"].get("for") == identifier or control in list(descendants(label))
                ) for label in labels
            ), f"Missing accessible label for {identifier}"
    for control in descendants(form):
        if control["tag"] in {"input", "textarea"}:
            assert control["attrs"].get("value", "") == ""
            assert "checked" not in control["attrs"]
            if control["tag"] == "textarea":
                assert not all_text(control).strip()
        elif control["tag"] == "select":
            options = [n for n in descendants(control) if n["tag"] == "option"]
            selected = [n for n in options if "selected" in n["attrs"]] or options[:1]
            assert len(selected) == 1 and selected[0]["attrs"].get("value", all_text(selected[0])) == ""
    mode = by_id(markup, "configuration-mode")
    options = [n for n in descendants(mode) if n["tag"] == "option"]
    assert {n["attrs"].get("value") for n in options} == {"form", "json"}
    selected = [n for n in options if "selected" in n["attrs"]] or options[:1]
    assert selected[0]["attrs"]["value"] == "form"
    details = [n for n in descendants(markup) if n["tag"] == "details"]
    assert any({"config-file", "configuration"} <= {
        n["attrs"].get("id") for n in descendants(detail)
    } for detail in details)
    # Negated safety copy ("keine Empfehlung") is allowed; promoted values are not.
    for control in descendants(form):
        assert "recommended" not in control["attrs"].get("class", "").lower()
        assert "empfohlen" not in control["attrs"].get("placeholder", "").lower()
    text = all_text(form).lower()
    assert "0.01" in text and "1%" in text.replace(" ", "")
    assert "spread" in text and ("absolut" in text or "absolute" in text)
    assert "seite" in text or "side" in text
    assert "ratio" in text or "verhältnis" in text
    visible = all_text(markup).lower()
    assert "one-bar" in visible or "ein-balken" in visible or "einen balken" in visible
    assert "stop" in visible and ("keine" in visible or "no real" in visible)


HARNESS = r'''
const vm = require("node:vm"), fs = require("node:fs");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
function build(raw, parent=null) {
  const n = {tagName:raw.tag.toUpperCase(), attrs:raw.attrs, parentElement:parent,
    children:[], listeners:{}, checked:false, disabled:false, hidden:false,
    files:[], textContent:raw.text, value:raw.attrs.value || "",
    addEventListener(type, fn){(this.listeners[type] ||= []).push(fn);},
    async fire(type){const event={target:this,preventDefault(){}};
      for(let p=this;p;p=p.parentElement) for(const fn of p.listeners[type] || []) await fn(event);},
    getAttribute(key){return this.attrs[key] ?? null;},
    setAttribute(key,value){this.attrs[key]=String(value);},
    removeAttribute(key){delete this.attrs[key];},
    querySelectorAll(selector){return walk(this).filter(x=>matches(x,selector));},
    querySelector(selector){return this.querySelectorAll(selector)[0] || null;},
    append(...nodes){for(const child of nodes){child.parentElement=this;this.children.push(child);}},
    replaceChildren(...nodes){this.children=[];this.textContent="";this.append(...nodes);}};
  n.id=n.attrs.id || "";
  n.dataset=Object.fromEntries(Object.entries(n.attrs).filter(([k])=>k.startsWith("data-"))
    .map(([k,v])=>[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase()),v]));
  n.children=raw.children.map(c=>build(c,n));
  if(n.tagName==="SELECT") {n.options=walk(n).filter(x=>x.tagName==="OPTION");
    const chosen=n.options.find(x=>"selected" in x.attrs) || n.options[0];
    n.value=chosen ? (chosen.attrs.value ?? chosen.textContent) : "";}
  if(n.tagName==="TEXTAREA") n.value=raw.text;
  return n;
}
function walk(n){return n.children.flatMap(c=>[c,...walk(c)]);}
function matches(n,selector){
  if(selector.includes(",")) return selector.split(",").some(s=>matches(n,s.trim()));
  const parts=selector.trim().split(/\s+(?![^\[]*\])/);
  if(parts.length>1){
    if(!matches(n,parts.pop())) return false;
    const ancestorSelector=parts.join(" ");
    for(let p=n.parentElement;p;p=p.parentElement) if(matches(p,ancestorSelector)) return true;
    return false;
  }
  if(selector.startsWith("#")) return n.id===selector.slice(1);
  const m=selector.match(/^([a-zA-Z]+)?(?:\[([\w-]+)(?:=["']?([^\]"']+)["']?)?\])?$/);
  if(!m) throw new Error("Unsupported fake DOM selector: "+selector);
  return (!m[1] || n.tagName===m[1].toUpperCase()) && (!m[2] ||
    (m[2] in n.attrs && (m[3]===undefined || n.attrs[m[2]]===m[3])));
}
const document=build(input.markup), root=document.querySelector("#variant-form");
document.getElementById=id=>document.querySelector("#"+id);
document.createElement=tag=>build({tag,attrs:{},children:[],text:""});
const get=id=>{const n=document.getElementById(id);if(!n) throw new Error("Missing #"+id);return n;};
const put=(id,value)=>{get(id).value=String(value);};
for(const [key,value] of Object.entries(input.configuration.order)) put("order-"+key,value);
for(const [index,variant] of input.configuration.variants.entries()) {
  for(const [key,value] of Object.entries(variant)) {
    const fields=value && typeof value==="object" ? Object.entries(value).map(([k,v])=>[key+"."+k,v]) : [[key,value]];
    for(const [field,v] of fields) {
      const id="variant-"+index+"-"+field.replaceAll(".","-");
      if(v!==null) put(id,v);
      else {
        // Either the documented value field or a companion select can carry the
        // explicit unlimited choice; infer only from delivered option markup.
        const fieldset=root.querySelector('[data-variant="'+index+'"]');
        const choice=walk(fieldset).find(n=>n.tagName==="SELECT" &&
          n.options.some(o=>o.attrs.value==="unlimited"));
        if(choice) choice.value="unlimited"; else put(id,"unlimited");
      }
    }
  }
  const fieldset=root.querySelector('[data-variant="'+index+'"]');
  for(const select of walk(fieldset).filter(n=>n.tagName==="SELECT" && n.options.some(o=>o.attrs.value==="unlimited"))) {
    if(variant.strategy_parameters.max_signals_per_day != null && !select.value) {
      const finite=select.options.find(o=>o.attrs.value && o.attrs.value!=="unlimited");
      select.value=finite.attrs.value;
    }
  }
}
for(const [id,value] of Object.entries(input.overrides || {})) put(id,value);
put("timeframe",input.configuration.dataset.timeframe);
const requests=[];let releasePreview,releaseDataCheck;
const context=vm.createContext({document,console,Uint8Array,TextEncoder,TextDecoder,
  btoa:s=>Buffer.from(s,"binary").toString("base64"),
  fetch:async(path)=>{requests.push(path);
    if(input.action==="stale-preview" && path.endsWith("request-preview")) await new Promise(resolve=>{releasePreview=resolve;});
    if(input.action==="data-check" && path.endsWith("data-check")) {
      await new Promise(resolve=>{releaseDataCheck=resolve;});
      if(input.checkOutcome==="error") return {ok:false,status:503};
      return {ok:true,json:async()=>({headline:"Synthetic completed data check",meaning:"No simulation",
        data_quality:{period_start:null,period_end:null,rows:12,timeframe:"5m",gaps:[],issues:[],warnings:[],history:null},
        next_steps:[]})};
    }
    return {ok:true,json:async()=>path.endsWith("customer-context")?
    {csrf_token:"csrf",can_write:true}:{binding_fingerprint:"sha256:test",variant_ids:["A","B","C"]}};}});
context.window=context;context.globalThis=context;
(async()=>{
  // Run the actual delivered script; only its DOM/HTTP environment is synthetic.
  vm.runInContext(input.script,context,{timeout:2000});
  const read=vm.runInContext("readFormConfiguration",context);
  if(input.action==="serialize") {
    try {process.stdout.write(JSON.stringify({value:read(root,input.timeframe ?? input.configuration.dataset.timeframe),
      jsonModeConfiguration:input.configuration}));}
    catch(error){process.stdout.write(JSON.stringify({error:String(error.message)}));}
    return;
  }
  await new Promise(resolve=>setImmediate(resolve));
  get("csv").files=[{size:3,arrayBuffer:async()=>new Uint8Array([97,98,99]).buffer}];
  if(input.action==="data-check") {
    const rendered=n=>[n.textContent,...n.children.map(rendered)].join(" ");
    const pending=get("data-check").fire("submit");
    await new Promise(resolve=>setImmediate(resolve));
    if(!releaseDataCheck) throw new Error("Data-check request was not sent");
    const loading=rendered(get("quality"));
    if(input.editTarget==="variant") {
      put("variant-0-strategy_parameters-min_strength","0.1");
      await get("variant-0-strategy_parameters-min_strength").fire(input.editEvent);
    } else if(input.editTarget==="csv") {
      get("csv").files=[{size:3,arrayBuffer:async()=>new Uint8Array([100,101,102]).buffer}];
      await get("csv").fire("change");
    } else if(input.editTarget==="timeframe") {
      put("timeframe","15m");await get("timeframe").fire("change");
    } else throw new Error("Unknown data-check edit target");
    const afterEdit=rendered(get("quality"));
    releaseDataCheck();await pending;
    process.stdout.write(JSON.stringify({loading,afterEdit,quality:rendered(get("quality")),
      disabled:get("submit-research").disabled,requests}));return;
  }
  if(input.action==="stale-preview") {
    const pending=get("preview").fire("click");
    await new Promise(resolve=>setImmediate(resolve));
    if(!releasePreview) throw new Error("Preview request was not sent");
    put("variant-0-seed","1");await get("variant-0-seed").fire("input");
    releasePreview();await pending;
    get("rights").checked=true;get("approval").checked=true;
    await get("rights").fire("change");await get("approval").fire("change");
    process.stdout.write(JSON.stringify({disabled:get("submit-research").disabled,
      binding:get("binding").textContent,requests}));return;
  }
  async function bind(){await get("preview").fire("click");await new Promise(resolve=>setImmediate(resolve));
    get("rights").checked=true;get("approval").checked=true;
    await get("rights").fire("change");await get("approval").fire("change");
    if(get("submit-research").disabled) throw new Error("Valid preview did not enable explicit approval");}
  const results=[];
  for(const event of ["input","change","mode","import"]) {
    put("configuration-mode","form");await bind();get("quality").textContent="Existing dataset finding";
    if(event==="mode") {put("configuration-mode","json");await get("configuration-mode").fire("change");}
    else if(event==="import") {get("config-file").files=[{size:100,text:async()=>JSON.stringify(input.configuration)}];await get("config-file").fire("change");}
    else {put("variant-0-strategy_parameters-min_strength","0.1");await get("variant-0-strategy_parameters-min_strength").fire(event);}
    const state={event,rights:get("rights").checked,approval:get("approval").checked,
      disabled:get("submit-research").disabled,binding:get("binding").textContent,
      quality:get("quality").textContent};
    get("rights").checked=true;get("approval").checked=true;
    await get("rights").fire("change");await get("approval").fire("change");
    state.disabledAfterReapproval=get("submit-research").disabled;
    results.push(state);
  }
  process.stdout.write(JSON.stringify({results,requests}));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
'''


def run_form(node_runtime, markup, configuration, *, overrides=None, action="serialize", timeframe=None,
             check_outcome="success", edit_target="variant", edit_event="input"):
    payload = dict(markup=markup, script=ui.CUSTOMER_SCRIPT, configuration=configuration,
                   overrides=overrides or {}, action=action, checkOutcome=check_outcome,
                   editTarget=edit_target, editEvent=edit_event)
    if timeframe is not None:
        payload["timeframe"] = timeframe
    result = subprocess.run([node_runtime, "-e", HARNESS], input=json.dumps(payload),
                            text=True, capture_output=True, timeout=10, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_fixture_roundtrip_preserves_v0_v1_absolute_percent_and_ratios(node_runtime, markup, example):
    generated = run_form(node_runtime, markup, example)["value"]
    assert generated == example
    assert validate_configuration(generated) == example
    assert set(generated["variants"][0]["strategy_parameters"]) == {
        "lookback_bars", "stop_distance_pct", "min_strength", "allow_short"
    }
    assert generated["variants"][1]["risk"]["risk_per_trade_pct"] == 0.01
    assert generated["variants"][0]["costs"] == {"fee_rate": 0.001, "spread": 0.02, "slippage": 0.0005}


def test_unlimited_requires_explicit_choice(node_runtime, markup, example):
    example["variants"][1]["strategy_parameters"]["max_signals_per_day"] = None
    generated = run_form(node_runtime, markup, example)["value"]
    assert generated == example
    assert validate_configuration(generated) == example
    variant = by_id(markup, "variant-form")
    unlimited_controls = [n for n in descendants(variant) if n["tag"] == "select"
                          and any(c["attrs"].get("value") == "unlimited" for c in descendants(n))
                          and n["attrs"].get("id", "").startswith("variant-1-")]
    overrides = {"variant-1-strategy_parameters-max_signals_per_day": ""}
    overrides.update({n["attrs"]["id"]: "" for n in unlimited_controls})
    assert "error" in run_form(node_runtime, markup, example, overrides=overrides)


NUMERIC_FIELDS = ["seed"] + ["strategy_parameters." + key for key in STRATEGY_FIELDS if key != "allow_short"]
NUMERIC_FIELDS += ["risk." + key for key in RISK_FIELDS if key != "sizing_mode"]
NUMERIC_FIELDS += ["costs.fee_rate", "costs.spread", "costs.slippage"]


@pytest.mark.parametrize("field", NUMERIC_FIELDS)
@pytest.mark.parametrize("bad", ["", "   ", "not-a-number", "NaN", "Infinity", "-Infinity"])
def test_each_numeric_field_rejects_missing_or_nonfinite(node_runtime, markup, example, field, bad):
    # Use v1 so every v1-only field is effective; ignored risk fields still required.
    assert "error" in run_form(node_runtime, markup, example, overrides={
        "variant-1-" + field.replace(".", "-"): bad,
    })


@pytest.mark.parametrize("field", ["seed", "strategy_parameters.lookback_bars",
    "strategy_parameters.cooldown_bars", "strategy_parameters.max_signals_per_day", "risk.max_losing_streak"])
@pytest.mark.parametrize("bad", ["1.5", "9007199254740992", "-9007199254740992"])
def test_integer_fields_reject_fractional_or_unsafe_values(node_runtime, markup, example, field, bad):
    assert "error" in run_form(node_runtime, markup, example, overrides={
        "variant-1-" + field.replace(".", "-"): bad,
    })


@pytest.mark.parametrize("identifier", ["order-data_origin", "variant-0-strategy",
    "variant-0-strategy_parameters-allow_short", "variant-0-risk-sizing_mode",
    "variant-1-strategy_parameters-max_signals_per_day_mode"])
@pytest.mark.parametrize("bad", ["", "unknown"])
def test_required_choices_never_fall_back(node_runtime, markup, example, identifier, bad):
    assert "error" in run_form(node_runtime, markup, example, overrides={identifier: bad})


def test_duplicate_variant_ids_rejected(node_runtime, markup, example):
    assert "error" in run_form(node_runtime, markup, example, overrides={
        "variant-2-id": example["variants"][0]["id"],
    })


@pytest.mark.parametrize("identifier", ["order-" + key for key in ORDER_FIELDS] + [
    "variant-0-id", "variant-0-hypothesis",
])
def test_required_text_cannot_be_blank(node_runtime, markup, example, identifier):
    assert "error" in run_form(node_runtime, markup, example, overrides={identifier: "  "})


@pytest.mark.parametrize("timeframe", ["", "unknown"])
def test_timeframe_is_explicit(node_runtime, markup, example, timeframe):
    assert "error" in run_form(node_runtime, markup, example, timeframe=timeframe)


def test_form_changes_mode_and_import_invalidate_binding_and_consent(node_runtime, markup, example):
    result = run_form(node_runtime, markup, example, action="invalidate")
    for state in result["results"]:
        assert state["rights"] is False and state["approval"] is False, state
        assert state["disabled"] is True and "sha256:test" not in state["binding"], state
        assert state["disabledAfterReapproval"] is True, state
        if state["event"] in {"input", "change"}:
            assert state["quality"] == "Existing dataset finding", state
    assert "/v1/research/request-preview" in result["requests"]
    assert "/v1/research/customer-jobs" not in result["requests"]


def test_stale_preview_cannot_restore_binding_after_form_edit(node_runtime, markup, example):
    result = run_form(node_runtime, markup, example, action="stale-preview")
    assert result["disabled"] is True
    assert "sha256:test" not in result["binding"]
    assert "/v1/research/customer-jobs" not in result["requests"]


@pytest.mark.parametrize("outcome", ["success", "error"])
@pytest.mark.parametrize("event", ["input", "change"])
def test_pending_data_check_finishes_after_variant_edit(node_runtime, markup, example, outcome, event):
    result = run_form(node_runtime, markup, example, action="data-check",
                      check_outcome=outcome, edit_event=event)
    assert "Daten werden geprüft" in result["loading"]
    assert result["afterEdit"] == result["loading"]
    assert "Daten werden geprüft" not in result["quality"]
    expected = "Synthetic completed data check" if outcome == "success" else "Research ist derzeit nicht verfügbar"
    assert expected in result["quality"]
    assert result["disabled"] is True
    assert result["requests"].count("/v1/research/data-check") == 1
    assert "/v1/research/customer-jobs" not in result["requests"]


@pytest.mark.parametrize("outcome", ["success", "error"])
@pytest.mark.parametrize("target", ["csv", "timeframe"])
def test_pending_data_check_discards_stale_completion_or_error_after_dataset_change(
    node_runtime, markup, example, outcome, target,
):
    result = run_form(node_runtime, markup, example, action="data-check",
                      check_outcome=outcome, edit_target=target)
    assert "Daten werden geprüft" in result["loading"]
    assert result["afterEdit"] != result["loading"]
    assert "Bitte Daten erneut prüfen" in result["afterEdit"]
    assert result["quality"] == result["afterEdit"]
    assert "Synthetic completed data check" not in result["quality"]
    assert "Research ist derzeit nicht verfügbar" not in result["quality"]
    assert result["disabled"] is True
    assert result["requests"].count("/v1/research/data-check") == 1
    assert "/v1/research/customer-jobs" not in result["requests"]


def test_generated_inputs_have_identical_existing_preview_fingerprint(node_runtime, markup, example):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from liquent_platform.transport.http.customer_research import register_customer_research
    from test_customer_research_http import Sessions, Memberships, Contexts, Store, Control

    serialized = run_form(node_runtime, markup, example)
    generated = serialized["value"]
    json_mode = serialized["jsonModeConfiguration"]
    assert validate_configuration(generated) == validate_configuration(example)
    raw = (EXAMPLES / "synthetic.csv").read_bytes()
    # The retained JSON editor also sends JSON.stringify(JSON.parse(text)).
    # JS emits 0 for fixture 0.0; compare actual wire configurations, without
    # changing the backend's existing int/float-sensitive canonical hashing.
    assert json_mode == example
    expected = customer_input_binding(raw, json_mode)
    assert customer_input_binding(raw, generated) == expected
    store, control, app = Store(), Control(), FastAPI()
    register_customer_research(app, sessions=Sessions(), memberships=Memberships(True),
                              contexts=Contexts(), store=store, control=control)
    with TestClient(app) as client:
        client.cookies.set("liquent_session", "session")
        client.headers["X-CSRF-Token"] = "csrf"
        for config in (json_mode, generated):
            response = client.post("/v1/research/request-preview", json={
                "csv_base64": base64.b64encode(raw).decode(), "configuration": config,
            })
            assert response.status_code == 200, response.text
            assert response.json()["binding_fingerprint"] == expected
            assert response.json()["variant_ids"] == [v["id"] for v in example["variants"]]
            assert response.json()["order_created"] is False
            assert response.json()["simulation_started"] is False
    assert store.requests == store.feedback == control.calls == []


def test_delivered_script_csp_and_sri_match_updated_bytes(markup):
    digest = base64.b64encode(hashlib.sha256(ui.CUSTOMER_SCRIPT.encode()).digest()).decode()
    scripts = [n for n in descendants(markup) if n["tag"] == "script"]
    assert len(scripts) == 1
    assert scripts[0]["attrs"]["src"] == "/research/customer.js"
    assert scripts[0]["attrs"]["integrity"] == "sha256-" + digest
    assert "script-src 'sha256-" + digest + "'" in ui.CUSTOMER_CSP
    assert "'unsafe-inline'" not in ui.CUSTOMER_CSP
    assert "'unsafe-eval'" not in ui.CUSTOMER_CSP
    assert "connect-src 'self'" in ui.CUSTOMER_CSP
    assert not any(key.startswith("on") for n in descendants(markup) for key in n["attrs"])
