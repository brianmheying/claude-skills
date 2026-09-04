# claude-skills

A personal library of reusable [Claude Skills](https://www.anthropic.com/news/skills) — packaged instructions that give Claude a specific, repeatable way to approach a task.

Each Skill lives in its own folder with a `Skill.md` (the skill definition Claude reads) and a `README.md` (a human-readable explanation of what it does and when to use it).

## Catalog

### Critique & review

Skills that blind-read a finished artifact from a specific adversarial perspective and report what holds up, without editing the work.

| Skill | What it does |
|---|---|
| [`audience-committee`](critique-and-review/audience-committee) | Adjudicates an artifact across peer, potential-client, and hiring-manager perspectives at once, and reports what survives all three |
| [`peer-reader`](critique-and-review/peer-reader) | Reads as a sophisticated practitioner peer, testing rigor and distinctiveness |
| [`potential-client-reader`](critique-and-review/potential-client-reader) | Reads as a skeptical potential client, testing commercial trust and buying demand |
| [`hiring-manager-reader`](critique-and-review/hiring-manager-reader) | Reads as a hiring manager, testing operating signal and execution credibility |
| [`plain-language-interpreter`](critique-and-review/plain-language-interpreter) | Rewrites dense or academic writing into plain language without losing analytical depth |

### Job search writing

Skills for diagnosing a job description and building the case for a specific candidate.

| Skill | What it does |
|---|---|
| [`jd-five-problems`](job-search-writing/jd-five-problems) | Diagnoses the 3–5 underlying business problems a role exists to solve |
| [`cover-letter-architect`](job-search-writing/cover-letter-architect) | Architects a differentiated, company-specific cover letter argument |
| [`resume-adjudicator`](job-search-writing/resume-adjudicator) | Adjudicates a near-final tailored resume: ship, revise, or reopen |

## Using a Skill

Copy the Skill's folder (or just its `Skill.md`) into wherever your Claude setup loads Skills from, keeping the folder name and `Skill.md` filename as-is.
