from pathlib import Path
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'android'/'app'/'src'/'main'/'assets'/'face_landmarker.task'
URL='https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task'
OUT.parent.mkdir(parents=True,exist_ok=True)
if OUT.exists() and OUT.stat().st_size>1_000_000:
    print('Model already present:',OUT)
else:
    print('Downloading MediaPipe Face Landmarker...')
    urllib.request.urlretrieve(URL,OUT)
    if OUT.stat().st_size<1_000_000:raise SystemExit('Downloaded model looks too small')
    print('Saved:',OUT,OUT.stat().st_size)
