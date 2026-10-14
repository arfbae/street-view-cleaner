from .edit_strategies import InstagramCleaningStrategy

PRESETS={
 "clean_mode":"Remove only clearly identified Street View interface overlays inside the supplied UI mask. Reconstruct only adjacent background pixels. Preserve every real-world object, texture, edge, sign, person, vehicle, building, vegetation element, pole, fence, bin, road marking, shadow, reflection, sky feature, and perspective relationship. Never add, remove, move, or redesign scene content. If uncertain, make no edit.",
 "preserve_scene":"Make the smallest possible edit. Remove only explicitly detected Street View UI pixels. Preserve all scene content exactly. Do not infer or invent hidden objects. If safe reconstruction is not possible, return the original or require manual review.",
 "keep_sky":"Apply preserve_scene and never alter sky gradients, clouds, sun, haze, or horizon geometry except pixels directly occupied by confirmed UI.",
 "keep_edges":"Apply preserve_scene and protect building edges, fence lines, poles, tree trunks, signs, roads, and other high-contrast boundaries.",
 "soft_rebuild":"Use only after a confirmed UI mask and for a narrow adjacent background region. Match local texture, color, lighting, and perspective. Do not reconstruct objects or extend geometry.",
 "instagram_screenshot_cleaner":"Remove only confirmed Instagram screenshot UI: top navigation, story tray, bottom action icons, and post interaction overlays. Preserve the photograph, people, products, text, captions that are part of the scene, architecture, colors, lighting, shadows, and every real-world object. Do not remove or invent scene content. If confidence is low or boundaries are uncertain, use Preserve Scene behavior and require manual review."
}

def instruction_for(confidence:float, requested:str|None):
    if requested=="instagram_screenshot_cleaner": return requested, PRESETS[requested]
    if confidence < .85: return "preserve_scene", PRESETS["preserve_scene"]
    name=requested if requested in PRESETS else "clean_mode"
    return name, PRESETS[name]

# Direct preset-to-strategy registration used by the pipeline and callers.
STRATEGY_BY_PRESET={"instagram_screenshot_cleaner": InstagramCleaningStrategy}

def strategy_class_for(preset: str|None):
    return STRATEGY_BY_PRESET.get(preset)
