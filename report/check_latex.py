"""LaTeX 语法基础校验脚本（仅用于本论文检查，不用于编译）"""
import re
from collections import Counter

with open('paper_formal.tex', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 检查 \begin/\end 平衡
begins = re.findall(r'\\begin\{(\w+)\}', content)
ends = re.findall(r'\\end\{(\w+)\}', content)
bc = Counter(begins)
ec = Counter(ends)
print('=== 环境平衡检查 ===')
all_envs = set(list(bc.keys()) + list(ec.keys()))
balanced = True
for env in sorted(all_envs):
    if bc[env] != ec[env]:
        print(f'  不平衡: {env}  begin={bc[env]} end={ec[env]}')
        balanced = False
    else:
        print(f'  OK: {env}  {bc[env]}')
if balanced:
    print('  >>> 所有环境平衡')

# 2. 检查 \cite/\bibitem 对应
cites = re.findall(r'\\cite\{([^}]+)\}', content)
cite_keys = set()
for c in cites:
    for k in c.split(','):
        cite_keys.add(k.strip())
bibitems = set(re.findall(r'\\bibitem\{([^}]+)\}', content))
print('\n=== 引用对应检查 ===')
print(f'  cite 引用的key: {sorted(cite_keys)}')
print(f'  bibitem 定义的key: {sorted(bibitems)}')
missing_bib = cite_keys - bibitems
unused_bib = bibitems - cite_keys
if missing_bib:
    print(f'  [X] 引用但未定义: {missing_bib}')
if unused_bib:
    print(f'  [!] 定义但未引用: {unused_bib}')
if not missing_bib and not unused_bib:
    print('  >>> 所有引用一一对应')

# 3. 检查 \label/\ref/\eqref 对应
labels = set(re.findall(r'\\label\{([^}]+)\}', content))
refs = set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}', content))
print('\n=== 标签对应检查 ===')
missing_label = refs - labels
unused_label = labels - refs
if missing_label:
    print(f'  [X] 引用但未定义label: {missing_label}')
else:
    print('  >>> 所有 ref/eqref 都有对应 label')
if unused_label:
    print(f'  [i] 定义但未被引用的label(允许): {sorted(unused_label)}')

# 4. 检查文档结构
sections = re.findall(r'\\section\{([^}]+)\}', content)
subsections = re.findall(r'\\subsection\{([^}]+)\}', content)
print('\n=== 章节结构 ===')
for s in sections:
    print(f'  section: {s}')
print(f'  共 {len(sections)} 个 section, {len(subsections)} 个 subsection')

# 5. 基本语法检查
print('\n=== 基本语法检查 ===')
brace_open = content.count('{')
brace_close = content.count('}')
print(f'  花括号: {brace_open} 开 / {brace_close} 闭 / 差={brace_open-brace_close}')
if '\\documentclass' in content:
    print('  documentclass 存在')
if '\\begin{document}' in content and '\\end{document}' in content:
    print('  document 环境完整')
# 检查 \newpage 前是否有内容残留
print('\n=== 摘要页检查 ===')
abstract_part = content.split('\\newpage')[0]
if '对于问题一' in abstract_part and '对于问题二' in abstract_part:
    print('  摘要包含问题一、二分段')
if '对于问题三' in abstract_part and '对于问题四' in abstract_part:
    print('  摘要包含问题三、四分段')
if '关键词' in abstract_part:
    print('  摘要包含关键词')

print('\n检查完成。')
