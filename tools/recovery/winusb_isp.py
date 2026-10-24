"""Send the Hi75C ISP entry feature reports through WinUSB (no HID driver needed).

Use this when the vendor HID interface (interface 1) fails to start in Windows
and hidapi can no longer open it. Requires WinUSB to be bound to the device
(or to its interface 1) with Zadig.

Usage:
    python winusb_isp.py            # list WinUSB devices
    python winusb_isp.py --send     # send the two ISP reports
"""

import ctypes
import ctypes.wintypes as wt
import sys
import time

GUID_DEVINTERFACE_WINUSB = "{DEE824EF-729B-4A0E-9C14-B7117D33A817}"

DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_FLAG_OVERLAPPED = 0x40000000
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

VID = 0x258A
PID = 0x010C


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


class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("ClassGuid", GUID),
        ("DevInst", wt.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


class WINUSB_SETUP_PACKET(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("RequestType", ctypes.c_ubyte),
        ("Request", ctypes.c_ubyte),
        ("Value", wt.USHORT),
        ("Index", wt.USHORT),
        ("Length", wt.USHORT),
    ]


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_void_p),
        ("InternalHigh", ctypes.c_void_p),
        ("Offset", wt.DWORD),
        ("OffsetHigh", wt.DWORD),
        ("hEvent", wt.HANDLE),
    ]


setupapi = ctypes.WinDLL("setupapi.dll")
kernel32 = ctypes.WinDLL("kernel32.dll")
winusb = ctypes.WinDLL("winusb.dll")

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
kernel32.CreateEventW.restype = wt.HANDLE
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
kernel32.WaitForSingleObject.restype = wt.DWORD
kernel32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
kernel32.GetOverlappedResult.restype = wt.BOOL
kernel32.GetOverlappedResult.argtypes = [wt.HANDLE, ctypes.POINTER(OVERLAPPED), ctypes.POINTER(wt.DWORD), wt.BOOL]

winusb.WinUsb_Initialize.restype = wt.BOOL
winusb.WinUsb_Initialize.argtypes = [wt.HANDLE, ctypes.POINTER(wt.HANDLE)]
winusb.WinUsb_Free.argtypes = [wt.HANDLE]
winusb.WinUsb_ControlTransfer.restype = wt.BOOL
winusb.WinUsb_ControlTransfer.argtypes = [wt.HANDLE, WINUSB_SETUP_PACKET, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]


def guid_from_string(s):
    g = GUID()
    ctypes.windll.ole32.CLSIDFromString(wt.LPCWSTR(s), ctypes.byref(g))
    return g


def enum_winusb_paths():
    guid = guid_from_string(GUID_DEVINTERFACE_WINUSB)
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
            # cbSize is a DWORD at the start of SP_DEVICE_INTERFACE_DETAIL_DATA_W
            ctypes.cast(buf, ctypes.POINTER(wt.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            if not setupapi.SetupDiGetDeviceInterfaceDetailW(hdev, ctypes.byref(did), buf, need.value, ctypes.byref(need), None):
                continue
            paths.append(ctypes.wstring_at(ctypes.addressof(buf) + ctypes.sizeof(wt.DWORD)))
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(hdev)
    return paths


def open_device(path):
    h = kernel32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OVERLAPPED, None)
    return h


def send_control(winusb_handle, request_type, request, value, index, payload):
    buf = ctypes.create_string_buffer(bytes(payload), len(payload))
    transferred = wt.DWORD(0)
    pkt = WINUSB_SETUP_PACKET(request_type, request, value, index, len(payload))
    ov = OVERLAPPED()
    ov.hEvent = kernel32.CreateEventW(None, True, False, None)
    ok = winusb.WinUsb_ControlTransfer(winusb_handle, pkt, buf, len(payload), ctypes.byref(transferred), ctypes.byref(ov))
    if not ok:
        err = ctypes.GetLastError()
        if err == 997:  # ERROR_IO_PENDING
            kernel32.WaitForSingleObject(ov.hEvent, 2000)
            kernel32.GetOverlappedResult(winusb_handle, ctypes.byref(ov), ctypes.byref(transferred), False)
            err = ctypes.GetLastError()
        kernel32.CloseHandle(ov.hEvent)
        return False, transferred.value, err
    kernel32.CloseHandle(ov.hEvent)
    return True, transferred.value, 0


def main():
    paths = enum_winusb_paths()
    print(f"WinUSB interfaces: {len(paths)}")
    opened = []
    for p in paths:
        print("  ", p)
        h = open_device(p)
        if h == INVALID_HANDLE_VALUE:
            print("     open failed:", ctypes.GetLastError())
            continue
        wh = wt.HANDLE()
        if not winusb.WinUsb_Initialize(h, ctypes.byref(wh)):
            print("     WinUsb_Initialize failed:", ctypes.GetLastError())
            kernel32.CloseHandle(h)
            continue
        opened.append((p, h, wh))

    if "--send" not in sys.argv:
        for p, h, wh in opened:
            winusb.WinUsb_Free(wh)
            kernel32.CloseHandle(h)
        return 0

    # The two ISP reports; report ID 5 is included in the payload.
    reports = [
        [0x05, 0x03, 0x01, 0x00, 0x06, 0x00],
        [0x05, 0x75, 0x00, 0x00, 0x00, 0x00],
    ]
    for p, h, wh in opened:
        print("device:", p)
        for idx, payload in enumerate(reports):
            # Try interface 1 first, then 0 (in case the composite is bound).
            done = False
            for iface in (1, 0):
                ok, n, err = send_control(wh, 0x21, 0x09, 0x0305, iface, payload)
                print(f"  report {idx+1} iface {iface}: ok={ok} transferred={n} err={err}")
                if ok:
                    done = True
                    break
            if not done:
                print("  report failed on both interfaces")
        winusb.WinUsb_Free(wh)
        kernel32.CloseHandle(h)

    print("sent; waiting for the bootloader (0603:1020)...")
    time.sleep(2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
