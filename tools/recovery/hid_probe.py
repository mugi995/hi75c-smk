"""Probe all Hi75C HID collections and try sending the ISP feature reports.

If the vendor collection (interface 1) is broken but the keyboard collection
(interface 0) still accepts feature reports, this can recover the device
without WinUSB.

Usage:
    python hid_probe.py           # list collections
    python hid_probe.py --send    # try the ISP reports on every collection
"""

import ctypes
import ctypes.wintypes as wt
import sys
import time

GUID_DEVINTERFACE_HID = "{4D1E55B2-F16F-11CF-88CB-001111000030}"
DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
VID = 0x258A
PID = 0x010C


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wt.DWORD), ("Data2", wt.WORD), ("Data3", wt.WORD), ("Data4", ctypes.c_ubyte * 8)]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("InterfaceClassGuid", GUID), ("Flags", wt.DWORD), ("Reserved", ctypes.c_void_p)]


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Size", wt.ULONG), ("VendorID", wt.USHORT), ("ProductID", wt.USHORT), ("VersionNumber", wt.USHORT)]


setupapi = ctypes.WinDLL("setupapi.dll")
kernel32 = ctypes.WinDLL("kernel32.dll")
hid = ctypes.WinDLL("hid.dll")

setupapi.SetupDiGetClassDevsW.restype = wt.HANDLE
setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD]
setupapi.SetupDiEnumDeviceInterfaces.restype = wt.BOOL
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wt.BOOL
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [wt.HANDLE, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wt.HANDLE]

kernel32.CreateFileW.restype = wt.HANDLE
kernel32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
kernel32.CloseHandle.argtypes = [wt.HANDLE]

hid.HidD_GetAttributes.restype = wt.BOOL
hid.HidD_GetAttributes.argtypes = [wt.HANDLE, ctypes.POINTER(HIDD_ATTRIBUTES)]
hid.HidD_GetPreparsedData.restype = wt.BOOL
hid.HidD_GetPreparsedData.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid.HidP_GetCaps.restype = ctypes.c_long
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
hid.HidD_SetFeature.restype = wt.BOOL
hid.HidD_SetFeature.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wt.USHORT), ("UsagePage", wt.USHORT),
        ("InputReportByteLength", wt.USHORT), ("OutputReportByteLength", wt.USHORT),
        ("FeatureReportByteLength", wt.USHORT),
        ("Reserved", wt.USHORT * 17),
        ("NumberLinkCollectionNodes", wt.USHORT), ("NumberInputButtonCaps", wt.USHORT),
        ("NumberInputValueCaps", wt.USHORT), ("NumberInputDataIndices", wt.USHORT),
        ("NumberOutputButtonCaps", wt.USHORT), ("NumberOutputValueCaps", wt.USHORT),
        ("NumberOutputDataIndices", wt.USHORT), ("NumberFeatureButtonCaps", wt.USHORT),
        ("NumberFeatureValueCaps", wt.USHORT), ("NumberFeatureDataIndices", wt.USHORT),
    ]


def guid_from_string(s):
    g = GUID()
    ctypes.windll.ole32.CLSIDFromString(wt.LPCWSTR(s), ctypes.byref(g))
    return g


def enum_paths():
    guid = guid_from_string(GUID_DEVINTERFACE_HID)
    hdev = setupapi.SetupDiGetClassDevsW(ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE)
    if hdev == INVALID_HANDLE_VALUE:
        return []
    paths = []
    try:
        i = 0
        while True:
            did = SP_DEVICE_INTERFACE_DATA()
            did.cbSize = ctypes.sizeof(did)
            if not setupapi.SetupDiEnumDeviceInterfaces(hdev, None, ctypes.byref(guid), i, ctypes.byref(did)):
                break
            i += 1
            need = wt.DWORD(0)
            setupapi.SetupDiGetDeviceInterfaceDetailW(hdev, ctypes.byref(did), None, 0, ctypes.byref(need), None)
            if need.value == 0:
                continue
            buf = ctypes.create_string_buffer(need.value)
            ctypes.cast(buf, ctypes.POINTER(wt.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            if not setupapi.SetupDiGetDeviceInterfaceDetailW(hdev, ctypes.byref(did), buf, need.value, ctypes.byref(need), None):
                continue
            paths.append(ctypes.wstring_at(ctypes.addressof(buf) + ctypes.sizeof(wt.DWORD)))
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(hdev)
    return paths


def get_caps(handle):
    pp = ctypes.c_void_p()
    if not hid.HidD_GetPreparsedData(handle, ctypes.byref(pp)):
        return None
    try:
        caps = HIDP_CAPS()
        if hid.HidP_GetCaps(pp, ctypes.byref(caps)) < 0:
            return None
        return caps
    finally:
        hid.HidD_FreePreparsedData(pp)


def main():
    paths = enum_paths()
    targets = []
    for p in paths:
        h = kernel32.CreateFileW(p, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
        if h == INVALID_HANDLE_VALUE:
            continue
        attr = HIDD_ATTRIBUTES()
        attr.Size = ctypes.sizeof(attr)
        if not hid.HidD_GetAttributes(h, ctypes.byref(attr)):
            kernel32.CloseHandle(h)
            continue
        if attr.VendorID != VID or attr.ProductID != PID:
            kernel32.CloseHandle(h)
            continue
        caps = get_caps(h)
        up = caps.UsagePage if caps else 0
        us = caps.Usage if caps else 0
        fl = caps.FeatureReportByteLength if caps else 0
        print(f"VID {attr.VendorID:04X}:{attr.ProductID:04X} usage {up:04X}:{us:04X} feature_len {fl}  {p}")
        targets.append((p, fl))
        kernel32.CloseHandle(h)

    if "--send" not in sys.argv:
        return 0

    reports = [[0x05, 0x03, 0x01, 0x00, 0x06, 0x00], [0x05, 0x75, 0x00, 0x00, 0x00, 0x00]]
    for p, fl in targets:
        print("trying", p)
        h = kernel32.CreateFileW(p, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
        if h == INVALID_HANDLE_VALUE:
            print("  open failed", ctypes.GetLastError())
            continue
        for i, rep in enumerate(reports):
            buf = ctypes.create_string_buffer(bytes(rep), len(rep))
            ok = hid.HidD_SetFeature(h, buf, len(rep))
            print(f"  report {i+1}: {'OK' if ok else 'FAILED'} err={ctypes.GetLastError()}")
        kernel32.CloseHandle(h)
        time.sleep(0.3)
    print("done; check for 0603:1020")
    return 0


if __name__ == "__main__":
    sys.exit(main())
