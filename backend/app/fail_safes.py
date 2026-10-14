from .validation import valid_image, structural_integrity_check, hallucination_check, decode

def validate_output(original, output_bytes, ui_regions=None, threshold: float=0.15):
    ok, reason=valid_image(output_bytes, original)
    if not ok: return False, reason
    cleaned=decode(output_bytes)
    ok, reason=structural_integrity_check(original, cleaned, ui_regions, threshold)
    if not ok: return False, reason
    return hallucination_check(original, cleaned, ui_regions)

def batch_should_stop(results, failure_ratio: float):
    if not results: return False
    failures=sum(1 for item in results if item.get("status") in {"manual_review","failed"})
    return failures / len(results) > failure_ratio
