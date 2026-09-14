#!/usr/bin/env python3
"""Builds roy-job-scanner.n8n.json — an importable n8n Cloud workflow."""
import json, pathlib

HERE = pathlib.Path(__file__).parent
PROMPT = HERE.parent / "scoring_prompt.md"          # your own, git-ignored
if not PROMPT.exists():
    PROMPT = HERE.parent / "scoring_prompt.example.md"  # the shipped template
SYSTEM_PROMPT = PROMPT.read_text()
FETCH_WORKDAY = (HERE / "fetch_workday.js").read_text()

# ---------------------------------------------------------------- code nodes
BUILD_FEED_URLS = r"""
// One item per active company → the public JSON feed URL for its ATS.
const out = [];
for (const item of $input.all()) {
  const c = item.json;
  const active = String(c.active ?? 'yes').trim().toLowerCase();
  if (['no', 'false', '0', 'off'].includes(active)) continue;
  const ats = String(c.ats || '').trim().toLowerCase();
  const slug = String(c.slug || '').trim();
  if (!ats || !slug) continue;
  let url = null;
  if (ats === 'greenhouse') url = `https://boards-api.greenhouse.io/v1/boards/${slug}/jobs`; // no content=true: descriptions are fetched per candidate later (memory)
  else if (ats === 'lever') url = `https://api.lever.co/v0/postings/${slug}?mode=json`;
  else if (ats === 'lever-eu') url = `https://api.eu.lever.co/v0/postings/${slug}?mode=json`; // EU-hosted Lever (e.g. Mobileye)
  else if (ats === 'ashby') url = `https://api.ashbyhq.com/posting-api/job-board/${slug}`;
  else if (ats === 'comeet') {
    // slug = "<company_uid>|<token>" copied from the company's careers page source
    const [uid, token] = slug.split('|');
    if (uid && token) url = `https://www.comeet.co/careers-api/2.0/company/${uid}/positions?token=${token}`; // details fetched per candidate later
  }
  if (!url) continue;
  out.push({ json: { company: c.company || slug, ats, slug, url, type: c.type || '' } });
}
return out;
"""

TAG_FEED = r"""
// Runs once per response item. n8n resolves which company the item came from (its paired input item),
// which the Code node cannot see in "all items" mode — so we stamp the source onto each item here.
let src = {};
try { src = $('Build Feed URLs').item.json; } catch (e) { src = {}; }
return { json: { src, body: $input.item.json } };
"""

