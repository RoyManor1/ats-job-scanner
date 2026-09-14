// Emulates the n8n Code-node runtime just enough to exercise every jsCode block in the workflow.
const fs = require('fs');
const wf = JSON.parse(fs.readFileSync(__dirname + '/../workflow/job-scanner.workflow.json', 'utf8'));
const code = name => wf.nodes.find(n => n.name === name).parameters.jsCode;
const outputs = {}; // node name -> array of items

function run(name, inputItems) {
  const $input = { all: () => inputItems, first: () => inputItems[0] };
  const $ = n => ({ all: () => outputs[n] || [], first: () => (outputs[n] || [])[0], item: undefined });
  const fn = new Function('$input', '$', '$json', `return (async () => { ${code(name)} })();`);
  return fn($input, $, inputItems[0]?.json).then(res => { outputs[name] = res; return res; });
}
const items = arr => arr.map((json, i) => ({ json, pairedItem: { item: i } }));

// ---- fixtures (field names verified live against Greenhouse / Lever / Ashby on 2026-09-07)
const GH = { jobs: [
  { id: 7556263, title: 'Sales Development Representative', absolute_url: 'https://job-boards.greenhouse.io/similarweb/jobs/7556263', location: { name: 'Tel Aviv-Yafo' }, first_published: '2026-09-06T04:51:31-05:00', updated_at: '2026-09-06T09:34:14-04:00', departments: [{ name: 'Sales' }], content: '&lt;p&gt;We are looking for an &lt;strong&gt;SDR&lt;/strong&gt; to join our Tel Aviv team.&amp;nbsp;&lt;/p&gt;&lt;ul&gt;&lt;li&gt;0-2 years experience&lt;/li&gt;&lt;li&gt;Native English&lt;/li&gt;&lt;/ul&gt;' },
  { id: 1, title: 'Senior Backend Engineer', absolute_url: 'https://x/1', location: { name: 'Tel Aviv-Yafo' }, first_published: '', updated_at: '', departments: [{ name: 'R&D' }], content: 'Go, Kubernetes' },
  { id: 2, title: 'Account Executive', absolute_url: 'https://x/2', location: { name: 'New York' }, first_published: '', updated_at: '', departments: [], content: 'sales' },
  { id: 3, title: 'Marketing Coordinator', absolute_url: 'https://x/3', location: { name: 'Remote' }, first_published: '', updated_at: '', departments: [], content: 'marketing ops hubspot' },
] };
const LV = [
  { id: 'abc', text: 'Business Development Representative - German speaking', hostedUrl: 'https://jobs.lever.co/walkme/abc', categories: { commitment: 'Full-time', department: 'Sales', location: 'Tel Aviv', team: 'SDR', allLocations: ['Tel Aviv'] }, createdAt: 1779974249905, workplaceType: 'hybrid', descriptionPlain: 'Join our BDR team.', lists: [{ text: 'Requirements', content: '<li>Fluent German</li><li>1 year SDR</li>' }], additionalPlain: 'Benefits' },
  { id: 'def', text: 'Revenue Operations Analyst', hostedUrl: 'https://jobs.lever.co/walkme/def', categories: { location: 'Tel Aviv', allLocations: ['Tel Aviv'] }, createdAt: 1779974249905, descriptionPlain: 'Own Salesforce reporting and pipeline hygiene.', lists: [], additionalPlain: '' },
];
const AB = { jobs: [
  { id: '9a61', title: 'BizOps Senior Lead', jobUrl: 'https://jobs.ashbyhq.com/lemonade/9a61', location: 'TLV', secondaryLocations: [], department: 'Ops', team: 'BizOps', employmentType: 'FullTime', publishedAt: '2026-09-01T00:00:00Z', isRemote: false, isListed: true, descriptionPlain: 'Lead bizops.' },
  { id: '9a62', title: 'Student Position - Sales Operations', jobUrl: 'https://jobs.ashbyhq.com/lemonade/9a62', location: 'TLV', secondaryLocations: [], department: 'Sales', team: 'Sales Ops', employmentType: 'PartTime', publishedAt: '2026-09-06T00:00:00Z', isRemote: false, isListed: true, descriptionPlain: 'Part-time student position supporting the sales ops team. Excel, HubSpot, Clay.' },
] };
const LINKEDIN = [
  { id: '4123456789', title: 'Sales Development Representative (SDR)', companyName: 'Monday.com', location: 'Tel Aviv-Yafo, Tel Aviv District, Israel', link: 'https://www.linkedin.com/jobs/view/sales-development-representative-at-monday-com-4123456789?refId=x', postedAt: '2026-09-06', descriptionText: 'We are hiring an SDR. English native. 0-1 years.' },
  { id: '4123456790', title: 'VP Sales', companyName: 'X', location: 'Israel', link: 'https://www.linkedin.com/jobs/view/4123456790', descriptionText: 'vp' },
];
const CLAUDE_OK = { id: 'msg', content: [{ type: 'text', text: '```json\n{"score": 82, "tier": "HOT", "role_family": "SDR/BDR", "seniority_read": "junior/entry", "why_fit": "SDR seat at an international company; Charm outreach is direct evidence.", "gap": "No formal outbound track record.", "angle": "Lead with the Charm cold email that got a CEO reply in 10 hours.", "disqualifier": ""}\n```' }] };
const CLAUDE_SKIP = { content: [{ type: 'text', text: '{"score": 0, "tier": "SKIP", "role_family": "SDR/BDR", "seniority_read": "junior/entry", "why_fit": "", "gap": "Requires German.", "angle": "", "disqualifier": "4: German-speaking role"}' }] };
const CLAUDE_ERR = { error: { type: 'overloaded_error', message: 'Overloaded' } };

