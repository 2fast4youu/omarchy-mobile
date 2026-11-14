# Pixel 3 sensor firmware and FastRPC

The ROM uses the regular Pixel 3 kernel and enables SLPI when the sensor build artifacts are provided. The SMP2P `sleepstate` entry prevents the `sar.cc:27:chre_utils fatal` error observed without it. The analogous SDM670 change was documented by Richard Acayan. [Kernel patch](https://www.mail-archive.com/linux-remoteproc@vger.kernel.org/msg01132.html)

Use HexagonRPC commit `da7a3742ab8d5273a281b70ee11f16fb2cb6a690` from [linux-msm/hexagonrpc](https://github.com/linux-msm/hexagonrpc). Apply the patch with `git apply --unidiff-zero hexagonrpc.patch`, build on Linux ARM64 with Meson, Ninja, a C compiler, libc development files and Linux headers, and install the resulting `hexagonrpcd` as `usr/local/libexec/blueline-hexagonrpcd` under `SENSOR_ARTIFACTS`. The patch builds a static executable and accepts registry writes under the private RAM directory populated at boot.

Copy the signed Pixel 3 SLPI firmware to `usr/lib/firmware/qcom/sdm845/Google/blueline/slpi.mbn` under the same directory. Place the Google vendor `etc/sensors/registry` JSON files in `usr/share/blueline-sensors/config`, the vendor `etc/sensors/sns_reg_config` in `usr/share/blueline-sensors/sns_reg_config`, and the vendor DSP `sdsp` files in `usr/share/blueline-sensors/dsp/sdsp`. Use firmware and configuration from the same factory image. The system generates its registry under `/run/blueline-sensors` from these files at boot.

The Arch package `iio-sensor-proxy` provides the standard system D-Bus API. The Pixel 3 rules add accelerometer and proximity to the SDSP node. The standalone session launches the Omarchy rotation client and keeps portrait on the lock screen.