NORMALIZE_ATS = r"""
// Turn every ATS response into one flat item per job. Keeps only Israel / remote / unspecified locations.
const IL = /israel|tel.?aviv|tlv|herzliya|herzelia|hertzelia|haifa|ramat gan|petah|petach|jerusalem|ra'?anana|netanya|beer.?sheva|be'er sheva|rehovot|kfar saba|hod hasharon|rosh ha|yokneam|caesarea|holon|modi'?in|bnei brak|or yehuda|airport city|kiryat|^il$/i;
const REMOTE = /remote|anywhere|worldwide|distributed/i;
const OTHER_COUNTRY = /\b(us|usa|u\.s\.?a?|united states|america|uk|united kingdom|england|london|germany|berlin|munich|france|paris|canada|toronto|india|bangalore|emea|europe|eu|apac|latam|australia|sydney|singapore|japan|tokyo|poland|warsaw|spain|madrid|barcelona|netherlands|amsterdam|ireland|dublin|brazil|mexico|portugal|lisbon|ukraine|kyiv|romania|bulgaria|serbia|czech|prague|austria|switzerland|sweden|stockholm|denmark|norway|finland|italy|milan|greece|turkey|uae|dubai|new york|nyc|san francisco|austin|boston|chicago|seattle|denver|atlanta|texas|california|remote[ -]*us|alabama|alaska|arizona|arkansas|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|utah|vermont|virginia|washington|wisconsin|wyoming|philadelphia|los angeles|san diego|san jose|miami|phoenix|dallas|houston|portland|vancouver|montreal|ottawa|hong kong|china|beijing|shanghai|shenzhen|korea|seoul|taiwan|vietnam|philippines|manila|indonesia|thailand|bangkok|malaysia|south africa|nigeria|kenya|egypt|argentina|buenos aires|colombia|chile|peru|hungary|budapest|lithuania|vilnius|latvia|estonia|tallinn|croatia|slovakia|slovenia|belgium|brussels|luxembourg|scotland|edinburgh|manchester|new zealand|auckland|saudi|riyadh|qatar|doha|cyprus|malta)\b/i;
const strip = s => String(s || '')
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;|&rsquo;|&lsquo;/g, "'").replace(/&nbsp;/g, ' ')
  .replace(/<br\s*\/?>|<\/p>|<\/li>|<\/h\d>/gi, '\n').replace(/<[^>]+>/g, ' ')
  .replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();

const out = [];
const okIdx = new Set(), failIdx = new Set();
let feedsOk = 0, feedsFailed = 0;

$input.all().forEach((item, i) => {
  const src = item.json.src || {};
  const idx = src.url || i; // one feed = one URL; Lever/Comeet arrays arrive split into many items sharing a URL
  const body = item.json.body;
  if (!body || body.error) { failIdx.add(idx); return; }
  let jobs = [];
  try {
    if (src.ats === 'greenhouse') jobs = (body.jobs || []).map(j => ({
      id: j.id, title: j.title, url: j.absolute_url, location: j.location?.name || '',
      posted: j.first_published || j.updated_at || '', dept: (j.departments || []).map(d => d.name).join(', '),
      desc: strip(j.content), detail: `https://boards-api.greenhouse.io/v1/boards/${src.slug}/jobs/${j.id}` }));
    else if (src.ats === 'lever' || src.ats === 'lever-eu') jobs = (Array.isArray(body) ? body : (body.hostedUrl ? [body] : [])).map(j => ({ // n8n splits Lever's array into one item per job
      id: j.id, title: j.text, url: j.hostedUrl, location: j.categories?.location || (j.categories?.allLocations || []).join(', '),
      posted: j.createdAt ? new Date(j.createdAt).toISOString() : '', dept: [j.categories?.team, j.categories?.department].filter(Boolean).join(', '),
      desc: '', detail: `https://api${src.ats === 'lever-eu' ? '.eu' : ''}.lever.co/v0/postings/${src.slug}/${j.id}` }));
    else if (src.ats === 'ashby') jobs = (body.jobs || []).filter(j => j.isListed !== false).map(j => ({
      id: j.id, title: j.title, url: j.jobUrl, location: [j.location, ...(j.secondaryLocations || []).map(l => l.location)].filter(Boolean).join(', ') + (j.isRemote ? ' (Remote)' : ''),
      posted: j.publishedAt || '', dept: [j.department, j.team].filter(Boolean).join(', '),
      desc: j.descriptionPlain || strip(j.descriptionHtml), detail: '' })); // Ashby has no single-posting endpoint; keep the list text
    else if (src.ats === 'comeet') jobs = (Array.isArray(body) ? body : (body.uid && body.name ? [body] : [])).map(j => ({ // n8n splits Comeet's array too
      id: j.uid, title: j.name, url: j.url_active_page, location: j.location?.name || '',
      posted: j.time_updated || '', dept: j.department || '', level: j.experience_level || '',
      desc: '', detail: `https://www.comeet.co/careers-api/2.0/company/${src.slug.split('|')[0]}/positions/${j.uid}?token=${src.slug.split('|')[1]}&details=true` }));
    okIdx.add(idx);
  } catch (e) { failIdx.add(idx); return; }

  for (const j of jobs) {
    if (!j.id || !j.title) continue;
    const loc = j.location || '';
    if (loc && !IL.test(loc) && !(REMOTE.test(loc) && !OTHER_COUNTRY.test(loc))) continue;
    out.push({ json: {
      job_id: `${src.ats}:${src.slug}:${j.id}`,
      source: 'ats', company: src.company, company_type: src.type,
      title: String(j.title).trim(), location: loc, url: j.url || '',
      posted_at: j.posted || '', department: j.dept || '', level: j.level || '',
      description: String(j.desc || '').slice(0, 4000), detail_url: j.detail || '',
    } });
  }
});

feedsOk = okIdx.size; feedsFailed = [...failIdx].filter(i => !okIdx.has(i)).length;
out.push({ json: { _meta: true, feeds_ok: feedsOk, feeds_failed: feedsFailed, jobs_in_scope: out.length } });
return out;
"""



