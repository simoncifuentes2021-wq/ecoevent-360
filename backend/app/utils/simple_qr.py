from io import BytesIO

from PIL import Image


DATA_CODEWORDS_L = {1: 19, 2: 34, 3: 55, 4: 80, 5: 108}
ECC_CODEWORDS_L = {1: 7, 2: 10, 3: 15, 4: 20, 5: 26}
ALIGNMENT_POSITIONS = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30]}
GF_EXP = [0] * 512
GF_LOG = [0] * 256


def _init_gf() -> None:
    value = 1
    for index in range(255):
        GF_EXP[index] = value
        GF_LOG[value] = index
        value <<= 1
        if value & 0x100:
            value ^= 0x11D
    for index in range(255, 512):
        GF_EXP[index] = GF_EXP[index - 255]


_init_gf()


def make_qr_png(data: str, *, scale: int = 14, border: int = 4) -> bytes:
    try:
        return _make_standard_qr_png(data, scale=scale, border=border)
    except ImportError:
        return _make_builtin_qr_png(data, scale=scale, border=border)


def _make_standard_qr_png(data: str, *, scale: int, border: int) -> bytes:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=scale,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _make_builtin_qr_png(data: str, *, scale: int, border: int) -> bytes:
    raw = data.encode("utf-8")
    version = _pick_version(len(raw))
    matrix, reserved = _base_matrix(version)
    codewords = _data_codewords(raw, version)
    ecc = _rs_encode(codewords, ECC_CODEWORDS_L[version])
    bits = _codewords_to_bits(codewords + ecc)
    _place_data(matrix, reserved, bits)
    _apply_mask_zero(matrix, reserved)
    _place_format(matrix, mask=0)
    return _matrix_to_png(matrix, scale=scale, border=border)


def _pick_version(length: int) -> int:
    for version, capacity in DATA_CODEWORDS_L.items():
        if length + 2 <= capacity:
            return version
    raise ValueError("QR target URL is too long for the built-in generator")


def _data_codewords(data: bytes, version: int) -> list[int]:
    capacity = DATA_CODEWORDS_L[version] * 8
    bits = [0, 1, 0, 0]
    bits.extend(_int_bits(len(data), 8))
    for byte in data:
        bits.extend(_int_bits(byte, 8))
    bits.extend([0] * min(4, capacity - len(bits)))
    while len(bits) % 8:
        bits.append(0)
    codewords = [_bits_to_int(bits[index : index + 8]) for index in range(0, len(bits), 8)]
    pads = [0xEC, 0x11]
    pad_index = 0
    while len(codewords) < DATA_CODEWORDS_L[version]:
        codewords.append(pads[pad_index % 2])
        pad_index += 1
    return codewords


def _base_matrix(version: int) -> tuple[list[list[bool | None]], list[list[bool]]]:
    size = 17 + 4 * version
    matrix: list[list[bool | None]] = [[None for _ in range(size)] for _ in range(size)]
    reserved = [[False for _ in range(size)] for _ in range(size)]
    _draw_finder(matrix, reserved, 0, 0)
    _draw_finder(matrix, reserved, size - 7, 0)
    _draw_finder(matrix, reserved, 0, size - 7)
    _draw_timing(matrix, reserved)
    _draw_alignment(matrix, reserved, version)
    _reserve_format(matrix, reserved)
    _set(matrix, reserved, 8, 4 * version + 9, True)
    return matrix, reserved


def _draw_finder(matrix, reserved, x: int, y: int) -> None:
    size = len(matrix)
    for yy in range(y - 1, y + 8):
        for xx in range(x - 1, x + 8):
            if 0 <= xx < size and 0 <= yy < size:
                reserved[yy][xx] = True
                matrix[yy][xx] = False
    for yy in range(7):
        for xx in range(7):
            dark = xx in {0, 6} or yy in {0, 6} or (2 <= xx <= 4 and 2 <= yy <= 4)
            matrix[y + yy][x + xx] = dark


def _draw_timing(matrix, reserved) -> None:
    size = len(matrix)
    for index in range(8, size - 8):
        _set(matrix, reserved, index, 6, index % 2 == 0)
        _set(matrix, reserved, 6, index, index % 2 == 0)


