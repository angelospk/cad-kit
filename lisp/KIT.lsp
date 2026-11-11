;;; KIT.lsp - parametrika koufomata / portes / pseudorofi
;;; ASCII only (no Greek letters) so that every CAD reads the file the same way.
;;; Works with AutoLISP in AutoCAD 2024+, AutoCAD LT 2024+, BricsCAD, ZWCAD, GstarCAD.
;;; Uses only entmake + basic AutoLISP. No vl-*, no (command ...).
;;;
;;; Load:  APPLOAD -> KIT.lsp     (or drag the file into the drawing window)
;;;
;;; Commands
;;;   KSYR    syromeno koufoma se katopsi, 2 / 3 / 4 fylla
;;;   KSYRM   syromena fylla mazemena sti gonia (to ena piso apo to allo)
;;;   KSYRX   syromena fylla xoneyta mesa ston toixo
;;;   KPAR    parathyro se katopsi
;;;   KPORTA  porta se opsi / anaptygma (platos x ypsos, me xerouli)
;;;   KPSEYD  pseudorofi se tomi (gypsosanida + anartiseis)
;;;   KPORTAK porta se katopsi, 1 i 2 fylla, me kasa stin akri i sti mesi
;;;   KSKALA  eythygrammi skala se katopsi me grammi anavasis
;;;   KTRAP   trapezaria me karekles gyro gyro
;;;   KRAGA   raga fotismou me spot
;;;   KLED    lentotainia
;;;   KSYND   kokkini diakekommeni syndesi fotistikon
;;;   KDAP    super hatch dapedou: plakaki (dineis megethos), TL01.., CN01, WD06
;;;   KXYLO   super hatch xylo se opoiadipote kleisti polyline
;;;   KOROFI  super hatch anopsis (xromata tou ypomnimatos)
;;;   KKLIMAKA klimaka ektyposis gia KLED / KSYND / KOROFI (25, 50, 100)
;;;   KITHELP lista entolon
;;;
;;; Every command builds a block for the size you give and inserts it on the
;;; CURRENT layer. Main lines are ByLayer. Thin lines use colour 252, dashed
;;; lines use colour 253, so the KIT ctb files plot them thin.
;;;
;;; Units: the drawing unit is the metre. For another unit change kit:u below
;;; (100.0 for centimetres, 1000.0 for millimetres).
;;;
;;; UCS: World, or a UCS rotated about Z. Not made for a tilted (3D) UCS.

(setq kit:u 1.0)

(if (null kit:tw) (setq kit:tw 0.25))   ; last wall thickness
(if (null kit:nf) (setq kit:nf 2))      ; last number of leaves
(if (null kit:dw) (setq kit:dw 0.90))   ; last door width
(if (null kit:dh) (setq kit:dh 2.20))   ; last door height
(if (null kit:ch) (setq kit:ch 0.30))   ; last ceiling drop
(if (null kit:pos) (setq kit:pos "Akri")) ; frame at the wall face or in the middle
(if (null kit:sc) (setq kit:sc 50))     ; plot scale 1:kit:sc for paper-sized things
(if (null kit:sw) (setq kit:sw 1.00))   ; last stair width
(if (null kit:sh) (setq kit:sh 3.00))   ; last stair height
(if (null kit:st) (setq kit:st 0.28))   ; last stair tread
(if (null kit:tl) (setq kit:tl 1.80))   ; last table length
(if (null kit:tb) (setq kit:tb 0.90))   ; last table width
(if (null kit:tx) (setq kit:tx 1.20))   ; last tile size along x
(if (null kit:ty) (setq kit:ty 1.20))   ; last tile size along y
(setq kit:yo 0.0)                       ; y offset of a frame inside the wall

;;; ------------------------------------------------------------------ helpers

;;; colour, linetype and lineweight of an entity. c = nil : colour ByLayer.
;;; Always written, so that an entity does not take the current colour,
;;; linetype or lineweight of the drawing.
(defun kit:col (c)
  (list (cons 62 (if c c 256)) '(6 . "ByLayer") '(370 . -1)))

(defun kit:ltype ()
  (if (null (tblsearch "LTYPE" "KIT_DASH"))
    (entmake
      (list '(0 . "LTYPE") '(100 . "AcDbSymbolTableRecord")
            '(100 . "AcDbLinetypeTableRecord") '(2 . "KIT_DASH") '(70 . 0)
            '(3 . "KIT dashed 10cm - 5cm") '(72 . 65) '(73 . 2) '(40 . 0.15)
            '(49 . 0.1) '(74 . 0) '(49 . -0.05) '(74 . 0))))
  (princ))

;;; kit:line, kit:dash and kit:rect add kit:yo to every y. The global kit:yo
;;; is 0.0; a frame definition binds its own local kit:yo (AutoLISP scope is
;;; dynamic), so the global value comes back even if the definition fails.
(defun kit:line (x1 y1 x2 y2 c)
  (entmake
    (append (list '(0 . "LINE") '(8 . "0")) (kit:col c)
            (list (list 10 x1 (+ y1 kit:yo) 0.0) (list 11 x2 (+ y2 kit:yo) 0.0)))))

(defun kit:dash (x1 y1 x2 y2)
  (entmake
    (list '(0 . "LINE") '(8 . "0") '(62 . 253) '(6 . "KIT_DASH") '(370 . -1)
          (list 10 x1 (+ y1 kit:yo) 0.0) (list 11 x2 (+ y2 kit:yo) 0.0))))

