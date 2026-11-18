#!/bin/sh
set -eu
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
sdk=${ANDROID_SDK_ROOT:?Set ANDROID_SDK_ROOT to the Android SDK path}
jdk=${BLUELINE_ANDROID_JDK:?Set BLUELINE_ANDROID_JDK to a JDK 17 path}
signing=${BLUELINE_ANDROID_SIGNING:?Set BLUELINE_ANDROID_SIGNING to a private signing directory}
destination=${1:?Supply the output APK path}
tools=$sdk/build-tools/36.0.0
platform=$sdk/platforms/android-35/android.jar

export PATH="$jdk/bin:$PATH"
stage=$(mktemp -d)
trap 'rm -r -- "$stage"' EXIT
mkdir "$stage/classes"
javac --release 11 -encoding UTF-8 -Xlint:all -cp "$platform" -d "$stage/classes" "$source_dir/MainActivity.java"
jar cf "$stage/classes.jar" -C "$stage/classes" .
"$tools/d8" --min-api 26 --lib "$platform" --output "$stage" "$stage/classes.jar"
"$tools/aapt2" compile --dir "$source_dir/res" -o "$stage/res.zip"
"$tools/aapt2" link -I "$platform" --manifest "$source_dir/AndroidManifest.xml" -R "$stage/res.zip" --auto-add-overlay -o "$stage/resources.apk"
zip -q -j -X "$stage/resources.apk" "$stage/classes.dex"
"$tools/zipalign" -f 4 "$stage/resources.apk" "$stage/aligned.apk"

if [ ! -e "$signing/key.p12" ]; then
    umask 077
    mkdir -p "$signing"
    openssl rand -hex 32 >"$signing/password"
    keytool -genkeypair -keystore "$signing/key.p12" -alias pixel-control -storetype PKCS12 \
        -storepass:file "$signing/password" -keyalg RSA -keysize 3072 -validity 3650 \
        -dname 'CN=Pixel Control local build' >/dev/null
fi
"$tools/apksigner" sign --ks "$signing/key.p12" --ks-key-alias pixel-control \
    --ks-pass "file:$signing/password" --out "$destination" "$stage/aligned.apk"
"$tools/apksigner" verify --verbose "$destination"
"$tools/zipalign" -c 4 "$destination"
