"""
parse_text.py — Phase 1A text file parsers

Reads Arena data from ARENA_DIR and writes JSON to OUTPUT_DIR.
Files parsed:
  - QUESTION.TXT  → questions.json
  - DUNGEON.TXT   → dungeons.json
  - CITYTXT        → cities.json
  - SPELLMKR.TXT  → spell_effects.json
  - HELP.TXT      → help.json (if present)
"""

import json
import os
import re

ARENA_DIR = r"c:\Users\Davy\Documents\My Games\Arena"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def save(name, data):
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  wrote {len(data)} records → {path}")


# ---------------------------------------------------------------------------
# QUESTION.TXT
# Format: numbered questions (1. ... 40.) each with 3 options (a/b/c).
# Score tag at end of each option: (5v)=warrior, (5l)=mage/lore, (5c)=thief/cunning
# ---------------------------------------------------------------------------

SCORE_RE = re.compile(r'\((\d+)([vlc])\)\s*$', re.IGNORECASE)
QUESTION_NUM_RE = re.compile(r'^(\d+)\.\s+(.*)', re.DOTALL)
OPTION_RE = re.compile(r'^([a-c])\)\s+(.*)', re.DOTALL)

CATEGORY_MAP = {'v': 'warrior', 'l': 'mage', 'c': 'thief'}


def _clean(text):
    """Strip extra whitespace/newlines, normalise to single spaces."""
    return re.sub(r'\s+', ' ', text).strip()


def parse_questions():
    path = os.path.join(ARENA_DIR, "QUESTION.TXT")
    with open(path, encoding="latin-1") as f:
        raw = f.read()

    # Split on question numbers (1. through 40.)
    # We'll collect lines and parse sequentially
    lines = [ln.rstrip('\r\n') for ln in raw.splitlines()]

    questions = []
    current_q = None
    current_opt = None
    buffer = []

    def flush_option():
        if current_opt and buffer:
            text_full = _clean(' '.join(buffer))
            m = SCORE_RE.search(text_full)
            if m:
                points = int(m.group(1))
                cat = CATEGORY_MAP.get(m.group(2).lower(), 'unknown')
                text_clean = SCORE_RE.sub('', text_full).strip()
            else:
                points, cat, text_clean = 0, 'unknown', text_full
            current_q['options'].append({
                'letter': current_opt,
                'text': text_clean,
                'scores': {cat: points},
            })
            buffer.clear()

    def flush_question():
        if current_q:
            flush_option()
            questions.append(current_q)

    for line in lines:
        # New question number?
        mq = QUESTION_NUM_RE.match(line)
        if mq:
            flush_question()
            current_q = {'id': int(mq.group(1)), 'question': _clean(mq.group(2)), 'options': []}
            current_opt = None
            buffer = []
            continue

        # New option letter?
        mo = OPTION_RE.match(line)
        if mo and current_q:
            flush_option()
            current_opt = mo.group(1).lower()
            buffer = [mo.group(2)]
            continue

        # Continuation of question text (before first option)
        if current_q and current_opt is None and line.strip():
            current_q['question'] = _clean(current_q['question'] + ' ' + line)
            continue

        # Continuation of option text
        if current_opt:
            buffer.append(line)

    flush_question()  # flush last

    save("questions.json", questions)
    return questions


# ---------------------------------------------------------------------------
# DUNGEON.TXT
# Format: records separated by '#', each record = name (first line) + description
# ---------------------------------------------------------------------------

def parse_dungeons():
    path = os.path.join(ARENA_DIR, "DUNGEON.TXT")
    with open(path, encoding="latin-1") as f:
        raw = f.read()

    records = [r.strip() for r in raw.split('#') if r.strip()]
    dungeons = []
    for i, rec in enumerate(records):
        lines = [ln.strip('\r\n') for ln in rec.splitlines() if ln.strip()]
        if not lines:
            continue
        name = lines[0].strip()
        description = _clean(' '.join(lines[1:]))
        # Extract staff piece number from description
        staff_match = re.search(r'(\w+) piece of the Staff of Chaos', description)
        staff_piece = staff_match.group(1) if staff_match else None
        dungeons.append({
            'id': i,
            'name': name,
            'description': description,
            'staff_piece': staff_piece,
        })

    save("dungeons.json", dungeons)
    return dungeons


