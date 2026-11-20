#!/usr/bin/env python3
"""جمع إعلانات المؤتمرات والجوائز الجديدة لموقع «الباحث» وإضافتها إلى events.js.

طريقتان، تختارين بينهما في updater/settings.json بالمفتاح "mode":
  free  — مجانية: تقرأ مواقع الإعلانات المذكورة في "sources".
  ai    — ذكية: تبحث في الويب عبر Claude API (تحتاج السر ANTHROPIC_API_KEY في GitHub).
  both  — الطريقتان معًا.
يعمل بمكتبات بايثون القياسية فقط، دون تثبيت أي حزمة.
"""
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS_FILE = os.path.join(ROOT, "events.js")
SETTINGS_FILE = os.path.join(ROOT, "updater", "settings.json")
TODAY = dt.date.today()

FIELDS = ["فلسفة", "دراسات إسلامية", "لغة عربية وأدب", "لسانيات وحوسبة لغوية", "ترجمة", "تاريخ", "علم اجتماع",
          "أنثروبولوجيا", "دراسات الشرق الأوسط", "مكتبات ومعلومات", "اقتصاد وإدارة", "تربية", "فيزياء", "كيمياء",
          "أحياء", "طب وعلوم صحية", "هندسة", "رياضيات وحاسوب"]
KINDS = ["مؤتمر", "جائزة", "مسابقة", "منحة", "مدرسة صيفية/شتوية"]
STAGES = ["announced", "abstract", "paper", "notify", "start", "end"]

# كلمات تصنيف المجالات (عربية وإنجليزية)
FIELD_WORDS = {
    "فلسفة": ["philosoph", "ethic", "metaphys", "epistem", "فلسف", "أخلاق", "منطق"],
    "دراسات إسلامية": ["islam", "muslim", "qur", "koran", "hadith", "sufi", "إسلام", "قرآن", "حديث", "فقه", "تصوف", "شريعة"],
    "لغة عربية وأدب": ["arabic literature", "arabic language", "poetry", "novel", "literary", "اللغة العربية", "أدب", "شعر", "رواية", "نقد أدبي", "بلاغة"],
    "لسانيات وحوسبة لغوية": ["linguist", "language processing", "nlp", "lexicograph", "لسان", "لغوي", "معجم", "حوسبة"],
    "ترجمة": ["translation", "translat", "ترجمة", "الترجمة"],
    "تاريخ": ["history", "historical", "archive", "manuscript", "تاريخ", "مخطوط", "أرشيف", "وثائق"],
    "علم اجتماع": ["sociolog", "social science", "society", "اجتماع", "مجتمع"],
    "أنثروبولوجيا": ["anthropolog", "ethnograph", "أنثروبولوج", "إثنوغراف"],
    "دراسات الشرق الأوسط": ["middle east", "arab world", "mena", "الشرق الأوسط", "العالم العربي"],
    "مكتبات ومعلومات": ["librar", "information science", "مكتبات", "المعلومات"],
    "اقتصاد وإدارة": ["econom", "finance", "management", "business", "اقتصاد", "إدارة", "مالية"],
    "تربية": ["education", "pedagog", "teaching", "تربية", "تعليم"],
    "فيزياء": ["physics", "فيزياء"], "كيمياء": ["chemistry", "كيمياء"], "أحياء": ["biolog", "أحياء"],
    "طب وعلوم صحية": ["medic", "health", "clinical", "طب", "صحة"],
    "هندسة": ["engineering", "هندسة"],
    "رياضيات وحاسوب": ["mathemat", "computer science", "computing", "artificial intelligence", "رياضيات", "حاسوب", "ذكاء اصطناعي"],
}
KIND_WORDS = [("جائزة", ["prize", "award", "جائزة"]), ("مسابقة", ["competition", "contest", "مسابقة"]),
              ("منحة", ["grant", "fellowship", "منحة بحثية", "منح بحثية"]),
              ("مدرسة صيفية/شتوية", ["summer school", "winter school", "مدرسة صيفية", "مدرسة شتوية"])]

MONTHS_EN = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
MONTHS_AR = {"يناير": 1, "كانون الثاني": 1, "فبراير": 2, "شباط": 2, "مارس": 3, "آذار": 3, "أبريل": 4, "ابريل": 4,
             "إبريل": 4, "نيسان": 4, "مايو": 5, "أيار": 5, "يونيو": 6, "حزيران": 6, "يوليو": 7, "تموز": 7,
             "أغسطس": 8, "اغسطس": 8, "آب": 8, "سبتمبر": 9, "أيلول": 9, "أكتوبر": 10, "اكتوبر": 10,
             "تشرين الأول": 10, "نوفمبر": 11, "تشرين الثاني": 11, "ديسمبر": 12, "كانون الأول": 12}
