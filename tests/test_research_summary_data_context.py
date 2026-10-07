"""Real stored data context, not invented demand or performance evidence."""

from liquent_platform.transport.http.research_results import result_document
from test_research_customer_results import pilot


def test_synthetic_label_and_history_warning_before_positive_result():
    evidence = pilot()
    evidence['pilot_result']['order'] = {'data_origin': 'synthetic'}
    evidence['pilot_result']['data_quality'] = {'warnings': ['Sehr kurze Historie']}
    html = result_document('synthetic', 'succeeded', evidence)
    assert html.index('Synthetische Demonstration') < html.index('Kurz erklärt')
    assert html.index('Sehr kurze Historie') < html.index('positiv (über null)')


def test_absent_context_not_invented_and_stored_warning_escaped():
    evidence = pilot()
    assert 'Synthetische Demonstration' not in result_document('job', 'succeeded', evidence)
    evidence['pilot_result']['data_quality'] = {'warnings': ['<script>bad()</script>', None]}
    html = result_document('job', 'succeeded', evidence)
    assert 'Datenhinweis: &lt;script&gt;bad()&lt;/script&gt;' in html
    assert '<script>' not in html
