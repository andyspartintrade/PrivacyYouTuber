"""
GIMP 3 Python-Fu script: POSTER με layers
Canvas 1280x720, εικόνα ως layer + 4 text layers (editable)
Τρέχει: gimp-console-3.0.exe --batch-interpreter python-fu-eval -b "(exec(open(...).read()))"
"""
import os

W, H = 1280, 720
IMG_PATH = r"C:/Users/andys/privacy-yt/thumbnails/gemini/G2-POSTER.jpg"
OUT_XCF = r"C:/Users/andys/privacy-yt/thumbnails/gemini/POSTER-EDITABLE.xcf"
FONT = "SF Pro Display"

# --- 1. ΝΕΑ ΕΙΚΟΝΑ ---
image = gimp.Image(W, H, RGB)  # noqa: F821
gimp.Display(image)  # noqa: F821

# --- 2. BACKGROUND ---
bg = gimp.Layer(image, "BACKGROUND", W, H, RGB_IMAGE, 100, LAYER_MODE_NORMAL)  # noqa: F821
image.insert_layer(bg, None, 0)
gimp.context_set_foreground((0.05, 0.05, 0.07))  # noqa: F821
bg.edit_fill(FILL_FOREGROUND)  # noqa: F821

# --- 3. LAYER "IMAGE" (η original εικόνα) ---
img_layer = gimp.file_load_layer(RUN_NONINTERACTIVE, image, IMG_PATH)  # noqa: F821
image.insert_layer(img_layer, None, 0)
img_layer.name = "IMAGE"
# Τοποθέτηση: κέντρο οριζόντια, 0 από πάνω (θα την μετακινήσεις εσύ)
iw = img_layer.width
img_layer.set_offsets((W - iw) // 2, 0)

# --- 4. TEXT LAYERS (editable) ---
def add_text(name, text, color, xpos, ypos, size=68):
    layer = gimp.TextLayer(image, name, text, 0, size, FONT)  # noqa: F821
    image.insert_layer(layer, None, 0)
    layer.set_offsets(xpos, ypos)
    try:
        layer.color = color
    except Exception as e:
        print(f"  color err {name}: {e}")
    print(f"  + {name}")
    return layer

# TEXT-1-WARM (αμμώδες + παγωμένο λευκό)
add_text("TEXT-1-WARM", "THEY\nWANT", (1.0, 0.851, 0.627), 860, 120)
add_text("TEXT-1b-WARM-white", "YOUR\nDATA", (0.910, 0.957, 0.973), 860, 290)

# TEXT-2-POP (πορτοκαλί + cyan)
add_text("TEXT-2-POP-orange", "THEY\nWANT", (1.0, 0.702, 0.278), 860, 120)
add_text("TEXT-2b-POP-cyan", "YOUR\nDATA", (0.310, 0.878, 0.816), 860, 290)

# TEXT-3-ICE (λευκό)
add_text("TEXT-3-ICE", "THEY\nWANT\nYOUR\nDATA", (1.0, 1.0, 1.0), 860, 120)

print(f"\n  Layers: {len(image.list_layers())}")

# --- 5. ΑΠΟΘΗΚΕΥΣΗ XCF ---
image.save_as(OUT_XCF)  # noqa: F821
print(f"  SAVED: {OUT_XCF}")
gimp.quit()  # noqa: F821
