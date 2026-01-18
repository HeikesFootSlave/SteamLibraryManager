"""
AppInfo VDF Parser - Standalone Implementation
NO external dependencies - fully self-contained!

Speichern als: src/utils/appinfo_vdf_parser.py
"""

import struct
import hashlib
from pathlib import Path
from typing import Dict, Any, BinaryIO, Optional


class AppInfoParser:
    """Parser für Steam's appinfo.vdf (Binary VDF Format)"""
    
    # VDF Type Bytes
    TYPE_NONE = 0x00
    TYPE_STRING = 0x01
    TYPE_INT32 = 0x02
    TYPE_UINT64 = 0x06
    TYPE_END = 0x08
    TYPE_INT64 = 0x0A
    
    MAGIC = 0x07564427  # 'DV'27 in little endian
    UNIVERSE = 0x01
    
    @staticmethod
    def load(file_path: Path) -> Dict[str, Any]:
        with open(file_path, 'rb') as f:
            return AppInfoParser._parse_file(f)
    
    @staticmethod
    def _parse_file(f: BinaryIO) -> Dict[str, Any]:
        apps = {}
        magic = struct.unpack('<I', f.read(4))[0]
        if magic != AppInfoParser.MAGIC:
            raise ValueError(f"Invalid magic: {hex(magic)}")
        universe = struct.unpack('<I', f.read(4))[0]
        
        while True:
            app_id_bytes = f.read(4)
            if len(app_id_bytes) < 4:
                break
            app_id = struct.unpack('<I', app_id_bytes)[0]
            if app_id == 0:
                break
            app_data = AppInfoParser._parse_app_entry(f)
            if app_data:
                apps[str(app_id)] = app_data
        return apps
    
    @staticmethod
    def _parse_app_entry(f: BinaryIO) -> Optional[Dict]:
        size = struct.unpack('<I', f.read(4))[0]
        info_state = struct.unpack('<I', f.read(4))[0]
        last_updated = struct.unpack('<I', f.read(4))[0]
        access_token = struct.unpack('<Q', f.read(8))[0]
        sha_hash = f.read(20)
        change_number = struct.unpack('<I', f.read(4))[0]
        
        try:
            return AppInfoParser._parse_section(f)
        except Exception as e:
            print(f"Error parsing app entry: {e}")
            return None
    
    @staticmethod
    def _parse_section(f: BinaryIO) -> Dict:
        result = {}
        type_byte = f.read(1)[0]
        if type_byte != AppInfoParser.TYPE_NONE:
            return result
        section_name = AppInfoParser._read_cstring(f)
        
        while True:
            type_byte = f.read(1)[0]
            if type_byte == AppInfoParser.TYPE_END:
                break
            key = AppInfoParser._read_cstring(f)
            value = AppInfoParser._read_value(f, type_byte)
            result[key] = value
        
        return {section_name: result} if section_name else result
    
    @staticmethod
    def _read_value(f: BinaryIO, type_byte: int) -> Any:
        if type_byte == AppInfoParser.TYPE_NONE:
            dict_data = {}
            while True:
                inner_type = f.read(1)[0]
                if inner_type == AppInfoParser.TYPE_END:
                    break
                key = AppInfoParser._read_cstring(f)
                value = AppInfoParser._read_value(f, inner_type)
                dict_data[key] = value
            return dict_data
        elif type_byte == AppInfoParser.TYPE_STRING:
            return AppInfoParser._read_cstring(f)
        elif type_byte == AppInfoParser.TYPE_INT32:
            return struct.unpack('<i', f.read(4))[0]
        elif type_byte in (AppInfoParser.TYPE_UINT64, AppInfoParser.TYPE_INT64):
            return struct.unpack('<Q', f.read(8))[0]
        else:
            raise ValueError(f"Unknown type: {hex(type_byte)}")
    
    @staticmethod
    def _read_cstring(f: BinaryIO) -> str:
        chars = []
        while True:
            c = f.read(1)
            if not c or c == b'\x00':
                break
            chars.append(c)
        try:
            return b''.join(chars).decode('utf-8', errors='replace')
        except:
            return ''
    
    @staticmethod
    def dump(data: Dict, file_path: Path) -> bool:
        try:
            with open(file_path, 'wb') as f:
                AppInfoParser._write_file(f, data)
            return True
        except Exception as e:
            print(f"Error saving: {e}")
            return False
    
    @staticmethod
    def _write_file(f: BinaryIO, apps: Dict):
        f.write(struct.pack('<I', AppInfoParser.MAGIC))
        f.write(struct.pack('<I', AppInfoParser.UNIVERSE))
        for app_id_str, app_data in apps.items():
            app_id = int(app_id_str)
            f.write(struct.pack('<I', app_id))
            AppInfoParser._write_app_entry(f, app_data)
        f.write(struct.pack('<I', 0))
    
    @staticmethod
    def _write_app_entry(f: BinaryIO, app_data: Dict):
        import io
        data_buffer = io.BytesIO()
        AppInfoParser._write_section(data_buffer, app_data)
        serialized_data = data_buffer.getvalue()
        size = len(serialized_data)
        text_vdf = AppInfoParser._to_text_vdf(app_data)
        checksum = hashlib.sha1(text_vdf.encode('utf-8')).digest()
        
        f.write(struct.pack('<I', size))
        f.write(struct.pack('<I', 2))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<Q', 0))
        f.write(checksum)
        f.write(struct.pack('<I', 0))
        f.write(serialized_data)
    
    @staticmethod
    def _write_section(f: BinaryIO, data: Dict, section_name: str = ''):
        f.write(bytes([AppInfoParser.TYPE_NONE]))
        AppInfoParser._write_cstring(f, section_name)
        for key, value in data.items():
            AppInfoParser._write_entry(f, key, value)
        f.write(bytes([AppInfoParser.TYPE_END]))
    
    @staticmethod
    def _write_entry(f: BinaryIO, key: str, value: Any):
        if isinstance(value, dict):
            f.write(bytes([AppInfoParser.TYPE_NONE]))
            AppInfoParser._write_cstring(f, key)
            for inner_key, inner_value in value.items():
                AppInfoParser._write_entry(f, inner_key, inner_value)
            f.write(bytes([AppInfoParser.TYPE_END]))
        elif isinstance(value, str):
            f.write(bytes([AppInfoParser.TYPE_STRING]))
            AppInfoParser._write_cstring(f, key)
            AppInfoParser._write_cstring(f, value)
        elif isinstance(value, int):
            if -2147483648 <= value <= 2147483647:
                f.write(bytes([AppInfoParser.TYPE_INT32]))
                AppInfoParser._write_cstring(f, key)
                f.write(struct.pack('<i', value))
            else:
                f.write(bytes([AppInfoParser.TYPE_UINT64]))
                AppInfoParser._write_cstring(f, key)
                f.write(struct.pack('<Q', value))
        else:
            f.write(bytes([AppInfoParser.TYPE_STRING]))
            AppInfoParser._write_cstring(f, key)
            AppInfoParser._write_cstring(f, str(value))
    
    @staticmethod
    def _write_cstring(f: BinaryIO, s: str):
        f.write(s.encode('utf-8', errors='replace'))
        f.write(b'\x00')
    
    @staticmethod
    def _to_text_vdf(data: Dict, indent: int = 0) -> str:
        lines = []
        tab = '\t' * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f'{tab}"{AppInfoParser._escape_vdf(key)}"')
                lines.append(f'{tab}{{')
                lines.append(AppInfoParser._to_text_vdf(value, indent + 1))
                lines.append(f'{tab}}}')
            else:
                val_str = AppInfoParser._escape_vdf(str(value))
                lines.append(f'{tab}"{AppInfoParser._escape_vdf(key)}"\t\t"{val_str}"')
        return '\n'.join(lines)
    
    @staticmethod
    def _escape_vdf(s: str) -> str:
        return s.replace('\\', '\\\\')


def load_appinfo(file_path: Path) -> Dict:
    return AppInfoParser.load(file_path)

def save_appinfo(data: Dict, file_path: Path) -> bool:
    return AppInfoParser.dump(data, file_path)