AR_MONTH_RE = "|".join(sorted(map(re.escape, MONTHS_AR), key=len, reverse=True))
EN_MONTH_RE = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
LABELS = {
    "abstract": ["abstract", "proposal", "ملخص", "الملخصات", "مقترح"],
    "notify": ["notification", "acceptance", "إشعار", "القبول", "النتائج"],
    "paper": ["deadline", "submission", "full paper", "آخر موعد", "التقديم", "الترشح", "تسليم", "الترشيح"],
    "start": ["conference date", "dates:", "will be held", "takes place", "when", "held on", "event date", "seminar", "symposium",
              "colloquium", "congress", "workshop", "winter school", "summer school", "ينعقد", "انعقاد", "يعقد", "تُعقد",
              "الندوة", "الملتقى", "المؤتمر في"],
}

report = {"added": [], "errors": [], "notes": []}


# ---------------------------------------------------------------- ملف الإعلانات
def load_events():
    text = open(EVENTS_FILE, encoding="utf-8").read()
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("//"))
    i = body.find("window.EVENTS")
    if i < 0:
        raise ValueError("لم أجد window.EVENTS في events.js")
    a, b = body.find("[", i), body.rfind("]")
    raw = re.sub(r",\s*([\]}])", r"\1", body[a:b + 1])
    return json.loads(raw)


def write_events(events):
    head = [
        "// ملف الإعلانات لموقع «الباحث». آخر تحديث: " + TODAY.isoformat(),
        "// راجعي دليل README.md لطريقة التعديل. الإعلانات التي أضافها التحديث التلقائي فيها \"source\".",
        "window.EVENTS = [",
    ]
    rows = ["  " + json.dumps(e, ensure_ascii=False) for e in events]
    open(EVENTS_FILE, "w", encoding="utf-8").write("\n".join(head) + "\n" + ",\n".join(rows) + "\n];\n")


# ---------------------------------------------------------------- أدوات
def norm_url(u):
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


def norm_title(t):
    return re.sub(r"[\W_]+", "", (t or "").lower())


def strip_tags(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t\r\f\v]+", " ", html.unescape(s)).strip()


def western_digits(s):
    return s.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))


def mk_date(y, m, d):
    try:
        return dt.date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def find_dates(text):
    """يعيد قائمة (موضع، تاريخ، تاريخ_نهاية_أو_None)."""
    t = western_digits(text)
    out = []
    for m in re.finditer(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t):
        out.append((m.start(), mk_date(*m.groups()), None, m.end()))
    # June 14–18, 2027
    for m in re.finditer(r"\b(" + EN_MONTH_RE + r")\s+(\d{1,2})\s*[-–—]\s*(\d{1,2}),?\s+(\d{4})", t, re.I):
        mo = MONTHS_EN.get(m.group(1)[:3].lower())
        if mo:
            out.append((m.start(), mk_date(m.group(4), mo, m.group(2)), mk_date(m.group(4), mo, m.group(3)), m.end()))
    # June 14, 2027 / Jun 14 2027
    for m in re.finditer(r"\b(" + EN_MONTH_RE + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", t, re.I):
        mo = MONTHS_EN.get(m.group(1)[:3].lower())
        if mo:
            out.append((m.start(), mk_date(m.group(3), mo, m.group(2)), None, m.end()))
    # 14 June 2027
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + EN_MONTH_RE + r"),?\s+(\d{4})", t, re.I):
        mo = MONTHS_EN.get(m.group(2)[:3].lower())
        if mo:
            out.append((m.start(), mk_date(m.group(3), mo, m.group(1)), None, m.end()))
    # 14 يونيو 2027 / 14-18 يونيو 2027
    for m in re.finditer(r"(\d{1,2})(?:\s*[-–—]\s*(\d{1,2}))?\s+(" + AR_MONTH_RE + r")\s*(?:\(\s*[^)]{0,20}\))?\s*(\d{4})", t):
        mo = MONTHS_AR[m.group(3)]
        out.append((m.start(), mk_date(m.group(4), mo, m.group(1)), mk_date(m.group(4), mo, m.group(2)) if m.group(2) else None, m.end()))
    out = [p for p in out if p[1]]
    out.sort(key=lambda p: (p[0], -(p[3] - p[0])))
    res, last_end = [], -1
    for p in out:
        if p[0] < last_end:  # تاريخ داخل مدى التقطناه من قبل
            continue
        res.append(p)
        last_end = p[3]
    return res


