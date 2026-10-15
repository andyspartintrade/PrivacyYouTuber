; GIMP Script-Fu: POSTER με editable text layers
; Canvas 1280x720, εικόνα + 3 text layers
; Τρέχει headless: gimp-console-3.0.exe -b "(load ...)"

(let* (
  (W 1280)
  (H 720)
  (IMG-PATH "C:/Users/andys/privacy-yt/thumbnails/gemini/G2-POSTER.jpg")
  (OUT-PATH "C:/Users/andys/privacy-yt/thumbnails/gemini/POSTER-EDITABLE.xcf")
  (FONT "SF Pro Display")
)

  ; --- 1. ΝΕΑ ΕΙΚΟΝΑ 1280x720 ---
  (let* ((image (car (gimp-image-new W H RGB))))
    (gimp-image-set-active-layer image (car (gimp-image-get-active-drawable image)))

    ; --- 2. BACKGROUND LAYER (λευκό) ---
    (let* ((bg (car (gimp-layer-new image W H RGB-IMAGE "BACKGROUND" 100 LAYER-MODE-NORMAL))))
      (gimp-image-insert-layer image bg 0 -1)
      (gimp-image-set-active-layer image bg)
      (gimp-edit-fill bg FILL-FOREGROUND))

    ; --- 3. LAYER "IMAGE" (η original εικόνα) ---
    (let* ((img-layer (car (gimp-file-load-layer RUN-NONINTERACTIVE image IMG-PATH))))
      (gimp-image-insert-layer image img-layer 0 -1)
      (gimp-layer-set-name img-layer "IMAGE")
      ; Τοποθέτηση: κέντρο-οριζόντια, 60px από πάνω
      (gimp-layer-set-offsets img-layer (/ (- W (car (gimp-drawable-width img-layer))) 2) 40)
      (gimp-image-set-active-layer image img-layer))

    ; --- 4. TEXT LAYERS ---
    ; TEXT-1-WARM: THEY/WANT=warm cream, YOUR/DATA=ice white
    (let* ((t1 (car (gimp-text-layer-new image "THEY\nWANT\nYOUR\nDATA" FONT 68 UNIT-PIXEL))))
      (gimp-image-insert-layer image t1 0 -1)
      (gimp-layer-set-name t1 "TEXT-1-WARM")
      (gimp-text-layer-set-color t1 '(255 217 160))
      (gimp-layer-set-offsets t1 860 120))
    (let* ((t1b (car (gimp-text-layer-new image "THEY\nWANT\nYOUR\nDATA" FONT 68 UNIT-PIXEL))))
      (gimp-image-insert-layer image t1b 0 -1)
      (gimp-layer-set-name t1b "TEXT-1b-WARM-white"))

    ; TEXT-2-POP: orange + cyan
    (let* ((t2 (car (gimp-text-layer-new image "THEY\nWANT" FONT 68 UNIT-PIXEL))))
      (gimp-image-insert-layer image t2 0 -1)
      (gimp-layer-set-name t2 "TEXT-2-POP-orange")
      (gimp-text-layer-set-color t2 '(255 179 71))
      (gimp-layer-set-offsets t2 860 120))
    (let* ((t2b (car (gimp-text-layer-new image "YOUR\nDATA" FONT 68 UNIT-PIXEL))))
      (gimp-image-insert-layer image t2b 0 -1)
      (gimp-layer-set-name t2b "TEXT-2b-POP-cyan")
      (gimp-text-layer-set-color t2b '(79 224 208))
      (gimp-layer-set-offsets t2b 860 280))

    ; TEXT-3-ICE: όλα λευκά
    (let* ((t3 (car (gimp-text-layer-new image "THEY\nWANT\nYOUR\nDATA" FONT 68 UNIT-PIXEL))))
      (gimp-image-insert-layer image t3 0 -1)
      (gimp-layer-set-name t3 "TEXT-3-ICE")
      (gimp-text-layer-set-color t3 '(255 255 255))
      (gimp-layer-set-offsets t3 860 120))

    ; --- 5. SAVE XCF ---
    (gimp-image-flatten image)
    (file-xcf-save RUN-NONINTERACTIVE image (car (gimp-image-get-active-drawable image)) OUT-PATH OUT-PATH)
    (gimp-image-delete image)
    (gimp-quit 0)
  )
)
