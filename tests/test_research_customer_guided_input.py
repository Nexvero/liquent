"""Guided input uses the delivered script and the existing executable Node DOM."""

from copy import deepcopy
import json
import subprocess

import pytest

from liquent_platform.transport.http import research_customer_ui as ui
from test_research_variant_form import (
    HARNESS, all_text, by_id, descendants, example, markup, node_runtime,
)


GUIDED_ACTIONS = r'''
  get("csv").files[0].name='<svg onload="alert(1)">.csv';
  const rendered=n=>[n.textContent,...n.children.map(rendered)].join("\n");
  const state=()=>({rights:get("rights").checked,approval:get("approval").checked,
    rightsDisabled:get("rights").disabled,approvalDisabled:get("approval").disabled,
    disabled:get("submit-research").disabled,binding:get("binding").textContent,
    preview:rendered(get("configuration-preview"))});
  const controls=()=>Object.fromEntries(walk(root).filter(n=>n.dataset.field)
    .map(n=>[n.id,n.value]));
  const approve=async()=>{get("rights").checked=true;get("approval").checked=true;
    await get("rights").fire("change");await get("approval").fire("change");};
  if(input.action==="pending-consent") {
    const pending=get("preview").fire("click");
    await new Promise(resolve=>setImmediate(resolve));
    if(!releasePreview) throw new Error("Missing pending preview");
    const pendingState=state();
    // Deliberately force even disabled checkboxes to model the old race.
    await approve();const premature=state();
    releasePreview();await pending;const published=state();
    await approve();
    process.stdout.write(JSON.stringify({pendingState,premature,published,approved:state(),requests}));return;
  }
  if(input.action==="copy-pending") {
    const pending=get("preview").fire("click");
    await new Promise(resolve=>setImmediate(resolve));
    if(!releasePreview) throw new Error("Missing pending preview");
    await get("copy-risk-costs-"+input.target).fire("click");
    releasePreview();await pending;await approve();
    process.stdout.write(JSON.stringify({state:state(),requests}));return;
  }
  if(["guided-preview","rejected-preview","guided-copy","blank-copy"].includes(input.action)) {
    if(input.mode==="json") {put("configuration-mode","json");
      await get("configuration-mode").fire("change");
      put("configuration",JSON.stringify(input.configuration));}
    const before=controls();
    await get("preview").fire("click");
    const beforeApproval=state(), previewNodes=walk(get("configuration-preview"));
    const headings=previewNodes.filter(n=>n.tagName==="H3").map(n=>n.textContent);
    const paragraphs=previewNodes.filter(n=>n.tagName==="P").map(n=>n.textContent);
    const variantParagraphs=get("configuration-preview").children
      .filter(n=>n.tagName==="SECTION" && n.children.some(c=>c.tagName==="H3"))
      .map(n=>walk(n).filter(c=>c.tagName==="P").map(c=>c.textContent));
    if(input.action==="guided-preview" || input.action==="rejected-preview") {
      await approve();
      process.stdout.write(JSON.stringify({beforeApproval,afterApproval:state(),headings,paragraphs,variantParagraphs,
        tags:previewNodes.map(n=>n.tagName),bodies,requests}));return;
    }
    await approve();const bound=state();
    get("quality").textContent="Existing data finding";
    if(input.action==="blank-copy") put("variant-0-risk-initial_equity","");
    await get("copy-risk-costs-"+input.target).fire("click");
    const after=controls(),invalidated=state();await approve();
    // No automatic propagation when variant 1 is subsequently edited.
    put("variant-0-costs-spread","123");await get("variant-0-costs-spread").fire("input");
    process.stdout.write(JSON.stringify({before,after,bound,invalidated,afterApproval:state(),
      afterSourceEdit:controls(),quality:get("quality").textContent,requests}));return;
  }
'''


