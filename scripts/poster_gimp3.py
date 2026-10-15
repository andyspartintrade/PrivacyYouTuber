"""
GIMP 3 Python-Fu: POSTER με layers (canvas 1280x720)
Διορθώσεις: Gegl.Color.new(str), σωστά enums
"""
W, H = 1280, 720
IMG_PATH = r"C:/Users/andys/privacy-yt/thumbnails/gemini/G2-POSTER.jpg"
OUT_XCF = r"C:/Users/andys/privacy-yt/thumbnails/gemini/POSTER-EDITABLE.xcf"
FONT = "SF Pro Display"

from gi.repository import Gimp, Gegl

def col(r, g, b):
    return Gegl.Color.new(f"rgb({r}, {g}, {b})")

# --- 1. ΝΕΑ ΕΙΚΟΝΑ ---
image = Gimp.Image.new(W, H, Gimp.ImageBaseType.RGB)
print("  image ok")

# --- 2. BACKGROUND ---
bg = Gimp.Layer.new(image, "BACKGROUND", W, H, Gimp.ImageType.RGB_IMAGE, 100, Gimp.LayerMode.NORMAL)
image.insert_layer(bg, None, 0)
Gimp.context_set_foreground(col(0.05, 0.05, 0.07))
bg.edit_fill(Gimp.FillType.FOREGROUND)
print("  + BACKGROUND")

# --- 3. IMAGE LAYER ---
img_layer = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image,
                                 Gimp.File.new_for_path(IMG_PATH), True)
image.insert_layer(img_layer, None, 0)
img_layer.set_name("IMAGE")
iw = img_layer.get_width()
img_layer.set_offsets((W - iw) // 2, 0)
print(f"  + IMAGE ({iw}x{img_layer.get_height()})")

# --- 4. TEXT LAYERS ---
def add_text(name, text, c, xpos, ypos, size=68):
    layer = Gimp.TextLayer.new(image, name, text, Gimp.Unit.pixel(), size, FONT)
    image.insert_layer(layer, None, 0)
    layer.set_offsets(xpos, ypos)
    try:
        layer.set_color(col(*c))
    except Exception as e:
        print(f"    color err {name}: {e}")
    print(f"  + {name}")

# A WARM
add_text("TEXT-1-WARM", "THEY\nWANT", (0.996, 0.851, 0.627), 860, 120)
add_text("TEXT-1b-WARM-white", "YOUR\nDATA", (0.910, 0.957, 0.973), 860, 290)
# B POP
add_text("TEXT-2-POP-orange", "THEY\nWANT", (0.996, 0.702, 0.278), 860, 120)
add_text("TEXT-2b-POP-cyan", "YOUR\nDATA", (0.310, 0.878, 0.816), 860, 290)
# C ICE
add_text("TEXT-3-ICE", "THEY\nWANT\nYOUR\nDATA", (1.0, 1.0, 1.0), 860, 120)

print(f"  layers: {len(image.get_layers())}")

# --- 5. SAVE XCF ---
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image,
               Gimp.File.new_for_path(OUT_XCF), None)
print(f"  SAVED: {OUT_XCF}")