def _pick(at, first):
    """يختار المرحلة من مواضع الكلمات؛ first=True: أقرب كلمة بعد التاريخ، وإلا أقرب كلمة قبله."""
    found = {k: v for k, v in at.items() if v >= 0}
    if not found:
        return None
    best = (min if first else max)(found, key=found.get)
    if best == "paper":  # «Abstract deadline» و«Deadline for abstracts» و«Notification due»
        for spec in ("abstract", "notify"):
            if spec in found and abs(found[spec] - found["paper"]) <= 20:
                return spec
    return best


def label_dates(text):
    """يعرف أي مرحلة يمثّلها كل تاريخ: من الوصف الذي بعده مباشرة («31 ديسمبر 2026: آخر موعد…»)، وإلا من الكلمات التي قبله."""
    t = western_digits(text)
    low = t.lower()
    found = find_dates(t)
    dates = {}
    for i, (pos, d, end, stop) in enumerate(found):
        nxt = found[i + 1][0] if i + 1 < len(found) else len(low)
        after = low[stop:min(nxt, stop + 90)]
        best = None
        if re.match(r"^\s*[:：\-–—)]", after):
            best = _pick({k: min([after.find(w) for w in ws if w in after] or [-1]) for k, ws in LABELS.items()}, True)
        if best is None:
            before = low[max(0, pos - 70):pos]
            best = _pick({k: max(before.rfind(w) for w in ws) for k, ws in LABELS.items()}, False)
        if best is None:
            continue
        if best not in dates:
            dates[best] = d
            if best == "start" and end:
                dates["end"] = end
        elif best == "start" and "end" not in dates and d > dates["start"]:
            dates["end"] = d
    return dates


def classify(text, default_fields, allowed):
    low = (text or "").lower()
    fields = [f for f, words in FIELD_WORDS.items() if any(w in low for w in words)]
    fields = [f for f in dict.fromkeys(list(default_fields) + fields) if f in FIELDS]
    if allowed:
        fields = [f for f in fields if f in allowed] or [f for f in default_fields if f in FIELDS]
    return fields


def guess_kind(text, default):
    low = (text or "").lower()
    for kind, words in KIND_WORDS:
        if any(w in low for w in words):
            return kind
    return default or "مؤتمر"


def fetch(url, data=None, headers=None, timeout=40):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "albahith-updater/1.0 (+GitHub Actions)", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


# ---------------------------------------------------------------- الطريقة المجانية
def from_rss(src):
    xml = fetch(src["url"])
    xml = re.sub(r"\sxmlns(:\w+)?=\"[^\"]+\"", "", xml, count=5)
    root = ET.fromstring(xml.encode("utf-8"))
    items = root.findall(".//item") or root.findall(".//entry")
    out = []
    for it in items[:60]:
        title = strip_tags(it.findtext("title") or "")
        link = it.findtext("link") or ""
        if not link:
            le = it.find("link")
            link = le.get("href", "") if le is not None else ""
        desc = strip_tags(it.findtext("description") or it.findtext("summary") or it.findtext("content") or "")
        out.append({"title": title, "url": link.strip(), "text": title + "\n" + desc, "org": "", "place": ""})
    return out


def from_upenn(src):
    page = fetch(src["url"])
    out = []
    for chunk in re.split(r"(?=<h2\b)", page)[1:]:
        m = re.search(r"<h2[^>]*>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", chunk, re.S)
        if not m:
            continue
        url = urllib.parse.urljoin(src["url"], html.unescape(m.group(1)))
        title = strip_tags(m.group(2))
        text = strip_tags(chunk[:6000])
        org = ""
        o = re.search(r"(?:am|pm)\s+(.{3,160}?)\s+deadline for submissions", text, re.I | re.S)
        if o:
            org = o.group(1).strip()
        text = re.sub(r"deadline for submissions:", "submission deadline:", text, flags=re.I)
        text = re.sub(r"updated:\s*\w+,\s*" + EN_MONTH_RE + r"\s+\d{1,2},\s+\d{4}", " ", text, flags=re.I)
        out.append({"title": title, "url": url, "text": text, "org": org, "place": ""})
    return out


