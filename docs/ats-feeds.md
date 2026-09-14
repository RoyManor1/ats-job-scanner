# Reading applicant-tracking systems directly

Working notes from building a scanner over five ATS platforms. Everything here is a
public, unauthenticated endpoint that the employer already serves to render its own
careers page. No login, no scraping, no browser automation.

The general shape: find the employer's board slug, hit a list endpoint for every open
role, then hit a detail endpoint only for the roles you actually care about. Fetching
descriptions for everything up front is the single easiest way to blow up your memory
limit.

## Greenhouse

```
list    GET https://boards-api.greenhouse.io/v1/boards/<slug>/jobs
detail  GET https://boards-api.greenhouse.io/v1/boards/<slug>/jobs/<id>
```

The easiest of the five. `?content=true` on the list endpoint returns every description
in one response, which is tempting and is the trap mentioned above. Use the detail
endpoint instead.

Finding the slug: look for `boards.greenhouse.io/<slug>`, `job-boards.greenhouse.io/<slug>`,
or a `?gh_jid=` link in the careers page source. The slug is often not the company name
(Box is `boxinc`, Navan is `tripactions`, Weka is `wekatest`), so guessing it from the
company name fails about a third of the time.

There is a separate EU host, `boards-api.eu.greenhouse.io`, for employers on EU data
residency. The same slug on the wrong host returns 404.

## Lever

```
list    GET https://api.lever.co/v0/postings/<slug>?mode=json
detail  GET https://api.lever.co/v0/postings/<slug>/<id>
```

Returns a bare JSON array rather than an object. In n8n that array is split into one item
per job, which quietly destroys your association between a job and the employer it came
from, because a Code node in "all items" mode cannot read `pairedItem`. Stamp the source
onto each item with a run-per-item node before doing anything else.

Lever also has an EU host, `api.eu.lever.co`. Mobileye is on it. Same slug, different host.

## Ashby

```
list  GET https://api.ashbyhq.com/posting-api/job-board/<slug>
```

The list response already contains `descriptionPlain`, and there is no per-posting
endpoint, so this is a single-request platform. Respect `isListed`: entries where it is
false are drafts or internal roles and should be skipped. Slugs are case-sensitive in
practice for some boards.

## Comeet

Very common among Israeli employers and the most awkward of the five.

```
list    GET https://www.comeet.co/careers-api/2.0/company/<uid>/positions?token=<token>
detail  GET https://www.comeet.co/careers-api/2.0/company/<uid>/positions/<pos>?token=<token>&details=true
```

Both `uid` and `token` are public values embedded in the employer's own careers page.
Read them out of the page source: the uid looks like `4F.00B` and the token is a long
hex string. They also appear together inside any `careers-api/2.0/company/.../positions?token=`
URL on the page, which is the more reliable thing to match on.

Three things to know.

**Tokens rotate.** A board that worked yesterday starts returning HTTP 400. That is not a
dead company, it is a stale token, and the fix is to re-scrape the careers page. Any
long-lived scanner needs to tell "rotated token" apart from "board has no open roles"
apart from "slug is dead", because the remedies are completely different.

**A grep that stops early truncates the token.** One of ours captured 33 of 39 hex
characters and worked for a day before failing, which was maddening to diagnose. Match
greedily on `[A-F0-9]{20,}` and verify the token by calling the endpoint before storing it.

**Comeet has been rebranded Spark Hire Recruit.** Deactivated accounts return a friendly
HTML page rather than an error, so check for the word "deactivated" in the body.

Like Lever, the list response is a bare array.

## Workday

The one people assume is unscrapeable. It is not, but it is POST-only and the pagination
is booby-trapped.

```
list    POST https://<tenant>.<dc>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs
        body: {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
detail  GET  https://<tenant>.<dc>.myworkdayjobs.com/wday/cxs/<tenant>/<site><externalPath>
```

Three coordinates identify a board: the tenant (`nvidia`), the data centre (`wd1`, `wd3`,
`wd5`, `wd12`) and the site name (`NVIDIAExternalCareerSite`). All three are visible in
the careers page URL. Site names are not guessable; tenants publish things like
`External`, `Search`, `Cisco_Careers`, `jobs-and-careers` and `External_Career_Site`.

**`limit` above 20 returns zero rows with HTTP 200 and no error.** Not a truncated page,
an empty one. Page with `offset` in steps of 20 and stop when `total` is reached.

**Filter server-side with facets.** A first request with `appliedFacets: {}` returns a
`facets` array describing every filter the board offers. Find the value whose `descriptor`
is your country and re-query with `appliedFacets: {<facetParameter>: [<id>]}`. This turns
"paginate through 2,000 postings to find 60" into three requests. Two shapes exist in
the wild: a flat `Country` group, where the country id is a Workday-global constant
shared across tenants, and a nested `locationHierarchy1` group, where the id is
per-tenant and you have to walk the nested `values` arrays to find it.

Some tenants expose neither and return only `locationMainGroup`. Those need the facet ids
read out of the careers site HTML instead, which is not implemented here.

The detail endpoint is a plain GET, so it can share a normal HTTP node with the other
four platforms. The description lands in `jobPostingInfo.jobDescription` as HTML.

Also note `postedOn` is a localised sentence like "Posted Today", not a date. Send
`Accept-Language: en-US` and take real dates from the detail endpoint's `startDate`.

## Platforms not covered here

SuccessFactors, Taleo, Jobvite, Eightfold, BambooHR, Workable, SmartRecruiters, Teamtailor
and JazzHR all appear among Israeli employers. BambooHR, Workable and SmartRecruiters have
straightforward public JSON endpoints and would be cheap to add. Taleo and SuccessFactors
are painful. Several large employers run bespoke careers sites with no machine-readable
feed at all, and the honest answer there is that they are out of scope.

`israeli-tech-ats-directory.tsv` in this folder records which platform each employer was
using when it was checked.
