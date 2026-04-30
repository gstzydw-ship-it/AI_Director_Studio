import re

# Read the file
with open('agents/director_graph.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the problematic line with nested quotes
# Line 3191 has: issues.append("- 受击/反应落点缺少明确切镜：请写清"镜头切至谁、什么景别、什么机位、画面里保留谁/什么空间锚点"。")
# The inner quotes need to be escaped or changed

old_str = 'issues.append("- 受击/反应落点缺少明确切镜：请写清"镜头切至谁、什么景别、什么机位、画面里保留谁/什么空间锚点"。")'
new_str = "issues.append('- 受击/反应落点缺少明确切镜：请写清\"镜头切至谁、什么景别、什么机位、画面里保留谁/什么空间锚点\"。')"

if old_str in content:
    content = content.replace(old_str, new_str)
    print("Fixed line 3191")
else:
    print("Pattern not found, trying alternative...")
    # Try to find and fix with regex
    pattern = r'issues\.append\("- 受击/反应落点缺少明确切镜：请写清"镜头切至谁、什么景别、什么机位、画面里保留谁/什么空间锚点"\."\)'
    replacement = "issues.append('- 受击/反应落点缺少明确切镜：请写清\"镜头切至谁、什么景别、什么机位、画面里保留谁/什么空间锚点\"。')"
    content = re.sub(pattern, replacement, content)
    print("Fixed with regex")

# Write the fixed file
with open('agents/director_graph.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
