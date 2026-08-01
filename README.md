# Screenshot Skill

This OVOS skill takes a screenshot when you ask for one by voice. It saves the image as a PNG file and shows a notification with the file location.

![screen-124907-181124](https://github.com/user-attachments/assets/dde3b4ec-33f2-4f2c-a17f-2b8550c4cc81)

**Supported platforms**: ovos-shell, Windows, macOS, Linux and OpenBSD

## Install

```bash
pip install ovos-skill-screenshot
```

## Usage

Say one of these phrases to take a screenshot:

* "take a screenshot"
* "capture the screen"

The skill saves the screenshot to `~/Pictures/Screenshots` by default. To use a different folder, set `screenshots_path` in the skill settings.

On ovos-shell, the skill asks the shell to take the screenshot. On other platforms, it captures the screen with the [mss](https://github.com/BoboTiG/python-mss) library.

## Related projects

* [OpenVoiceOS/ovos-core](https://github.com/OpenVoiceOS/ovos-core): the assistant this skill runs on
* [OpenVoiceOS/ovos-gui-plugin-shell-companion](https://github.com/OpenVoiceOS/ovos-gui-plugin-shell-companion): the shell extension this skill talks to for screenshots on ovos-shell

## License

Apache-2.0
