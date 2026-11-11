#!/usr/bin/env bash
# Headless Linux toolchain for the kylo-3d-shorts plugin: Blender 5.2 + Mesa EGL (software EEVEE),
# Kokoro TTS (local stand-in for ElevenLabs) and faster-whisper for word timings. Idempotent.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if ! command -v claude >/dev/null || ! claude plugin list 2>/dev/null | grep -q kylo-3d-shorts; then
  claude plugin marketplace add Hitid123/kylo-3d-shorts || true
  claude plugin install kylo-3d-shorts@kylo-3d-shorts || true
fi

if ! ldconfig -p | grep -q libEGL.so.1; then
  apt-get update -qq
  apt-get install -y -qq libegl1 libegl-mesa0 libgl1-mesa-dri libgl1 libglx-mesa0 libxxf86vm1 libxfixes3 \
    libxi6 libxkbcommon0 libsm6 libice6 fonts-dejavu-core >/dev/null
fi

if [ ! -x /opt/blender/blender ]; then
  f=$(curl -sL https://download.blender.org/release/Blender5.2/ | grep -o 'blender-5\.2\.[0-9]*-linux-x64\.tar\.xz' | sort -uV | tail -1)
  curl -sL -o /tmp/blender.tar.xz "https://download.blender.org/release/Blender5.2/$f"
  mkdir -p /opt/blender && tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1
fi
ln -sf /opt/blender/blender /usr/local/bin/blender

if [ ! -x /opt/tts/bin/python ]; then
  python3 -m venv /opt/tts
  /opt/tts/bin/pip install -q kokoro-onnx soundfile faster-whisper pillow numpy
fi
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "/opt/tts/$f" ] || curl -sL -o "/opt/tts/$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
done
echo "setup ok: $(blender --version | head -1)"
