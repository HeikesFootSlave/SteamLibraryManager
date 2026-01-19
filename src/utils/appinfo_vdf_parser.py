"""
AppInfo VDF Parser - Binary VDF Reader
Speichern als: src/utils/appinfo_vdf_parser.py
"""

import struct
from pathlib import Path
from typing import Dict, Any, BinaryIO

class AppInfoParser:
    """Parser für Steam's appinfo.vdf (Binary VDF Format)"""

    # VDF Type Bytes
    TYPE_NONE = 0x00
    TYPE_STRING = 0x01
    TYPE_INT32 = 0x02
    TYPE_UINT64 = 0x06
    TYPE_END = 0x08
    TYPE_INT64 = 0x0A

    # Supported versions
    MAGIC_V27 = 0x07564427
    MAGIC_V28 = 0x07564428
    MAGIC_V29 = 0x07564429
    SUPPORTED_VERSIONS = [MAGIC_V27, MAGIC_V28, MAGIC_V29]

    @staticmethod
    def load(file_path: Path) -> Dict[str, Any]:
        """Load appinfo.vdf file"""
        with open(file_path, 'rb') as f:
            return AppInfoParser._parse_file(f)

    @staticmethod
    def _parse_file(f: BinaryIO) -> Dict[str, Any]:
        """Parse entire appinfo file"""
        magic = struct.unpack('<I', f.read(4))[0]
        if magic not in AppInfoParser.SUPPORTED_VERSIONS:
            raise ValueError(f"Unsupported AppInfo version: {hex(magic)}")

        # Skip header (universe version)
        f.read(4) 

        apps = {}
        while True:
            app_id = struct.unpack('<I', f.read(4))[0]
            if app_id == 0:
                break

            # Size
            _ = struct.unpack('<I', f.read(4))[0]
            
            # Info state
            _ = struct.unpack('<I', f.read(4))[0]
            
            # Last updated
            _ = struct.unpack('<I', f.read(4))[0]
            
            # Token
            _ = struct.unpack('<Q', f.read(8))[0]
            
            # SHA1
            f.read(20)
            
            # Change number
            _ = struct.unpack('<I', f.read(4))[0]

            # Binary VDF Data
            app_data = AppInfoParser._read_binary_vdf(f)
            apps[str(app_id)] = app_data

        return apps

    @staticmethod
    def _read_binary_vdf(f: BinaryIO) -> Dict[str, Any]:
        """Read a single VDF object"""
        data = {}
        while True:
            type_byte = f.read(1)
            if not type_byte or type_byte == b'\x08': # End struct
                break
            
            type_id = ord(type_byte)
            key = AppInfoParser._read_string(f)
            
            if type_id == AppInfoParser.TYPE_NONE:
                data[key] = AppInfoParser._read_binary_vdf(f)
            elif type_id == AppInfoParser.TYPE_STRING:
                data[key] = AppInfoParser._read_string(f)
            elif type_id == AppInfoParser.TYPE_INT32:
                data[key] = struct.unpack('<i', f.read(4))[0]
            elif type_id == AppInfoParser.TYPE_UINT64:
                data[key] = struct.unpack('<Q', f.read(8))[0]
            elif type_id == AppInfoParser.TYPE_INT64:
                data[key] = struct.unpack('<q', f.read(8))[0]
            
        return data

    @staticmethod
    def _read_string(f: BinaryIO) -> str:
        """Read null-terminated string"""
        chars = []
        while True:
            c = f.read(1)
            if c == b'\x00':
                break
            chars.append(c)
        return b"".join(chars).decode('utf-8', errors='replace')

    @staticmethod
    def dump(data: Dict, file_path: Path) -> bool:
        """Dump not supported for binary format yet"""
        # Writing binary VDF with correct checksums is complex
        # We only support reading for metadata extraction
        return False
            return section_data

        except Exception as e:
            # Skip to next entry using size
            try:
                current_pos = f.tell()
                bytes_read = current_pos - start_pos - 4

                if 'size' in locals() and size > bytes_read:
                    skip_bytes = size - bytes_read
                    f.read(skip_bytes)
            except:
                pass

            return None

    @staticmethod
    def _parse_section(f: BinaryIO) -> Dict:
        """Parse VDF section"""
        result = {}

        type_byte = f.read(1)[0]
        if type_byte != AppInfoParser.TYPE_NONE:
            return result

        section_name = AppInfoParser._read_cstring(f)

        while True:
            type_byte_data = f.read(1)
            if not type_byte_data:
                break

            type_byte = type_byte_data[0]
            if type_byte == AppInfoParser.TYPE_END:
                break

            key = AppInfoParser._read_cstring(f)
            value = AppInfoParser._read_value(f, type_byte)
            result[key] = value

        return {section_name: result} if section_name else result

    @staticmethod
    def _read_value(f: BinaryIO, type_byte: int) -> Any:
        """Read value by type"""
        if type_byte == AppInfoParser.TYPE_NONE:
            dict_data = {}
            while True:
                inner_type_data = f.read(1)
                if not inner_type_data:
                    break
                inner_type = inner_type_data[0]
                if inner_type == AppInfoParser.TYPE_END:
                    break
                key = AppInfoParser._read_cstring(f)
                value = AppInfoParser._read_value(f, inner_type)
                dict_data[key] = value
            return dict_data

        elif type_byte == AppInfoParser.TYPE_STRING:
            return AppInfoParser._read_cstring(f)

        elif type_byte == AppInfoParser.TYPE_INT32:
            data = f.read(4)
            if len(data) < 4:
                raise ValueError("Unexpected EOF reading INT32")
            return struct.unpack('<i', data)[0]

        elif type_byte == AppInfoParser.TYPE_UINT64:
            data = f.read(8)
            if len(data) < 8:
                raise ValueError("Unexpected EOF reading UINT64")
            return struct.unpack('<Q', data)[0]

        elif type_byte == AppInfoParser.TYPE_INT64:
            data = f.read(8)
            if len(data) < 8:
                raise ValueError("Unexpected EOF reading INT64")
            return struct.unpack('<q', data)[0]

        else:
            raise ValueError(f"Unknown type: {hex(type_byte)}")

    @staticmethod
    def _read_cstring(f: BinaryIO) -> str:
        """Read null-terminated string"""
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
    def dump(data: Dict, file_path: Path, version: int = None) -> bool:
        """Save appinfo.vdf"""
        if version is None:
            version = AppInfoParser.MAGIC_V29

        try:
            with open(file_path, 'wb') as f:
                AppInfoParser._write_file(f, data, version)
            return True
        except Exception as e:
            print(f"Error saving appinfo.vdf: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def _write_file(f: BinaryIO, apps: Dict, version: int):
        """Write appinfo file"""
        f.write(struct.pack('<I', version))
        f.write(struct.pack('<I', AppInfoParser.UNIVERSE))

        for app_id_str, app_data in apps.items():
            app_id = int(app_id_str)
            f.write(struct.pack('<I', app_id))
            AppInfoParser._write_app_entry(f, app_data, version)

        f.write(struct.pack('<I', 0))

    @staticmethod
    def _write_app_entry(f: BinaryIO, app_data: Dict, version: int):
        """Write app entry with correct checksums"""
        # Serialize VDF data to get size
        data_buffer = BytesIO()
        AppInfoParser._write_section(data_buffer, app_data)
        serialized_data = data_buffer.getvalue()
        size = len(serialized_data)

        # Calculate checksum from TEXT VDF format (for sha_hash)
        text_vdf = AppInfoParser._to_text_vdf(app_data)
        sha_hash = hashlib.sha1(text_vdf.encode('utf-8')).digest()

        # Calculate binary data checksum (for binary_data_hash in v28+)
        binary_data_hash = hashlib.sha1(serialized_data).digest()

        # Write header
        f.write(struct.pack('<I', size))
        f.write(struct.pack('<I', 2))  # info_state
        f.write(struct.pack('<I', 0))  # last_updated
        f.write(struct.pack('<Q', 0))  # access_token
        f.write(sha_hash)

        # V28/29: Write binary data hash BEFORE change_number
        if version >= AppInfoParser.MAGIC_V28:
            f.write(binary_data_hash)

        f.write(struct.pack('<I', 0))  # change_number

        # Write VDF data
        f.write(serialized_data)

    @staticmethod
    def _write_section(f: BinaryIO, data: Dict, section_name: str = ''):
        """Write VDF section"""
        f.write(bytes([AppInfoParser.TYPE_NONE]))
        AppInfoParser._write_cstring(f, section_name)

        for key, value in data.items():
            AppInfoParser._write_entry(f, key, value)

        f.write(bytes([AppInfoParser.TYPE_END]))

    @staticmethod
    def _write_entry(f: BinaryIO, key: str, value: Any):
        """Write key-value entry"""
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
            # Fallback: convert to string
            f.write(bytes([AppInfoParser.TYPE_STRING]))
            AppInfoParser._write_cstring(f, key)
            AppInfoParser._write_cstring(f, str(value))

    @staticmethod
    def _write_cstring(f: BinaryIO, s: str):
        """Write null-terminated string"""
        f.write(s.encode('utf-8', errors='replace'))
        f.write(b'\x00')

    @staticmethod
    def _to_text_vdf(data: Dict, indent: int = 0) -> str:
        """
        Convert to text VDF format for checksum calculation
        CRITICAL: Backslashes must be escaped (doubled)!
        """
        lines = []
        tab = '\t' * indent

        for key, value in data.items():
            if isinstance(value, dict):
                # Dictionary: key with nested content
                escaped_key = AppInfoParser._escape_vdf(key)
                lines.append(f'{tab}"{escaped_key}"')
                lines.append(f'{tab}{{')
                lines.append(AppInfoParser._to_text_vdf(value, indent + 1))
                lines.append(f'{tab}}}')
            else:
                # Key-value pair
                escaped_key = AppInfoParser._escape_vdf(key)
                escaped_value = AppInfoParser._escape_vdf(str(value))
                lines.append(f'{tab}"{escaped_key}"\t\t"{escaped_value}"')

        return '\n'.join(lines)

    @staticmethod
    def _escape_vdf(s: str) -> str:
        """
        Escape special characters for VDF
        CRITICAL: Backslashes MUST be doubled for checksum!
        """
        # Double all backslashes
        s = s.replace('\\', '\\\\')
        # Escape quotes (if needed)
        s = s.replace('"', '\\"')
        return s


def load_appinfo(file_path: Path) -> Dict:
    """Load appinfo.vdf file"""
    return AppInfoParser.load(file_path)


def save_appinfo(data: Dict, file_path: Path) -> bool:
    """Save appinfo.vdf file"""
    return AppInfoParser.dump(data, file_path)