GUIDED_HARNESS = HARNESS.replace(
    '  return n;\n}',
    '  Object.defineProperty(n,"innerHTML",{set(){throw new Error("Unsafe HTML rendering");}});\n  return n;\n}',
).replace(
    'const requests=[];', 'const bodies=[];const requests=[];',
).replace(
    'fetch:async(path)=>{requests.push(path);',
    'fetch:async(path,options)=>{requests.push(path);if(options.body)bodies.push(JSON.parse(options.body));'
    'if(input.action==="rejected-preview" && path.endsWith("request-preview"))return {ok:false,status:422};',
).replace(
    'input.action==="stale-preview" && path.endsWith("request-preview")',
    '["stale-preview","copy-pending","pending-consent"].includes(input.action) && path.endsWith("request-preview")',
).replace(
    '  if(input.action==="stale-preview") {', GUIDED_ACTIONS + '\n  if(input.action==="stale-preview") {',
)


def run_guided(node_runtime, markup, example, action, *, target=1, mode="form"):
    payload = dict(markup=markup, script=ui.CUSTOMER_SCRIPT, configuration=example,
                   action=action, target=target, mode=mode)
    result = subprocess.run([node_runtime, "-e", GUIDED_HARNESS], input=json.dumps(payload),
                            text=True, capture_output=True, timeout=10, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_numbered_sections_copy_buttons_and_explanation_only_details(markup):
    headings = [all_text(n) for n in descendants(markup) if n["tag"] == "h2"]
    assert [heading[:2] for heading in headings[:3]] == ["1.", "2.", "3."]
    variants = [n for n in descendants(markup) if "data-variant" in n["attrs"]]
    assert len(variants) == 3
    for index, variant in enumerate(variants):
        buttons = [n for n in descendants(variant) if n["tag"] == "button"]
        assert len(buttons) == (0 if index == 0 else 1)
        if index:
            assert buttons[0]["attrs"]["id"] == f"copy-risk-costs-{index}"
            assert buttons[0]["attrs"]["type"] == "button"
    explanation = by_id(markup, "technical-explanation")
    assert explanation["tag"] == "details"
    assert not any(n["tag"] in {"input", "select", "textarea"} for n in descendants(explanation))
    # No required form controls were newly collapsed in explanatory disclosures.
    for detail in (n for n in descendants(by_id(markup, "variant-form")) if n["tag"] == "details"):
        assert not any("required" in n["attrs"] for n in descendants(detail))
    approval_section = next(n for n in descendants(markup) if n["attrs"].get("aria-labelledby") == "approval-heading")
    ids = [n["attrs"].get("id") for n in descendants(approval_section)]
    assert ids.index("configuration-preview") < ids.index("rights") < ids.index("approval")
    assert "checked" not in by_id(markup, "rights")["attrs"]
    assert "checked" not in by_id(markup, "approval")["attrs"]


@pytest.mark.parametrize("target", [1, 2])
def test_copy_only_target_risk_costs_invalidates_binding_consent_and_preview(node_runtime, markup, example, target):
    result = run_guided(node_runtime, markup, example, "guided-copy", target=target)
    assert result["bound"]["disabled"] is False
    assert result["bound"]["preview"]
    for identifier, original in result["before"].items():
        prefix = f"variant-{target}-"
        copied = identifier.startswith((prefix + "risk-", prefix + "costs-"))
        expected = result["before"][identifier.replace(prefix, "variant-0-", 1)] if copied else original
        assert result["after"][identifier] == expected, identifier
    invalidated = result["invalidated"]
    assert invalidated["rights"] is invalidated["approval"] is False
    assert invalidated["disabled"] is True
    assert "sha256:test" not in invalidated["binding"]
    assert not invalidated["preview"].strip()
    assert result["afterApproval"]["disabled"] is True
    assert result["quality"] == "Existing data finding"
    assert result["afterSourceEdit"][f"variant-{target}-costs-spread"] == result["after"][f"variant-{target}-costs-spread"]
    assert "/v1/research/customer-jobs" not in result["requests"]


@pytest.mark.parametrize("target", [1, 2])
def test_copy_blank_source_does_not_supply_defaults(node_runtime, markup, example, target):
    result = run_guided(node_runtime, markup, example, "blank-copy", target=target)
    assert result["after"][f"variant-{target}-risk-initial_equity"] == ""
    assert result["afterApproval"]["disabled"] is True


@pytest.mark.parametrize("target", [1, 2])
def test_explicit_identical_copy_still_invalidates(node_runtime, markup, example, target):
    example["variants"][target]["risk"] = deepcopy(example["variants"][0]["risk"])
    example["variants"][target]["costs"] = deepcopy(example["variants"][0]["costs"])
    result = run_guided(node_runtime, markup, example, "guided-copy", target=target)
    assert result["after"] == result["before"]
    assert result["invalidated"]["rights"] is result["invalidated"]["approval"] is False
    assert result["afterApproval"]["disabled"] is True
    assert not result["invalidated"]["preview"].strip()


@pytest.mark.parametrize("target", [1, 2])
def test_copy_discards_inflight_preview(node_runtime, markup, example, target):
    result = run_guided(node_runtime, markup, example, "copy-pending", target=target)
    assert result["state"]["disabled"] is True
    assert "sha256:test" not in result["state"]["binding"]
    assert not result["state"]["preview"].strip()


@pytest.mark.parametrize("mode", ["form", "json"])
def test_exact_ordered_preview_all_values_safe_text_before_approval(node_runtime, markup, example, mode):
    config = deepcopy(example)
    hostile = '<img src=x onerror="alert(1)">&<script>bad()</script>'
    config["order"]["title"] = hostile
    config["variants"][0]["hypothesis"] = hostile
    config["variants"][1]["strategy_parameters"]["max_signals_per_day"] = None
    config["variants"][2]["costs"]["slippage"] = 1e-7
    original = deepcopy(config)
    result = run_guided(node_runtime, markup, config, "guided-preview", mode=mode)
    assert config == original
    before = result["beforeApproval"]
    assert before["rights"] is before["approval"] is False
    assert before["disabled"] is True
    assert "sha256:test" in before["binding"]
    assert result["afterApproval"]["disabled"] is False
    assert result["headings"][1:4] == [f"Variante {i+1}: {v['id']}" for i, v in enumerate(config["variants"])]
    assert hostile in before["preview"]
    assert '<svg onload="alert(1)">.csv' in before["preview"]
    assert not {"IMG", "SCRIPT", "SVG", "INPUT"}.intersection(result["tags"])
    assert result["bodies"][0]["configuration"] == config

    def leaves(value):
        for key, item in value.items():
            if isinstance(item, dict):
                yield from leaves(item)
            elif isinstance(item, list):
                for variant in item:
                    yield from leaves(variant)
            else:
                yield key, item

    def assert_exact(paragraphs, values):
        for key, value in leaves(values):
            exact = ("null (unbegrenzt)" if value is None else str(value).lower()
                     if isinstance(value, bool) else str(value))
            # JS canonical string spelling, without rounded display values.
            if isinstance(value, float) and value.is_integer():
                exact = str(int(value))
            if value == 1e-7:
                exact = "1e-7"
            assert any(p.endswith(f"({key}): {exact}") for p in paragraphs), (key, value)

    assert_exact(result["paragraphs"], config)
    assert len(result["variantParagraphs"]) == 3
    for paragraphs, variant in zip(result["variantParagraphs"], config["variants"]):
        assert_exact(paragraphs, variant)
    for limit in ["One-bar exit", "Mittelkurs-Proxy", "Keine echten Stop-Orders",
                  "ohne Tagesreset", "max_daily_loss", "Runner-Exposure", "net_pnl / quantity"]:
        assert limit in before["preview"]
    assert "/v1/research/customer-jobs" not in result["requests"]


def test_rejected_preview_cannot_display_approved_configuration(node_runtime, markup, example):
    result = run_guided(node_runtime, markup, example, "rejected-preview")
    assert not result["beforeApproval"]["preview"].strip()
    assert "sha256:test" not in result["beforeApproval"]["binding"]
    assert result["afterApproval"]["disabled"] is True


def test_pending_preview_cannot_carry_consent_into_new_display(node_runtime, markup, example):
    result = run_guided(node_runtime, markup, example, "pending-consent")
    for key in ("pendingState", "premature"):
        assert result[key]["rightsDisabled"] is result[key]["approvalDisabled"] is True
        assert result[key]["disabled"] is True
    published = result["published"]
    assert published["preview"] and "sha256:test" in published["binding"]
    assert published["rights"] is published["approval"] is False
    assert published["rightsDisabled"] is published["approvalDisabled"] is False
    assert published["disabled"] is True
    assert result["approved"]["disabled"] is False
    assert "/v1/research/customer-jobs" not in result["requests"]