DEDUPE_PREFILTER = r"""
// Drop jobs already in the Seen sheet, then cheap keyword screening before spending tokens on Claude.
const cfg = $('Config').first().json;
const seen = new Set($input.all().filter(i => String(i.json.tier || '').toUpperCase() !== 'ERROR').map(i => String(i.json.job_id || '').trim()).filter(Boolean));
const all = $('Fetch Workday Jobs').all().map(i => i.json); // ATS feeds passed through + Workday postings
const meta = { feeds_ok: 0, feeds_failed: 0, jobs_in_scope: 0 };
for (const m of all.filter(j => j._meta)) for (const k of Object.keys(meta)) if (m[k] != null) meta[k] += Number(m[k]);
const jobs = all.filter(j => j.job_id && j.title);

const ALLOW = /\b(gtm|go[- ]to[- ]market|sdr|bdr|sales development|business development|account (executive|manager|representative)|customer success|partnerships?|revenue|marketing|growth|sales engineer|solutions? (engineer|specialist|consultant|architect)|revops|revenue operations|sales ops|sales operations|marketing ops|marketing operations|bizops|business operations|chief of staff|founder'?s? (associate|office))\b/i; // commercial titles that may legitimately contain a NEG word ("Sales Engineer", "SDR - Security"). v6: student/junior/graduate no longer rescue a NEG title.
const SENIOR = /\b(senior|sr\.?|staff|principal|director|head|vp|vice president|chief|lead(er)?|manager|architect|expert|executive director|c[a-z]o|team lead)\b/i; // always drop, whatever the function
const NEG = /\b(engineer(ing)?|developer|programmer|devops|sre|scientist|research(er)?|designer|artist|writer|counsel|legal|attorney|recruit(er|ing)?|talent|people|hr|payroll|controller|accountant|bookkeep(er|ing)|fp&a|finops|treasury|collections?|actuar(y|ial)|underwrit(er|ing)|qa|tester|physician|nurse|driver|warehouse|technician|ux|ui|copywriter|video editor|animator|security|pentest|incident|grc|compliance|soc|threat|detection|dfir|forensics?|data platform|machine learning|ml\b|algo|algorithms?|backend|back[- ]end|frontend|front[- ]end|full[- ]?stack|embedded|firmware|hardware|asic|fpga|rtl|dsp|verification|validation|v&v|physical design|analog|silicon|chip|compiler|kernel|ios|android|operator|control center)\b/i; // drop unless ALLOW matches
const TITLE_POS = /\b(sales|sdr|bdr|business development|revenue|revops|gtm|go[- ]to[- ]market|account (executive|development|representative|manager)|customer success|partnerships?|partner|student|intern|junior|entry|graduate|analyst|operations|ops|bizops|growth|marketing|enablement|solutions?|associate|coordinator|chief of staff|strategy|founder'?s? (associate|office)|pipeline|outbound|prospecting|lead generation|demand generation|market intelligence|customer|client|onboarding|implementation)\b/i;
const DESC_POS = /\b(sdr|bdr|sales development|business development representative|revenue operations|sales operations|go[- ]to[- ]market|gtm|student position|internship|entry[- ]level|0-[12] years|no experience required|clay|apollo\.io|outbound prospecting)\b/i;
const PRIORITY = /\b(revops|revenue operations|sales ops|sales operations|marketing ops|marketing operations|bizops|business operations|gtm|go[- ]to[- ]market|chief of staff|strategy|analyst|bdr|business development|student|intern|junior|entry|graduate)\b/i; // v7: ops and analyst titles sort ahead of pure SDR

const uniq = new Map();
for (const j of jobs) {
  const id = String(j.job_id).trim();
  if (seen.has(id) || uniq.has(id)) continue;
  const t = j.title;
  if (SENIOR.test(t) && !/\b(student|intern(ship)?|junior)\b/i.test(t) && !/chief of staff/i.test(t)) continue;
  if (/^(senior|director|management|executive)/i.test(j.level || '') && !/\b(student|intern(ship)?|junior)\b/i.test(t)) continue; // Comeet experience_level
  if (NEG.test(t) && !ALLOW.test(t)) continue; // engineering/back-office titles go, even when tagged student/junior/graduate
  if (!TITLE_POS.test(t) && !DESC_POS.test((j.description || '').slice(0, 2500))) continue;
  uniq.set(id, j);
}
let cands = [...uniq.values()];
cands.sort((a, b) => (PRIORITY.test(b.title) - PRIORITY.test(a.title)) || (a.source === 'ats' ? -1 : 1));
const cap = Number(cfg.max_to_score || 0); // 0 = no cap: every net-new posting is scored the day it appears
const overflow = cap > 0 ? Math.max(0, cands.length - cap) : 0;
if (cap > 0) cands = cands.slice(0, cap);

const stats = { ...meta, seen_before: seen.size, new_after_dedupe: jobs.filter(j => !seen.has(String(j.job_id).trim())).length, sent_to_claude: cands.length, overflow };
if (cands.length === 0) return [{ json: { none: true, stats } }];
return cands.map(j => ({ json: { ...j, stats } }));
"""

