import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request
import threading
import time
import itertools
from collections import deque
from sklearn.cluster import KMeans
from skimage.color import deltaE_ciede2000, rgb2lab

import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

app = Flask(__name__, 
            template_folder=resource_path('templates'), 
            static_folder=resource_path('static'))

# Global variables
# List of 4 dictionaries: {'rgb': (0,0,0), 'lab': (0,0,0), 'hex': '#000000'}
box_colors = [
    {'rgb': (0, 0, 0), 'lab': (0, 0, 0), 'hex': '#000000'},
    {'rgb': (0, 0, 0), 'lab': (0, 0, 0), 'hex': '#000000'},
    {'rgb': (0, 0, 0), 'lab': (0, 0, 0), 'hex': '#000000'},
    {'rgb': (0, 0, 0), 'lab': (0, 0, 0), 'hex': '#000000'}
]

# History for Temporal Smoothing (Rolling Average)
HISTORY_LEN = 10
box_histories = [deque(maxlen=HISTORY_LEN) for _ in range(4)]

# Lighting State
current_lighting = "D65"

status_message = "Ready"
max_delta_e = 0.0
pass_fail = "N/A"

lock = threading.Lock()
camera = None

# Constants
ROI_SIZE = 160  # boxes
CONSISTENCY_THRESHOLD = 2.0  # Max Delta E allowed between any pair

def get_dominant_color(roi):
    """
    Get dominant color using K-Means clustering.
    Filters out shadows, highlights, and low saturation pixels.
    """
    # Reshape to list of pixels
    pixels = roi.reshape((-1, 3))
    pixels = np.float32(pixels)
    
    # 1. Lightness Filter (Shadows/Highlights)
    sums = np.sum(pixels, axis=1)
    # Filter out dark (< 60 sum) and bright (> 700 sum)
    mask_lightness = (sums > 60) & (sums < 705)
    
    # 2. Saturation Filter (Washed out pixels)
    # Simple approx: Max(RGB) - Min(RGB) is roughly saturation
    max_vals = np.max(pixels, axis=1)
    min_vals = np.min(pixels, axis=1)
    saturation = max_vals - min_vals
    # Filter out low saturation (< 20)
    mask_saturation = saturation > 20
    
    # Combine masks
    mask = mask_lightness & mask_saturation
    filtered_pixels = pixels[mask]
    
    # Fallback if empty
    if len(filtered_pixels) == 0:
        filtered_pixels = pixels
    if len(filtered_pixels) == 0:
        return (0, 0, 0)

    # Use K-Means with k=5 for better separation
    try:
        kmeans = KMeans(n_clusters=5, n_init=3, random_state=42)
        kmeans.fit(filtered_pixels)
        
        centers = kmeans.cluster_centers_
        labels = kmeans.labels_
        
        unique, counts = np.unique(labels, return_counts=True)
        dominant_cluster_index = unique[np.argmax(counts)]
        
        dominant_color = centers[dominant_cluster_index]
        
        b, g, r = dominant_color
        return (r, g, b)
        
    except Exception as e:
        print(f"KMeans error: {e}")
        avg = np.mean(filtered_pixels, axis=0)
        b, g, r = avg
        return (r, g, b)

def rgb_to_lab_skimage(rgb):
    """Convert RGB tuple to Lab using skimage (D65 default)."""
    rgb_norm = np.array([[ [x/255.0 for x in rgb] ]])
    lab = rgb2lab(rgb_norm)
    return lab[0][0]

def calculate_delta_e_ciede2000(lab1, lab2):
    """Calculate CIEDE2000 distance between two Lab colors."""
    l1 = np.array(lab1, dtype=np.float64)
    l2 = np.array(lab2, dtype=np.float64)
    return deltaE_ciede2000(l1, l2)

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

