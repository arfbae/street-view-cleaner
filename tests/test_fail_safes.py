from PIL import Image
from backend.app.fail_safes import validate_output, batch_should_stop
from backend.app.ui_detection import detect_ui
from backend.app.image_io import encode_png

def test_mock_output_passes_all_safeguards():
    image=Image.new("RGB",(64,48),(20,40,60))
    data=encode_png(image)
    regions=detect_ui(image)["regions"]
    assert validate_output(image,data,regions)==(True,"ok")

def test_resolution_change_fails():
    original=Image.new("RGB",(64,48),(20,40,60))
    changed=Image.new("RGB",(32,24),(20,40,60))
    assert validate_output(original,encode_png(changed))[0] is False

def test_batch_stops_above_twenty_percent():
    results=[{"status":"ok"},{"status":"manual_review"},{"status":"ok"},{"status":"ok"}]
    assert batch_should_stop(results,.20)
