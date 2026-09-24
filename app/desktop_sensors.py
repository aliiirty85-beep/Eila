from __future__ import annotations
import os,time

class DesktopSensors:
    def __init__(self):
        self._last_pixels=None
        self._last_capture=0.0

    def active_window(self):
        if os.name!="nt":return {"active_window":"","process":""}
        try:
            import ctypes,psutil
            user32=ctypes.windll.user32
            hwnd=user32.GetForegroundWindow()
            length=user32.GetWindowTextLengthW(hwnd)
            buf=ctypes.create_unicode_buffer(length+1)
            user32.GetWindowTextW(hwnd,buf,length+1)
            pid=ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            try:proc=psutil.Process(pid.value).name()
            except Exception:proc=""
            return {"active_window":buf.value,"process":proc}
        except Exception:return {"active_window":"","process":""}

    def input_recent(self,threshold_seconds=5):
        if os.name!="nt":return None
        try:
            import ctypes
            class LASTINPUTINFO(ctypes.Structure):
                _fields_=[("cbSize",ctypes.c_uint),("dwTime",ctypes.c_uint)]
            li=LASTINPUTINFO();li.cbSize=ctypes.sizeof(li)
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):return None
            now=ctypes.windll.kernel32.GetTickCount()
            idle=((now-li.dwTime)&0xffffffff)/1000.0
            return idle<=threshold_seconds
        except Exception:return None

    def screen_change(self):
        now=time.time()
        if now-self._last_capture<2:return None
        self._last_capture=now
        try:
            import mss
            from PIL import Image
            with mss.mss() as sct:
                shot=sct.grab(sct.monitors[1])
                img=Image.frombytes("RGB",shot.size,shot.rgb).convert("L").resize((32,18))
                cur=list(img.getdata())
            if self._last_pixels is None:
                self._last_pixels=cur;return 0.0
            diff=sum(abs(a-b) for a,b in zip(cur,self._last_pixels))/(255*len(cur))
            self._last_pixels=cur
            return round(float(diff),4)
        except Exception:return None

    def sample(self):
        w=self.active_window()
        return {**w,"input_recent":self.input_recent(),"screen_change":self.screen_change()}
