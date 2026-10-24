"""Leobog Hi75C ISP entry helper (Windows, no external dependencies).

Lists the vendor HID collection and, with --send, writes the vendor feature
report that makes the firmware jump to the ISP bootloader.

The firmware compares the first two bytes of the report with 0x05 0x75 and
then runs the same ISP entry sequence as SMK's isp_jump().

Usage:
    python hi75c_isp.py            # list matching HID collections
    python hi75c_isp.py --send     # send the ISP entry report
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
USAGE_PAGE = 0xFF00
USAGE = 0x0001


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wt.DWORD),
        ("Data2", wt.WORD),
        ("Data3", wt.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wt.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", wt.ULONG),
        ("VendorID", wt.USHORT),
        ("ProductID", wt.USHORT),
        ("VersionNumber", wt.USHORT),
    ]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wt.USHORT),
        ("UsagePage", wt.USHORT),
        ("InputReportByteLength", wt.USHORT),
        ("OutputReportByteLength", wt.USHORT),
        ("FeatureReportByteLength", wt.USHORT),
        ("Reserved", wt.USHORT * 17),
        ("NumberLinkCollectionNodes", wt.USHORT),
        ("NumberInputButtonCaps", wt.USHORT),
        ("NumberInputValueCaps", wt.USHORT),
        ("NumberInputDataIndices", wt.USHORT),
        ("NumberOutputButtonCaps", wt.USHORT),
        ("NumberOutputValueCaps", wt.USHORT),
        ("NumberOutputDataIndices", wt.USHORT),
        ("NumberFeatureButtonCaps", wt.USHORT),
        ("NumberFeatureValueCaps", wt.USHORT),
        ("NumberFeatureDataIndices", wt.USHORT),
    ]


hid = ctypes.WinDLL("hid.dll")
setupapi = ctypes.WinDLL("setupapi.dll")
kernel32 = ctypes.WinDLL("kernel32.dll")

hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
hid.HidD_GetAttributes.argtypes = [wt.HANDLE, ctypes.POINTER(HIDD_ATTRIBUTES)]
hid.HidD_GetPreparsedData.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid.HidD_SetFeature.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG]
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]

setupapi.SetupDiGetClassDevsW.restype = wt.HANDLE
setupapi.SetupDiGetClassDevsW.argtypes = [
    ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD,
]
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
    wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD,
    ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
]
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    wt.HANDLE, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), ctypes.c_void_p,
    wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p,
]
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wt.HANDLE]

kernel32.CreateFileW.restype = wt.HANDLE
kernel32.CreateFileW.argtypes = [
    wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD,
    wt.HANDLE,
]
kernel32.CloseHandle.argtypes = [wt.HANDLE]


def guid_from_string(text):
    guid = GUID()
    hr = ctypes.windll.ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(guid))
    if hr != 0:
        raise OSError(f"CLSIDFromString failed: {hr:#x}")
    return guid


def enumerate_paths():
    guid = guid_from_string(GUID_DEVINTERFACE_HID)
    info = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if info == INVALID_HANDLE_VALUE:
        raise OSError("SetupDiGetClassDevs failed")

    paths = []
    index = 0
    while True:
        iface = SP_DEVICE_INTERFACE_DATA()
        iface.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
        ok = setupapi.SetupDiEnumDeviceInterfaces(
            info, None, ctypes.byref(guid), index, ctypes.byref(iface)
        )
        if not ok:
            break
        index += 1

        required = wt.DWORD(0)
        setupapi.SetupDiGetDeviceInterfaceDetailW(
            info, ctypes.byref(iface), None, 0, ctypes.byref(required), None
        )
        if required.value == 0:
            continue
        buf = ctypes.create_string_buffer(required.value)
        ctypes.cast(buf, ctypes.POINTER(wt.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
        ok = setupapi.SetupDiGetDeviceInterfaceDetailW(
            info, ctypes.byref(iface), buf, required.value, ctypes.byref(required), None
        )
        if not ok:
            continue
        path = ctypes.wstring_at(ctypes.addressof(buf) + 4)
        paths.append(path)

    setupapi.SetupDiDestroyDeviceInfoList(info)
    return paths


def open_path(path):
    return kernel32.CreateFileW(
        path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
        None, OPEN_EXISTING, 0, None,
    )


def describe(handle):
    attr = HIDD_ATTRIBUTES()
    attr.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
    if not hid.HidD_GetAttributes(handle, ctypes.byref(attr)):
        return None
    preparsed = ctypes.c_void_p()
    if not hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
        return None
    caps = HIDP_CAPS()
    try:
        if hid.HidP_GetCaps(preparsed, ctypes.byref(caps)) < 0:
            return None
    finally:
        hid.HidD_FreePreparsedData(preparsed)
    return attr, caps


def find_vendor():
    matches = []
    for path in enumerate_paths():
        handle = open_path(path)
        if handle == INVALID_HANDLE_VALUE:
            continue
        try:
            info = describe(handle)
            if not info:
                continue
            attr, caps = info
            if attr.VendorID == VID and attr.ProductID == PID:
                matches.append((path, attr, caps))
        finally:
            kernel32.CloseHandle(handle)
    return matches


def main():
    matches = find_vendor()
    if not matches:
        print(f"No HID collection with VID {VID:04X} PID {PID:04X} found.")
        return 1

    print(f"{len(matches)} matching collection(s):")
    target = None
    for path, attr, caps in matches:
        print(
            f"  usage_page=0x{caps.UsagePage:04X} usage=0x{caps.Usage:04X} "
            f"feature_len={caps.FeatureReportByteLength} "
            f"iface_hint={path.split('&mi_')[-1].split('#')[0] if '&mi_' in path else '?'}"
        )
        print(f"    {path}")
        # The vendor control collection carries report ID 5 with 5 data bytes
        # (FeatureReportByteLength == 6). Other collections on the same usage
        # page are input-only (length 0) or the 520-byte RGB report; picking the
        # first usage match is not stable across enumeration orders.
        if (
            target is None
            and caps.UsagePage == USAGE_PAGE
            and caps.Usage == USAGE
            and caps.FeatureReportByteLength == 6
        ):
            target = (path, caps)

    if target is None:
        print("No vendor usage 0xFF00/0x0001 collection found.")
        return 2

    if "--send" not in sys.argv and "--seq" not in sys.argv:
        print("\nDry run. Pass --send or --seq to write feature reports.")
        return 0

    path, caps = target
    length = caps.FeatureReportByteLength
    if length < 6:
        print(f"Unexpected feature report length: {length}")
        return 3

    def send(data):
        report = bytearray(length)
        report[0] = 0x05
        report[1:1 + len(data)] = bytes(data)
        handle = open_path(path)
        if handle == INVALID_HANDLE_VALUE:
            print("CreateFile failed:", ctypes.GetLastError())
            return False
        try:
            ok = hid.HidD_SetFeature(handle, bytes(report), length)
            print("HidD_SetFeature:", "OK" if ok else f"FAILED (err={ctypes.GetLastError()})")
            return bool(ok)
        finally:
            kernel32.CloseHandle(handle)

    if "--seq" in sys.argv:
        # Step 1: vendor command [05 03 01 ?? 06 00] -> state 9.
        # EP0_OUT_BUF[0] is the report ID (0x05), so the data starts at 0x03.
        if not send([0x03, 0x01, 0x00, 0x06, 0x00]):
            return 5
        time.sleep(0.2)
        # Step 2: EP0_OUT_BUF = [05 75 ...] -> ISP jump.
        if not send([0x75, 0x00, 0x00, 0x00, 0x00]):
            return 6
        return 0

    return 0 if send([0x05, 0x75, 0x00, 0x00, 0x00]) else 5


if __name__ == "__main__":
    sys.exit(main())
