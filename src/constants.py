WALL_THICKNESS      = 100    # mm  (CBSW panel simplified plan thickness)
BAMBOO_POLE_R       = 35     # mm  (70 mm dia pole shown in plan)
GRID_BUBBLE_R       = 400    # mm
GRID_BUBBLE_OFFSET  = 1200   # mm  (gap between wall face and bubble center)
GRID_LINE_EXTEND    = 800    # mm  (grid line extension beyond bubble)
DIM_OFFSET          = 800    # mm  (first dimension line from wall face)
DIM_GAP             = 600    # mm  (gap between stacked dimension lines)
TEXT_HEIGHT         = 250    # mm  (room label text)
DOOR_HIDDEN_DASH    = True   # draw swing arc as hidden (dashed) line

# Standard CBFT door widths (mm)
DOOR_WIDTHS  = {"D1": 900, "D2": 800, "D3": 700}
# Standard CBFT window widths (mm)
WINDOW_WIDTHS = {"W1": 750, "W2": 1000, "W3": 500, "W4": 1200, "W5": 600}

# Layer names matching the reference drawing
L_WALL      = "A-WALL"
L_DOOR      = "A-DOOR"
L_WINDOW    = "A-WINDOW"
L_BAMBOO    = "A-BAMBOO POLE"
L_GRID      = "A-GRID"
L_GRIDLN    = "A-GRID-LN"
L_DIM       = "A-ANNO-DIMS"
L_TEXT      = "A-ANNO-TEXT"
L_HIDDEN    = "A-HIDD1"
L_CENTER    = "A-CENTER"
L_DEFPTS    = "Defpoints"
L_ANNOTEXT2 = "A-ANNO-TEXT2"
