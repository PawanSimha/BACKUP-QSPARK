import io, re

def strip_literals(b):
    return re.sub(r"'(?:[^']|'')*'", "''", b)

bad = 0
for path in ['oracle/08a_ords_helpers.sql', 'oracle/08b_ords_reads.sql', 'oracle/08c_ords_writes.sql']:
    s = io.open(path, encoding='utf-8').read()

    # 1. every handler body balances
    for m in re.finditer(r"qspark_h\('([^']*)',\s*'([A-Z]+)',\s*q'!(.*?)!'\);", s, re.S):
        body = strip_literals(m.group(3))
        if body.count('(') != body.count(')'):
            print('PAREN', path, 'line', s[:m.start()].count('\n') + 1,
                  m.group(1), m.group(2), body.count('('), body.count(')'))
            bad += 1

    # 2. every standalone procedure/function block balances
    for m in re.finditer(r'CREATE OR REPLACE (PROCEDURE|FUNCTION) (\w+)(.*?)\n/\n', s, re.S):
        body = strip_literals(m.group(3))
        if body.count('(') != body.count(')'):
            print('PAREN-TOP', path, m.group(2), body.count('('), body.count(')'))
            bad += 1

    # 3. RETURNING CLOB only inside SELECT ... INTO
    for m in re.finditer(r'RETURNING CLOB', s):
        if 'INTO' not in s[m.start():m.start() + 60]:
            print('NOT-INTO', path, s[:m.start()].count('\n') + 1)
            bad += 1

    # 4. q-quote balance
    o, c = len(re.findall(r"q'!", s)), len(re.findall(r"!'", s))
    if o != c:
        print('QQUOTE', path, o, c)
        bad += 1

print('problems', bad)
