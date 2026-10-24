"""Try the ISP feature reports on every Hi75C HID collection (including MI_00).

Reuses the proven enumeration from tools/hi75c_isp.py.
"""

import ctypes
import importlib.util
import os
import sys
import time

ISP_PATH = os.path.join(os.path.dirname(__file__), "..", "hi75c_isp.py")
spec = importlib.util.spec_from_file_location("hi75c_isp", ISP_PATH)
isp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(isp)

matches = isp.find_vendor()
print(f"collections: {len(matches)}")
for path, attr, caps in matches:
    print(f"  usage {caps.UsagePage:04X}:{caps.Usage:04X} feature_len {caps.FeatureReportByteLength} {path}")

if "--send" not in sys.argv:
    sys.exit(0)

reports = [[0x05, 0x03, 0x01, 0x00, 0x06, 0x00], [0x05, 0x75, 0x00, 0x00, 0x00, 0x00]]
for path, attr, caps in matches:
    print("trying", path)
    h = isp.open_path(path)
    if h == isp.INVALID_HANDLE_VALUE:
        print("  open failed", ctypes.GetLastError())
        continue
    try:
        for i, rep in enumerate(reports):
            buf = ctypes.create_string_buffer(bytes(rep), len(rep))
            ok = isp.hid.HidD_SetFeature(h, buf, len(rep))
            print(f"  report {i+1}: {'OK' if ok else 'FAILED'} err={ctypes.GetLastError()}")
    finally:
        isp.kernel32.CloseHandle(h)
    time.sleep(0.3)

print("done")
