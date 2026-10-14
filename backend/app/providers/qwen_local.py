import httpx
class QwenLocalProvider:
    def __init__(self, base_url: str, model: str, timeout: int): self.base_url,self.model,self.timeout=base_url.rstrip('/'),model,timeout
    async def edit(self, image: bytes, instruction: str) -> bytes:
        if not self.base_url: raise RuntimeError("QWEN_BASE_URL is not configured")
        files={"image":("input.png",image,"image/png")}; data={"model":self.model,"prompt":instruction}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r=await c.post(self.base_url+"/v1/images/edits",files=files,data=data); r.raise_for_status()
            ct=r.headers.get("content-type","")
            if ct.startswith("image/"): return r.content
            body=r.json(); import base64
            for item in body.get("data",[]):
                if item.get("b64_json"): return base64.b64decode(item["b64_json"])
        raise RuntimeError("Qwen returned no image")
