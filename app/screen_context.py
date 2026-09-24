from __future__ import annotations
import base64, io

class ScreenContext:
    def __init__(self): self.last_error=""
    def capture_jpeg(self,quality=55,max_width=1600):
        try:
            import mss
            from PIL import Image
            with mss.mss() as sct:
                shot=sct.grab(sct.monitors[1]); img=Image.frombytes("RGB",shot.size,shot.rgb)
                if img.width>max_width:
                    h=int(img.height*max_width/img.width); img=img.resize((max_width,h))
                b=io.BytesIO(); img.save(b,format="JPEG",quality=quality,optimize=True); return b.getvalue()
        except Exception as e:
            self.last_error=f"{type(e).__name__}: {e}"; return None
    def crop_from_normalized(self,jpeg:bytes,x:float,y:float,span=.32):
        try:
            from PIL import Image
            img=Image.open(io.BytesIO(jpeg)).convert("RGB"); x=max(0,min(1,float(x))); y=max(0,min(1,float(y)))
            hw=int(img.width*span/2); hh=int(img.height*span/2); cx=int(img.width*x); cy=int(img.height*y)
            crop=img.crop((max(0,cx-hw),max(0,cy-hh),min(img.width,cx+hw),min(img.height,cy+hh)))
            b=io.BytesIO(); crop.save(b,format="JPEG",quality=65,optimize=True); return b.getvalue()
        except Exception:return None
    @staticmethod
    def data_url(jpeg:bytes): return "data:image/jpeg;base64,"+base64.b64encode(jpeg).decode()
