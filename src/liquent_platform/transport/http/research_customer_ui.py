"""Customer controls inside the existing authenticated Research page."""
import base64
import hashlib

from .ui_brand import CONTENT_SECURITY_POLICY

def _form_field(identifier, label, *, field=None, choices=None, integer=False, text=False):
    """Render blank controls; no research values or choices are supplied for the user."""
    attributes = f'id="{identifier}"'
    if field:
        attributes += f' data-field="{field}"'
    if choices:
        control = f'<select {attributes} required><option value="">Bitte wählen</option>'
        control += ''.join(f'<option value="{value}">{caption}</option>' for value, caption in choices)
        control += '</select>'
    elif text:
        control = f'<input {attributes} type="text" required>'
    else:
        control = f'<input {attributes} type="number" step="{"1" if integer else "any"}" required>'
    return f'<label for="{identifier}">{label}</label>{control}'


def _variant_form():
    parts = ['<div id="variant-form" aria-describedby="form-help">',
             '<p id="form-help">Alle Werte und Auswahlfelder sind ausdrücklich auszufüllen. Keine Vorgaben, Rangfolge oder Empfehlungen. Verhältnisse werden unverändert übernommen: 0.01 bedeutet 1 %, keine Prozentumrechnung. Alle Risikofelder bleiben erforderlich, auch wenn der gewählte Modus sie ignoriert.</p>',
             '<fieldset><legend>Gemeinsame Auftragsangaben</legend>']
    for name, label in [('reference', 'Referenz'), ('title', 'Titel'), ('instrument', 'Instrument'),
                        ('price_unit', 'Preis- und Simulationseinheit'), ('assumptions', 'Annahmen und Grenzen')]:
        parts.append(_form_field('order-' + name, label, text=True))
    parts.append(_form_field('order-data_origin', 'Datenherkunft', choices=[
        ('synthetic', 'Synthetische Daten'), ('customer_provided', 'Eigene bereitgestellte Daten')]))
    parts.append('</fieldset>')
    for index in range(3):
        parts.append(f'<fieldset data-variant="{index}"><legend>Variante {index + 1} – eigene Eingaben</legend>')
        def field(name, label, **kwargs):
            return _form_field(f'variant-{index}-' + name.replace('.', '-'), label, field=name, **kwargs)
        parts.extend([field('id', 'Eindeutige Varianten-ID (1–64 Buchstaben, Zahlen, _ oder -)', text=True),
                      field('strategy', 'Strategie', choices=[('mid-breakout-v0', 'mid-breakout-v0'), ('mid-breakout-v1', 'mid-breakout-v1')]),
                      field('seed', 'Seed (sichere ganze Zahl)', integer=True),
                      field('hypothesis', 'Vorab festgelegte Hypothese', text=True)])
        parts.append('<p>Modellgrenze: Ausstieg nach einem Datenbalken (One-bar exit). Keine echten Stop-Orders; die Stop-Distanz dient dem Sizing, nicht der Stop-Ausführung.</p>')
        for name, label, integer in [
            ('lookback_bars', 'Rückschau in Balken (ganze Zahl)', True),
            ('stop_distance_pct', 'Stop-Distanz als Verhältnis (0.01 = 1 %; kein echter Stop)', False),
            ('min_strength', 'Minimale Signalstärke', False)]:
            parts.append(field('strategy_parameters.' + name, label, integer=integer))
        parts.append(field('strategy_parameters.allow_short', 'Short-Signale zulassen', choices=[('true', 'Ja'), ('false', 'Nein')]))
        parts.append('<div data-v1-only hidden>')
        parts.extend([field('strategy_parameters.breakout_threshold_pct', 'Breakout-Schwelle als Verhältnis (0.01 = 1 %)'),
                      field('strategy_parameters.cooldown_bars', 'Cooldown in Balken (ganze Zahl)', integer=True),
                      field('strategy_parameters.max_signals_per_day_mode', 'Signale pro Tag begrenzen', choices=[('limited', 'Ausdrückliche Obergrenze'), ('unlimited', 'Unbegrenzt (null)')]),
                      field('strategy_parameters.max_signals_per_day', 'Maximale Signale pro Tag (ganze Zahl; nur bei Obergrenze)', integer=True)])
        parts.append('</div>')
        parts.append(field('risk.sizing_mode', 'Sizing-Modus', choices=[('absolute', 'Absolute Größe'), ('percent_risk', 'Equity-Anteil / Stop-Distanz')]))
        for name, label in [
            ('initial_equity', 'Startkapital in Simulationseinheiten'),
            ('max_position_size', 'Maximale Positionsgröße in Stück/Einheiten'),
            ('max_total_exposure', 'Exposure-Kappe (absolute: Stück; percent_risk: Notional; Runner-Exposure bleibt 0)'),
            ('risk_per_trade', 'Absolute Ausgangsgröße (kein Geldrisiko; bei percent_risk ignoriert)'),
            ('max_daily_drawdown', 'Kumulativer Drawdown-Stopp in Simulationseinheiten (kein Tagesreset)'),
            ('risk_per_trade_pct', 'Equity-Risikoanteil als Verhältnis (0.01 = 1 %; bei absolute ignoriert)'),
            ('max_position_notional', 'Notional-Kappe (0 deaktiviert; bei absolute ignoriert)'),
            ('max_daily_loss', 'Tagesverlustfeld (kein wirksamer Verlustschutz; bei absolute ignoriert)'),
            ('max_losing_streak', 'Verlustserie bis Pause (ganze Zahl; 0 deaktiviert; bei absolute ignoriert)')]:
            parts.append(field('risk.' + name, label, integer=name == 'max_losing_streak'))
        for name, label in [('fee_rate', 'Gebührenverhältnis pro Seite (0.01 = 1 %)'),
                            ('spread', 'Absoluter Spread pro Seite in Preiseinheiten'),
                            ('slippage', 'Slippage-Verhältnis pro Seite (0.01 = 1 %)')]:
            parts.append(field('costs.' + name, label))
        parts.append('</fieldset>')
    parts.append('</div>')
    return ''.join(parts)