MERGE_DETAILS = r"""
// Attach the full posting text (fetched per candidate) back onto each candidate. Falls back to whatever the list feed had.
const cands = $('Dedupe & Prefilter').all();
const strip = s => String(s || '')
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;|&rsquo;|&lsquo;/g, "'").replace(/&nbsp;/g, ' ')
  .replace(/<br\s*\/?>|<\/p>|<\/li>|<\/h\d>/gi, '\n').replace(/<[^>]+>/g, ' ')
  .replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
return $input.all().map((item, i) => {
  const p = item.pairedItem;
  const idx = Array.isArray(p) ? p[0]?.item : (p?.item ?? i);
  const c = { ...((cands[idx] || {}).json || {}) };
  const b = item.json || {};
  const ats = String(c.job_id || '').split(':')[0];
  let desc = '';
  try {
    if (b.error) desc = '';
    else if (ats === 'greenhouse') desc = strip(b.content);
    else if (ats === 'comeet') desc = (b.details || []).map(d => `${d.name}\n${strip(d.value)}`).join('\n');
    else if (ats === 'lever' || ats === 'lever-eu') desc = [b.descriptionPlain, ...(b.lists || []).map(l => `${l.text}\n${strip(l.content)}`), b.additionalPlain].filter(Boolean).join('\n');
    else if (ats === 'workday') { const info = b.jobPostingInfo || {}; desc = [info.jobDescription ? strip(info.jobDescription) : '', info.timeType ? `Time type: ${info.timeType}` : '', info.jobRequisitionLocation?.descriptor ? `Location: ${info.jobRequisitionLocation.descriptor}` : ''].filter(Boolean).join('\n'); }
  } catch (e) { desc = ''; }
  if (!desc) desc = c.description || '';
  delete c.detail_url;
  return { json: { ...c, description: String(desc).slice(0, 7000) } };
});
"""

