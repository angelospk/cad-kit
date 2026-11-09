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

(defun kit:line (x1 y1 x2 y2 c)
  (entmake
    (append (list '(0 . "LINE") '(8 . "0")) (kit:col c)
            (list (list 10 x1 y1 0.0) (list 11 x2 y2 0.0)))))

(defun kit:dash (x1 y1 x2 y2)
  (entmake
    (list '(0 . "LINE") '(8 . "0") '(62 . 253) '(6 . "KIT_DASH") '(370 . -1)
          (list 10 x1 y1 0.0) (list 11 x2 y2 0.0))))

(defun kit:rect (x1 y1 x2 y2 c)
  (entmake
    (append (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") '(8 . "0"))
            (kit:col c)
            (list '(100 . "AcDbPolyline") '(90 . 4) '(70 . 1)
                  (list 10 x1 y1) (list 10 x2 y1) (list 10 x2 y2)
                  (list 10 x1 y2)))))

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
    (kit:line 0.0 tw len tw 252)))

;;; sliding frame, leaves closed. n = 2, 3 or 4
(defun kit:def-syr (name len n tw / j ov tp d w ll i xa trk)
  (setq j 0.05 ov 0.06 tp 0.05)
  (if (= n 3) (setq d (* 3 tp)) (setq d (* 2 tp)))
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
(defun kit:def-syrm (name len n tw pocket / j ov tp d w ll i x0)
  (setq j 0.05 ov 0.06 tp 0.05)
  (setq d (* n tp))
  (if (< d 0.1) (setq d 0.1))
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
(defun kit:def-par (name len tw / j d)
  (setq j 0.05 d 0.07)
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
(defun kit:def-porta (name w h right / k wood grain lh n i s r1 r2 x ya yb xh xo xc)
  (setq k 0.05 wood 13482661 grain 9857088)
  (setq lh (- h k))
  (kit:ltype)
  (kit:blk-begin name)
  (kit:fill 0.0 0.0 w h wood)
  ;; wood grain: thin vertical lines, fixed pseudo-random pattern
  (setq n (fix (/ (- w (* 2.0 k)) 0.03)) i 0 s 7)
  (while (< i n)
    (setq s (rem (+ (* s 73) 17) 101))
    (setq r1 (/ s 101.0))
    (setq s (rem (+ (* s 73) 17) 101))
    (setq r2 (/ s 101.0))
    (setq x (+ k 0.015 (* i 0.03)))
    (setq ya (* lh 0.6 r1))
    (setq yb (+ ya (* lh (+ 0.15 (* 0.25 r2)))))
    (if (< (+ x 0.01) (- w k))
      (kit:tline x ya x yb grain))
    (setq i (1+ i)))
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

(defun c:KSYR ( / pa n tw len name)
  (setq n (kit:ask-n 2 4) tw (kit:ask-tw) pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "SYR" (itoa n) "_" (itoa (kit:mm len)) "_" (itoa (kit:mm tw))))
      (if (kit:leaves-fit len n (if (= n 4) 2 (- n 1)))
        (kit:place name pa (list 'kit:def-syr name len n tw)))))
  (princ))

(defun c:KSYRM ( / pa n tw len name)
  (setq n (kit:ask-n 2 4) tw (kit:ask-tw) pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "SYRM" (itoa n) "_" (itoa (kit:mm len)) "_" (itoa (kit:mm tw))))
      (if (kit:leaves-fit len n (- n 1))
        (kit:place name pa (list 'kit:def-syrm name len n tw nil)))))
  (princ))

(defun c:KSYRX ( / pa n tw len name)
  (setq n (kit:ask-n 1 3) tw (kit:ask-tw) pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "SYRX" (itoa n) "_" (itoa (kit:mm len)) "_" (itoa (kit:mm tw))))
      (if (kit:leaves-fit len n (- n 1))
        (kit:place name pa (list 'kit:def-syrm name len n tw T)))))
  (princ))

(defun c:KPAR ( / pa tw len name)
  (setq tw (kit:ask-tw) pa (kit:two-points))
  (if pa
    (progn
      (setq len (/ (kit:mm (caddr pa)) 1000.0))
      (setq name (strcat "PAR_" (itoa (kit:mm len)) "_" (itoa (kit:mm tw))))
      (kit:place name pa (list 'kit:def-par name len tw))))
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

(defun c:KITHELP ()
  (princ "\nKIT: KSYR syromeno | KSYRM mazemena sti gonia | KSYRX xoneyta ston toixo")
  (princ "\n     KPAR parathyro | KPORTA porta se opsi | KPSEYD pseudorofi se tomi")
  (princ))

(princ "\nKIT.lsp fortothike. Entoles: KSYR KSYRM KSYRX KPAR KPORTA KPSEYD KITHELP")
(princ)
