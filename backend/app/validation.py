from io import BytesIO
import cv2
import numpy as np
from PIL import Image
from .ui_detection import mask_from_regions

def decode(data: bytes) -> Image.Image:
    if not data: raise ValueError("empty_image")
    im=Image.open(BytesIO(data)); im.verify()
    im=Image.open(BytesIO(data)); im.load(); return im.convert("RGB")

def resolution_check(original: Image.Image, cleaned: Image.Image) -> tuple[bool,str]:
    return (True,"ok") if original.size==cleaned.size else (False,"resolution_changed")

def corruption_check(data: bytes|None, original: Image.Image) -> tuple[bool,str]:
    if not data: return False,"empty_output"
    try: out=decode(data)
    except Exception: return False,"corrupt_output"
    if out.width<2 or out.height<2: return False,"invalid_dimensions"
    ok,reason=resolution_check(original,out)
    return (ok,reason)

def _changed_mask(original: Image.Image, cleaned: Image.Image) -> np.ndarray:
    a=cv2.cvtColor(np.asarray(original),cv2.COLOR_RGB2GRAY)
    b=cv2.cvtColor(np.asarray(cleaned),cv2.COLOR_RGB2GRAY)
    diff=cv2.absdiff(a,b)
    return (diff>12).astype(np.uint8)*255

def structural_integrity_check(original: Image.Image, cleaned: Image.Image, ui_regions=None, threshold: float=0.15) -> tuple[bool,str]:
    ok,reason=resolution_check(original,cleaned)
    if not ok: return False,reason
    changed=_changed_mask(original,cleaned)
    allowed=mask_from_regions(original.size,ui_regions)
    protected=allowed==0
    protected_pixels=int(protected.sum())
    changed_protected=int(((changed>0)&protected).sum())
    if protected_pixels and changed_protected/protected_pixels>threshold:
        return False,"structural_diff_exceeded"
    # Protect high-contrast edges from being broadly repainted outside UI zones.
    edges=cv2.Canny(cv2.cvtColor(np.asarray(original),cv2.COLOR_RGB2GRAY),80,160)>0
    edge_changes=((changed>0)&edges&protected).sum()
    edge_count=max(1,int((edges&protected).sum()))
    if edge_changes/edge_count>threshold:
        return False,"protected_edges_changed"
    return True,"ok"

def hallucination_check(original: Image.Image, cleaned: Image.Image, ui_regions=None) -> tuple[bool,str]:
    changed=_changed_mask(original,cleaned)
    allowed=mask_from_regions(original.size,ui_regions)
    outside=((changed>0)&(allowed==0)).astype(np.uint8)*255
    n, labels, stats, _=cv2.connectedComponentsWithStats(outside,8)
    # Any sizeable disconnected change outside the UI mask is treated as a possible new object.
    for i in range(1,n):
        if int(stats[i,cv2.CC_STAT_AREA]) >= max(64, int(original.width*original.height*0.0005)):
            return False,"possible_new_object"
    return True,"ok"

def valid_image(data: bytes|None, original: Image.Image) -> tuple[bool,str]:
    ok,reason=corruption_check(data,original)
    if not ok: return False,reason
    out=decode(data)
    # Reject all-black/all-white or otherwise degenerate outputs.
    arr=np.asarray(out)
    if float(arr.std())<1.0: return False,"blank_or_invalid_output"
    return True,"ok"