PREPARE_CLAUDE = r"""
// Build the Anthropic Messages API request for each candidate posting.
const cfg = $('Config').first().json;
const SYSTEM = $('Config').first().json.system_prompt;
return $input.all().map(item => {
  const j = item.json;
  const user = [
    `COMPANY: ${j.company}${j.company_type ? ' (' + j.company_type + ')' : ''}`,
    `TITLE: ${j.title}`,
    `LOCATION: ${j.location || 'unspecified'}`,
    `DEPARTMENT: ${j.department || 'unspecified'}`,
    `SOURCE: ${j.source}`,
    `POSTED: ${j.posted_at || 'unknown'}`,
    `URL: ${j.url}`,
    '',
    'DESCRIPTION:',
    j.description || '(no description available — score on title, company and location only, and say so in gap)',
  ].join('\n');
  return { json: { ...j, body: {
    model: cfg.model || 'claude-sonnet-5',
    max_tokens: 4000,
    system: SYSTEM,
    messages: [{ role: 'user', content: user }],
  } } };
});
"""

PARSE_SCORES = r"""
// Merge Claude's JSON verdict back onto the posting it scored.
const srcs = $('Prepare Claude Request').all();
const today = new Date().toISOString().slice(0, 10);
const out = [];
$input.all().forEach((item, i) => {
  const p = item.pairedItem;
  const idx = Array.isArray(p) ? p[0]?.item : (p?.item ?? i);
  const src = { ...((srcs[idx] || {}).json || {}) };
  const stats = src.stats; delete src.body; delete src.stats;
  let verdict = null, raw = '';
  try {
    raw = (item.json.content || []).map(c => c.text || '').join('') || item.json.text || '';
    const cleaned = raw.replace(/```(?:json)?/gi, '').trim();
    const start = cleaned.indexOf('{'), end = cleaned.lastIndexOf('}');
    let body = cleaned.slice(start, end + 1);
    // Claude sometimes puts raw line breaks / tabs inside string values, which strict JSON forbids
    body = body.replace(/[\u0000-\u001f]+/g, ' ').replace(/[\u201c\u201d]/g, '"').replace(/,\s*([}\]])/g, '$1');
    verdict = JSON.parse(body);
  } catch (e) { verdict = null; }
  if (!verdict || item.json.error) {
    const diag = item.json.error?.message || item.json.error
      || (raw ? 'unparseable: ' + raw.slice(0, 200) : 'empty response: ' + JSON.stringify({ stop_reason: item.json.stop_reason, type: item.json.type, keys: Object.keys(item.json || {}) }).slice(0, 200));
    verdict = { score: 0, tier: 'ERROR', role_family: '', seniority_read: '', why_fit: '', gap: 'Scoring failed: ' + diag, angle: '', disqualifier: '' };
  }
  const score = Math.max(0, Math.min(100, Math.round(Number(verdict.score) || 0)));
  let tier = String(verdict.tier || '').toUpperCase();
  if (tier !== 'ERROR') tier = score >= 70 ? 'HOT' : score >= 50 ? 'WARM' : 'SKIP';
  out.push({ json: {
    job_id: src.job_id, first_seen: today, company: src.company, title: src.title, location: src.location,
    url: src.url, source: src.source, posted_at: src.posted_at, score, tier,
    role_family: verdict.role_family || '', seniority_read: verdict.seniority_read || '',
    why_fit: verdict.why_fit || '', gap: verdict.gap || '', angle: verdict.angle || '',
    disqualifier: verdict.disqualifier || '', status: '', _stats: stats,
  } });
});
return out;
"""