(async () => {
  outputs['Config'] = items([{ sheet_id: 'SHEET', email_to: 'roy@example.com', model: 'claude-sonnet-5', max_to_score: 0,
    linkedin_keywords: 'Sales Development Representative, GTM Engineer', linkedin_location: 'Israel', linkedin_date_posted: 'past24Hours', linkedin_limit_per_search: 40, system_prompt: 'SYSTEM PROMPT' }]);

  const companies = items([
    { company: 'Similarweb', ats: 'greenhouse', slug: 'similarweb', type: 'Israeli scale-up', active: 'yes' },
    { company: 'WalkMe', ats: 'lever', slug: 'walkme', type: 'Israeli scale-up', active: 'yes' },
    { company: 'Lemonade', ats: 'ashby', slug: 'lemonade', type: 'Israeli scale-up', active: '' },
    { company: 'Dead Co', ats: 'greenhouse', slug: 'deadco', type: '', active: 'yes' },
    { company: 'Off Co', ats: 'greenhouse', slug: 'offco', type: '', active: 'no' },
  ]);
  const urls = await run('Build Feed URLs', companies);
  console.log('Build Feed URLs →', urls.length, 'feeds;', urls.map(u => u.json.ats).join(','));
  if (urls.length !== 4) throw new Error('expected 4 feed urls');

  // Simulate HTTP node: same order, pairedItem to input index, one failure
  const httpOut = [GH, LV, AB, { error: { message: '404' } }].map((json, i) => ({ json, pairedItem: { item: i } }));
  const tag = (items) => items.map(it => ({ json: { src: outputs['Build Feed URLs'][it.pairedItem.item]?.json || {}, body: it.json }, pairedItem: it.pairedItem }));
  const ats = await run('Normalize ATS Jobs', tag(httpOut));
  const atsJobs = ats.filter(i => i.json.job_id);
  console.log('Normalize ATS →', atsJobs.length, 'jobs in scope;', JSON.stringify(ats.at(-1).json));
  console.log('   ', atsJobs.map(j => `${j.json.job_id} | ${j.json.title} | ${j.json.location}`).join('\n    '));
  const gh = atsJobs.find(j => j.json.job_id === 'greenhouse:similarweb:7556263').json;
  if (!/boards-api.greenhouse.io\/v1\/boards\/similarweb\/jobs\/7556263$/.test(gh.detail_url)) throw new Error('GH detail_url wrong: ' + gh.detail_url);
  if (atsJobs.some(j => j.json.location === 'New York')) throw new Error('NY job leaked through');
  const lv = atsJobs.find(j => j.json.job_id === 'lever:walkme:abc').json;
  if (!/api.lever.co\/v0\/postings\/walkme\/abc$/.test(lv.detail_url)) throw new Error('Lever detail_url wrong: ' + lv.detail_url);
  // Comeet fixture: n8n splits the array → one item per position
  outputs['Build Feed URLs'].push({ json: { company: 'Windward', ats: 'comeet', slug: '31.002|TOKEN', url: 'x', type: '' }, pairedItem: { item: 4 } });
  const cm = await run('Normalize ATS Jobs', tag([...httpOut, { json: { uid: 'P1', name: 'Sales Development Representative', url_active_page: 'https://www.comeet.com/jobs/windward/31.002/p1', location: { name: 'Tel Aviv' }, time_updated: '2026-09-01', department: 'Sales', experience_level: 'Entry-level' }, pairedItem: { item: 4 } }, { json: { uid: 'P2', name: 'Account Manager', url_active_page: 'u', location: { name: 'Tel Aviv' }, experience_level: 'Senior' }, pairedItem: { item: 4 } }]));
  const cmj = cm.find(j => j.json.job_id === 'comeet:31.002|TOKEN:P1');
  if (!cmj || cmj.json.detail_url !== 'https://www.comeet.co/careers-api/2.0/company/31.002/positions/P1?token=TOKEN&details=true') throw new Error('Comeet detail_url wrong: ' + JSON.stringify(cmj && cmj.json));
  if (cm.at(-1).json.feeds_ok !== 4) throw new Error('feeds_ok should be 4 (comeet counted once): ' + JSON.stringify(cm.at(-1).json));
  outputs['Normalize ATS Jobs'] = cm; outputs['Fetch Workday Jobs'] = cm; ats.length = 0; ats.push(...cm);

  const searches = [{json:{}}];

  const li = [];



  outputs['Normalize ATS Jobs'] = [...ats, ...li];
  // v8: Dedupe reads the Workday node, which passes ATS items through and appends Workday postings
  const workdayJob = { json: { job_id: 'workday:kla|wd1|Search:JR9001', source: 'ats', company: 'KLA', company_type: 'International tech (Israel office)', title: 'Operations Administrative Student', location: "Migdal Ha'emek, Israel", url: 'https://kla.wd1.myworkdayjobs.com/en-US/Search/job/x', posted_at: '', department: '', level: '', description: '', detail_url: 'https://kla.wd1.myworkdayjobs.com/wday/cxs/kla/Search/job/x' } };
  outputs['Fetch Workday Jobs'] = [...ats, ...li, workdayJob, { json: { _meta: true, feeds_ok: 1, feeds_failed: 0, jobs_in_scope: 1 } }];
  // Seen sheet: one previously-seen id; simulate empty sheet too
  const seenRows = items([{ job_id: 'lever:walkme:def', tier: 'WARM' }]);
  const cands = await run('Dedupe & Prefilter', seenRows);
  console.log('Dedupe & Prefilter →', cands.map(c => c.json.title || 'NONE').join(' | '));
  console.log('    stats:', JSON.stringify(cands[0].json.stats));
  const titles = cands.map(c => c.json.title);
  if (titles.includes('Senior Backend Engineer')) throw new Error('senior engineer leaked');
  if (titles.includes('VP Sales')) throw new Error('VP leaked');
  if (titles.includes('BizOps Senior Lead')) throw new Error('senior lead leaked');
  if (titles.includes('Revenue Operations Analyst')) throw new Error('seen job not deduped');
  if (titles.includes('Account Manager')) throw new Error('Comeet Senior level leaked');
  if (!titles.includes('Sales Development Representative')) throw new Error('Comeet SDR dropped');
  if (!titles.includes('Student Position - Sales Operations')) throw new Error('student role dropped');
  if (!titles.includes('Operations Administrative Student')) throw new Error('Workday posting dropped');
  if (!/SDR|Student|Business Development|Operations|Analyst|BizOps|GTM/i.test(titles[0])) throw new Error('priority sort wrong: ' + titles[0]);

  const empty = await run('Dedupe & Prefilter', items([{}]));
  if (empty.length !== cands.length + 1) throw new Error('empty seen sheet should add back the previously-seen job: ' + empty.length);
  outputs['Normalize ATS Jobs'] = [{ json: { _meta: true, feeds_ok: 0, feeds_failed: 4, jobs_in_scope: 0 } }];
  outputs['Fetch Workday Jobs'] = [{ json: { _meta: true, feeds_ok: 0, feeds_failed: 4, jobs_in_scope: 0 } }];
  const none = await run('Dedupe & Prefilter', items([{}]));
  if (!(none.length === 1 && none[0].json.none === true)) throw new Error('none path broken');
  console.log('    none path OK:', JSON.stringify(none[0].json.stats));
  outputs['Dedupe & Prefilter'] = cands;

  // Fetch Details (HTTP) simulated: GH single job, comeet single position w/ details, lever single posting, ashby page → error
  const detOut = cands.map((c, i) => { const a = c.json.job_id.split(':')[0]; const j = a === 'greenhouse' ? { id: 7556263, content: '&lt;p&gt;We are looking for an &lt;strong&gt;SDR&lt;/strong&gt; to join our Tel Aviv team.&lt;/p&gt;' } : a === 'comeet' ? { uid: 'P1', details: [{ name: 'Description', value: '<p>Hunt outbound. 0-1 years.</p>' }] } : a === 'lever' ? { id: 'abc', descriptionPlain: 'Join our BDR team.', lists: [{ text: 'Requirements', content: '<li>Fluent German</li>' }] } : { error: { message: 'not json' } }; return { json: j, pairedItem: { item: i } }; });
  const merged = await run('Merge Details', detOut);
  console.log('Merge Details →', merged.map(m => `${m.json.title}: ${(m.json.description || '').slice(0, 40).replace(/\n/g, ' ')}`).join(' | '));
  const mg = merged.find(m => m.json.job_id.startsWith('greenhouse:')); if (mg && (!/SDR to join our Tel Aviv team/.test(mg.description || mg.json.description) || /&lt;|<p>/.test(mg.json.description))) throw new Error('GH content not decoded: ' + mg.json.description);
  const ml = merged.find(m => m.json.job_id.startsWith('lever:')); if (ml && !/Fluent German/.test(ml.json.description)) throw new Error('Lever lists not merged');
  const ma = merged.find(m => m.json.job_id.startsWith('ashby:')); if (ma && !/student position/i.test(ma.json.description)) throw new Error('Ashby fallback description lost');
  const mc = merged.find(m => m.json.job_id.startsWith('comeet:')); if (!mc || !/Hunt outbound/.test(mc.json.description)) throw new Error('Comeet details not merged');
  if (merged.some(m => 'detail_url' in m.json)) throw new Error('detail_url should be dropped');
  if (!merged[0].json.stats) throw new Error('stats lost in merge');
  outputs['Merge Details'] = merged;
  const reqs = await run('Prepare Claude Request', merged);
  console.log('Prepare Claude →', reqs.length, 'requests; model', reqs[0].json.body.model, '; user msg starts:', JSON.stringify(reqs[0].json.body.messages[0].content.slice(0, 60)));
  if (reqs[0].json.body.system !== 'SYSTEM PROMPT') throw new Error('system prompt not injected');

  const claudeOut = reqs.map((r, i) => ({ json: i === 0 ? CLAUDE_OK : i === 1 ? CLAUDE_SKIP : i === 2 ? CLAUDE_ERR : CLAUDE_OK, pairedItem: { item: i } }));
  const parsed = await run('Parse Scores', claudeOut);
  console.log('Parse Scores →', parsed.map(p => `${p.json.tier}:${p.json.score} ${p.json.title}`).join(' | '));
  if (parsed[0].json.tier !== 'HOT' || parsed[0].json.score !== 82) throw new Error('HOT parse failed');
  if (parsed[1].json.tier !== 'SKIP') throw new Error('SKIP parse failed');
  if (parsed[2] && parsed[2].json.tier !== 'ERROR') throw new Error('error path failed');
  if (parsed[0].json.company !== cands[0].json.company) throw new Error('pairedItem mapping wrong');
  const cols = Object.keys(parsed[0].json).filter(k => !k.startsWith('_'));
  console.log('    Seen columns:', cols.join(','));

  const mail = await run('Build Email', parsed);
  console.log('Build Email →', mail[0].json.subject, '| html', mail[0].json.html.length, 'chars');
  fs.writeFileSync(__dirname + '/../docs/sample-digest.html', mail[0].json.html);
  const mailNone = await run('Build Email', none);
  console.log('Build Email (none) →', mailNone[0].json.subject);
  if (!/Nothing new/.test(mailNone[0].json.subject)) throw new Error('none email wrong');
  console.log('\nALL CODE NODES PASS');
})().catch(e => { console.error('FAIL:', e); process.exit(1); });
