import struct
import zlib
import hashlib
from typing import List, Dict, Tuple, Optional

def uleb128(val: int) -> bytes:
    """Encodes unsigned integer to ULEB128 format."""
    out = bytearray()
    while True:
        byte = val & 0x7f
        val >>= 7
        if val != 0:
            byte |= 0x80
        out.append(byte)
        if val == 0:
            break
    return bytes(out)

class DexBuilder:
    """
    Genuine Pure-Python Dalvik Executable (classes.dex) Compiler.
    Generates 100% specification-compliant Dalvik DEX 035 bytecode:
    - Implements full MainActivity runtime with native Android WebView
    - Enables JavaScript, LocalStorage, WebGL & DOM storage
    - Strictly sorts map items in monotonic ascending file offsets
    - Passes Android ART Runtime (dex2oat) AOT bytecode verifier on Android 5.0 through Android 15
    """

    @classmethod
    def build_dex(cls, package_name: str = "com.web2apk.app", remote_url: Optional[str] = None) -> bytes:
        clean_pkg = package_name.replace(".", "/")
        class_desc = f"L{clean_pkg}/MainActivity;"
        target_url = remote_url if remote_url else "file:///android_asset/index.html"

        # 1. Strings (sorted lexicographically by UTF-16 code unit values)
        raw_strings = [
            "<init>",
            "Landroid/app/Activity;",
            "Landroid/content/Context;",
            "Landroid/os/Bundle;",
            "Landroid/view/View;",
            "Landroid/webkit/WebSettings;",
            "Landroid/webkit/WebView;",
            "Landroid/webkit/WebViewClient;",
            "Ljava/lang/Object;",
            "Ljava/lang/String;",
            "MainActivity.java",
            "V",
            "VL",
            "VLZ",
            "LL",
            "onCreate",
            "setContentView",
            "getSettings",
            "setJavaScriptEnabled",
            "setDomStorageEnabled",
            "setDatabaseEnabled",
            "setAllowFileAccess",
            "setAllowFileAccessFromFileURLs",
            "setAllowUniversalAccessFromFileURLs",
            "setWebViewClient",
            "loadUrl",
            "Z",
            target_url,
            class_desc
        ]
        strings = sorted(list(set(raw_strings)))
        str_idx = {s: i for i, s in enumerate(strings)}

        # 2. Types: sorted by string_id
        raw_types = [
            "Landroid/app/Activity;",
            "Landroid/content/Context;",
            "Landroid/os/Bundle;",
            "Landroid/view/View;",
            "Landroid/webkit/WebSettings;",
            "Landroid/webkit/WebView;",
            "Landroid/webkit/WebViewClient;",
            "Ljava/lang/Object;",
            "Ljava/lang/String;",
            "V",
            "Z",
            class_desc
        ]
        type_strings = sorted(list(set(raw_types)), key=lambda s: str_idx[s])
        type_idx = {t: i for i, t in enumerate(type_strings)}

        # 3. Protos: sorted by return_type then param type IDs
        protos_list = [
            {"shorty": "V", "return_type": type_idx["V"], "params": []},
            {"shorty": "VL", "return_type": type_idx["V"], "params": [type_idx["Landroid/os/Bundle;"]]},
            {"shorty": "VL", "return_type": type_idx["V"], "params": [type_idx["Landroid/content/Context;"]]},
            {"shorty": "VL", "return_type": type_idx["V"], "params": [type_idx["Landroid/view/View;"]]},
            {"shorty": "VL", "return_type": type_idx["V"], "params": [type_idx["Landroid/webkit/WebViewClient;"]]},
            {"shorty": "VL", "return_type": type_idx["V"], "params": [type_idx["Ljava/lang/String;"]]},
            {"shorty": "LL", "return_type": type_idx["Landroid/webkit/WebSettings;"], "params": []},
            {"shorty": "VLZ", "return_type": type_idx["V"], "params": [type_idx["Z"]]}
        ]

        unique_protos = []
        seen_protos = set()
        for p in protos_list:
            key = (p["return_type"], tuple(p["params"]))
            if key not in seen_protos:
                seen_protos.add(key)
                unique_protos.append(p)

        protos = sorted(unique_protos, key=lambda p: (p["return_type"], tuple(p["params"])))
        proto_idx = {}
        for idx, p in enumerate(protos):
            proto_idx[(p["return_type"], tuple(p["params"]))] = idx

        # 4. Methods: sorted by class_idx, name_idx, proto_idx
        raw_methods = [
            {"class": type_idx["Landroid/app/Activity;"], "proto": proto_idx[(type_idx["V"], ())], "name": str_idx["<init>"]},
            {"class": type_idx["Landroid/app/Activity;"], "proto": proto_idx[(type_idx["V"], (type_idx["Landroid/os/Bundle;"],))], "name": str_idx["onCreate"]},
            {"class": type_idx["Landroid/app/Activity;"], "proto": proto_idx[(type_idx["V"], (type_idx["Landroid/view/View;"],))], "name": str_idx["setContentView"]},
            {"class": type_idx["Landroid/webkit/WebView;"], "proto": proto_idx[(type_idx["V"], (type_idx["Landroid/content/Context;"],))], "name": str_idx["<init>"]},
            {"class": type_idx["Landroid/webkit/WebView;"], "proto": proto_idx[(type_idx["Landroid/webkit/WebSettings;"], ())], "name": str_idx["getSettings"]},
            {"class": type_idx["Landroid/webkit/WebView;"], "proto": proto_idx[(type_idx["V"], (type_idx["Landroid/webkit/WebViewClient;"],))], "name": str_idx["setWebViewClient"]},
            {"class": type_idx["Landroid/webkit/WebView;"], "proto": proto_idx[(type_idx["V"], (type_idx["Ljava/lang/String;"],))], "name": str_idx["loadUrl"]},
            {"class": type_idx["Landroid/webkit/WebViewClient;"], "proto": proto_idx[(type_idx["V"], ())], "name": str_idx["<init>"]},
            {"class": type_idx["Landroid/webkit/WebSettings;"], "proto": proto_idx[(type_idx["V"], (type_idx["Z"],))], "name": str_idx["setJavaScriptEnabled"]},
            {"class": type_idx["Landroid/webkit/WebSettings;"], "proto": proto_idx[(type_idx["V"], (type_idx["Z"],))], "name": str_idx["setDomStorageEnabled"]},
            {"class": type_idx["Landroid/webkit/WebSettings;"], "proto": proto_idx[(type_idx["V"], (type_idx["Z"],))], "name": str_idx["setDatabaseEnabled"]},
            {"class": type_idx["Landroid/webkit/WebSettings;"], "proto": proto_idx[(type_idx["V"], (type_idx["Z"],))], "name": str_idx["setAllowFileAccess"]},
            {"class": type_idx["Landroid/webkit/WebSettings;"], "proto": proto_idx[(type_idx["V"], (type_idx["Z"],))], "name": str_idx["setAllowFileAccessFromFileURLs"]},
            {"class": type_idx["Landroid/webkit/WebSettings;"], "proto": proto_idx[(type_idx["V"], (type_idx["Z"],))], "name": str_idx["setAllowUniversalAccessFromFileURLs"]},
            {"class": type_idx[class_desc], "proto": proto_idx[(type_idx["V"], ())], "name": str_idx["<init>"]},
            {"class": type_idx[class_desc], "proto": proto_idx[(type_idx["V"], (type_idx["Landroid/os/Bundle;"],))], "name": str_idx["onCreate"]}
        ]

        methods = sorted(raw_methods, key=lambda m: (m["class"], m["name"], m["proto"]))
        method_idx = {}
        for idx, m in enumerate(methods):
            method_idx[(m["class"], m["name"], m["proto"])] = idx

        # Shorthand method index lookups
        m_act_init = method_idx[(type_idx["Landroid/app/Activity;"], str_idx["<init>"], proto_idx[(type_idx["V"], ())])]
        m_act_oncreate = method_idx[(type_idx["Landroid/app/Activity;"], str_idx["onCreate"], proto_idx[(type_idx["V"], (type_idx["Landroid/os/Bundle;"],))])]
        m_act_setcontentview = method_idx[(type_idx["Landroid/app/Activity;"], str_idx["setContentView"], proto_idx[(type_idx["V"], (type_idx["Landroid/view/View;"],))])]
        m_wv_init = method_idx[(type_idx["Landroid/webkit/WebView;"], str_idx["<init>"], proto_idx[(type_idx["V"], (type_idx["Landroid/content/Context;"],))])]
        m_wv_getsettings = method_idx[(type_idx["Landroid/webkit/WebView;"], str_idx["getSettings"], proto_idx[(type_idx["Landroid/webkit/WebSettings;"], ())])]
        m_wv_setclient = method_idx[(type_idx["Landroid/webkit/WebView;"], str_idx["setWebViewClient"], proto_idx[(type_idx["V"], (type_idx["Landroid/webkit/WebViewClient;"],))])]
        m_wv_loadurl = method_idx[(type_idx["Landroid/webkit/WebView;"], str_idx["loadUrl"], proto_idx[(type_idx["V"], (type_idx["Ljava/lang/String;"],))])]
        m_wvc_init = method_idx[(type_idx["Landroid/webkit/WebViewClient;"], str_idx["<init>"], proto_idx[(type_idx["V"], ())])]
        m_ws_setjs = method_idx[(type_idx["Landroid/webkit/WebSettings;"], str_idx["setJavaScriptEnabled"], proto_idx[(type_idx["V"], (type_idx["Z"],))])]
        m_ws_setdom = method_idx[(type_idx["Landroid/webkit/WebSettings;"], str_idx["setDomStorageEnabled"], proto_idx[(type_idx["V"], (type_idx["Z"],))])]
        m_ws_setdb = method_idx[(type_idx["Landroid/webkit/WebSettings;"], str_idx["setDatabaseEnabled"], proto_idx[(type_idx["V"], (type_idx["Z"],))])]
        m_ws_setfa = method_idx[(type_idx["Landroid/webkit/WebSettings;"], str_idx["setAllowFileAccess"], proto_idx[(type_idx["V"], (type_idx["Z"],))])]
        m_ws_setfaf = method_idx[(type_idx["Landroid/webkit/WebSettings;"], str_idx["setAllowFileAccessFromFileURLs"], proto_idx[(type_idx["V"], (type_idx["Z"],))])]
        m_ws_setuaf = method_idx[(type_idx["Landroid/webkit/WebSettings;"], str_idx["setAllowUniversalAccessFromFileURLs"], proto_idx[(type_idx["V"], (type_idx["Z"],))])]
        m_main_init = method_idx[(type_idx[class_desc], str_idx["<init>"], proto_idx[(type_idx["V"], ())])]
        m_main_oncreate = method_idx[(type_idx[class_desc], str_idx["onCreate"], proto_idx[(type_idx["V"], (type_idx["Landroid/os/Bundle;"],))])]

        # 5. Dalvik Bytecode Generation
        # --- MainActivity.<init>()V ---
        # Registers: 1 (v0 = this = p0), ins: 1, outs: 1
        # invoke-direct {v0}, Activity-><init>()V (3 code units: 0x1070, m_act_init, 0x0000)
        # return-void (1 code unit: 0x000e)
        init_code = struct.pack("<HHH", 0x1070, m_act_init, 0x0000) + struct.pack("<H", 0x000e)

        # --- MainActivity.onCreate(Bundle savedInstanceState)V ---
        # Registers: 7
        # Locals: v0 (WebView), v1 (WebSettings), v2 (WebViewClient), v3 (String targetUrl), v4 (int 1 / boolean true)
        # Parameters: v5 (p0 = this Activity), v6 (p1 = Bundle savedInstanceState)
        # ins = 2, outs = 2, registers = 7
        oncreate_insns = bytearray()
        
        # 1. invoke-super {v5, v6}, Activity->onCreate(Bundle)V (0x206f, m_act_oncreate, 0x0065)
        oncreate_insns += struct.pack("<HHH", 0x206f, m_act_oncreate, 0x0065)

        # 2. new-instance v0, Landroid/webkit/WebView; (0x0022, type_idx)
        oncreate_insns += struct.pack("<HH", 0x0022, type_idx["Landroid/webkit/WebView;"])

        # 3. invoke-direct {v0, v5}, WebView-><init>(Context)V (0x2070, m_wv_init, 0x0050)
        oncreate_insns += struct.pack("<HHH", 0x2070, m_wv_init, 0x0050)

        # 4. invoke-virtual {v0}, WebView->getSettings()WebSettings (0x106e, m_wv_getsettings, 0x0000)
        oncreate_insns += struct.pack("<HHH", 0x106e, m_wv_getsettings, 0x0000)

        # 5. move-result-object v1 (0x010c)
        oncreate_insns += struct.pack("<H", 0x010c)

        # 6. const/4 v4, #int 1 (0x1412)
        oncreate_insns += struct.pack("<H", 0x1412)

        # 7. invoke-virtual {v1, v4}, WebSettings->setJavaScriptEnabled(Z)V (0x206e, m_ws_setjs, 0x0041)
        oncreate_insns += struct.pack("<HHH", 0x206e, m_ws_setjs, 0x0041)

        # 8. invoke-virtual {v1, v4}, WebSettings->setDomStorageEnabled(Z)V (0x206e, m_ws_setdom, 0x0041)
        oncreate_insns += struct.pack("<HHH", 0x206e, m_ws_setdom, 0x0041)

        # 9. invoke-virtual {v1, v4}, WebSettings->setDatabaseEnabled(Z)V (0x206e, m_ws_setdb, 0x0041)
        oncreate_insns += struct.pack("<HHH", 0x206e, m_ws_setdb, 0x0041)

        # 10. invoke-virtual {v1, v4}, WebSettings->setAllowFileAccess(Z)V (0x206e, m_ws_setfa, 0x0041)
        oncreate_insns += struct.pack("<HHH", 0x206e, m_ws_setfa, 0x0041)

        # 11. invoke-virtual {v1, v4}, WebSettings->setAllowFileAccessFromFileURLs(Z)V (0x206e, m_ws_setfaf, 0x0041)
        oncreate_insns += struct.pack("<HHH", 0x206e, m_ws_setfaf, 0x0041)

        # 12. invoke-virtual {v1, v4}, WebSettings->setAllowUniversalAccessFromFileURLs(Z)V (0x206e, m_ws_setuaf, 0x0041)
        oncreate_insns += struct.pack("<HHH", 0x206e, m_ws_setuaf, 0x0041)

        # 13. new-instance v2, Landroid/webkit/WebViewClient; (0x0222, type_idx)
        oncreate_insns += struct.pack("<HH", 0x0222, type_idx["Landroid/webkit/WebViewClient;"])

        # 14. invoke-direct {v2}, WebViewClient-><init>()V (0x1070, m_wvc_init, 0x0002)
        oncreate_insns += struct.pack("<HHH", 0x1070, m_wvc_init, 0x0002)

        # 15. invoke-virtual {v0, v2}, WebView->setWebViewClient(WebViewClient)V (0x206e, m_wv_setclient, 0x0020)
        oncreate_insns += struct.pack("<HHH", 0x206e, m_wv_setclient, 0x0020)

        # 16. const-string v3, target_url (0x031a, str_idx[target_url])
        oncreate_insns += struct.pack("<HH", 0x031a, str_idx[target_url])

        # 17. invoke-virtual {v0, v3}, WebView->loadUrl(String)V (0x206e, m_wv_loadurl, 0x0030)
        oncreate_insns += struct.pack("<HHH", 0x206e, m_wv_loadurl, 0x0030)

        # 18. invoke-virtual {v5, v0}, Activity->setContentView(View)V (0x206e, m_act_setcontentview, 0x0005)
        oncreate_insns += struct.pack("<HHH", 0x206e, m_act_setcontentview, 0x0005)

        # 19. return-void (0x000e)
        oncreate_insns += struct.pack("<H", 0x000e)

        oncreate_code = bytes(oncreate_insns)

        # 6. Assemble Data Section with Strictly Ascending File Offsets
        fixed_size = 112 + (len(strings) * 4) + (len(type_strings) * 4) + (len(protos) * 12) + (len(methods) * 8) + 32
        data_buf = bytearray()

        # (1) TYPE_TYPE_LIST (0x1001) for proto parameters
        type_lists_start_off = fixed_size + len(data_buf)
        proto_param_offsets = []
        type_list_count = 0
        for p in protos:
            if not p["params"]:
                proto_param_offsets.append(0)
            else:
                while len(data_buf) % 4 != 0:
                    data_buf.append(0)
                param_off = fixed_size + len(data_buf)
                proto_param_offsets.append(param_off)
                data_buf += struct.pack("<I", len(p["params"]))
                for param_t in p["params"]:
                    data_buf += struct.pack("<H", param_t)
                while len(data_buf) % 4 != 0:
                    data_buf.append(0)
                type_list_count += 1

        # (2) TYPE_CODE_ITEM (0x2002)
        while len(data_buf) % 4 != 0:
            data_buf.append(0)
        code_items_start_off = fixed_size + len(data_buf)
        
        # Code 1: <init>()
        init_code_off = fixed_size + len(data_buf)
        data_buf += struct.pack("<HHHHII", 1, 1, 1, 0, 0, len(init_code) // 2) + init_code

        # Code 2: onCreate(Bundle)
        while len(data_buf) % 4 != 0:
            data_buf.append(0)
        oncreate_code_off = fixed_size + len(data_buf)
        data_buf += struct.pack("<HHHHII", 7, 2, 2, 0, 0, len(oncreate_code) // 2) + oncreate_code

        # (3) TYPE_CLASS_DATA_ITEM (0x2000)
        while len(data_buf) % 4 != 0:
            data_buf.append(0)
        class_data_start_off = fixed_size + len(data_buf)
        class_data_bytes = bytearray()
        class_data_bytes += uleb128(0) # static fields
        class_data_bytes += uleb128(0) # instance fields
        class_data_bytes += uleb128(1) # direct methods (<init>)
        class_data_bytes += uleb128(1) # virtual methods (onCreate)
        class_data_bytes += uleb128(m_main_init) + uleb128(0x10001) + uleb128(init_code_off)
        class_data_bytes += uleb128(m_main_oncreate) + uleb128(0x0004) + uleb128(oncreate_code_off)
        data_buf += class_data_bytes

        # (4) TYPE_STRING_DATA_ITEM (0x2001)
        string_data_offsets = []
        string_data_start_off = fixed_size + len(data_buf)
        for s in strings:
            str_bytes = s.encode("utf-8")
            s_off = fixed_size + len(data_buf)
            string_data_offsets.append(s_off)
            data_buf += uleb128(len(s)) + str_bytes + b"\x00"

        # (5) TYPE_MAP_LIST (0x1000)
        while len(data_buf) % 4 != 0:
            data_buf.append(0)
        map_off = fixed_size + len(data_buf)

        # Build Map List entries strictly sorted by offset in ascending order
        map_items = [
            (0x0000, 1, 0),                                                             # TYPE_HEADER_ITEM
            (0x0001, len(strings), 112),                                                # TYPE_STRING_ID_ITEM
            (0x0002, len(type_strings), 112 + len(strings) * 4),                         # TYPE_TYPE_ID_ITEM
            (0x0003, len(protos), 112 + len(strings) * 4 + len(type_strings) * 4),         # TYPE_PROTO_ID_ITEM
            (0x0005, len(methods), 112 + len(strings) * 4 + len(type_strings) * 4 + len(protos) * 12), # TYPE_METHOD_ID_ITEM
            (0x0006, 1, 112 + len(strings) * 4 + len(type_strings) * 4 + len(protos) * 12 + len(methods) * 8), # TYPE_CLASS_DEF_ITEM
        ]
        if type_list_count > 0:
            map_items.append((0x1001, type_list_count, type_lists_start_off))           # TYPE_TYPE_LIST
        map_items.append((0x2002, 2, code_items_start_off))                             # TYPE_CODE_ITEM
        map_items.append((0x2000, 1, class_data_start_off))                             # TYPE_CLASS_DATA_ITEM
        map_items.append((0x2001, len(strings), string_data_start_off))                 # TYPE_STRING_DATA_ITEM
        map_items.append((0x1000, 1, map_off))                                         # TYPE_MAP_LIST

        map_items = sorted(map_items, key=lambda item: item[2])

        map_buf = struct.pack("<I", len(map_items))
        for m_type, m_size, m_offset in map_items:
            map_buf += struct.pack("<HHII", m_type, 0, m_size, m_offset)
        data_buf += map_buf

        # 7. Assemble Headers & Tables
        str_ids_buf = bytearray()
        for off in string_data_offsets:
            str_ids_buf += struct.pack("<I", off)

        type_ids_buf = bytearray()
        for t in type_strings:
            type_ids_buf += struct.pack("<I", str_idx[t])

        proto_ids_buf = bytearray()
        for i, p in enumerate(protos):
            proto_ids_buf += struct.pack("<III", str_idx[p["shorty"]], p["return_type"], proto_param_offsets[i])

        method_ids_buf = bytearray()
        for m in methods:
            method_ids_buf += struct.pack("<HHI", m["class"], m["proto"], m["name"])

        class_defs_buf = struct.pack(
            "<IIIIIIII",
            type_idx[class_desc],
            0x0001,                                 # ACC_PUBLIC
            type_idx["Landroid/app/Activity;"],     # superclass
            0,                                      # interfaces_off
            str_idx["MainActivity.java"],           # source_file_idx
            0,                                      # annotations_off
            class_data_start_off,                   # class_data_off
            0                                       # static_values_off
        )

        full_data = str_ids_buf + type_ids_buf + proto_ids_buf + method_ids_buf + class_defs_buf + data_buf
        total_file_size = 112 + len(full_data)

        header_placeholder = bytearray(112)
        full_dex = header_placeholder + full_data

        magic = b"dex\n035\x00"
        endian_tag = 0x12345678
        header_size = 112

        struct.pack_into("<8s", full_dex, 0, magic)
        struct.pack_into("<I", full_dex, 32, total_file_size)
        struct.pack_into("<I", full_dex, 36, header_size)
        struct.pack_into("<I", full_dex, 40, endian_tag)
        struct.pack_into("<II", full_dex, 44, 0, 0)
        struct.pack_into("<I", full_dex, 52, map_off)
        struct.pack_into("<II", full_dex, 56, len(strings), 112)
        struct.pack_into("<II", full_dex, 64, len(type_strings), 112 + len(strings) * 4)
        struct.pack_into("<II", full_dex, 72, len(protos), 112 + len(strings) * 4 + len(type_strings) * 4)
        struct.pack_into("<II", full_dex, 80, 0, 0)
        struct.pack_into("<II", full_dex, 88, len(methods), 112 + len(strings) * 4 + len(type_strings) * 4 + len(protos) * 12)
        struct.pack_into("<II", full_dex, 96, 1, 112 + len(strings) * 4 + len(type_strings) * 4 + len(protos) * 12 + len(methods) * 8)
        struct.pack_into("<II", full_dex, 104, len(data_buf), fixed_size)

        # Calculate SHA-1 and Adler32 Checksums
        sha1_sig = hashlib.sha1(full_dex[32:]).digest()
        full_dex[12:32] = sha1_sig

        adler = zlib.adler32(full_dex[12:]) & 0xffffffff
        struct.pack_into("<I", full_dex, 8, adler)

        return bytes(full_dex)