CUSTOMER_CONTROLS = '''<section aria-labelledby="data-heading"><h2 id="data-heading">Ihre OHLCV-Daten prüfen</h2>
<p>Wählen Sie eine CSV und das erwartete Intervall. Ohne Strategieparameter, ohne Simulation und ohne Auftrag. Die Prüfdatei wird nicht dauerhaft gespeichert. Maximal 5 MiB; UTF-8, UTC und feste Zeitabstände.</p>
<form id="data-check"><label>OHLCV-CSV <input id="csv" type="file" accept=".csv,text/csv" required></label>
<label>Erwartetes Intervall <select id="timeframe" required><option value="">Bitte wählen</option><option>1m</option><option>5m</option><option>15m</option><option>1h</option></select></label>
<button type="submit">Nur Daten prüfen</button></form><div id="quality" role="status" aria-live="polite"></div></section>
<section><h2>Optional: drei eigene Research-Konfigurationen</h2>
<p>Die Datenprüfung genügt als Einstieg. Research ist eine digitale Simulation, keine Bestellung, Zahlung, persönliche Beratung oder individuelle Handelsempfehlung. Keine automatische Parametersuche oder Empfehlung. Ein Preisangebot ist nicht eingerichtet; frühere Preise sind unbestätigte Hypothesen.</p>
<p>Verwenden Sie Ihre ausdrücklich ausgefüllte Konfiguration im bestehenden Research-Pilot-Format mit genau drei Varianten. Die Reihenfolge bleibt erhalten. Keine vorausgefüllte Zustimmung.</p>
<label for="configuration-mode">Eingabemodus</label><select id="configuration-mode"><option value="form">Formular – drei eigene Varianten</option><option value="json">JSON – erweiterter Import und Editor</option></select>
<!--VARIANT_FORM-->
<details id="json-editor" hidden><summary>Erweiterte JSON-Konfiguration importieren und bearbeiten</summary>
<p>Nur im JSON-Modus wird dieser Editor verwendet. Ein Import ersetzt keine Formulareingaben. Wechsel, Import oder Bearbeitung heben Bindung und Zustimmungen auf.</p>
<label>Eigene Konfiguration (JSON) <input id="config-file" type="file" accept=".json,application/json"></label>
<label>Konfiguration prüfen und bearbeiten <textarea id="configuration" rows="10" aria-label="Konfiguration prüfen und bearbeiten"></textarea></label>
</details>
<button id="preview" type="button">Eingaben prüfen und binden</button><div id="binding" role="status" aria-live="polite"></div>
<label><input id="rights" type="checkbox"> Ich habe die erforderlichen Rechte zur Verarbeitung dieser Daten.</label>
<label><input id="approval" type="checkbox"> Ich gebe genau diese Datei und diese drei Konfigurationen zur Simulation frei. Dafür wird die Datei geschützt gespeichert.</label>
<button id="submit-research" type="button" disabled>Research-Simulation freigeben</button><div id="order-status" role="status" aria-live="polite"></div></section>
<section><h2>Freiwilliges digitales Feedback</h2><p>Unabhängig von Prüfung und Auftrag. Ihre Antwort wird geschützt gespeichert, löst keine Ausführungsfreigabe aus und ist kein Kaufnachweis. Bitte keine vertraulichen Daten in Freitextfelder schreiben.</p>
<form id="feedback"><label>Welche Aufgabe möchten Sie erledigen? <textarea id="goal" maxlength="1000" required></textarea></label>
<label>Was hindert Sie? <textarea id="obstacle" maxlength="1000" required></textarea></label>
<label>Wahrgenommener Nutzen <select id="usefulness" required><option value="">Bitte wählen</option><option value="1">1 – gering</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5 – hoch</option></select></label>
<label>Würden Sie es wieder verwenden? <select id="again" required><option value="">Bitte wählen</option><option value="yes">Ja</option><option value="no">Nein</option><option value="unsure">Unsicher</option></select></label>
<label>Zusätzlicher Hinweis (optional) <textarea id="comment" maxlength="1000"></textarea></label>
<label><input id="synthetic-feedback" type="checkbox"> Dies ist synthetisches Testfeedback, keine echte Kundenantwort.</label>
<button type="submit">Feedback freiwillig speichern</button></form><div id="feedback-status" role="status" aria-live="polite"></div></section>
<script src="/research/customer.js" defer></script>'''.replace('<!--VARIANT_FORM-->', _variant_form())

