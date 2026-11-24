import shutil
import tempfile
import unittest
from pathlib import Path

from web2apk.template_engine import TemplateEngine


class TestOttInteractivity(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="web2apk_ott_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ott_interactivity_generated_artifacts(self):
        project_dir = self.test_dir / "project"
        TemplateEngine.generate_project(
            target_dir=str(project_dir),
            app_name="StreamOTT",
            package_name="com.streamott.play",
            version_code=1,
            version_name="1.0.0",
            is_fullscreen=True,
            remote_url="https://streaming.example.com",
            is_tv_compatible=True,
            screen_orientation="landscape"
        )

        # 1. Verify OttStreamingController.kt exists
        kotlin_file = project_dir / "app/src/main/java/com/streamott/play/OttStreamingController.kt"
        self.assertTrue(kotlin_file.exists(), "OttStreamingController.kt must be generated")
        kotlin_src = kotlin_file.read_text(encoding="utf-8")
        self.assertIn("class OttStreamingController", kotlin_src)
        self.assertIn("seekMedia", kotlin_src)
        self.assertIn("togglePlayback", kotlin_src)

        # 2. Verify OTT drawables exist
        res_dir = project_dir / "app/src/main/res"
        self.assertTrue((res_dir / "drawable/ott_hud_bg.xml").exists())
        self.assertTrue((res_dir / "drawable/ott_nav_bg.xml").exists())
        self.assertTrue((res_dir / "drawable/ott_btn_bg.xml").exists())
        self.assertTrue((res_dir / "drawable/ott_ripple_bg.xml").exists())

        # 3. Verify activity_main.xml has OTT widgets
        layout_xml = (res_dir / "layout/activity_main.xml").read_text(encoding="utf-8")
        self.assertIn("ottHudBadge", layout_xml)
        self.assertIn("ottRippleLeft", layout_xml)
        self.assertIn("ottRippleRight", layout_xml)
        self.assertIn("ottFloatingControls", layout_xml)
        self.assertIn("ottBottomNav", layout_xml)
        self.assertIn("btnOttPlayPause", layout_xml)
        self.assertIn("btnOttSpeed", layout_xml)
        self.assertIn("btnOttPip", layout_xml)

        # 4. Verify build.gradle includes Kotlin support
        build_gradle = (project_dir / "app/build.gradle").read_text(encoding="utf-8")
        self.assertIn("org.jetbrains.kotlin.android", build_gradle)
        self.assertIn("kotlin-stdlib", build_gradle)

        # 5. Verify MainActivity.java contains OTT methods & bridge
        activity_java = (project_dir / "app/src/main/java/com/streamott/play/MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("setupOttControls", activity_java)
        self.assertIn("triggerPictureInPicture", activity_java)
        self.assertIn("seekMedia", activity_java)
        self.assertIn("applyPlaybackSpeed", activity_java)
        self.assertIn("DOUBLE_TAP_TIMEOUT", activity_java)
        self.assertIn("triggerPiP", activity_java)