# ---------------------------------------------------------------------------
# CITYTXT
# Format: #PPLL header (PP=province 0-indexed, LL=location index), then greeting
# text ending with '&'
# ---------------------------------------------------------------------------

CITY_HEADER_RE = re.compile(r'^#(\d{2})(\d{2})$')


def parse_cities():
    path = os.path.join(ARENA_DIR, "CITYTXT")
    with open(path, encoding="latin-1") as f:
        raw = f.read()

    cities = []
    # Split on '#' markers then re-check first line
    blocks = raw.split('#')
    for block in blocks:
        block = block.strip('\r\n ')
        if not block:
            continue
        lines = block.splitlines()
        header_line = lines[0].strip()
        m = CITY_HEADER_RE.match('#' + header_line)
        if not m:
            # Header was consumed in split; try bare 4-digit id
            m2 = re.match(r'^(\d{2})(\d{2})$', header_line)
            if not m2:
                continue
            province_id = int(m2.group(1))
            location_id = int(m2.group(2))
        else:
            province_id = int(m.group(1))
            location_id = int(m.group(2))

        body = ' '.join(ln.strip() for ln in lines[1:])
        body = body.rstrip('&').strip()
        body = _clean(body)

        cities.append({
            'raw_id': f"{province_id:02d}{location_id:02d}",
            'province_id': province_id,
            'location_id': location_id,
            'greeting': body,
        })

    save("cities.json", cities)
    return cities


# ---------------------------------------------------------------------------
# SPELLMKR.TXT
# Format: #NN header, then template text with %0-%5, %a tokens
# ---------------------------------------------------------------------------

EFFECT_HEADER_RE = re.compile(r'^#(\d{2})$')


def parse_spell_effects():
    path = os.path.join(ARENA_DIR, "SPELLMKR.TXT")
    with open(path, encoding="latin-1") as f:
        raw = f.read()

    effects = []
    blocks = raw.split('#')
    for block in blocks:
        block = block.strip('\r\n ')
        if not block:
            continue
        lines = block.splitlines()
        header = lines[0].strip()
        m = re.match(r'^(\d{2})$', header)
        if not m:
            continue
        effect_id = int(m.group(1))
        template = _clean(' '.join(ln.strip() for ln in lines[1:]))
        # Extract parameter tokens
        params = sorted(set(re.findall(r'%[0-9a]', template)))
        effects.append({
            'id': effect_id,
            'template': template,
            'parameters': params,
        })

    save("spell_effects.json", effects)
    return effects


# ---------------------------------------------------------------------------
# HELP.TXT (optional)
# ---------------------------------------------------------------------------

def parse_help():
    path = os.path.join(ARENA_DIR, "HELP.TXT")
    if not os.path.exists(path):
        print("  HELP.TXT not found, skipping")
        return []

    with open(path, encoding="latin-1") as f:
        raw = f.read()

    sections = []
    blocks = re.split(r'#\d+', raw)
    headers = re.findall(r'#(\d+)', raw)
    for i, block in enumerate(blocks[1:], 0):
        title_match = re.match(r'\s*(.+?)\r?\n', block)
        title = title_match.group(1).strip() if title_match else f"Section {i}"
        body = _clean(block)
        sections.append({'id': int(headers[i]) if i < len(headers) else i,
                         'title': title,
                         'text': body})

    save("help.json", sections)
    return sections


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Phase 1A: Parsing Arena text files ===\n")

    print("QUESTION.TXT →")
    qs = parse_questions()
    print(f"  {len(qs)} questions parsed\n")

    print("DUNGEON.TXT →")
    ds = parse_dungeons()
    print(f"  {len(ds)} dungeons parsed\n")

    print("CITYTXT →")
    cs = parse_cities()
    print(f"  {len(cs)} cities parsed\n")

    print("SPELLMKR.TXT →")
    es = parse_spell_effects()
    print(f"  {len(es)} spell effects parsed\n")

    print("HELP.TXT →")
    parse_help()

    print("\n=== Done. Output in utils/arena_parser/output/ ===")
