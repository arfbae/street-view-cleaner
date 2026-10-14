from backend.app.presets import instruction_for

def test_low_confidence_is_conservative():
    name,text=instruction_for(.2,None)
    assert name=="preserve_scene"
    assert "scene content" in text

def test_requested_preset_is_allowlisted():
    name,_=instruction_for(.99,"keep_sky")
    assert name=="keep_sky"