class VideoCamera(object):
    def __init__(self, source=0):
        self.video = cv2.VideoCapture(source)
        if not self.video.isOpened():
             print(f"Error: Could not open video source {source}")
        
    def __del__(self):
        if self.video.isOpened():
            self.video.release()
    
    def get_frame(self):
        global box_colors, status_message, max_delta_e, pass_fail, box_histories
        
        if not self.video.isOpened():
            return None

        success, image = self.video.read()
        if not success:
            return None
            
        height, width, _ = image.shape
        
        # Define 4 ROIs (2x2 Grid)
        centers = [
            (int(width * 0.25), int(height * 0.25)), # Top-Left
            (int(width * 0.75), int(height * 0.25)), # Top-Right
            (int(width * 0.25), int(height * 0.75)), # Bottom-Left
            (int(width * 0.75), int(height * 0.75))  # Bottom-Right
        ]
        
        temp_colors = []
        
        for i, (cx, cy) in enumerate(centers):
            x1 = cx - ROI_SIZE // 2
            y1 = cy - ROI_SIZE // 2
            x2 = cx + ROI_SIZE // 2
            y2 = cy + ROI_SIZE // 2
            
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(width, x2), min(height, y2)
            
            roi = image[y1:y2, x1:x2]
            
            # Get raw dominant color
            raw_rgb = get_dominant_color(roi)
            
            # Add to history
            box_histories[i].append(raw_rgb)
            
            # Calculate Temporal Average
            history = np.array(box_histories[i])
            avg_rgb = np.mean(history, axis=0)
            
            # Use averaged RGB for final result
            final_rgb = tuple(avg_rgb)
            
            lab = rgb_to_lab_skimage(final_rgb)
            hex_val = rgb_to_hex(final_rgb)
            
            temp_colors.append({'rgb': final_rgb, 'lab': lab, 'hex': hex_val})
            
            # Draw ROI
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 4)
            cv2.putText(image, str(i+1), (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        with lock:
            box_colors = temp_colors
            
            # Calculate Consistency Groups
            indices = {0, 1, 2, 3}
            groups = []
            
            while indices:
                best_subset = []
                found = False
                for size in range(len(indices), 0, -1):
                    for subset in itertools.combinations(indices, size):
                        is_consistent = True
                        current_max_dE = 0.0
                        
                        if size > 1:
                            for i1, i2 in itertools.combinations(subset, 2):
                                dE = calculate_delta_e_ciede2000(box_colors[i1]['lab'], box_colors[i2]['lab'])
                                if dE > CONSISTENCY_THRESHOLD:
                                    is_consistent = False
                                    break
                                if dE > current_max_dE:
                                    current_max_dE = dE
                        
                        if is_consistent:
                            best_subset = list(subset)
                            found = True
                            break
                    if found:
                        break
                
                groups.append(best_subset)
                indices -= set(best_subset)

            # Determine Status Message
            pass_fail = f"{len(groups)} Group(s)"
            
            if len(groups) == 1:
                status_message = "All 4 Match (PASS)"
                pass_fail = "PASS"
            elif len(groups) == 4:
                status_message = "All Different"
                pass_fail = "FAIL"
            else:
                desc = []
                for g in groups:
                    g_str = "+".join([str(x+1) for x in g])
                    desc.append(f"[{g_str}]")
                status_message = "Similar: " + ", ".join(desc)
                pass_fail = "MIXED"

            # Update max_delta_e
            max_diff = 0.0
            labs = [c['lab'] for c in box_colors]
            for lab1, lab2 in itertools.combinations(labs, 2):
                diff = calculate_delta_e_ciede2000(lab1, lab2)
                if diff > max_diff:
                    max_diff = diff
            max_delta_e = max_diff

        # Draw Status on Frame
        color = (0, 255, 0) if pass_fail == "PASS" else (0, 0, 255)
        cv2.putText(image, f"Result: {pass_fail}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    global camera
    if camera is None:
        return "Camera not initialized", 500
    return Response(gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        else:
            break

@app.route('/api/status')
def get_status():
    with lock:
        # Calculate Similarity Percentages relative to Box 1
        similarities = []
        if box_colors:
            ref_lab = box_colors[0]['lab']
            for i, color in enumerate(box_colors):
                if i == 0:
                    similarities.append("Reference")
                else:
                    dE = calculate_delta_e_ciede2000(ref_lab, color['lab'])
                    # Formula: 100 - dE. Clamp at 0.
                    sim_percent = max(0, 100 - dE)
                    similarities.append(f"{sim_percent:.1f}%")
        else:
            similarities = ["--", "--", "--", "--"]

        return jsonify({
            'box_colors': [c['hex'] for c in box_colors],
            'similarities': similarities,
            'current_lighting': current_lighting,
            'max_delta_e': round(max_delta_e, 2),
            'pass_fail': pass_fail,
            'status_message': status_message
        })

@app.route('/api/set_lighting', methods=['POST'])
def set_lighting():
    global current_lighting
    data = request.json
    current_lighting = data.get('lighting', 'D65')
    return jsonify({'success': True, 'lighting': current_lighting})

@app.route('/api/set_camera', methods=['POST'])
def set_camera():
    global camera
    data = request.json
    url = data.get('url')
    
    if not url or url.strip() == '0':
        source = 0
    else:
        source = url
    
    if camera:
        del camera
    
    try:
        print(f"Attempting to connect to camera source: {source}")
        camera = VideoCamera(source)
        if not camera.video.isOpened():
            print(f"Failed to open video source: {source}")
            raise Exception(f"Could not open video source: {source}")
        print(f"Successfully connected to camera source: {source}")
        return jsonify({'success': True, 'message': f'Camera set to {source}'})
    except Exception as e:
        print(f"Error setting camera: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    # camera = VideoCamera(0) # Don't auto-start camera
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