PAGE_WORDS = ["مؤتمر", "ملتقى", "ندوة", "دعوة للمشاركة", "استكتاب", "جائزة", "مسابقة", "منحة", "مدرسة صيفية", "مدرسة شتوية",
              "conference", "symposium", "colloquium", "call for papers", "call for abstracts", "cfp", "workshop",
              "prize", "award", "competition", "summer school", "winter school", "fellowship"]


def from_page(src):
    """صفحة إعلانات أو فعاليات في موقع جامعة أو مركز بحثي: يلتقط روابط المؤتمرات والجوائز،
    ثم يفتح صفحة كل إعلان ليقرأ مواعيده منها (صفحات القوائم لا تذكر المواعيد عادة)."""
    page = fetch(src["url"])
    body = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    out, seen = [], set()
    for m in re.finditer(r"<a\b[^>]*href=\"([^\"#][^\"]*)\"[^>]*>(.*?)</a>", body, re.S | re.I):
        title = strip_tags(m.group(2))
        low = title.lower()
        if len(title) < 12 or not any(w in low for w in PAGE_WORDS):
            continue
        url = urllib.parse.urljoin(src["url"], html.unescape(m.group(1)))
        if url in seen or not url.startswith("http") or url.rstrip("/") == src["url"].rstrip("/"):
            continue
        seen.add(url)
        around = strip_tags(body[max(0, m.start() - 300):m.end() + 700])
        out.append({"title": title, "url": url, "text": title + "\n" + around, "org": src.get("org", ""), "place": src.get("place", "")})
        if len(out) >= int(src.get("max_links", 15)):
            break
    if src.get("follow_links", True):
        for it in out:
            try:
                it["text"] = it["title"] + "\n" + strip_tags(fetch(it["url"]))[:30000]
            except Exception as e:
                report["notes"].append(f"{src.get('name')}: تعذّر فتح {it['url']}: {type(e).__name__}")
    return out


def free_sources(settings):
    """مصادر الطريقة المجانية: قائمة sources، وصفحات فعاليات الجامعات (events_pages) في قائمة universities."""
    srcs = [s for s in settings.get("sources", []) if s.get("enabled", True)]
    for u in settings.get("universities", []):
        if not u.get("enabled", True):
            continue
        for page in u.get("events_pages", []):
            srcs.append({"name": u.get("name", u.get("domain", "")), "type": "page", "url": page,
                         "org": u.get("name", ""), "place": u.get("place", ""), "fields": []})
    return srcs


def collect_free(settings):
    found = []
    readers = {"upenn": from_upenn, "page": from_page}
    for src in free_sources(settings):
        try:
            items = readers.get(src.get("type"), from_rss)(src)
        except Exception as e:  # مصدر معطّل لا يوقف الباقي
            report["errors"].append(f"{src.get('name')}: {type(e).__name__}: {e}")
            continue
        for it in items:
            dates = label_dates(it["text"])
            found.append({
                "title": it["title"], "org": it["org"], "place": it["place"], "url": it["url"],
                "kind": src.get("kind") or guess_kind(it["title"], "مؤتمر"),
                "fields": classify(it["title"] + " " + it["text"][:1500], src.get("fields", []), None),
                "dates": dates, "note": "", "source": src.get("name", "free"),
            })
        report["notes"].append(f"{src.get('name')}: قُرئ {len(items)} عنصرًا")
    return found


# ---------------------------------------------------------------- الطريقة الذكية
AI_FORMAT = """Answer with ONLY a JSON array, no prose, each item:
{{"title": "...", "org": "...", "place": "City, Country in Arabic", "kind": one of {kinds},
 "url": "https://...", "fields": subset of {fields},
 "dates": {{"announced": "YYYY-MM-DD", "abstract": "...", "paper": "...", "notify": "...", "start": "...", "end": "..."}},
 "note": "one short Arabic sentence: eligibility or language, if stated"}}
(dates keys: abstract = abstract/proposal deadline; paper = full paper or application/nomination deadline; notify = acceptance or results; start/end = event or ceremony dates.)"""

AI_RULES = """Rules:
- Only real announcements you found on the web, with the OFFICIAL page URL of the announcement. Never invent dates or URLs; omit a date you did not see.
- Skip anything whose URL or title is already known (list below).
- At most {limit} items.
- Write title, org, place and note in Arabic (keep official names of foreign bodies, transliterated or in parentheses)."""


