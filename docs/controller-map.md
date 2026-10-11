# Odin 2 Controller — Verified Hardware Map

Input device:

    /dev/input/event5

Device:

    Odin Controller

USB identifier:

    VID 2020
    PID 0111

Android keylayout:

    /system/usr/keylayout/Vendor_2020_Product_0111.kl

Verified controls:

    Left stick       ABS_X / ABS_Y
    Right stick      ABS_Z / ABS_RZ
    Rear-left        BTN_C
    Rear-right       BTN_Z
    L3               BTN_THUMBL
    R3               BTN_THUMBR
    L1               BTN_TL
    R1               BTN_TR
    L2               ABS_BRAKE
    R2               ABS_GAS

Termux direct event5 read:

    VERIFIED

Android injection through local ADB:

    VERIFIED

Stock Android keylayout must remain unchanged.
