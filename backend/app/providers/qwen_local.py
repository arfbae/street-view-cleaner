import base64, httpx
from ..config import settings

class QwenLocalProvider:
    def __init__(self, base_url: str, model: str, timeout: int, edit_path: str|None=None):
        self.base_url,self.model,self.timeout=base_url.rstrip('/'),model,timeout
        self.edit_path=edit_path or settings.qwen_edit_path
    async def edit(self, image: bytes, instruction: str) -> bytes:
        if not self.base_url: raise RuntimeError("QWEN_BASE_URL is not configured")
        files={"image":("input.png",image,"image/png")}; data={"model":self.model,"prompt":instruction}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response=await client.post(self.base_url+"/"+self.edit_path.lstrip("/"),files=files,data=data)
            response.raise_for_status()
            if response.headers.get("content-type","").startswith("image/"): return response.content
            body=response.json()
        for item in body.get("data",[]):
            if item.get("b64_json"): return base64.b64decode(item["b64_json"])
            if item.get("url"):
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    fetched=await client.get(item["url"]); fetched.raise_for_status(); return fetched.content
        raise RuntimeError("Qwen returned no image")
