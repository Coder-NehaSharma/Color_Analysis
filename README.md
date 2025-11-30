# 4-Box Color Consistency System

A real-time computer vision application that analyzes video feeds to ensure color consistency across multiple samples. Designed for quality control in textile and manufacturing, it compares 4 distinct regions of interest (ROIs) and calculates color differences using the CIEDE2000 standard.

## Features

- **4-Box Analysis**: Simultaneously monitors 4 distinct regions in the video feed.
- **Reference vs. Sample**: Box 1 serves as the **Reference**. Boxes 2, 3, and 4 display a **Similarity Percentage** relative to the reference (100% = Perfect Match).
- **High Accuracy**:
    - **K-Means Clustering** (k=5) for dominant color extraction, ignoring noise and texture.
    - **Temporal Smoothing** (10-frame rolling average) for stable readings.
    - **CIEDE2000** (Delta E) for industry-standard color difference calculation.
- **Automated Pass/Fail**: Instantly flags samples that deviate beyond the set tolerance (Delta E > 2.0).
- **IP Camera Support**: Works with local webcams and network IP cameras (RTSP/HTTP).
- **Lighting Selection**: Tag readings with standard lighting conditions (D65, TL84, etc.).

## Installation & Running

### Option 1: Download Windows Executable 
If you are on Windows and just want to run the app:
1.  Go to the [Actions Tab](https://github.com/Coder-NehaSharma/Color_Analysis/actions).
2.  Click on the latest successful run.
3.  Scroll down to **Artifacts** and download **ColorAnalysis-Windows-Exe**.
4.  Unzip and run `ColorAnalysis.exe`.

### Option 2: Run from Source (Mac/Linux/Windows)
1.  Clone the repository:
    ```bash
    git clone https://github.com/Coder-NehaSharma/Color_Analysis.git
    cd Color_Analysis
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the application:
    ```bash
    python app.py
    ```
4.  Open your browser at `http://localhost:5000`.

## Usage Guide

1.  **Start the App**: Run the executable or python script.
2.  **Connect Camera**:
    *   **Local Webcam**: Leave the URL box empty and click **Start Analysis**.
    *   **IP Camera**: Enter your camera URL (e.g., `http://192.168.1.5:8080/video`) and click **Start Analysis**.
3.  **Place Samples**: Arrange your 4 cloth samples in the 4 quadrants of the camera view.
4.  **Analyze**:
    *   **Box 1** is your Reference.
    *   **Boxes 2-4** show how similar they are to Box 1.
    *   **Green Badge (PASS)**: All samples match.
    *   **Red Badge (FAIL)**: Significant color difference detected.

## Troubleshooting IP Camera
- Ensure your phone/camera and laptop are on the **same Wi-Fi network**.
- Verify the URL ends with `/video` or `/shot.jpg`.
- Check the console window for connection errors.

## Tech Stack
- **Backend**: Python, Flask, OpenCV, NumPy, Scikit-Learn, Scikit-Image.
- **Frontend**: HTML5, CSS3, JavaScript.
- **Build**: PyInstaller, GitHub Actions.
