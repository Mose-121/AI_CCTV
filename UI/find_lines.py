import re

def gather_lines():
    with open('d:\\Teg-CCTV-main\\UI\\UI_Main.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    pattern = re.compile(r'^(class|def)\s+([a-zA-Z0-9_]+)')
    matches = []
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
             matches.append(f"{i+1}:{m.group(1)} {m.group(2)}")
    
    with open('lines.txt', 'w', encoding='utf-8') as out:
        out.write('\n'.join(matches))

if __name__ == '__main__':
    gather_lines()
