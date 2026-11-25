#!/bin/bash
# Master an export to a loudness target (default -14 LUFS integrated, true peak -1 dBTP: what YouTube plays at).
#   master_loudness.sh IN.mp4 OUT.mp4 [TARGET_LUFS] [TRUE_PEAK]   video copied untouched, AAC 320k 48 kHz
#   master_loudness.sh IN.wav OUT.wav [TARGET_LUFS] [TRUE_PEAK]   audio only, 24-bit 48 kHz
# Chain: a gentle compressor (2:1 from -21 dB, soft knee) -> gain to just under the target -> limiter at -2 dBFS
# -> two-pass loudnorm in linear mode. Plain loudnorm can't reach -14 when a voice's peaks sit far above its
# average loudness (common with close-mic speech): it quietly falls back to dynamic mode. This chain doesn't.
# Measures the result at the end. Your original file is never changed.
set -e
IN="$1"; OUT="$2"; T="${3:--14}"; TP="${4:--1}"
[ -z "$IN" ] || [ -z "$OUT" ] && { sed -n '2,8p' "$0"; exit 1; }
[ "$IN" = "$OUT" ] && { echo "Write to a new file, not over the original."; exit 1; }
COMP="acompressor=threshold=-21dB:ratio=2:attack=10:release=200:knee=6"
IA=$(ffmpeg -nostats -i "$IN" -vn -af "$COMP,ebur128" -f null - 2>&1 </dev/null | sed -n '/Summary/,$p' | awk '/I:/{print $2}')
G=$(python3 -c "print(round(($T)+0.4-($IA),2))")
CH="$COMP,volume=${G}dB,alimiter=limit=-2dB:attack=3:release=60:level=false:asc=1"
J=$(ffmpeg -nostats -i "$IN" -vn -af "$CH,loudnorm=I=$T:TP=$TP:LRA=11:print_format=json" -f null - 2>&1 </dev/null | sed -n '/^{/,/^}/p')
read a b c t o <<<"$(echo "$J" | python3 -c "import json,sys;j=json.load(sys.stdin);print(j['input_i'],j['input_tp'],j['input_lra'],j['input_thresh'],j['target_offset'])")"
AF="$CH,loudnorm=I=$T:TP=$TP:LRA=11:measured_I=$a:measured_TP=$b:measured_LRA=$c:measured_thresh=$t:offset=$o:linear=true,aresample=48000"
case "$OUT" in
  *.wav) ffmpeg -v error -y -i "$IN" -vn -af "$AF" -c:a pcm_s24le "$OUT" </dev/null ;;
  *)     ffmpeg -v error -y -i "$IN" -map 0:v:0 -map 0:a:0 -c:v copy -af "$AF" -c:a aac -b:a 320k "$OUT" </dev/null ;;
esac
echo "in: $IA LUFS after compressor; gain ${G} dB; after limiter $a LUFS, true peak $b"
echo "result:"
ffmpeg -nostats -i "$OUT" -vn -af ebur128=peak=true -f null - 2>&1 </dev/null | sed -n '/Summary/,$p' | grep -E "I:|LRA:|Peak:"