BUILD_EMAIL = r"""
// Compose the morning digest. Works for both the scored path and the "nothing new" path.
const cfg = $('Config').first().json;
const items = $input.all().map(i => i.json);
const none = items.length && items[0].none;
const stats = (items[0] && (items[0].stats || items[0]._stats)) || {};
const scored = items.filter(i => i.job_id);
const hot = scored.filter(i => i.tier === 'HOT').sort((a, b) => b.score - a.score);
const warm = scored.filter(i => i.tier === 'WARM').sort((a, b) => b.score - a.score);
const skipped = scored.filter(i => i.tier === 'SKIP').length;
const errors = scored.filter(i => i.tier === 'ERROR').length;
const date = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Asia/Jerusalem' });
const esc = s => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const card = (j, color) => `
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-left:4px solid ${color};border-radius:8px;margin:0 0 12px 0;background:#fff">
<tr><td style="padding:14px 16px;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
  <div style="font-size:16px;font-weight:600;color:#111827"><a href="${esc(j.url)}" style="color:#111827;text-decoration:none">${esc(j.title)}</a> <span style="display:inline-block;font-size:12px;font-weight:600;color:#fff;background:${color};border-radius:10px;padding:2px 8px;vertical-align:middle">${j.score}</span></div>
  <div style="font-size:13px;color:#4b5563;margin-top:2px">${esc(j.company)} · ${esc(j.location || 'location n/a')} · ${esc(j.role_family || '')}${j.seniority_read ? ' · ' + esc(j.seniority_read) : ''} · via ${esc(j.source)}</div>
  <div style="font-size:14px;color:#111827;margin-top:10px"><b>Why:</b> ${esc(j.why_fit)}</div>
  <div style="font-size:14px;color:#111827;margin-top:4px"><b>Gap:</b> ${esc(j.gap)}</div>
  ${j.angle ? `<div style="font-size:14px;color:#111827;margin-top:4px"><b>Lead with:</b> ${esc(j.angle)}</div>` : ''}
  <div style="margin-top:10px"><a href="${esc(j.url)}" style="font-size:13px;color:#2563eb">Open posting →</a></div>
</td></tr></table>`;

let body;
if (none || scored.length === 0) {
  body = `<p style="font-size:15px;color:#111827">Nothing new cleared the keyword screen today.</p>`;
} else {
  body = '';
  body += hot.length ? `<h2 style="font-size:14px;letter-spacing:.06em;text-transform:uppercase;color:#b91c1c;margin:18px 0 8px">Apply today (${hot.length})</h2>${hot.map(j => card(j, '#dc2626')).join('')}` : `<p style="font-size:14px;color:#6b7280">No HOT matches today.</p>`;
  body += warm.length ? `<h2 style="font-size:14px;letter-spacing:.06em;text-transform:uppercase;color:#b45309;margin:18px 0 8px">Worth a look (${warm.length})</h2>${warm.map(j => card(j, '#d97706')).join('')}` : '';
}

const html = `<!doctype html><html><body style="margin:0;background:#f3f4f6;padding:20px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%">
<tr><td style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;padding:0 0 12px 0">
  <div style="font-size:20px;font-weight:700;color:#111827">Job scan · ${esc(date)}</div>
  <div style="font-size:13px;color:#6b7280;margin-top:2px">${hot.length} hot · ${warm.length} warm · ${skipped} skipped${errors ? ' · ' + errors + ' scoring errors' : ''}</div>
</td></tr>
<tr><td>${body}</td></tr>
<tr><td style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;font-size:12px;color:#9ca3af;padding-top:16px;border-top:1px solid #e5e7eb">
  Scanned ${stats.feeds_ok ?? '?'} company feeds (${stats.feeds_failed ?? 0} failed) → ${stats.jobs_in_scope ?? '?'} Israel/remote postings. ${stats.new_after_dedupe ?? '?'} new since last run, ${stats.sent_to_claude ?? 0} scored${stats.overflow ? ', ' + stats.overflow + ' deferred to tomorrow (cap)' : ''}.
  Full log and tracker: <a href="https://docs.google.com/spreadsheets/d/${esc(cfg.sheet_id)}" style="color:#6b7280">Seen sheet</a>.
</td></tr>
</table></td></tr></table></body></html>`;

const subject = (hot.length ? `🔥 ${hot.length} to apply today` : warm.length ? `${warm.length} worth a look` : 'Nothing new') + ` · job scan ${new Date().toISOString().slice(0, 10)}`;
return [{ json: { subject, html, hot: hot.length, warm: warm.length } }];
"""