(defun kit:rect (x1 y1 x2 y2 c)
  (setq y1 (+ y1 kit:yo) y2 (+ y2 kit:yo))
  (entmake
    (append (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") '(8 . "0"))
            (kit:col c)
            (list '(100 . "AcDbPolyline") '(90 . 4) '(70 . 1)
                  (list 10 x1 y1) (list 10 x2 y1) (list 10 x2 y2)
                  (list 10 x1 y2)))))

;;; arc, angles in radians, counter-clockwise from a0 to a1
(defun kit:arc (x y r a0 a1 c)
  (if (< a0 0.0) (setq a0 (+ a0 (* 2.0 pi))))
  (if (< a1 0.0) (setq a1 (+ a1 (* 2.0 pi))))
  (entmake
    (append (list '(0 . "ARC") '(8 . "0")) (kit:col c)
            (list (list 10 x y 0.0) (cons 40 r) (cons 50 a0) (cons 51 a1)))))

;;; filled triangle (a SOLID with the last corner repeated), colour c
(defun kit:tri (x1 y1 x2 y2 x3 y3 c)
  (entmake
    (append (list '(0 . "SOLID") '(8 . "0")) (kit:col c)
            (list (list 10 x1 y1 0.0) (list 11 x2 y2 0.0)
                  (list 12 x3 y3 0.0) (list 13 x3 y3 0.0)))))

;;; filled rectangle, ACI colour c
(defun kit:box (x1 y1 x2 y2 c)
  (entmake
    (append (list '(0 . "SOLID") '(8 . "0")) (kit:col c)
            (list (list 10 x1 y1 0.0) (list 11 x2 y1 0.0)
                  (list 12 x1 y2 0.0) (list 13 x2 y2 0.0)))))

;;; y offset that centres a frame of depth d in a wall of thickness tw
(defun kit:mid-yo (mid d tw)
  (if (and mid (> tw (+ d 0.001))) (/ (- tw d) 2.0) 0.0))

(defun kit:circle (x y r c)
  (entmake
    (append (list '(0 . "CIRCLE") '(8 . "0")) (kit:col c)
            (list (list 10 x y 0.0) (cons 40 r)))))

;;; filled rectangle in a true colour (rgb = r*65536 + g*256 + b)
(defun kit:fill (x1 y1 x2 y2 rgb)
  (entmake
    (list '(0 . "SOLID") '(8 . "0") '(6 . "ByLayer") (cons 420 rgb)
          (list 10 x1 y1 0.0) (list 11 x2 y1 0.0)
          (list 12 x1 y2 0.0) (list 13 x2 y2 0.0))))

;;; thin line in a true colour, 0.05 mm
(defun kit:tline (x1 y1 x2 y2 rgb)
  (entmake
    (list '(0 . "LINE") '(8 . "0") '(6 . "ByLayer") '(370 . 5) (cons 420 rgb)
          (list 10 x1 y1 0.0) (list 11 x2 y2 0.0))))

(defun kit:blk-begin (name)
  (entmake (list '(0 . "BLOCK") (cons 2 name) '(70 . 0) '(10 0.0 0.0 0.0))))

(defun kit:blk-end ()
  (entmake '((0 . "ENDBLK"))))

;;; metres -> whole millimetres
(defun kit:mm (v)
  (fix (+ 0.5 (* 1000.0 v))))

;;; round to the millimetre. The block name holds millimetres, so the block
;;; is drawn with the same rounded size.
(defun kit:q (v)
  (/ (kit:mm v) 1000.0))

(defun kit:insert (name p ang)
  (entmake
    (list '(0 . "INSERT") (cons 2 name) (cons 10 p)
          (cons 41 kit:u) (cons 42 kit:u) (cons 43 kit:u) (cons 50 ang))))

;;; ------------------------------------------------- block definitions (metres)

;;; one sliding leaf from xa to xb, centred on yc
(defun kit:leaf (xa xb yc / h s)
  (setq h 0.02 s 0.05)
  (kit:rect xa (- yc h) xb (+ yc h) nil)
  (kit:line (+ xa s) (- yc h) (+ xa s) (+ yc h) nil)
  (kit:line (- xb s) (- yc h) (- xb s) (+ yc h) nil)
  (kit:line (+ xa s) yc (- xb s) yc 252))

;;; the two frame jambs and the line of the other wall face
(defun kit:jambs (len d tw / j)
  (setq j 0.05)
  (kit:rect 0.0 0.0 j d nil)
  (kit:rect (- len j) 0.0 len d nil)
  (if (> tw (+ d 0.001))
    (kit:line 0.0 (- tw kit:yo) len (- tw kit:yo) 252)))

;;; sliding frame, leaves closed. n = 2, 3 or 4
;;; mid = T : the frame sits in the middle of the wall thickness.
(defun kit:def-syr (name len n tw mid / j ov tp d w ll i xa trk kit:yo)
  (setq j 0.05 ov 0.06 tp 0.05)
  (if (= n 3) (setq d (* 3 tp)) (setq d (* 2 tp)))
  (setq kit:yo (kit:mid-yo mid d tw))
  (setq w (- len (* 2.0 j)))
  (kit:blk-begin name)
  (kit:jambs len d tw)
  (kit:line j 0.0 (- len j) 0.0 252)
  (kit:line j d (- len j) d 252)
  (if (= n 4)
    (progn
      (setq ll (/ (+ w (* 2.0 ov)) 4.0))
      (kit:leaf j (+ j ll) (* 0.5 tp))
      (kit:leaf (- (+ j ll) ov) (- (+ j ll ll) ov) (* 1.5 tp))
      (kit:leaf (- (+ j ll ll) ov) (- (+ j ll ll ll) ov) (* 1.5 tp))
      (kit:leaf (- len j ll) (- len j) (* 0.5 tp)))
    (progn
      (setq ll (/ (+ w (* (- n 1) ov)) (float n)) i 0)
      (while (< i n)
        (setq xa (+ j (* i (- ll ov))))
        (kit:leaf xa (+ xa ll) (* (+ i 0.5) tp))
        (setq i (1+ i)))))
  (kit:blk-end)
  name)

;;; leaves gathered at the start side, one behind the other.
;;; pocket = T : the leaves sit inside the wall, before the opening.
(defun kit:def-syrm (name len n tw pocket mid / j ov tp d w ll i x0 kit:yo)
  (setq j 0.05 ov 0.06 tp 0.05)
  (setq d (* n tp))
  (if (< d 0.1) (setq d 0.1))
  (setq kit:yo (kit:mid-yo mid d tw))
  (setq w (- len (* 2.0 j)))
  (setq ll (/ (+ w (* (- n 1) ov)) (float n)))
  (kit:ltype)
  (kit:blk-begin name)
  (kit:jambs len d tw)
  (if pocket
    (progn
      (setq x0 (- 0.0 ll))
      (kit:dash (- x0 0.02) 0.0 0.0 0.0)
      (kit:dash (- x0 0.02) d 0.0 d)
      (kit:dash (- x0 0.02) 0.0 (- x0 0.02) d)
      (kit:dash j 0.0 (- len j) 0.0)
      (kit:dash j d (- len j) d))
    (progn
      (setq x0 j)
      (kit:dash (+ j ll) 0.0 (- len j) 0.0)
      (kit:dash (+ j ll) d (- len j) d)
      (kit:line j 0.0 (+ j ll) 0.0 252)
      (kit:line j d (+ j ll) d 252)))
  (setq i 0)
  (while (< i n)
    (kit:leaf x0 (+ x0 ll) (* (+ i 0.5) tp))
    (setq i (1+ i)))
  (kit:blk-end)
  name)

;;; window in plan
(defun kit:def-par (name len tw mid / j d kit:yo)
  (setq j 0.05 d 0.07)
  (setq kit:yo (kit:mid-yo mid d tw))
  (kit:blk-begin name)
  (kit:jambs len d tw)
  (kit:line 0.0 0.0 j d 252)
  (kit:line 0.0 d j 0.0 252)
  (kit:line (- len j) 0.0 len d 252)
  (kit:line (- len j) d len 0.0 252)
  (kit:line j 0.0 (- len j) 0.0 nil)
  (kit:line j d (- len j) d nil)
  (kit:line j (- (* 0.5 d) 0.008) (- len j) (- (* 0.5 d) 0.008) 252)
  (kit:line j (+ (* 0.5 d) 0.008) (- len j) (+ (* 0.5 d) 0.008) 252)
  (kit:blk-end)
  name)

;;; mirror an x value when the hinges are on the right
(defun kit:mx (x w right)
  (if right (- w x) x))

;;; door in elevation. right = T : hinges on the right
(defun kit:def-porta (name w h right / k wood grain grain2 lh i s x ya yb xh xo xc)
  (setq k 0.05 wood 13482661 grain 9857088 grain2 11570280)
  (setq lh (- h k))
  (kit:ltype)
  (kit:blk-begin name)
  (kit:fill 0.0 0.0 w h wood)
  ;; wood grain: long thin lines in two tones, 1.2 to 3.2 cm apart, each
  ;; column broken into pieces of different length. Fixed pseudo-random
  ;; pattern, so the same size always gives the same door.
  (setq x (+ k 0.012) i 0 s 7)
  (while (< (+ x 0.005) (- w k))
    (setq ya 0.02)
    (while (< ya (- lh 0.1))
      (setq s (rem (+ (* s 73) 17) 101))
      (setq yb (+ ya 0.25 (* lh 0.45 (/ s 101.0))))
      (if (> yb (- lh 0.02)) (setq yb (- lh 0.02)))
      (kit:tline x ya x yb (if (= 0 (rem i 3)) grain2 grain))
      (setq s (rem (+ (* s 73) 17) 101))
      (setq ya (+ yb 0.03 (* 0.2 (/ s 101.0)))))
    (setq s (rem (+ (* s 73) 17) 101))
    (setq x (+ x 0.012 (* 0.02 (/ s 101.0))) i (1+ i)))
  (kit:rect 0.0 0.0 w h nil)
  (kit:line k 0.0 k lh nil)
  (kit:line (- w k) 0.0 (- w k) lh nil)
  (kit:line k lh (- w k) lh nil)
  ;; opening direction: dashed lines that meet on the hinge side
  (setq xh (kit:mx k w right) xo (kit:mx (- w k) w right))
  (kit:dash xo 0.0 xh (* 0.5 lh))
  (kit:dash xh (* 0.5 lh) xo lh)
  ;; lever handle and key
  (setq xc (kit:mx (- w k 0.07) w right))
  (kit:circle xc 1.0 0.025 nil)
  (kit:rect (kit:mx (- w k 0.07 0.13) w right) 0.99 xc 1.01 nil)
  (kit:circle xc 0.9 0.012 nil)
  (kit:blk-end)
  name)

;;; suspended ceiling in section. len along the board, h = drop to the slab
(defun kit:def-pseyd (name len h / n sp i x)
  (kit:blk-begin name)
  ;; double gypsum board
  (kit:line 0.0 0.0 len 0.0 nil)
  (kit:line 0.0 0.0125 len 0.0125 252)
  (kit:line 0.0 0.025 len 0.025 nil)
  (kit:line 0.0 0.0 0.0 0.025 nil)
  (kit:line len 0.0 len 0.025 nil)
  ;; perimeter profiles
  (kit:rect 0.0 0.025 0.03 0.052 252)
  (kit:rect (- len 0.03) 0.025 len 0.052 252)
  ;; hangers, about every 60 cm
  (setq n (fix (+ 0.5 (/ len 0.6))))
  (if (< n 1) (setq n 1))
  (setq sp (/ len (float n)) i 0)
  (while (< i n)
    (setq x (* sp (+ i 0.5)))
    (kit:rect (- x 0.03) 0.025 (+ x 0.03) 0.052 nil)
    (kit:rect (- x 0.015) 0.052 (+ x 0.015) 0.075 252)
    (if (>= h 0.1)
      (progn
        (kit:line (- x 0.004) 0.075 (- x 0.004) (- h 0.02) 252)
        (kit:line (+ x 0.004) 0.075 (+ x 0.004) (- h 0.02) 252)
        (kit:rect (- x 0.012) (- h 0.02) (+ x 0.012) h 252)))
    (setq i (1+ i)))
  (kit:blk-end)
  name)

;;; door in plan. n = 1 or 2 leaves, right = T : single leaf hinged on the
;;; right. mid = T : the frame sits in the middle of the wall, so the hinge
;;; is inside the wall and not at its corner. The leaf opens to -y, the side
;;; away from the wall.
(defun kit:def-portak (name w tw n right mid / j d lt lw x kit:yo)
  (setq j 0.05 lt 0.04)
  (setq d (if (> tw 0.1) 0.1 (if (> tw 0.0) tw 0.1)))
  (setq kit:yo (kit:mid-yo mid d tw))
  (kit:blk-begin name)
  (kit:jambs w d tw)
  (setq lw (- w j j))
  (if (= n 2)
    (progn
      (setq lw (/ lw 2.0))
      (kit:rect j (- 0.0 lw) (+ j lt) 0.0 nil)
      (kit:rect (- w j lt) (- 0.0 lw) (- w j) 0.0 nil)
      (kit:arc j kit:yo lw (* 1.5 pi) (* 2.0 pi) 252)
      (kit:arc (- w j) kit:yo lw pi (* 1.5 pi) 252))
    (if right
      (progn
        (kit:rect (- w j lt) (- 0.0 lw) (- w j) 0.0 nil)
        (kit:arc (- w j) kit:yo lw pi (* 1.5 pi) 252))
      (progn
        (kit:rect j (- 0.0 lw) (+ j lt) 0.0 nil)
        (kit:arc j kit:yo lw (* 1.5 pi) (* 2.0 pi) 252))))
  (kit:blk-end)
  name)

;;; straight stair in plan, going up along +x, width along +y.
;;; n risers, tread t: n - 1 treads, length (n - 1) * t.
;;; Walking line in the middle: a circle at the start, an arrow at the top.
(defun kit:def-skala (name w n t0 / len i ym)
  (setq len (* (- n 1) t0) ym (* 0.5 w))
  (kit:blk-begin name)
  (kit:rect 0.0 0.0 len w nil)
  (setq i 1)
  (while (< i (- n 1))
    (kit:line (* i t0) 0.0 (* i t0) w nil)
    (setq i (1+ i)))
  (kit:circle (* 0.5 t0) ym 0.04 nil)
  (kit:line (+ (* 0.5 t0) 0.04) ym (- len 0.12) ym nil)
  (kit:tri len ym (- len 0.12) (+ ym 0.045) (- len 0.12) (- ym 0.045) nil)
  (kit:blk-end)
  name)

;;; one chair, seat centre x y, the back towards angle a (radians).
;;; kind "R" round (as in the reference plans), "T" square.
(defun kit:chair (x y a kind / c s)
  (if (= kind "R")
    (progn
      (kit:circle x y 0.2 252)
      (kit:arc x y 0.25 (- a (* 0.6 pi)) (+ a (* 0.6 pi)) nil))
    (progn
      (setq c (cos a) s (sin a))
      ;; square seat 0.44 x 0.44 and a back 0.05 deep, rotated by a
      (kit:poly4 (list (list -0.22 -0.22) (list 0.22 -0.22) (list 0.22 0.22) (list -0.22 0.22)) x y c s 252)
      (kit:poly4 (list (list 0.17 -0.22) (list 0.24 -0.22) (list 0.24 0.22) (list 0.17 0.22)) x y c s nil))))

;;; closed polyline from local points, rotated (c s) and moved to x y
(defun kit:poly4 (pl x y c s col / data)
  (setq data nil)
  (foreach q pl
    (setq data (cons (list 10 (+ x (- (* c (car q)) (* s (cadr q))))
                              (+ y (+ (* s (car q)) (* c (cadr q))))) data)))
  (entmake
    (append (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") '(8 . "0"))
            (kit:col col)
            (list '(100 . "AcDbPolyline") (cons 90 (length pl)) '(70 . 1))
            (reverse data))))

(defun kit:def-karekla (name kind)
  (kit:blk-begin name)
  (kit:chair 0.0 0.0 (* 0.5 pi) kind)
  (kit:blk-end)
  name)

;;; dining table len x wid, centred on 0,0, chairs every 60 cm or more on
;;; the long sides, one at each end when ends = T.
(defun kit:def-trap (name len wid ends / m sp i x yo2)
  (setq m (fix (/ len 0.6)))
  (if (< m 1) (setq m 1))
  (setq sp (/ len (float m)) yo2 (+ (* 0.5 wid) 0.08))
  (kit:blk-begin name)
  (setq i 0)
  (while (< i m)
    (setq x (+ (* -0.5 len) (* sp (+ i 0.5))))
    (kit:chair x yo2 (* 0.5 pi) "R")
    (kit:chair x (- 0.0 yo2) (* 1.5 pi) "R")
    (setq i (1+ i)))
  (if ends
    (progn
      (kit:chair (+ (* 0.5 len) 0.08) 0.0 0.0 "R")
      (kit:chair (- (* -0.5 len) 0.08) 0.0 pi "R")))
  (kit:rect (* -0.5 len) (* -0.5 wid) (* 0.5 len) (* 0.5 wid) nil)
  (kit:blk-end)
  name)

;;; number of chairs of kit:def-trap
(defun kit:trap-chairs (len ends / m)
  (setq m (fix (/ len 0.6)))
  (if (< m 1) (setq m 1))
  (+ (* 2 m) (if ends 2 0)))

;;; lighting track of length len with n spots spaced evenly
(defun kit:def-raga (name len n / i x)
  (kit:blk-begin name)
  (kit:fill 0.0 -0.0175 len 0.0175 10033694)
  (setq i 0)
  (while (< i n)
    (setq x (* len (/ (+ i 0.5) n)))
    (kit:circle x 0.0 0.04 1)
    (kit:circle x 0.0 0.028 1)
    (kit:circle x 0.0 0.012 1)
    (setq i (1+ i)))
  (kit:blk-end)
  name)

;;; LED tape as in the reference legend: a thick red dash, then three thin
;;; ticks, repeated. Sizes in paper mm at 1:sc, so it reads the same on
;;; every sheet. len in metres.
(defun kit:def-led (name len sc / s hw dash gap x xe k tx)
  (setq s (/ sc 1000.0) hw (* 0.3 s) dash (* 4.0 s) gap (* 3.0 s))
  (kit:blk-begin name)
  (setq x 0.0)
  (while (< x len)
    (setq xe (+ x dash))
    (if (> xe len) (setq xe len))
    (kit:box x (- 0.0 hw) xe hw 1)
    (setq k 1)
    (while (< k 4)
      (setq tx (+ xe (* k 0.25 gap)))
      (if (< tx len)
        (entmake
          (list '(0 . "LINE") '(8 . "0") '(62 . 1) '(6 . "ByLayer") '(370 . 9)
                (list 10 tx (* -0.7 hw) 0.0) (list 11 tx (* 0.7 hw) 0.0))))
      (setq k (1+ k)))
    (setq x (+ xe gap)))
  (kit:blk-end)
  name)

;;; linetype of the red connection lines, in paper mm (2 mm dash, 1 mm gap)
(defun kit:ltype-synd ()
  (if (null (tblsearch "LTYPE" "KIT_SYND"))
    (entmake
      (list '(0 . "LTYPE") '(100 . "AcDbSymbolTableRecord")
            '(100 . "AcDbLinetypeTableRecord") '(2 . "KIT_SYND") '(70 . 0)
            '(3 . "KIT connection 2mm - 1mm") '(72 . 65) '(73 . 2) '(40 . 3.0)
            '(49 . 2.0) '(74 . 0) '(49 . -1.0) '(74 . 0))))
  (princ))

;;; ------------------------------------------------------------------ hatch

;;; vertices of a LWPOLYLINE entity list as (x y bulge)
(defun kit:pl-verts (ed / out)
  (setq out nil)
  (foreach it ed
    (cond
      ((= (car it) 10)
       (setq out (cons (list (cadr it) (caddr it) 0.0) out)))
      ((and (= (car it) 42) out)
       (setq out (cons (list (car (car out)) (cadr (car out)) (cdr it)) (cdr out))))))
  (reverse out))

;;; pattern line in drawing units. ang (degrees), base and offset are given
;;; as in a .pat file (offset along / across the line); org is the pattern
;;; origin and rot the pattern rotation, both in the drawing. Returns the
;;; angle in radians: AutoLISP uses radians for group codes 50 to 58.
(defun kit:pat-line (ang bx by dx dy dashes org rot / a c s cr sr)
  (setq a (+ (* pi (/ ang 180.0)) rot))
  (setq c (cos a) s (sin a) cr (cos rot) sr (sin rot))
  (list a
        (+ (car org) (- (* cr bx) (* sr by)))
        (+ (cadr org) (+ (* sr bx) (* cr by)))
        (- (* c dx) (* s dy))
        (+ (* s dx) (* c dy))
        dashes))

;;; HATCH on the current layer, one closed polyline boundary.
;;; lines = nil : solid fill. col = ACI colour, rgb = true colour or nil.
(defun kit:hatch (verts pname lines col rgb / bul data)
  (setq bul nil)
  (foreach v verts (if (/= (caddr v) 0.0) (setq bul T)))
  (setq data (list '(0 . "HATCH") '(100 . "AcDbEntity") (cons 62 col) '(6 . "ByLayer") '(370 . -1)))
  (if rgb (setq data (append data (list (cons 420 rgb)))))
  (setq data (append data
                     (list '(100 . "AcDbHatch") '(10 0.0 0.0 0.0) '(210 0.0 0.0 1.0)
                           (cons 2 pname) (cons 70 (if lines 0 1)) '(71 . 0)
                           '(91 . 1) '(92 . 3) (cons 72 (if bul 1 0)) '(73 . 1)
                           (cons 93 (length verts)))))
  (foreach v verts
    (setq data (append data (list (list 10 (car v) (cadr v)))))
    (if bul (setq data (append data (list (cons 42 (caddr v)))))))
  (setq data (append data (list '(97 . 0) '(75 . 0) (cons 76 (if lines 2 1)))))
  (if lines
    (progn
      (setq data (append data (list '(52 . 0.0) '(41 . 1.0) '(77 . 0) (cons 78 (length lines)))))
      (foreach l lines
        (setq data (append data
                           (list (cons 53 (nth 0 l)) (cons 43 (nth 1 l)) (cons 44 (nth 2 l))
                                 (cons 45 (nth 3 l)) (cons 46 (nth 4 l))
                                 (cons 79 (length (nth 5 l))))))
        (foreach d (nth 5 l) (setq data (append data (list (cons 49 d))))))))
  (setq data (append data (list '(98 . 1) (list 10 (car (car verts)) (cadr (car verts))))))
  (entmake data))

;;; copy of the boundary, closed, in a true colour and 0.50 mm
(defun kit:outline (verts rgb / data)
  (setq data (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") '(62 . 7) (cons 420 rgb)
                   '(6 . "ByLayer") '(370 . 50) '(100 . "AcDbPolyline")
                   (cons 90 (length verts)) '(70 . 1)))
  (foreach v verts
    (setq data (append data (list (list 10 (car v) (cadr v)) (cons 42 (caddr v))))))
  (entmake data))

;;; tile grid tx by ty
(defun kit:pat-tiles (tx ty org rot)
  (list (kit:pat-line 0.0 0.0 0.0 0.0 ty nil org rot)
        (kit:pat-line 90.0 0.0 0.0 0.0 tx nil org rot)))

;;; wood grain, lines along the local y axis: 4 families 10 cm apart, so a
;;; line every 2.5 cm, broken into long pieces of different length
(defun kit:pat-wood (org rot / u)
  (setq u kit:u)
  (list (kit:pat-line 90.0 0.0 0.0 (* u 0.37) (* u 0.1) (list (* u 0.62) (* u -0.11) (* u 0.29) (* u -0.07)) org rot)
        (kit:pat-line 90.0 (* u 0.026) (* u 0.2) (* u 0.53) (* u 0.1) (list (* u 0.41) (* u -0.09) (* u 0.83) (* u -0.05)) org rot)
        (kit:pat-line 90.0 (* u 0.049) (* u 0.5) (* u 0.29) (* u 0.1) (list (* u 1.1) (* u -0.2) (* u 0.17) (* u -0.06)) org rot)
        (kit:pat-line 90.0 (* u 0.077) (* u 0.8) (* u 0.71) (* u 0.1) (list (* u 0.33) (* u -0.04) (* u 0.55) (* u -0.13)) org rot)))

;;; deck boards 14.5 cm wide
(defun kit:pat-deck (org rot)
  (list (kit:pat-line 0.0 0.0 0.0 0.0 (* kit:u 0.145) nil org rot)))

;;; 45 degree lines 2.6 mm apart on paper
(defun kit:pat-diag (org rot)
  (list (kit:pat-line 45.0 0.0 0.0 0.0 (* kit:u (/ (* 2.6 kit:sc) 1000.0)) nil org rot)))

;;; asks for closed polylines until Enter. Returns a list of vertex lists.
(defun kit:pick-plines ( / done es ed out)
  (setq out nil)
  (while (not done)
    (setq es (entsel "\nDialekse kleisti polyline (Enter = telos): "))
    (if (null es)
      (setq done T)
      (progn
        (setq ed (entget (car es)))
        (cond
          ((not (and (= (cdr (assoc 0 ed)) "LWPOLYLINE")
                     (= 1 (logand 1 (cdr (assoc 70 ed))))))
           (princ "\nDen einai kleisti LWPOLYLINE (PEDIT / Close i BOUNDARY)."))
          ;; the hatch is made at elevation 0: refuse a raised polyline
          ((and (assoc 38 ed) (/= 0.0 (cdr (assoc 38 ed))))
           (princ "\nI polyline exei elevation: valte ti se 0 (PROPERTIES)."))
          (T (setq out (cons (kit:pl-verts ed) out)))))))
  (reverse out))

;;; origin and rotation of a pattern: picked origin (Enter = first vertex)
;;; and an optional direction point.
(defun kit:ask-origin (first / p q)
  (setq p (getpoint "\nSimeio arxis (origin) <proti koryfi>: "))
  (if p
    (progn
      (setq q (getpoint p "\nKateythynsi armon <orizontia>: "))
      (setq p (trans p 1 0))
      (list (list (car p) (cadr p))
            (if q (angle p (trans q 1 0)) (kit:ucs-angle))))
    (list (list (car first) (cadr first)) (kit:ucs-angle))))

;;; ------------------------------------------------------------------ input

;;; two picks -> (insertion point in WCS, angle, length in metres)
;;; The length is the plan length: a difference in Z between the picks is ignored.
(defun kit:two-points ( / p1 p2 a b)
  (setq p1 (getpoint "\nProto simeio (gonia anoigmatos): "))
  (if p1
    (setq p2 (getpoint p1 "\nDeytero simeio (alli gonia) i mikos: ")))
  (if (and p1 p2)
    (progn
      (setq a (trans p1 1 0) b (trans p2 1 0))
      (setq b (list (car b) (cadr b) (caddr a)))
      (if (> (distance a b) (* 0.2 kit:u))
        (list a (angle a b) (/ (distance a b) kit:u))
        (progn (princ "\nPoly mikro anoigma (kato apo 20 cm).") nil)))
    nil))

;;; angle of the UCS X axis in the WCS
(defun kit:ucs-angle ()
  (angle (trans '(0.0 0.0 0.0) 1 0) (trans '(1.0 0.0 0.0) 1 0)))

(defun kit:ask-tw ( / v)
  (initget 4)
  (setq v (getdist (strcat "\nPaxos toixou <" (rtos (* kit:tw kit:u) 2 2) ">: ")))
  (if v (setq kit:tw (kit:q (/ v kit:u))))
  kit:tw)

;;; frame position in the wall. Returns T for the middle.
(defun kit:ask-pos ( / v)
  (initget "Akri Mesi")
  (setq v (getkword (strcat "\nThesi sto paxos toixou [Akri/Mesi] <" kit:pos ">: ")))
  (if v (setq kit:pos v))
  (= kit:pos "Mesi"))

;;; "_M" for a frame in the middle of the wall
(defun kit:msuf (mid)
  (if mid "_M" ""))

;;; number of leaves. Asks again until the answer is inside lo..hi.
(defun kit:ask-n (lo hi / v ok)
  (if (< kit:nf lo) (setq kit:nf lo))
  (if (> kit:nf hi) (setq kit:nf hi))
  (while (not ok)
    (initget 6)
    (setq v (getint (strcat "\nArithmos fyllon (" (itoa lo) "-" (itoa hi) ") <"
                            (itoa kit:nf) ">: ")))
    (cond
      ((null v) (setq ok T))
      ((and (>= v lo) (<= v hi)) (setq kit:nf v ok T))
      (T (princ (strcat "\nDose arithmo apo " (itoa lo) " eos " (itoa hi) ".")))))
  kit:nf)

;;; T when every leaf is longer than its two 5 cm stiles.
;;; k = number of 6 cm overlaps between the leaves.
(defun kit:leaves-fit (len n k)
  (if (> (/ (+ (- len 0.1) (* k 0.06)) (float n)) 0.1001)
    T
    (progn
      (princ (strcat "\nPoly mikro anoigma gia " (itoa n) " fylla."))
      nil)))

;;; define the block when it does not exist yet, then insert it
(defun kit:place (name pa maker)
  (if (null (tblsearch "BLOCK" name)) (eval maker))
  (if (tblsearch "BLOCK" name)
    (progn
      (kit:insert name (car pa) (cadr pa))
      (princ (strcat "\nBlock: " name)))
    (princ (strcat "\nSFALMA: den dimiourgithike to block " name ".")))
  (princ))

;;; ------------------------------------------------------------------ commands

(defun c:KSYR ( / pa n tw mid len name)
  (setq n (kit:ask-n 2 4) tw (kit:ask-tw) mid (kit:ask-pos) pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "SYR" (itoa n) "_" (itoa (kit:mm len)) "_" (itoa (kit:mm tw)) (kit:msuf mid)))
      (if (kit:leaves-fit len n (if (= n 4) 2 (- n 1)))
        (kit:place name pa (list 'kit:def-syr name len n tw mid)))))
  (princ))

(defun c:KSYRM ( / pa n tw mid len name)
  (setq n (kit:ask-n 2 4) tw (kit:ask-tw) mid (kit:ask-pos) pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "SYRM" (itoa n) "_" (itoa (kit:mm len)) "_" (itoa (kit:mm tw)) (kit:msuf mid)))
      (if (kit:leaves-fit len n (- n 1))
        (kit:place name pa (list 'kit:def-syrm name len n tw nil mid)))))
  (princ))

(defun c:KSYRX ( / pa n tw mid len name)
  (setq n (kit:ask-n 1 3) tw (kit:ask-tw) mid (kit:ask-pos) pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "SYRX" (itoa n) "_" (itoa (kit:mm len)) "_" (itoa (kit:mm tw)) (kit:msuf mid)))
      (if (kit:leaves-fit len n (- n 1))
        (kit:place name pa (list 'kit:def-syrm name len n tw T mid)))))
  (princ))

(defun c:KPAR ( / pa tw mid len name)
  (setq tw (kit:ask-tw) mid (kit:ask-pos) pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "PAR_" (itoa (kit:mm len)) "_" (itoa (kit:mm tw)) (kit:msuf mid)))
      (kit:place name pa (list 'kit:def-par name len tw mid))))
  (princ))

(defun c:KPORTA ( / v w h side p name right)
  (initget 6)
  (setq v (getdist (strcat "\nPlatos portas <" (rtos (* kit:dw kit:u) 2 2) ">: ")))
  (setq w (if v (kit:q (/ v kit:u)) kit:dw))
  (initget 6)
  (setq v (getdist (strcat "\nYpsos portas <" (rtos (* kit:dh kit:u) 2 2) ">: ")))
  (setq h (if v (kit:q (/ v kit:u)) kit:dh))
  (initget "A D")
  (setq side (getkword "\nMentesedes [A=aristera / D=deksia] <A>: "))
  (setq right (= side "D"))
  (if (or (< w 0.4) (< h 1.2))
    (princ "\nPoly mikri porta (elaxisto 0.40 x 1.20).")
    (progn
      (setq kit:dw w kit:dh h)
      (setq p (getpoint "\nSimeio eisagogis (kato aristera, sto dapedo): "))
      (if p
        (progn
          (setq name (strcat "POR_" (itoa (kit:mm w)) "_" (itoa (kit:mm h))
                             (if right "_D" "_A")))
          (kit:place name (list (trans p 1 0) (kit:ucs-angle))
                     (list 'kit:def-porta name w h right))))))
  (princ))

(defun c:KPSEYD ( / v h pa len name)
  (initget 6)
  (setq v (getdist (strcat "\nYpsos kenou apo plaka <" (rtos (* kit:ch kit:u) 2 2) ">: ")))
  (setq h (if v (kit:q (/ v kit:u)) kit:ch))
  (if (< h 0.1)
    (princ "\nPoly mikro keno (elaxisto 10 cm).")
    (progn
      (setq kit:ch h)
      (setq pa (kit:two-points))
      (if pa
        (progn
          (setq len (/ (kit:mm (caddr pa)) 1000.0))
          (setq name (strcat "PSEYD_" (itoa (kit:mm len)) "_" (itoa (kit:mm h))))
          (kit:place name pa (list 'kit:def-pseyd name len h))))))
  (princ))

(defun c:KPORTAK ( / n tw mid side right pa len name)
  (initget "1 2")
  (setq n (getkword "\nFylla [1/2] <1>: "))
  (setq n (if (= n "2") 2 1))
  (setq tw (kit:ask-tw) mid (kit:ask-pos))
  (if (= n 1)
    (progn
      (initget "A D")
      (setq side (getkword "\nMentesedes [A=aristera / D=deksia] <A>: "))
      (setq right (= side "D"))))
  (setq pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (if (< len (if (= n 2) 0.6 0.4))
        (princ "\nPoly mikri porta (elaxisto 0.40, diplofylli 0.60).")
        (progn
          (setq name (strcat "PK" (itoa n) "_" (itoa (kit:mm len)) "_" (itoa (kit:mm tw))
                             (if (= n 2) "" (if right "_D" "_A")) (kit:msuf mid)))
          (kit:place name pa (list 'kit:def-portak name len tw n right mid))))))
  (princ))

(defun c:KSKALA ( / v w h t0 n r p1 p2 a b name)
  (initget 6)
  (setq v (getdist (strcat "\nPlatos skalas <" (rtos (* kit:sw kit:u) 2 2) ">: ")))
  (setq w (if v (kit:q (/ v kit:u)) kit:sw))
  (initget 6)
  (setq v (getdist (strcat "\nYpsos pou anevainei <" (rtos (* kit:sh kit:u) 2 2) ">: ")))
  (setq h (if v (kit:q (/ v kit:u)) kit:sh))
  (initget 6)
  (setq v (getdist (strcat "\nPatima <" (rtos (* kit:st kit:u) 2 3) ">: ")))
  (setq t0 (if v (kit:q (/ v kit:u)) kit:st))
  (setq n (fix (+ 0.5 (/ h 0.175))))
  (if (< n 2) (setq n 2))
  (setq r (/ h n))
  (setq kit:sw w kit:sh h kit:st t0)
  (princ (strcat "\n" (itoa n) " riktes x " (rtos (* 100.0 r) 2 1) " cm, "
                 (itoa (- n 1)) " patimata x " (rtos (* 100.0 t0) 2 1) " cm, mikos "
                 (rtos (* (- n 1) t0) 2 2) " m. 2r+p = " (rtos (* 100.0 (+ r r t0)) 2 1)
                 " cm (kalo 60-65)."))
  (setq p1 (getpoint "\nArxi skalas (gonia protou skalopatiou): "))
  (if p1
    (setq p2 (getpoint p1 "\nKateythynsi anavasis: ")))
  (if (and p1 p2)
    (progn
      (setq a (trans p1 1 0) b (trans p2 1 0))
      (setq name (strcat "SK_" (itoa (kit:mm w)) "_" (itoa n) "_" (itoa (kit:mm t0))))
      (kit:place name (list a (angle a b)) (list 'kit:def-skala name w n t0))))
  (princ))

(defun c:KTRAP ( / v len wid e ends p name)
  (initget 6)
  (setq v (getdist (strcat "\nMikos trapeziou <" (rtos (* kit:tl kit:u) 2 2) ">: ")))
  (setq len (if v (kit:q (/ v kit:u)) kit:tl))
  (initget 6)
  (setq v (getdist (strcat "\nPlatos trapeziou <" (rtos (* kit:tb kit:u) 2 2) ">: ")))
  (setq wid (if v (kit:q (/ v kit:u)) kit:tb))
  (initget "Nai Oxi")
  (setq e (getkword "\nKarekles stis akres [Nai/Oxi] <Nai>: "))
  (setq ends (/= e "Oxi"))
  (if (or (< len 0.6) (< wid 0.5))
    (princ "\nPoly mikro trapezi (elaxisto 0.60 x 0.50).")
    (progn
      (setq kit:tl len kit:tb wid)
      (princ (strcat "\n" (itoa (kit:trap-chairs len ends)) " karekles."))
      (setq p (getpoint "\nKentro trapeziou: "))
      (if p
        (progn
          (setq name (strcat "TRAP_" (itoa (kit:mm len)) "_" (itoa (kit:mm wid)) (if ends "" "_X")))
          (kit:place name (list (trans p 1 0) (kit:ucs-angle))
                     (list 'kit:def-trap name len wid ends))))))
  (princ))

(defun c:KRAGA ( / pa n len name)
  (initget 4)
  (setq n (getint "\nArithmos spot pano sti raga <0>: "))
  (if (null n) (setq n 0))
  (setq pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "RAGA_" (itoa (kit:mm len)) "_" (itoa n)))
      (kit:place name pa (list 'kit:def-raga name len n))))
  (princ))

(defun c:KLED ( / pa len name)
  (setq pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "LED_" (itoa (kit:mm len)) "_" (itoa kit:sc)))
      (kit:place name pa (list 'kit:def-led name len kit:sc))))
  (princ))

;;; red dashed line through the lights, picked one after the other
(defun c:KSYND ( / p q pts data)
  (kit:ltype-synd)
  (setq p (getpoint "\nProto fotistiko: "))
  (if p (setq pts (list (trans p 1 0))))
  (while p
    (setq q (getpoint p "\nEpomeno fotistiko (Enter = telos): "))
    (if q (setq pts (cons (trans q 1 0) pts)))
    (setq p q))
  (if (> (length pts) 1)
    (progn
      (setq data (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") '(62 . 1)
                       '(6 . "KIT_SYND") (cons 48 (* kit:u (/ kit:sc 1000.0))) '(370 . -1)
                       '(100 . "AcDbPolyline") (cons 90 (length pts)) '(70 . 0)))
      (foreach q (reverse pts)
        (setq data (append data (list (list 10 (car q) (cadr q))))))
      (entmake data)))
  (princ))

(defun c:KKLIMAKA ( / v ok)
  (while (not ok)
    (initget 6)
    (setq v (getint (strcat "\nKlimaka ektyposis 1: [25/50/100] <" (itoa kit:sc) ">: ")))
    (cond
      ((null v) (setq ok T))
      ((or (= v 25) (= v 50) (= v 100)) (setq kit:sc v ok T))
      (T (princ "\nDose 25, 50 i 100."))))
  (princ))

;;; floor finishes from the floor legend, or a tile of any size
(defun c:KDAP ( / k v tx ty bs org lines solid rgb col)
  (initget "Plakaki TL01 TL02 TL03 TL07 CN01 WD06")
  (setq k (getkword "\nDapedo [Plakaki/TL01/TL02/TL03/TL07/CN01/WD06] <Plakaki>: "))
  (if (null k) (setq k "Plakaki"))
  (cond
    ((= k "Plakaki")
     (initget 6)
     (setq v (getdist (strcat "\nPlakaki, mikos <" (rtos (* kit:tx kit:u) 2 2) ">: ")))
     (if v (setq kit:tx (/ v kit:u)))
     (initget 6)
     (setq v (getdist (strcat "\nPlakaki, platos <" (rtos (* kit:ty kit:u) 2 2) ">: ")))
     (if v (setq kit:ty (/ v kit:u)))
     (setq tx kit:tx ty kit:ty))
    ((= k "TL07") (setq tx 1.5 ty 0.75))
    ((or (= k "TL01") (= k "TL02") (= k "TL03")) (setq tx 1.2 ty 1.2)))
  (setq bs (kit:pick-plines))
  (if bs
    (progn
      (setq org (kit:ask-origin (car (car bs))))
      (foreach b bs
        (cond
          ((= k "CN01") (kit:hatch b "SOLID" nil 254 13158603))
          ((= k "WD06") (kit:hatch b "KIT_DECK" (kit:pat-deck (car org) (cadr org)) 9 nil))
          (T (kit:hatch b "KIT_TILE" (kit:pat-tiles (* tx kit:u) (* ty kit:u) (car org) (cadr org)) 9 nil))))))
  (princ))

;;; wood: a tan fill and a grain pattern
(defun c:KXYLO ( / bs org)
  (setq bs (kit:pick-plines))
  (if bs
    (progn
      (setq org (kit:ask-origin (car (car bs))))
      (foreach b bs
        (kit:hatch b "SOLID" nil 254 13482661)
        (kit:hatch b "KIT_WOOD" (kit:pat-wood (car org) (cadr org)) 254 9857088))))
  (princ))

;;; ceiling heights of the ceiling legend
(defun kit:ceiling-rgb (k)
  (cond ((= k "H220") 8040415) ((= k "H225") 9643919) ((= k "H240") 15886114)
        ((= k "H245") 21155) ((= k "EPIKL") 1346303) ((= k "H275") 16761876)))

(defun c:KOROFI ( / k bs rgb)
  (initget "H220 H225 H240 H245 EPIKL H275")
  (setq k (getkword "\nAnopsi [H220/H225/H240/H245/EPIKL/H275] <H220>: "))
  (if (null k) (setq k "H220"))
  (setq rgb (kit:ceiling-rgb k))
  (setq bs (kit:pick-plines))
  (foreach b bs
    (kit:hatch b "KIT_DIAG" (kit:pat-diag (list (car (car b)) (cadr (car b))) 0.0) 7 rgb)
    (kit:outline b rgb))
  (princ))

(defun c:KITHELP ()
  (princ "\nKIT: KSYR syromeno | KSYRM mazemena sti gonia | KSYRX xoneyta ston toixo")
  (princ "\n     KPAR parathyro | KPORTA porta se opsi | KPORTAK porta se katopsi")
  (princ "\n     KPSEYD pseudorofi | KSKALA skala | KTRAP trapezaria")
  (princ "\n     KRAGA raga | KLED lentotainia | KSYND syndesi fotistikon | KKLIMAKA")
  (princ "\n     KDAP dapedo | KXYLO xylo | KOROFI anopsi")
  (princ))

(princ "\nKIT.lsp fortothike. KITHELP = lista entolon.")
(princ)
