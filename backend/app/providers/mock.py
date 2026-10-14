class MockProvider:
    async def edit(self, image: bytes, instruction: str) -> bytes:
        return image
