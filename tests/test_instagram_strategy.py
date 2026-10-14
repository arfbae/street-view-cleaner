from PIL import Image
from backend.app.edit_strategies import InstagramCleaningStrategy, strategy_for_preset
from backend.app.presets import strategy_class_for

def test_instagram_strategy_is_registered_and_exactly_profiles_zones():
    assert strategy_class_for("instagram_screenshot_cleaner") is InstagramCleaningStrategy
    assert isinstance(strategy_for_preset("instagram_screenshot_cleaner", "mock"), InstagramCleaningStrategy)
    regions=InstagramCleaningStrategy("mock").regions_for_image(Image.new("RGB",(1000,500)))
    assert regions[0]["box"]==[0,0,1000,60]
    assert {x["name"] for x in regions}=={"top_navigation_title_banner","story_tray_rings","post_engagement_overlay","bottom_application_menu_dock"}