def call_claude(key, ai, prompt, tool):
    body = {"model": ai.get("model", "claude-sonnet-5-5"), "max_tokens": 8000, "tools": [tool],
            "messages": [{"role": "user", "content": prompt}]}
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    text = ""
    for _ in range(6):
        resp = json.loads(fetch("https://api.anthropic.com/v1/messages", json.dumps(body).encode(), headers, timeout=600))
        content = resp.get("content", [])
        text += "".join(b.get("text", "") for b in content if b.get("type") == "text")
        if resp.get("stop_reason") != "pause_turn":
            break
        body["messages"] = body["messages"][:1] + [{"role": "assistant", "content": content}]
    return text


def run_claude(key, ai, prompt, tool, label):
    try:
        text = call_claude(key, ai, prompt, tool)
    except Exception as e:
        detail = ""
        if hasattr(e, "read"):
            try:
                detail = e.read().decode()[:300]
            except Exception:
                pass
        report["errors"].append(f"{label}: فشل الاتصال بـ Claude API: {e} {detail}")
        return []
    items = parse_json_array(text)
    if items is None:
        report["errors"].append(f"{label}: لم أستطع قراءة رد Claude بصيغة JSON.")
        return []
    for it in items:
        it["source"] = label
    report["notes"].append(f"{label}: اقترح {len(items)} إعلانًا")
    return items


def collect_ai(settings, known):
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        report["errors"].append("الوضع الذكي: لا يوجد السر ANTHROPIC_API_KEY، فاستُخدمت الطريقة المجانية وحدها.")
        return None
    ai = settings.get("ai", {})
    fields = settings.get("fields") or FIELDS
    known_list = "\n".join(sorted(known)[:250])
    limit = settings.get("max_new_per_run", 20)
    fmt = AI_FORMAT.format(kinds=json.dumps(KINDS, ensure_ascii=False), fields=json.dumps(fields, ensure_ascii=False))
    rules = AI_RULES.format(limit=limit)
    intro = f"Today is {TODAY.isoformat()}. You are the research assistant of «الباحث», an Arabic site that tracks academic conferences, competitions, prizes, grants and summer/winter schools."
    items = []

    # 1) بحث عام في الويب
    if ai.get("general_search", True):
        prompt = f"""{intro}

Use web search (Arabic and English queries) to find CURRENT announcements (calls for papers, calls for nominations, competitions) with at least one date after today, in these fields: {', '.join(fields)}.
{ai.get('extra_instructions', '')}

{rules}

{fmt}

Already known (URL or title):
{known_list}"""
        tool = {"type": "web_search_20250305", "name": "web_search", "max_uses": int(ai.get("max_searches", 12))}
        items += run_claude(key, ai, prompt, tool, "بحث ذكي عام (Claude)")

    # 2) بحث محصور في مواقع الجامعات ومراكزها البحثية (النطاقات الفرعية تدخل تلقائيًا)
    unis = [u for u in settings.get("universities", []) if u.get("enabled", True) and u.get("domain")]
    size = max(1, int(ai.get("universities_per_search", 8)))
    for i in range(0, len(unis), size):
        group = unis[i:i + size]
        names = "\n".join(f"- {u.get('name', '')} ({u['domain']})" for u in group)
        prompt = f"""{intro}

Search ONLY the websites of these universities, including their faculties and affiliated research centers and institutes (subdomains are included), for CURRENT announcements of conferences, symposia, calls for papers, prizes, competitions, grants or summer/winter schools that they organize or host, with at least one date after today. Use Arabic queries first (مؤتمر، ملتقى، ندوة دولية، دعوة للمشاركة، استكتاب، جائزة، مسابقة), then English.
Prefer these fields: {', '.join(fields)}; include other fields only if nothing else is found.
Universities:
{names}

{rules}

{fmt}

Already known (URL or title):
{known_list}"""
        tool = {"type": "web_search_20250305", "name": "web_search",
                "max_uses": int(ai.get("searches_per_university_group", 6)),
                "allowed_domains": [u["domain"] for u in group]}
        label = f"بحث ذكي في مواقع الجامعات ({i // size + 1})"
        report["notes"].append(label + ": " + "، ".join(u.get("name", u["domain"]) for u in group))
        items += run_claude(key, ai, prompt, tool, label)
    return items


def parse_json_array(text):
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("["):text.rfind("]") + 1] if "[" in text else ""
    try:
        data = json.loads(raw)
        return [x for x in data if isinstance(x, dict)]
    except Exception:
        return None