# ------------------------------------------------------------------- helpers
def node(name, type_, version, params, pos, **extra):
    n = {"parameters": params, "id": name.lower().replace(' ', '-').replace('?', ''), "name": name,
         "type": type_, "typeVersion": version, "position": pos}
    n.update(extra)
    return n

def sheets(name, op, sheet, pos, extra=None):
    p = {
        "operation": op,
        "documentId": {"__rl": True, "mode": "id", "value": "={{ $('Config').first().json.sheet_id }}"},
        "sheetName": {"__rl": True, "mode": "name", "value": sheet},
        "options": {},
    }
    if extra: p.update(extra)
    return node(name, "n8n-nodes-base.googleSheets", 4.5, p, pos,
                credentials={"googleSheetsOAuth2Api": {"id": "REPLACE_ME", "name": "Google Sheets account"}})

def code(name, js, pos, **extra):
    return node(name, "n8n-nodes-base.code", 2, {"jsCode": js.strip()}, pos, **extra)

CONFIG_FIELDS = [
    ("sheet_id", "string", "PASTE_GOOGLE_SHEET_ID_HERE"),
    ("email_to", "string", "you@example.com"),
    ("model", "string", "claude-sonnet-5"),
    ("max_to_score", "number", 0),
    ("system_prompt", "string", SYSTEM_PROMPT),
]

