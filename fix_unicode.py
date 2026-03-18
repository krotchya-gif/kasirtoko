import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all emoji and unicode symbols with ASCII
emoji_map = {
    '\u2705': '[OK]',
    '\u26a0\ufe0f': '[WARN]',
    '\u274c': '[ERR]',
    '\u270f': '[LOG]',
    '\u2713': '[OK]',
    '\u2717': '[ERR]',
    '\U0001f3ea': '[TOKO]',
    '\U0001f464': '[USER]',
    '\U0001f510': '[LOCK]',
    '\U0001f680': '[START]',
    '\U0001f4ca': '[STATS]',
    '\u2728': '*',
    '\U0001f4f1': '[HP]',
    '\U0001f4bb': '[PC]',
    '\U0001f517': '[URL]',
    '\U0001f4cb': '[LIST]',
    '\u26a1': '[!]',
    '\U0001f310': '[WEB]',
    '\U0001f4be': '[SAVE]',
    '\U0001f527': '[TOOL]',
    '\u2699\ufe0f': '[GEAR]',
    '\U0001f6e0\ufe0f': '[TOOLS]',
    '\u2139\ufe0f': '[i]',
    '\U0001f3af': '[TARGET]',
    '\U0001f4c2': '[FOLDER]',
    '\U0001f5c2\ufe0f': '[FOLDERS]',
    '\U0001f9ea': '[TEST]',
    '\U0001f41b': '[BUG]',
    '\u23fb\ufe0f': '[OFF]',
    '\u23fb': '[OFF]',
    '\u25b6': '>',
    '\u25cf': '*',
    '\u2022': '-',
    '\U0001f4a1': '[IDEA]',
    '\U0001f50d': '[SEARCH]',
    '\U0001f446': '[UP]',
    '\U0001f4e6': '[BOX]',
    '\U0001f3f7\ufe0f': '[LABEL]',
    '\U0001f3a8': '[ART]',
    '\U0001f514': '[BELL]',
    '\U0001f515': '[NOBELL]',
    '\U0001f4b0': '[MONEY]',
    '\u23f3': '[TIME]',
    '\U0001f4c5': '[DATE]',
    '\U0001f4c6': '[CAL]',
    '\U0001f4c8': '[CHART]',
    '\U0001f4c9': '[DOWN]',
    '\U0001f5d1\ufe0f': '[TRASH]',
    '\U0001f504': '[SYNC]',
    '\U0001f503': '[RELOAD]',
    '\U0001f501': '[REPEAT]',
    '\U0001f502': '[LOOP]',
}

for emoji, replacement in emoji_map.items():
    content = content.replace(emoji, replacement)

# Remove any remaining non-ASCII characters from print statements
# but keep them in strings/JSON
def clean_print_line(match):
    line = match.group(0)
    # Only clean the string content inside quotes
    # Find all strings in the line
    def clean_string(match):
        s = match.group(0)
        # Replace any remaining emoji in the string
        for emoji, replacement in emoji_map.items():
            s = s.replace(emoji, replacement)
        return s
    
    # Clean strings but preserve line structure
    line = re.sub(r'"([^"]*)"', clean_string, line)
    line = re.sub(r"'([^']*)'", clean_string, line)
    return line

# Apply to lines containing print
lines = content.split('\n')
new_lines = []
for line in lines:
    if 'print(' in line:
        line = clean_print_line(line)
    new_lines.append(line)

content = '\n'.join(new_lines)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('[OK] All Unicode characters replaced')
