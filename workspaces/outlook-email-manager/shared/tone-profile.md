# Tone Profile

This file is populated by the one-time tone-profile setup (`tone-profile/CONTEXT.md`). Run `learn my tone` before your first `02-draft-replies` run.

Derived from a sample of 100 sent emails (Sent folder, most recent ~7 months, mixed Hebrew/English). Hebrew and English are both first-class in this mailbox -- match the language of the email being replied to.

## Greeting/Sign-off Patterns

- **Hebrew, time-of-day greeting is the default opener** when addressing someone directly: "בוקר אור" (good morning, casual/light variant of "בוקר טוב") is the most frequent one, e.g. "בוקר אור, תודה רבה." / "בוקר אור אשמח להתעדכן איפה הדברים עומדים." Afternoon uses "צהריים טובים" or the abbreviated "אח\"צ טובים".
- **Name-first greeting** is common when the thread is more personal or after some back-and-forth: "היי רוני", "היי שחר בוקר אור", "מה נשמע רוני", "מה נשמע חיים".
- **Quick replies inside an active thread skip the greeting entirely** and open directly with the answer/content, e.g. "אמת, שלחתי לראות אם הם מסתדרים עם זה", "זמין עכשיו", "שלילי". This is the norm, not the exception, once a thread is a few messages deep.
- **English-language technical emails almost always skip the greeting** and open directly with the finding or the ask, e.g. the Cloudflare Turnstile debugging replies open with "Source-level guard —", the Carousel bug report opens with the Jira link then "What's breaking the interior gallery carousel". Exception: a broadcast/announcement email to a broader audience opens with "Hi Firas,".
- **Sign-off is almost always "תודה" / "תודה רבה" / "תודה!"** as the last line before the signature, sometimes with an exclamation or a 🙂. Many short technical replies have no sign-off line at all -- the message just ends and the signature block follows.
- Signature block is fixed/automatic (name, title, phone, email) and not a tone signal -- don't treat it as something to vary.

## Structure & Length Tendencies

- **Default length is short**: most replies are 1-4 sentences. Status updates, confirmations, and quick answers ("תודה רבה, שבוע מעולה 🙂", "מוזר אתמול במשרדים זה לא עבד\nעכשיו בבית זה כן עובד.") are the majority of the corpus.
- **Numbered lists (`1.` `2.` `3.`) and bullets (`•` or `*`) appear whenever there's more than one distinct question or finding**, in both languages. E.g. a Hebrew status-update ask splits into 4 bullet points for target dates; the English Cloudflare Turnstile root-cause reply is a clean numbered list of DNS/network findings.
- **Technical write-ups (bug reports, incident reports) follow a consistent shape**: a one-line problem statement, then a "Ruled out: ..." or root-cause section, then a numbered "Recommended fix" list with file/line references (e.g. `Carousel.js:52-57`, `CarouselVariant2.js:95`). These are dense and precise -- no hedging, no filler, cites exact config values and code paths.
- **Longer Hebrew emails (asks to stakeholders, status requests) build in short paragraphs**, each one a self-contained point, often ending with a direct ask ("אשמח אם תוכל לשתף זמנים ככל שיש לך.") rather than a vague close.
- Follow-up/escalation emails often open with "בהמשך ל..." (following up on...) to anchor the email to prior context before stating the new ask.

## Formality Range

- **With peers and cross-team collaborators (Hebrew): informal-direct.** Uses the informal register throughout, occasional slang ("אחלה", "אחלה מעולה"), laughter written out ("חחחחח"), abbreviations common in Israeli workplace Hebrew ("כפ\"מ", "בד\"כ", "אח\"צ", "מצ\"ב"), and emoji used sparingly for warmth (🙂, 🙌, ;)) -- never more than one per email, usually at the very end.
- **With HR/admin/support contacts (Hebrew): still concise and direct, slightly more polite framing** ("אשמח אם תוכלי לעזור לי להעביר למי שכן יכול לעזור, תודה!") but no long pleasantries or throat-clearing -- gets to the ask in the first line or two.
- **Technical/English writing: neutral-professional, zero fluff.** No hedging language, no "just wanted to check in" softening -- states the root cause, the evidence, and the fix, in that order. Reads like an engineer writing for other engineers.
- **Code-switching is constant and unmarked**: English technical terms and product names drop into Hebrew sentences with no translation or special formatting ("דרך Workato?", "בעיה עם Turnstile-- ממצאים", "ה- reCaptcha חדש", "התוכנית הנוכחית לא באמת מתאימה ל usage"). Don't force a full-Hebrew or full-English rewrite of technical vocabulary -- keep tool/library/product names in English inline.
- **Persuasive/ask emails (e.g. requesting a budget or tool upgrade) stay grounded in reasoning and numbers**, not appeals to authority or urgency-for-urgency's-sake -- e.g. the Cursor plan request cites actual dollar costs and throughput reasoning rather than "I really need this."

## Common Phrasings

- "בהמשך ל..." -- following up on / continuing from
- "אשמח אם תוכל/תוכלי..." -- I'd appreciate if you could...
- "מבחינתי" -- from my perspective / as I see it
- "תודה רבה" / "מעולה תודה" / "תודה!" as closers
- "לגבי..." to pivot to a new point within the same email
- "נכון" / "אמת" as a quick one-word confirmation opener before elaborating
- "בכל אופן" -- anyway / in any case, used to wrap up before a final ask
- Em-dash (—) used mid-sentence in both Hebrew and English to attach a clarifying clause, mirroring the English writing style even in Hebrew text
- Root-cause-first structure in any bug/incident report: state what's broken, then why, then the fix -- never buries the lede

## Manual Notes

Add corrections or new patterns here as you notice them. This section is never overwritten by re-running tone-profile setup -- it is the long-term home for refining the agent's voice over time.
