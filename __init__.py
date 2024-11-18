# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import time

import mss
from ovos_config import Configuration
from ovos_utils.log import LOG

from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill


class ScreenshotSkill(OVOSSkill):

    def initialize(self):
        self.add_event("ovos.display.screenshot.get.response",
                       self.handle_screenshot_taken)

    @property
    def is_ovos_shell(self) -> bool:
        return Configuration().get("gui", {}).get("extension", "") == "ovos-gui-plugin-shell-companion"

    @property
    def screenshots_folder(self) -> str:
        p = self.settings.get("screenshots_path") or "~/Pictures/Screenshots"
        p = os.path.expanduser(p)
        os.makedirs(p, exist_ok=True)
        return p

    def notify(self, output):
        display_message = f"Screenshot saved to {output}"
        self.gui.show_notification(display_message)
        LOG.debug(f"screenshot saved: {output}")
        self.speak_dialog("screenshot.taken")

    def handle_screenshot_taken(self, message):
        result = message.data.get("result")
        self.notify(result)

    @intent_handler("take.screenshot.intent")
    def handle_screenshot_intent(self, message):
        if self.is_ovos_shell:
            LOG.debug("Taking screenshot via ovos-shell")
            self.bus.emit(message.forward("ovos.display.screenshot.get",
                                          {"folderpath": self.screenshots_folder}))
            return

        output = os.path.join(self.screenshots_folder, f"{time.time()}.png")
        try:
            with mss.mss() as sct:
                screenshot = sct.shot(output=output)
            self.notify(output)
        except Exception as e:
            LOG.error(f"Failed to take screenshot: {e}")
            self.speak_dialog("screenshot.failed")

