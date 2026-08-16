import json
base = 'utils/arena_parser/output'

print('=== CLASS MECHANICS ===')
cls = json.load(open(f'{base}/class_mechanics.json'))
for c in cls:
    cid = c['id']
    name = c['name']
    cat = c['category']
    hp = c['hp_formula']
    sp = c['sp_formula']
    td = c['thieving_divisor']
    xp = c['initial_xp_cap']
    print(f'  [{cid:2d}] {name:<14} {cat:<8} {hp:<10} {sp:<12} thiev={td} xp={xp}')

print()
print('=== WEAPONS ===')
wpn = json.load(open(f'{base}/weapons.json'))
for w in wpn:
    wid = w['id']
    wname = w['name']
    wtype = w['type']
    dmg = w['damage_label']
    print(f'  [{wid:2d}] {wname:<14} {wtype:<7} dmg={dmg}')

print()
print('=== MATERIALS ===')
mat = json.load(open(f'{base}/materials.json'))
for m in mat:
    mname = m['name']
    dmg = m['damage_mult']
    val = m['value_mult']
    print(f'  {mname:<14} dmg_mult={dmg}  val_mult={val}')
