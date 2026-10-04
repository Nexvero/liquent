"""Customer controls inside the existing authenticated Research page."""
import base64
import hashlib

from .ui_brand import CONTENT_SECURITY_POLICY

CUSTOMER_CONTROLS = '''<section aria-labelledby="data-heading"><h2 id="data-heading">Ihre OHLCV-Daten prüfen</h2>
<p>Wählen Sie eine CSV und das erwartete Intervall. Ohne Strategieparameter, ohne Simulation und ohne Auftrag. Die Prüfdatei wird nicht dauerhaft gespeichert. Maximal 5 MiB; UTF-8, UTC und feste Zeitabstände.</p>
<form id="data-check"><label>OHLCV-CSV <input id="csv" type="file" accept=".csv,text/csv" required></label>
<label>Erwartetes Intervall <select id="timeframe" required><option value="">Bitte wählen</option><option>1m</option><option>5m</option><option>15m</option><option>1h</option></select></label>
<button type="submit">Nur Daten prüfen</button></form><div id="quality" role="status" aria-live="polite"></div></section>
<section><h2>Optional: drei eigene Research-Konfigurationen</h2>
<p>Die Datenprüfung genügt als Einstieg. Research ist eine digitale Simulation, keine Bestellung, Zahlung, persönliche Beratung oder individuelle Handelsempfehlung. Keine automatische Parametersuche oder Empfehlung. Ein Preisangebot ist nicht eingerichtet; frühere Preise sind unbestätigte Hypothesen.</p>
<p>Verwenden Sie Ihre ausdrücklich ausgefüllte Konfiguration im bestehenden Research-Pilot-Format mit genau drei Varianten. Die Reihenfolge bleibt erhalten. Keine vorausgefüllte Zustimmung.</p>
<label>Eigene Konfiguration (JSON) <input id="config-file" type="file" accept=".json,application/json"></label>
<label>Konfiguration prüfen und bearbeiten <textarea id="configuration" rows="10" aria-label="Konfiguration prüfen und bearbeiten"></textarea></label>
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
<script src="/research/customer.js" defer></script>'''

