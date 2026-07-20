import re

dark_qss = open("src/ui/themes/mint_dark.qss").read()
light_qss = open("src/ui/themes/mint_light.qss").read()

dark_palette = {
    "@ACCENT@": "#45B7A0",
    "@ACCENT_HOVER@": "#3CA38E",
    "@ACCENT_PRESSED@": "#34907D",
    "@ACCENT_MUTED@": "#1F5C4F",
    "@BACKGROUND@": "#1B1F2B",
    "@SURFACE@": "#232838",
    "@SURFACE_RAISED@": "#2A3042",
    "@TEXT@": "#E8ECEF",
    "@TEXT_SECONDARY@": "#8A94A6",
    "@TEXT_MUTED@": "#4A5568",
    "@BORDER@": "#2E3548",
    "@DANGER@": "#E17055",
    "@DANGER_HOVER@": "#D63031",
}

# Replace colors with placeholders in dark
template = dark_qss
for var, color in dark_palette.items():
    template = template.replace(color, var)

# Replace paddings to enforce 8px grid
template = template.replace("padding: 7px 16px;", "padding: 8px 16px;")
template = template.replace("padding: 7px 10px;", "padding: 8px 12px;")
template = template.replace("border-radius: 5px;", "border-radius: 8px;")
template = template.replace("border-radius: 6px;", "border-radius: 8px;")

# Add font fallbacks
template = template.replace('font-family: "Inter", "Segoe UI", "SF Pro Text", system-ui, sans-serif;', 'font-family: "Inter", "Roboto", "Segoe UI", system-ui, sans-serif;')

with open("src/ui/themes/base.template.qss", "w") as f:
    f.write(template)

print("Generated base.template.qss")
