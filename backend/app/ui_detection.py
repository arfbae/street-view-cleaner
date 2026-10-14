from PIL import Image

PROFILES={
 "street_view": {
  "bottom_left_map_inset": (0.00,0.68,0.32,1.00),
  "top_left_address_label": (0.00,0.00,0.48,0.20),
  "bottom_timeline": (0.00,0.84,1.00,1.00),
  "bottom_right_watermark": (0.72,0.72,1.00,1.00),
 },
 "instagram": {
  "top_navigation_bar": (0.00,0.00,1.00,0.12),
  "story_tray": (0.00,0.10,1.00,0.30),
  "post_interaction_overlay": (0.00,0.70,1.00,0.90),
  "bottom_action_icons": (0.00,0.88,1.00,1.00),
 },
}

# Backward-compatible constant for callers that expect the Street View profile.
UI_ZONES=PROFILES["street_view"]

def detect_ui(image:Image.Image, profile:str="street_view") -> dict:
    """Return conservative candidate zones for the selected screenshot profile."""
    if profile not in PROFILES: raise ValueError("unsupported_detection_profile")
    w,h=image.size; regions=[]
    for name,(x1,y1,x2,y2) in PROFILES[profile].items():
        regions.append({"name":name,"box":[int(x1*w),int(y1*h),int(x2*w),int(y2*h)],"confidence":0.50,"profile":profile})
    return {"profile":profile,"confidence":0.50,"regions":regions}

def mask_from_regions(size:tuple[int,int], regions):
    import numpy as np
    if getattr(regions,"ndim",None)==2:
        if regions.shape != (size[1],size[0]): raise ValueError("mask_size_mismatch")
        return (regions>0).astype(np.uint8)*255
    mask=np.zeros((size[1],size[0]),dtype=np.uint8)
    for region in regions or []:
        x1,y1,x2,y2=region["box"]
        mask[max(0,y1):min(size[1],y2),max(0,x1):min(size[0],x2)]=255
    return mask

def patch_ui_regions(image:Image.Image, regions, radius:int=3) -> Image.Image:
    """Apply a deterministic OpenCV Telea patch to masked UI zones.

    This helper is opt-in for local workflows; the normal provider pipeline still
    validates the model result and fails closed rather than blindly patching.
    """
    import cv2, numpy as np
    source=cv2.cvtColor(np.asarray(image.convert("RGB")),cv2.COLOR_RGB2BGR)
    mask=mask_from_regions(image.size,regions)
    kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
    mask=cv2.dilate(mask,kernel,iterations=1)
    patched=cv2.inpaint(source,mask,radius,cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(patched,cv2.COLOR_BGR2RGB))
