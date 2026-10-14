import base64, httpx
class NanoBananaProvider:
    def __init__(self, endpoint: str, api_key: str, timeout: int): self.endpoint,self.key,self.timeout=endpoint,api_key,timeout
    async def edit(self, image: bytes, instruction: str) -> bytes:
        if not self.endpoint or not self.key: raise RuntimeError("Nano Banana is not configured")
        payload={"contents":[{"parts":[{"text":instruction},{"inlineData":{"mimeType":"image/png","data":base64.b64encode(image).decode()}}]}],"generationConfig":{"responseModalities":["TEXT","IMAGE"]}}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r=await c.post(self.endpoint+"?key="+self.key,json=payload); r.raise_for_status(); body=r.json()
        for cand in body.get("candidates",[]):
            for part in cand.get("content",{}).get("parts",[]):
                d=part.get("inlineData",{}).get("data")
                if d: return base64.b64decode(d)
        raise RuntimeError("Nano Banana returned no image")