def _draw_alignment(matrix, reserved, version: int) -> None:
    positions = ALIGNMENT_POSITIONS[version]
    for cy in positions:
        for cx in positions:
            if reserved[cy][cx]:
                continue
            for yy in range(-2, 3):
                for xx in range(-2, 3):
                    dark = max(abs(xx), abs(yy)) in {0, 2}
                    _set(matrix, reserved, cx + xx, cy + yy, dark)


def _reserve_format(matrix, reserved) -> None:
    size = len(matrix)
    for index in range(9):
        if index != 6:
            reserved[8][index] = True
            reserved[index][8] = True
    for index in range(8):
        reserved[8][size - 1 - index] = True
        reserved[size - 1 - index][8] = True


def _place_data(matrix, reserved, bits: list[bool]) -> None:
    size = len(matrix)
    bit_index = 0
    upward = True
    x = size - 1
    while x > 0:
        if x == 6:
            x -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for y in rows:
            for dx in (0, -1):
                xx = x + dx
                if reserved[y][xx]:
                    continue
                matrix[y][xx] = bits[bit_index] if bit_index < len(bits) else False
                bit_index += 1
        upward = not upward
        x -= 2


def _apply_mask_zero(matrix, reserved) -> None:
    size = len(matrix)
    for y in range(size):
        for x in range(size):
            if not reserved[y][x] and (x + y) % 2 == 0:
                matrix[y][x] = not matrix[y][x]


def _place_format(matrix, mask: int) -> None:
    bits = _format_bits(mask)
    size = len(matrix)
    first = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8), (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    second = [(size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8), (size - 5, 8), (size - 6, 8), (size - 7, 8), (8, size - 8), (8, size - 7), (8, size - 6), (8, size - 5), (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1)]
    for index, (x, y) in enumerate(first):
        matrix[y][x] = bool((bits >> index) & 1)
    for index, (x, y) in enumerate(second):
        matrix[y][x] = bool((bits >> index) & 1)


def _format_bits(mask: int) -> int:
    value = (0b01 << 3) | mask
    data = value << 10
    generator = 0x537
    for shift in range(14, 9, -1):
        if data & (1 << shift):
            data ^= generator << (shift - 10)
    return (((value << 10) | data) ^ 0x5412) & 0x7FFF


def _rs_encode(data: list[int], ecc_len: int) -> list[int]:
    generator = [1]
    for index in range(ecc_len):
        generator = _poly_mul(generator, [1, GF_EXP[index]])
    message = data + [0] * ecc_len
    for index, coefficient in enumerate(data):
        if coefficient == 0:
            continue
        for offset, gen_coeff in enumerate(generator):
            message[index + offset] ^= _gf_mul(gen_coeff, coefficient)
    return message[-ecc_len:]


def _poly_mul(left: list[int], right: list[int]) -> list[int]:
    result = [0] * (len(left) + len(right) - 1)
    for left_index, left_value in enumerate(left):
        for right_index, right_value in enumerate(right):
            result[left_index + right_index] ^= _gf_mul(left_value, right_value)
    return result


def _gf_mul(left: int, right: int) -> int:
    if left == 0 or right == 0:
        return 0
    return GF_EXP[GF_LOG[left] + GF_LOG[right]]


def _codewords_to_bits(codewords: list[int]) -> list[bool]:
    bits = []
    for codeword in codewords:
        bits.extend(bool((codeword >> shift) & 1) for shift in range(7, -1, -1))
    return bits


def _int_bits(value: int, length: int) -> list[int]:
    return [(value >> shift) & 1 for shift in range(length - 1, -1, -1)]


def _bits_to_int(bits: list[int]) -> int:
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def _set(matrix, reserved, x: int, y: int, value: bool) -> None:
    matrix[y][x] = value
    reserved[y][x] = True


def _matrix_to_png(matrix: list[list[bool | None]], *, scale: int, border: int) -> bytes:
    size = len(matrix)
    image_size = (size + border * 2) * scale
    image = Image.new("RGB", (image_size, image_size), "white")
    pixels = image.load()
    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            if not value:
                continue
            x0 = (x + border) * scale
            y0 = (y + border) * scale
            for yy in range(y0, y0 + scale):
                for xx in range(x0, x0 + scale):
                    pixels[xx, yy] = (0, 0, 0)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
