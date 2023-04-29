import cv2
import numpy as np


SQUARE_TEMPLATE = [
    [1, 1, 1, 1],
    [1, 1, 1, 1],
    [1, 1, 1, 1],
    [1, 1, 1, 1],
]

RECTANGLE_TEMPLATE = [
    [0, 0, 0, 0],
    [1, 1, 1, 1],
    [1, 1, 1, 1],
    [0, 0, 0, 0],
]

TRIANGLE_TEMPLATE = [
    [0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0],
    [0, 0, 1, 1, 1, 0, 0],
    [0, 0, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1],
]

TEMPLATES = [("square", SQUARE_TEMPLATE), ("rectangle", RECTANGLE_TEMPLATE), ("triangle", TRIANGLE_TEMPLATE)]


RED_COLOR = ((0, 0, 255), np.array([0, 30, 20]), np.array([20, 255, 255]))
GREEN_COLOR = ((0, 255, 0), np.array([45, 30, 20]), np.array([70, 255, 255]))
BLUE_COLOR = ((255, 0, 0), np.array([110, 30, 20]), np.array([130, 255, 255]))
COLORS = [RED_COLOR, GREEN_COLOR, BLUE_COLOR]


def generate_mask(template, width, height):
    return cv2.inRange(cv2.resize(np.array(template).astype(float), (width, height)), 0.5, 1) / 255

def build_focused_rect(frame, start_point, end_point, color, border_width):
    return cv2.rectangle(frame, start_point, end_point, color, border_width)

def get_focused_hsv_frame(frame, start_point, end_point):
    return cv2.cvtColor(frame[start_point[1]:end_point[1], start_point[0]:end_point[0]], cv2.COLOR_BGR2HSV)

def get_not_white_mask(frame):
    return cv2.inRange(frame, np.array([0, 30, 0]), np.array([180, 255, 255])) / 255


def calc_corellation(frame, mask, width, height):
    return np.count_nonzero(frame == mask) / (width * height)

def calc_corellations(frame, templates, width, height):
    corellations = []
    for template in templates:
        corellations.append(calc_corellation(frame, generate_mask(template[1], width, height), width, height))
    return corellations


def calc_color_rates(frame, mask, colors):
    rates = []
    for color in colors:
        rates.append(np.count_nonzero(cv2.inRange(frame, color[1], color[2]) * mask) / np.count_nonzero(mask))
    return rates


def render(frame, left_border, top_border, focused_rect_size, color, border_width):
    start_point = (int(left_border), int(top_border))
    end_point = (int(left_border + focused_rect_size), int(top_border + focused_rect_size))

    #focused_rect = build_focused_rect(frame, start_point, end_point, color, border_width)
    
    focused_hsv_frame = get_focused_hsv_frame(frame, start_point, end_point)

    not_white_mask = get_not_white_mask(focused_hsv_frame)

    corellations = calc_corellations(not_white_mask, TEMPLATES, focused_rect_size, focused_rect_size)
    max_corellation = max(corellations)

    org = end_point
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 0.7

    text = "idk"
    if (max_corellation > 0.85):
        template_idx = corellations.index(max_corellation)
        text = TEMPLATES[template_idx][0]
        color_rates = calc_color_rates(focused_hsv_frame, generate_mask(TEMPLATES[template_idx][1], focused_rect_size, focused_rect_size), COLORS)
        max_color_rate = max(color_rates)
        if (max_color_rate > 0.85):
            color = COLORS[color_rates.index(max_color_rate)][0]

    focused_rect = build_focused_rect(frame, start_point, end_point, color, border_width)
    cv2.putText(focused_rect, text, org, font, fontScale, color, border_width, cv2.LINE_AA)

    return focused_rect



MOVE_STEP = 5
ZOOM_STEP = 10

left_border = 0
top_border = 0
focused_rect_size = 200
color = (0, 0, 0)
border_width = 2


def gstreamer_pipeline(
    capture_width=1280,
    capture_height=720,
    display_width=1280,
    display_height=720,
    framerate=30,
    flip_method=0,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink max-buffers=1 drop=true"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )


cap = cv2.VideoCapture(gstreamer_pipeline(flip_method=4), cv2.CAP_GSTREAMER)

while(cap.isOpened()):
    ret, frame = cap.read()

    processed = render(frame, left_border, top_border, focused_rect_size, color, border_width)

    cv2.imshow("cam", processed)

    k = cv2.waitKey(1) & 0xFF
    if (k == ord("e")):
        print ("bye-bye")
        break
    elif (k == ord("w")):
        if (top_border > MOVE_STEP):
            top_border -= MOVE_STEP
    elif (k == ord("s")):
        if (top_border < (frame.shape[0] - focused_rect_size - MOVE_STEP)):
            top_border += MOVE_STEP
    elif (k == ord("a")):
        if (left_border > MOVE_STEP):
            left_border -= MOVE_STEP
    elif (k == ord("d")):
        if (left_border < (frame.shape[1] - focused_rect_size - MOVE_STEP)):
            left_border += MOVE_STEP
    elif (k == ord("z")):
        focused_rect_size -= ZOOM_STEP
    elif (k == ord("x")):
        if (((left_border + focused_rect_size + ZOOM_STEP) <= frame.shape[1]) & ((top_border + focused_rect_size + ZOOM_STEP) <= frame.shape[0])):
            focused_rect_size += ZOOM_STEP