nodes = [
    node("Every morning", "n8n-nodes-base.scheduleTrigger", 1.2,
         {"rule": {"interval": [{"field": "cronExpression", "expression": "30 7 * * *"}]}}, [-1200, 300]),
    node("Config", "n8n-nodes-base.set", 3.4,
         {"assignments": {"assignments": [
             {"id": f"cfg-{i}", "name": k, "type": t, "value": v} for i, (k, t, v) in enumerate(CONFIG_FIELDS)]},
          "options": {}}, [-980, 300]),
    sheets("Get Companies", "read", "Companies", [-760, 160]),
    code("Build Feed URLs", BUILD_FEED_URLS, [-540, 160]),
    node("Fetch Feed", "n8n-nodes-base.httpRequest", 4.2,
         {"url": "={{ $json.url }}", "options": {"batching": {"batch": {"batchSize": 6, "batchInterval": 300}},
                                                  "timeout": 30000, "response": {"response": {"responseFormat": "json"}}}},
         [-320, 160], onError="continueRegularOutput"),
    node("Tag Feed Items", "n8n-nodes-base.code", 2, {"mode": "runOnceForEachItem", "jsCode": TAG_FEED.strip()}, [-100, 160]),
    code("Normalize ATS Jobs", NORMALIZE_ATS, [120, 160], alwaysOutputData=True),
    code("Fetch Workday Jobs", FETCH_WORKDAY, [220, 160],
         notes="Workday boards are POST-only and paginate 20 at a time, so they cannot use the shared Fetch Feed node. "
               "This node queries each Workday tenant with its Israel location facet applied, emits normalized job items, "
               "and passes the ATS items through."),
    sheets("Get Seen", "read", "Seen", [340, 300]),
    code("Dedupe & Prefilter", DEDUPE_PREFILTER, [560, 300]),
    node("Any candidates?", "n8n-nodes-base.if", 2.2,
         {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                         "conditions": [{"id": "c1", "leftValue": "={{ $json.none === true }}", "rightValue": "", "operator": {"type": "boolean", "operation": "false", "singleValue": True}}],
                         "combinator": "and"}, "options": {}}, [780, 300]),
    node("Fetch Details", "n8n-nodes-base.httpRequest", 4.2,
         {"url": "={{ $json.detail_url || $json.url }}", "options": {"batching": {"batch": {"batchSize": 6, "batchInterval": 300}},
                                                  "timeout": 30000, "response": {"response": {"responseFormat": "json"}}}},
         [1000, 160], onError="continueRegularOutput"),
    code("Merge Details", MERGE_DETAILS, [1200, 160]),
    code("Prepare Claude Request", PREPARE_CLAUDE, [1400, 160]),
    node("Score with Claude", "n8n-nodes-base.httpRequest", 4.2,
         {"method": "POST", "url": "https://api.anthropic.com/v1/messages",
          "authentication": "predefinedCredentialType", "nodeCredentialType": "anthropicApi",
          "sendHeaders": True, "headerParameters": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"}]},
          "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}",
          "options": {"batching": {"batch": {"batchSize": 3, "batchInterval": 600}}, "timeout": 120000,
                      "response": {"response": {"responseFormat": "json"}}}},
         [1220, 160], onError="continueRegularOutput",
         credentials={"anthropicApi": {"id": "REPLACE_ME", "name": "Anthropic account"}}),
    code("Parse Scores", PARSE_SCORES, [1440, 160]),
    sheets("Append to Seen", "append", "Seen", [1660, 160],
           {"columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []}}),
    code("Build Email", BUILD_EMAIL, [1900, 300]),
    node("Send Digest", "n8n-nodes-base.gmail", 2.1,
         {"sendTo": "={{ $('Config').first().json.email_to }}", "subject": "={{ $json.subject }}",
          "emailType": "html", "message": "={{ $json.html }}", "options": {"appendAttribution": False}},
         [2120, 300], credentials={"gmailOAuth2": {"id": "REPLACE_ME", "name": "Gmail account"}}),
]

# Get Seen: run once, and still emit an item when the sheet is empty
for n in nodes:
    if n["name"] == "Get Seen":
        n["executeOnce"] = True; n["alwaysOutputData"] = True
    if n["name"] == "Append to Seen":
        n["alwaysOutputData"] = True

def conn(a, b, out=0, inp=0):
    return (a, {"node": b, "type": "main", "index": inp}, out)

edges = [
    conn("Every morning", "Config"),
    conn("Config", "Get Companies"),
    conn("Get Companies", "Build Feed URLs"), conn("Build Feed URLs", "Fetch Feed"), conn("Fetch Feed", "Tag Feed Items"), conn("Tag Feed Items", "Normalize ATS Jobs"),
    conn("Normalize ATS Jobs", "Fetch Workday Jobs"), conn("Fetch Workday Jobs", "Get Seen"), conn("Get Seen", "Dedupe & Prefilter"), conn("Dedupe & Prefilter", "Any candidates?"),
    conn("Any candidates?", "Fetch Details", 0), conn("Any candidates?", "Build Email", 1),
    conn("Fetch Details", "Merge Details"), conn("Merge Details", "Prepare Claude Request"),
    conn("Prepare Claude Request", "Score with Claude"), conn("Score with Claude", "Parse Scores"),
    conn("Parse Scores", "Append to Seen"), conn("Append to Seen", "Build Email"),
    conn("Build Email", "Send Digest"),
]
connections = {}
for a, target, out in edges:
    c = connections.setdefault(a, {"main": []})
    while len(c["main"]) <= out: c["main"].append([])
    c["main"][out].append(target)

wf = {
    "name": "Roy — Morning Job Scan",
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1", "timezone": "Asia/Jerusalem", "saveExecutionProgress": True},
    "meta": {"instanceId": "roy-job-scan"},
    "pinData": {},
}
# The generator emits a SANITISED template (placeholder sheet id and credential ids).
# The real export, with Roy's sheet id and n8n credential ids, is ../roy-job-scanner.n8n.json
# and is written by hand from the live workflow. Never point this at the real export.
out = HERE.parent / "workflow" / "job-scanner.workflow.json"
out.write_text(json.dumps(wf, indent=2, ensure_ascii=False))
print(f"wrote {out} ({out.stat().st_size} bytes, {len(nodes)} nodes)")
