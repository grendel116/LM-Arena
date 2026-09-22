---
name: portrait_generation
description: Render follower portraits using ComfyUI.
summary: "Generate character portraits using [generate_local_image(prompt=\"...\")]"
retrieval: vector
triggers: portrait, picture, image, selfie, photo, render, appearance, outfit, generate_imagen, generate_local_image, sketch
---
# SKILL: Follower Portrait Generation
When generating a portrait, construct a detailed comma-separated prompt of visual tags capturing the full scene context, and output ONLY the tool call.

### Prompt Tag Directives:
1. **Subject**: Depict {{char}} as the main subject (e.g. `1girl, solo, {{char}}`). Do not invent extra subjects.
2. **Current Outfit & Appearance**: Include the character's current clothing, armor, and accessories.
3. **Setting & Environment**: Include the setting, background, atmosphere, and lighting from the character's current environment.

### Mandatory Output Format:
Your ENTIRE response MUST consist ONLY of the single tool call tag:
`[generate_local_image(prompt="[comma-separated setting, outfit, pose, and expression tags]")]`
Stop immediately after closing the bracket `]`. Do not include conversational text, commentary, or narrative.