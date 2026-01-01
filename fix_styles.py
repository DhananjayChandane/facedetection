import re

# Read the file
with open('generate_project_report.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all style references
content = content.replace("styles['Heading1']", "styles['CustomHeading1']")
content = content.replace("styles['Heading2']", "styles['CustomHeading2']")
content = content.replace("styles['Body']", "styles['CustomBody']")
content = content.replace("styles['Code']", "styles['CustomCode']")
content = content.replace("styles['Center']", "styles['CustomCenter']")

# Write back
with open('generate_project_report.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Style references updated successfully!")
