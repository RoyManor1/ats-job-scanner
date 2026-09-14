// Workday tenants: POST-only JSON API, 20 results per page, Israel applied as a location facet.
// slug format in the Companies tab: tenant|datacenter|site|facetKey|facetId
// Emits normalized job items for Workday, then passes the ATS items from Normalize straight through.
const helpers = this.helpers;
const passthrough = $input.all();
const MAX_PAGES = 25; // 500 postings per employer; NVIDIA is the largest at ~423

let companies = [];
try {
  companies = $('Get Companies').all().map(i => i.json).filter(c => {
    const active = String(c.active ?? 'yes').trim().toLowerCase();
    return String(c.ats || '').trim().toLowerCase() === 'workday' && !['no', 'false', '0', 'off'].includes(active);
  });
} catch (e) { companies = []; }

const strip = s => String(s || '')
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;|&rsquo;|&lsquo;/g, "'").replace(/&nbsp;/g, ' ')
  .replace(/<br\s*\/?>|<\/p>|<\/li>|<\/h\d>/gi, '\n').replace(/<[^>]+>/g, ' ')
  .replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();

const post = (url, body) => helpers.httpRequest({ url, method: 'POST', json: true, body, timeout: 20000,
  headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36', 'Content-Type': 'application/json', 'Accept': 'application/json', 'Accept-Language': 'en-US' } });

const jobs = [];
let ok = 0, failed = 0;
const capped = [];

async function one(c) {
  const parts = String(c.slug || '').split('|');
  const [tenant, dc, site, facetKey, facetId] = parts;
  if (!tenant || !dc || !site || !facetKey || !facetId) { failed++; return; }
  const api = `https://${tenant}.${dc}.myworkdayjobs.com/wday/cxs/${tenant}/${site}`;
  const ui = `https://${tenant}.${dc}.myworkdayjobs.com/en-US/${site}`;
  let got = 0, total = null, page = 0;
  try {
    while (page < MAX_PAGES) {
      const r = await post(`${api}/jobs`, { appliedFacets: { [facetKey]: [facetId] }, limit: 20, offset: page * 20, searchText: '' });
      const batch = r.jobPostings || [];
      if (total === null) total = r.total ?? null;
      for (const j of batch) {
        const path = j.externalPath || '';
        const id = (Array.isArray(j.bulletFields) && j.bulletFields[0]) || path.split('/').pop() || path;
        if (!id || !j.title) continue;
        const rawLoc = String(j.locationsText || '').trim();
        // every row here is already Israel-faceted, so make that explicit for the location filter downstream
        const location = /israel/i.test(rawLoc) ? rawLoc : (rawLoc ? `${rawLoc} (Israel)` : 'Israel');
        jobs.push({
          job_id: `workday:${tenant}|${dc}|${site}:${id}`,
          source: 'ats', company: c.company || tenant, company_type: c.type || '',
          title: String(j.title).trim(), location, url: path ? `${ui}${path}` : ui,
          posted_at: '', department: '', level: '',
          description: '', detail_url: path ? `${api}${path}` : '',
        });
      }
      got += batch.length;
      page++;
      if (batch.length < 20 || (total !== null && got >= total)) break;
    }
    if (page >= MAX_PAGES && total !== null && got < total) capped.push(`${c.company}:${got}/${total}`);
    ok++;
  } catch (e) { failed++; }
}

let i = 0;
async function worker() { while (i < companies.length) await one(companies[i++]); }
await Promise.all(Array.from({ length: Math.min(3, Math.max(1, companies.length)) }, () => worker()));

const extra = [...jobs.map(j => ({ json: j })), { json: { _meta: true, feeds_ok: ok, feeds_failed: failed, jobs_in_scope: jobs.length, workday_capped: capped.join(', ') } }];
return [...passthrough, ...extra];