# ---------------------------------------------------------------- التنقية والدمج
def clean(item, allowed_fields):
    title = strip_tags(str(item.get("title", "")))[:220]
    url = str(item.get("url", "")).strip()
    if not title or not re.match(r"^https?://", url):
        return None
    dates = {}
    for k in STAGES:
        v = str((item.get("dates") or {}).get(k, "")).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v) and mk_date(*v.split("-")):
            dates[k] = v
    if not any(dt.date.fromisoformat(v) >= TODAY for v in dates.values()):
        return None  # لا موعد قادم
    fields = [f for f in item.get("fields", []) if f in FIELDS] or classify(title + " " + str(item.get("note", "")), [], None)
    if allowed_fields and not any(f in allowed_fields for f in fields):
        return None
    kind = item.get("kind") if item.get("kind") in KINDS else guess_kind(title, "مؤتمر")
    eid = "auto-" + hashlib.sha1(norm_url(url).encode()).hexdigest()[:10]
    return {"id": eid, "title": title, "org": strip_tags(str(item.get("org", "")))[:160],
            "place": strip_tags(str(item.get("place", "")))[:100], "kind": kind, "url": url,
            "fields": fields, "dates": {k: dates[k] for k in STAGES if k in dates},
            "note": strip_tags(str(item.get("note", "")))[:300], "source": item.get("source", ""),
            "added": TODAY.isoformat()}


def last_date(e):
    vals = [v for v in (e.get("dates") or {}).values() if re.match(r"^\d{4}-\d{2}-\d{2}$", str(v))]
    return max(vals) if vals else None


def main():
    settings = json.load(open(SETTINGS_FILE, encoding="utf-8"))
    mode = settings.get("mode", "free")
    events = load_events()
    known_urls = {norm_url(e.get("url")) for e in events}
    known_titles = {norm_title(e.get("title")) for e in events}
    known_ids = {e.get("id") for e in events}

    candidates = []
    if mode in ("ai", "both"):
        got = collect_ai(settings, {e.get("url", "") for e in events} | {e.get("title", "") for e in events})
        if got is None:
            mode = "free"
        else:
            candidates += got
    if mode in ("free", "both"):
        candidates += collect_free(settings)

    allowed = settings.get("fields") or []
    limit = int(settings.get("max_new_per_run", 20))
    new = []
    for c in candidates:
        e = clean(c, allowed)
        if not e:
            continue
        if norm_url(e["url"]) in known_urls or norm_title(e["title"]) in known_titles or e["id"] in known_ids:
            continue
        known_urls.add(norm_url(e["url"]))
        known_titles.add(norm_title(e["title"]))
        known_ids.add(e["id"])
        new.append(e)
        if len(new) >= limit:
            break

    pruned = 0
    days = int(settings.get("prune_after_days", 0) or 0)
    if days > 0:
        cut = (TODAY - dt.timedelta(days=days)).isoformat()
        keep = [e for e in events if not (last_date(e) and last_date(e) < cut)]
        pruned = len(events) - len(keep)
        events = keep

    if new or pruned:
        write_events(events + new)
    report["added"] = new

    lines = [f"## تحديث «الباحث»: {TODAY.isoformat()}", "", f"الطريقة: **{settings.get('mode', 'free')}**", ""]
    if new:
        lines.append(f"### إعلانات جديدة ({len(new)})")
        for e in new:
            nd = ", ".join(f"{k}: {v}" for k, v in e["dates"].items())
            lines.append(f"- [{e['title']}]({e['url']}) — {e['kind']} — {nd} — المصدر: {e['source']}")
    else:
        lines.append("لا إعلانات جديدة هذه المرة.")
    if pruned:
        lines += ["", f"حُذف {pruned} إعلانًا قديمًا."]
    if report["errors"]:
        lines += ["", "### ملاحظات وأخطاء"] + [f"- {x}" for x in report["errors"]]
    if report["notes"]:
        lines += ["", "<details><summary>تفاصيل المصادر</summary>", ""] + [f"- {x}" for x in report["notes"]] + ["", "</details>"]
    md = "\n".join(lines) + "\n\nراجعي الروابط والتواريخ قبل الدمج؛ ما يُجمع آليًا قد يخطئ.\n"
    out_dir = os.environ.get("RUNNER_TEMP") or os.path.join(ROOT, "updater")
    open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8").write(md)
    print(md)

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"changed={'true' if (new or pruned) else 'false'}\n")
            f.write(f"added={len(new)}\n")
            f.write(f"review={'true' if settings.get('review', True) else 'false'}\n")
            f.write(f"report={os.path.join(out_dir, 'report.md')}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("خطأ:", e, file=sys.stderr)
        sys.exit(1)