CUSTOMER_SCRIPT = r'''"use strict";
(()=>{const el=id=>document.getElementById(id);let csrf=null,canWrite=false,binding=null,version=0,busy=false;
const text=(id,message)=>{el(id).textContent=message;};
const reset=()=>{version++;binding=null;el("rights").checked=false;el("approval").checked=false;text("binding","");text("quality","Eingaben geändert. Bitte Daten erneut prüfen; frühere Befunde sind nicht mehr gültig.");update();};
const update=()=>{el("submit-research").disabled=busy||!csrf||!canWrite||!binding||!el("rights").checked||!el("approval").checked;};
async function api(path,body){const response=await fetch(path,{method:body===undefined?"GET":"POST",credentials:"same-origin",cache:"no-store",headers:body===undefined?{}:{"Content-Type":"application/json","X-CSRF-Token":csrf||""},body:body===undefined?undefined:JSON.stringify(body)});
if(!response.ok)throw new Error(response.status===401?"Sitzung beendet. Bitte über die bestehende Anmeldung erneut anmelden.":response.status===403?"Freigabe oder Zugriffsrechte fehlen. Bitte Sitzung und Berechtigungen prüfen.":response.status===413?"Datei ist zu groß (maximal 5 MiB).":response.status===503?"Research ist derzeit nicht verfügbar. Es wurde kein Erfolg bestätigt.":"Eingaben abgewiesen. Bitte Datei, Intervall und vollständige Konfiguration prüfen.");return await response.json();}
async function dataset(){const file=el("csv").files[0];if(!file||!file.size||file.size>5*1024*1024)throw new Error("Bitte eine nicht leere CSV bis 5 MiB wählen.");const bytes=new Uint8Array(await file.arrayBuffer());let raw="";for(let i=0;i<bytes.length;i+=16384)raw+=String.fromCharCode(...bytes.subarray(i,i+16384));return btoa(raw);}
const configuration=()=>{const value=JSON.parse(el("configuration").value);if(value.dataset?.timeframe!==el("timeframe").value)throw new Error("Intervall der Konfiguration und der Datenprüfung müssen übereinstimmen.");return value;};
function showQuality(result){const parent=el("quality");parent.replaceChildren();for(const value of [result.headline,result.meaning]){const p=document.createElement("p");p.textContent=value;parent.append(p);}const q=result.data_quality;
for(const [label,value] of [["Zeitraum",q.period_start&&q.period_end?q.period_start+" bis "+q.period_end:"Nicht verfügbar"],["Datenbalken",q.rows],["Intervall",q.timeframe],["Datenlücken",q.gaps.length],["Fehler",q.issues.length?q.issues.join(" "):"Keine bei dieser Prüfung gefunden"],["Historie",q.history?`${q.history.actual_bars} vorhanden; Empfehlung ${q.history.required_bars} Balken`:"Nicht bewertbar"]]){const p=document.createElement("p");p.textContent=label+": "+value;parent.append(p);}for(const hint of [...q.warnings,...result.next_steps]){const p=document.createElement("p");p.textContent=hint;parent.append(p);}}
for(const id of ["csv","timeframe","configuration"])el(id).addEventListener("change",reset);el("configuration").addEventListener("input",reset);
for(const id of ["rights","approval"])el(id).addEventListener("change",update);
el("config-file").addEventListener("change",async()=>{reset();const stamp=version,file=el("config-file").files[0];if(!file)return;if(file.size>65536){text("binding","Konfiguration maximal 64 KiB.");return;}const value=await file.text();if(stamp===version)el("configuration").value=value;});
el("data-check").addEventListener("submit",async event=>{event.preventDefault();const stamp=version;text("quality","Daten werden geprüft; keine Simulation.");try{const data=await dataset();const result=await api("/v1/research/data-check",{csv_base64:data,timeframe:el("timeframe").value});if(stamp===version)showQuality(result);}catch(error){if(stamp===version)text("quality",error.message);}});
el("preview").addEventListener("click",async()=>{reset();const stamp=version;try{const config=configuration(),raw=await dataset();const result=await api("/v1/research/request-preview",{csv_base64:raw,configuration:config});if(stamp!==version)return;binding=result.binding_fingerprint;text("binding","Geprüfte Varianten in Ihrer Reihenfolge: "+result.variant_ids.join(" → ")+". Eingabebindung: "+binding+". Noch kein Auftrag oder Simulationsstart.");update();}catch(error){if(stamp===version)text("binding",error.message);}});
el("submit-research").addEventListener("click",async()=>{if(el("submit-research").disabled)return;busy=true;update();try{const result=await api("/v1/research/customer-jobs",{csv_base64:await dataset(),configuration:configuration(),binding_fingerprint:binding,data_rights:el("rights").checked,execution_approved:el("approval").checked});reset();text("order-status","Auftrag zugeordnet. Aktueller Status: "+result.status+". Identische Eingaben werden nicht doppelt ausgeführt. ");const a=document.createElement("a");a.href="/research/jobs/"+encodeURIComponent(result.job_id);a.textContent="Status und Ergebnis ansehen";el("order-status").append(a);}catch(error){text("order-status",error.message);}finally{busy=false;update();}});
el("feedback").addEventListener("submit",async event=>{event.preventDefault();try{await api("/v1/research/customer-feedback",{feedback:{goal:el("goal").value,main_obstacle:el("obstacle").value,usefulness:Number(el("usefulness").value),would_use_again:el("again").value,comment:el("comment").value},synthetic:el("synthetic-feedback").checked});text("feedback-status","Rückmeldung geschützt gespeichert; keine Auftragsfreigabe, kein Kaufnachweis.");}catch(error){text("feedback-status",error.message);}});
api("/v1/research/customer-context").then(value=>{csrf=value.csrf_token;canWrite=value.can_write;update();if(!canWrite)text("order-status","Ihre Sitzung erlaubt Datenprüfung und Feedback; Research-Ausführung benötigt gesonderte Schreibrechte.");}).catch(error=>{text("quality",error.message);});
})();'''

CUSTOMER_CSP = CONTENT_SECURITY_POLICY.replace("default-src 'none';", "default-src 'none'; script-src 'self'; connect-src 'self';")

CUSTOMER_STYLE = "label{display:block;margin:18px 0;color:#435b73}input:not([type=checkbox]),select,textarea{display:block;width:100%;max-width:100%;margin-top:8px;padding:12px;border:1px solid #a4b7ca;border-radius:8px;background:#fff;color:#082d56;font:inherit}textarea{resize:vertical}input[type=checkbox]{margin-right:8px}button:disabled{opacity:.55;cursor:not-allowed}#quality,#binding,#order-status,#feedback-status{overflow-wrap:anywhere}"
_style_hash = base64.b64encode(hashlib.sha256(CUSTOMER_STYLE.encode()).digest()).decode()
_script_hash = base64.b64encode(hashlib.sha256(CUSTOMER_SCRIPT.encode()).digest()).decode()
CUSTOMER_CONTROLS = ('<style>' + CUSTOMER_STYLE + '</style>' + CUSTOMER_CONTROLS).replace(
    'src="/research/customer.js" defer', 'src="/research/customer.js" integrity="sha256-' + _script_hash + '" defer')
CUSTOMER_CSP = CONTENT_SECURITY_POLICY.replace(
    "default-src 'none';", "default-src 'none'; script-src 'sha256-" + _script_hash + "'; connect-src 'self';").replace(
    "; frame-ancestors", " 'sha256-" + _style_hash + "'; frame-ancestors")