CUSTOMER_SCRIPT = r'''"use strict";
function readFormConfiguration(root,timeframe){
    const value=(scope,selector,name)=>{const control=scope.querySelector(selector);const raw=control?.value;
        if(typeof raw!=="string"||!raw.trim())throw new Error(name+": bitte ausdrücklich ausfüllen oder wählen.");return raw.trim();};
    const choice=(raw,allowed,name)=>{if(!allowed.includes(raw))throw new Error(name+": gültige Auswahl erforderlich.");return raw;};
    const numeric=(scope,name,integer=false)=>{const raw=value(scope,`[data-field="${name}"]`,name);
        if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(raw))throw new Error(name+": Zahl erforderlich.");
        const number=Number(raw);if(!Number.isFinite(number)||(Number.isInteger(number)&&!Number.isSafeInteger(number))||(integer&&!Number.isSafeInteger(number)))throw new Error(name+": endliche Zahl bzw. sichere ganze Zahl erforderlich.");return number;};
    choice(timeframe,["1m","5m","15m","1h"],"Intervall");
    const order={};for(const name of ["reference","title","instrument","price_unit","data_origin","assumptions"]){
        order[name]=value(root,"#order-"+name,"order."+name);if(order[name].length>2000)throw new Error("order."+name+": maximal 2000 Zeichen.");}
    choice(order.data_origin,["synthetic","customer_provided"],"Datenherkunft");
    const fieldsets=Array.from(root.querySelectorAll("fieldset[data-variant]"));
    if(fieldsets.length!==3)throw new Error("Genau drei Varianten sind erforderlich.");
    const ids=new Set();const variants=fieldsets.map(scope=>{
        const read=name=>value(scope,`[data-field="${name}"]`,name);
        const id=read("id");if(!/^[A-Za-z0-9_-]{1,64}$/.test(id)||ids.has(id))throw new Error("Varianten-IDs müssen gültig und eindeutig sein.");ids.add(id);
        const strategy=choice(read("strategy"),["mid-breakout-v0","mid-breakout-v1"],"Strategie");
        const strategy_parameters={};for(const name of ["lookback_bars","stop_distance_pct","min_strength"])
            strategy_parameters[name]=numeric(scope,"strategy_parameters."+name,name==="lookback_bars");
        strategy_parameters.allow_short=choice(read("strategy_parameters.allow_short"),["true","false"],"Short-Auswahl")==="true";
        if(strategy==="mid-breakout-v1"){
            strategy_parameters.breakout_threshold_pct=numeric(scope,"strategy_parameters.breakout_threshold_pct");
            strategy_parameters.cooldown_bars=numeric(scope,"strategy_parameters.cooldown_bars",true);
            const mode=choice(read("strategy_parameters.max_signals_per_day_mode"),["limited","unlimited"],"Signalgrenze");
            strategy_parameters.max_signals_per_day=mode==="unlimited"?null:numeric(scope,"strategy_parameters.max_signals_per_day",true);
        }
        const risk={sizing_mode:choice(read("risk.sizing_mode"),["absolute","percent_risk"],"Sizing-Modus")};
        for(const name of ["initial_equity","max_position_size","max_total_exposure","risk_per_trade","max_daily_drawdown","risk_per_trade_pct","max_position_notional","max_daily_loss","max_losing_streak"])
            risk[name]=numeric(scope,"risk."+name,name==="max_losing_streak");
        const costs={};for(const name of ["fee_rate","spread","slippage"])costs[name]=numeric(scope,"costs."+name);
        return {id,strategy,seed:numeric(scope,"seed",true),hypothesis:read("hypothesis"),strategy_parameters,risk,costs};
    });
    return {schema:"liquent.research-pilot.config.v1",order,dataset:{timeframe},variants};
}
(()=>{const el=id=>document.getElementById(id);let csrf=null,canWrite=false,binding=null,version=0,datasetRevision=0,busy=false;
const text=(id,message)=>{el(id).textContent=message;};
const reset=(dataChanged=false)=>{version++;binding=null;el("rights").checked=false;el("approval").checked=false;text("binding","Eingaben geändert. Bitte erneut prüfen und ausdrücklich freigeben.");if(dataChanged){datasetRevision++;text("quality","Eingaben geändert. Bitte Daten erneut prüfen; frühere Befunde sind nicht mehr gültig.");}update();};
const update=()=>{el("submit-research").disabled=busy||!csrf||!canWrite||!binding||!el("rights").checked||!el("approval").checked;};
async function api(path,body){const response=await fetch(path,{method:body===undefined?"GET":"POST",credentials:"same-origin",cache:"no-store",headers:body===undefined?{}:{"Content-Type":"application/json","X-CSRF-Token":csrf||""},body:body===undefined?undefined:JSON.stringify(body)});
if(!response.ok)throw new Error(response.status===401?"Sitzung beendet. Bitte über die bestehende Anmeldung erneut anmelden.":response.status===403?"Freigabe oder Zugriffsrechte fehlen. Bitte Sitzung und Berechtigungen prüfen.":response.status===413?"Datei ist zu groß (maximal 5 MiB).":response.status===503?"Research ist derzeit nicht verfügbar. Es wurde kein Erfolg bestätigt.":"Eingaben abgewiesen. Bitte Datei, Intervall und vollständige Konfiguration prüfen.");return await response.json();}
async function dataset(){const file=el("csv").files[0];if(!file||!file.size||file.size>5*1024*1024)throw new Error("Bitte eine nicht leere CSV bis 5 MiB wählen.");const bytes=new Uint8Array(await file.arrayBuffer());let raw="";for(let i=0;i<bytes.length;i+=16384)raw+=String.fromCharCode(...bytes.subarray(i,i+16384));return btoa(raw);}
const configuration=()=>{if(el("configuration-mode").value==="form")return readFormConfiguration(el("variant-form"),el("timeframe").value);const value=JSON.parse(el("configuration").value);if(value.dataset?.timeframe!==el("timeframe").value)throw new Error("Intervall der Konfiguration und der Datenprüfung müssen übereinstimmen.");return value;};
function showQuality(result){const parent=el("quality");parent.replaceChildren();for(const value of [result.headline,result.meaning]){const p=document.createElement("p");p.textContent=value;parent.append(p);}const q=result.data_quality;
for(const [label,value] of [["Zeitraum",q.period_start&&q.period_end?q.period_start+" bis "+q.period_end:"Nicht verfügbar"],["Datenbalken",q.rows],["Intervall",q.timeframe],["Datenlücken",q.gaps.length],["Fehler",q.issues.length?q.issues.join(" "):"Keine bei dieser Prüfung gefunden"],["Historie",q.history?`${q.history.actual_bars} vorhanden; Empfehlung ${q.history.required_bars} Balken`:"Nicht bewertbar"]]){const p=document.createElement("p");p.textContent=label+": "+value;parent.append(p);}for(const hint of [...q.warnings,...result.next_steps]){const p=document.createElement("p");p.textContent=hint;parent.append(p);}}
for(const id of ["csv","timeframe"])el(id).addEventListener("change",()=>reset(true));
for(const name of ["input","change"])el("configuration").addEventListener(name,()=>reset());
function updateVariantFields(){for(const scope of el("variant-form").querySelectorAll("fieldset[data-variant]")){
    const v1=scope.querySelector('[data-field="strategy"]').value==="mid-breakout-v1";
    scope.querySelector("[data-v1-only]").hidden=!v1;
    const unlimited=scope.querySelector('[data-field="strategy_parameters.max_signals_per_day_mode"]').value==="unlimited";
    for(const control of scope.querySelector("[data-v1-only]").querySelectorAll("input, select")){
        control.disabled=!v1||(control.dataset.field==="strategy_parameters.max_signals_per_day"&&unlimited);control.required=!control.disabled;
    }
}}
for(const name of ["input","change"])el("variant-form").addEventListener(name,()=>{reset();updateVariantFields();});
el("configuration-mode").addEventListener("change",()=>{reset();const json=el("configuration-mode").value==="json";el("variant-form").hidden=json;el("json-editor").hidden=!json;el("json-editor").open=json;});
updateVariantFields();
for(const id of ["rights","approval"])el(id).addEventListener("change",update);
el("config-file").addEventListener("change",async()=>{reset();const stamp=version,file=el("config-file").files[0];if(!file)return;if(file.size>65536){text("binding","Konfiguration maximal 64 KiB.");return;}try{const value=await file.text();if(stamp===version)el("configuration").value=value;}catch(error){if(stamp===version)text("binding","Konfigurationsdatei konnte nicht gelesen werden.");}});
el("data-check").addEventListener("submit",async event=>{event.preventDefault();const stamp=datasetRevision,timeframe=el("timeframe").value;text("quality","Daten werden geprüft; keine Simulation.");try{const data=await dataset();if(stamp!==datasetRevision)return;const result=await api("/v1/research/data-check",{csv_base64:data,timeframe});if(stamp===datasetRevision)showQuality(result);}catch(error){if(stamp===datasetRevision)text("quality",error.message);}});
el("preview").addEventListener("click",async()=>{reset();const stamp=version;try{const config=configuration(),raw=await dataset();if(stamp!==version)return;const result=await api("/v1/research/request-preview",{csv_base64:raw,configuration:config});if(stamp!==version)return;binding=result.binding_fingerprint;text("binding","Geprüfte Varianten in Ihrer Reihenfolge: "+result.variant_ids.join(" → ")+". Eingabebindung: "+binding+". Noch kein Auftrag oder Simulationsstart.");update();}catch(error){if(stamp===version)text("binding",error.message);}});
el("submit-research").addEventListener("click",async()=>{if(el("submit-research").disabled)return;const stamp=version;busy=true;update();try{const config=configuration(),fingerprint=binding,raw=await dataset();if(stamp!==version||!el("rights").checked||!el("approval").checked)return;const result=await api("/v1/research/customer-jobs",{csv_base64:raw,configuration:config,binding_fingerprint:fingerprint,data_rights:true,execution_approved:true});reset();text("order-status","Auftrag zugeordnet. Aktueller Status: "+result.status+". Identische Eingaben werden nicht doppelt ausgeführt. ");const a=document.createElement("a");a.href="/research/jobs/"+encodeURIComponent(result.job_id);a.textContent="Status und Ergebnis ansehen";el("order-status").append(a);}catch(error){text("order-status",error.message);}finally{busy=false;update();}});
el("feedback").addEventListener("submit",async event=>{event.preventDefault();try{await api("/v1/research/customer-feedback",{feedback:{goal:el("goal").value,main_obstacle:el("obstacle").value,usefulness:Number(el("usefulness").value),would_use_again:el("again").value,comment:el("comment").value},synthetic:el("synthetic-feedback").checked});text("feedback-status","Rückmeldung geschützt gespeichert; keine Auftragsfreigabe, kein Kaufnachweis.");}catch(error){text("feedback-status",error.message);}});
api("/v1/research/customer-context").then(value=>{csrf=value.csrf_token;canWrite=value.can_write;update();if(!canWrite)text("order-status","Ihre Sitzung erlaubt Datenprüfung und Feedback; Research-Ausführung benötigt gesonderte Schreibrechte.");}).catch(error=>{text("quality",error.message);});
})();'''

