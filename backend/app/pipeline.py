import json, uuid
from pathlib import Path
from .config import settings
from .presets import instruction_for
from .fail_safes import validate_output, batch_should_stop
from .ui_detection import detect_ui, enrich_with_google_vision
from .image_io import load_image, save_bytes
from .logging_module import logger
from .edit_strategies import strategy_for_preset, normalize_regions

async def edit_safe(original:bytes, instruction:str, selected:str, preset:str|None, regions=None):
    names=[]
    for name in [selected,"nano_banana","qwen_local"]:
        if name not in names and name in {"mock","nano_banana","qwen_local"}: names.append(name)
    errors=[]
    normalized=normalize_regions(regions)
    for name in names:
        strategy=strategy_for_preset(preset, name)
        for attempt in range(settings.retry_count+1):
            try:
                result=await strategy.edit(original,instruction,normalized)
                ok,reason=validate_output(load_image(original),result,normalized,settings.structural_diff_threshold)
                if ok: return result,name,"ok",None
                errors.append(f"{name}:{reason}")
            except Exception as exc:
                errors.append(f"{name}:{type(exc).__name__}")
    logger.warning("all providers failed validation: %s", ",".join(errors))
    return None,None,"manual_review",errors[-1] if errors else "manual_review"

async def process_item(job_id,item_id,filename,data,requested_provider,requested_preset):
    job=Path(settings.storage_root)/job_id; (job/"original").mkdir(parents=True,exist_ok=True); (job/"output").mkdir(exist_ok=True)
    original_path=job/"original"/f"{item_id}_{Path(filename).name}"; save_bytes(original_path,data)
    try: image=load_image(data)
    except Exception: return {"item_id":item_id,"filename":filename,"status":"failed","reason":"invalid_image"}
    profile="instagram" if requested_preset=="instagram_screenshot_cleaner" else "street_view"
    detection=detect_ui(image, profile=profile)
    detection=await enrich_with_google_vision(image,data,detection)
    preset,instruction=instruction_for(detection["confidence"],requested_preset)
    selected_strategy=strategy_for_preset(preset, requested_provider)
    if hasattr(selected_strategy, "regions_for_image"):
        exact_regions=selected_strategy.regions_for_image(image)
        ocr_regions=[region for region in detection["regions"] if region.get("name")=="google_vision_ui_text"]
        detection["regions"]=exact_regions + ocr_regions
    result,used,status,reason=await edit_safe(data,instruction,requested_provider,preset,detection["regions"])
    out_path=None
    if result:
        out_path=job/"output"/f"{item_id}.png"; save_bytes(out_path,result)
    return {"item_id":item_id,"filename":filename,"status":status,"provider":used,"preset":preset,"ui_profile":detection["profile"],"ui_confidence":detection["confidence"],"ui_regions":detection["regions"],"reason":reason,"output":str(out_path) if out_path else None}

async def process_job(job_id,items,provider_name,preset):
    results=[]
    for filename,data in items:
        item=await process_item(job_id,uuid.uuid4().hex,filename,data,provider_name,preset); results.append(item)
        if batch_should_stop(results,settings.max_batch_failure_ratio):
            logger.warning("batch %s stopped above failure ratio",job_id); break
    status="stopped" if batch_should_stop(results,settings.max_batch_failure_ratio) else "completed"
    job=Path(settings.storage_root)/job_id; save_bytes(job/"manifest.json",json.dumps({"job_id":job_id,"status":status,"results":results},indent=2).encode())
    return results,status
