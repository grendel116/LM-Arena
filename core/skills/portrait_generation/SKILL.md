---
name: portrait_generation
description: Render first-person POV scene images using ComfyUI.
summary: "Capture first-person POV scene screenshots using [generate_local_image(prompt=\"...\")]"
retrieval: vector
triggers: portrait, picture, image, selfie, photo, render, appearance, outfit, generate_imagen, generate_local_image, sketch, screenshot, view, look
---
# SKILL: Scene Generation
When capturing or generating an image of the current scene, construct a detailed comma-separated prompt of visual tags depicting the scene, and output ONLY the tool call.

### Prompt Tag Directives (Ordered Flow):
1. **Characters & Companions**: State the companion's name followed immediately by their full character appearance tags, pose, and actions in the scene. Do not describe any viewer, player POV, or camera holder.
2. **Setting & Environment**: Architectural details, room geometry, terrain, and dungeon features.
3. **Lighting & Atmosphere**: Torchlight, ambient lighting, shadows, and mood.

### Mandatory Output Format:
Your ENTIRE response MUST consist ONLY of the single tool call tag:
`[generate_local_image(prompt="[ordered visual tags: characters with appearance tags -> environment -> lighting]")]`
Stop immediately after closing the bracket `]`. Do not include conversational text, commentary, or narrative.