CUSTOMER_CSP = CONTENT_SECURITY_POLICY.replace("default-src 'none';", "default-src 'none'; script-src 'self'; connect-src 'self';")

CUSTOMER_STYLE = "[hidden]{display:none!important}fieldset{min-width:0;margin:24px 0;padding:20px;border:1px solid #a4b7ca;border-radius:8px}legend{color:#082d56;font-weight:600}details{margin:24px 0}summary{cursor:pointer;color:#082d56}label{display:block;margin:18px 0;color:#435b73}input:not([type=checkbox]),select,textarea{box-sizing:border-box;display:block;width:100%;max-width:100%;margin-top:8px;padding:12px;border:1px solid #a4b7ca;border-radius:8px;background:#fff;color:#082d56;font:inherit}textarea{resize:vertical}input[type=checkbox]{margin-right:8px}input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible,button:focus-visible{outline:3px solid #082d56;outline-offset:3px}button:disabled{opacity:.55;cursor:not-allowed}#quality,#binding,#order-status,#feedback-status{overflow-wrap:anywhere}"
_style_hash = base64.b64encode(hashlib.sha256(CUSTOMER_STYLE.encode()).digest()).decode()
_script_hash = base64.b64encode(hashlib.sha256(CUSTOMER_SCRIPT.encode()).digest()).decode()
CUSTOMER_CONTROLS = ('<style>' + CUSTOMER_STYLE + '</style>' + CUSTOMER_CONTROLS).replace(
    'src="/research/customer.js" defer', 'src="/research/customer.js" integrity="sha256-' + _script_hash + '" defer')
CUSTOMER_CSP = CONTENT_SECURITY_POLICY.replace(
    "default-src 'none';", "default-src 'none'; script-src 'sha256-" + _script_hash + "'; connect-src 'self';").replace(
    "; frame-ancestors", " 'sha256-" + _style_hash + "'; frame-ancestors")
